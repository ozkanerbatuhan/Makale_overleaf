# Hakem Raporu

**Makale:** An Ethernet-Enabled Customizable Neural Inference Framework on Low-Cost FPGA SoC for High-Frequency Trading
**Hedef dergi:** Journal of Systems Architecture (Elsevier, Q1)
**İnceleme kapsamı:** `main.tex` + `references.bib` + VHDL (`hft.srcs/sources_1/new/`) + Vitis firmware (`lwip_echo_server/src/`)
**Tarih:** 28 Temmuz 2026

---

## 0. Özet ve Tavsiye

**Tavsiye: Major Revision (mevcut haliyle reddedilme riski yüksek).**

Altta yatan mühendislik işi sağlam: 3 nöron/çevrim SIMD, 13 kademeli, tam pipeline'lanmış 192 çarpıcılı bir MAC dizisi, çalışan bir AXI-DMA/AXI-Stream veri yolu, gerçek donanım üzerinde osiloskopla ölçülmüş katman süreleri ve PS tarafında donanım sayacıyla (Global Timer) alınmış aşama bazlı gecikme dökümü. Bu, birçok "FPGA'da NN" makalesinden daha fazla gerçek ölçüm içeriyor.

Ancak makale bu haliyle JSA hakeminden geçmez. Üç kategoride sorun var:

1. **Metin ile kodun çeliştiği yerler** (argmax, feature preparation, runtime weight loading, "yeniden sentez gerekmez" iddiası). Hakem kodu görmese bile bunların bir kısmı metin içi tutarsızlıktan yakalanır.
2. **Ölçüm metodolojisinin savunulamaz olduğu yerler** (Ethernet "reception" ölçümünün ne olduğu, enstrümantasyon yükünün karakterize edilmemesi, p99'ların toplanması, iki farklı end-to-end sayısı).
3. **Bilimsel çerçevenin eksikliği** (3 kaynak, veri kümesi hiç tanımlanmamış, %61.7 doğruluk için taban çizgisi yok, adil bir yazılım karşılaştırması yok).

En kritik tek nokta aşağıda **M1**: sabit noktalı donanım ile Python Q8.8 referansı arasındaki eşleşmenin neden %100 değil %96.85 olduğu. Kodda muhtemel sebebi buldum ve aşağıda yazdım.

---

## MAJOR — Kabul için mutlaka giderilmeli

### M1. FPGA ile Python Q8.8 eşleşmesi neden %100 değil? (Tablo 6)

Tablo 6: *"Output match rate (Python Q8.8 vs FPGA) = %96.85 (159,447/164,627)"*, *"Max absolute output error = 1.374 (mean 0.335)"*.

İki taraf da **bit-exact sabit noktalı** aritmetik yapıyorsa bu oran %100 olmalıdır. %3.15 uyuşmazlık ve Q8.8 ölçeğinde 1.374 gibi büyük bir maksimum hata, ya bir dönüştürme farkına ya da bir donanım hatasına işaret eder. Makale bunu hiç tartışmıyor — hakem bunu ilk soracaktır ve tatmin edici cevap gelmezse "donanım doğrulanmamış" der.

**Kodda bulduğum muhtemel sebep** — `lwip_echo_server/src/mlp_weight_loader.h:9`:

```c
static inline int float_to_q88(float val) { return (int)(val * 256.0f); }
```

Bu **sıfıra doğru budama (truncation)**, yuvarlama değil. Python tarafındaki kuantizasyon neredeyse kesinlikle `np.round()` kullanıyor. Her ağırlıkta ortalama 0.5 LSB'lik sistematik bir sapma, 64 girişli bir MAC'te birikerek çıkışta tam da gözlenen mertebede fark üretir. Tek satırlık düzeltme:

```c
static inline int float_to_q88(float val) { return (int)lrintf(val * 256.0f); }
```

Ayrıca bu fonksiyonda **doygunluk (saturation) yok**: |val| > 127.996 olan bir ağırlık sessizce sarmalanır.

**Yapılması gereken:** Düzeltmeyi uygulayıp ölçümü tekrarlayın. Eşleşme %100'e (veya ~%99.9'a) çıkarsa bunu makalede *bit-exact doğrulama* olarak raporlayın — bu, makalenin en güçlü katkılarından biri olur. Çıkmazsa, kalan farkın kaynağını (doygunluk? ReLU sınırı? padding?) izole edip raporlayın. Her iki durumda da makaleye kısa bir "Fixed-point verification" alt bölümü ekleyin.

### M2. Argmax **donanımda değil, yazılımda** — Tablo 5 yanlış

Tablo 5 (`tab:hw_sw_partitioning`) "Argmax decision → PL (hardware)" diyor. Bölüm 3'te de "the PL implements the inference core, the argmax decision" ifadesi var.

Gerçekte VHDL'de argmax **yok**. `mlp_axi_wrapper.vhd` sadece `output_rd_data <= buf_A(addr)` sunuyor; LED bloğundaki `-- Simdilik sadece argmax sonucu goster` yorumu da bunu doğruluyor. Karar `main.c:177-189`'da PS yazılımında alınıyor:

```c
s16 out0 = mlp_read_reg(0x100); s16 out1 = ...; s16 out2 = ...;
u8 final_decision = 0;
if (out1 > out0 && out1 > out2) final_decision = 1; else if (...) ...
```

Dahası, bu üç AXI-Lite okuması **Tablo 10'daki 0.96 µs "Result readout"** kaleminin ta kendisi. Yani makalenin "donanımda" dediği karar aşaması, ölçülen gecikmenin gözle görülür bir kısmını oluşturan yazılım aşamasıdır.

**Yapılması gereken:** Ya Tablo 5'i ve ilgili cümleleri düzeltin (argmax = PS), ya da argmax'ı RTL'e taşıyın (12. kademeden sonra 3 elemanlı karşılaştırıcı — birkaç LUT). İkincisi hem daha dürüst hem de 0.96 µs'i tek okumaya indirdiği için makaleyi güçlendirir. Şiddetle ikincisini öneririm.

### M3. "Feature preparation" PS'te yapılmıyor

Makale boyunca (Abstract, Bölüm 3.1, Tablo 5, Tablo 10) PS'in "packet reception, feature preparation, and control" yaptığı söyleniyor. Kodda PS'in yaptığı tek şey (`main.c:152`):

```c
memcpy(inputs, payload + 4, 64 * sizeof(s16));
```

Host, **zaten Q8.8'e kuantize edilmiş, zaten 64'e sıfır-doldurulmuş** bir vektör gönderiyor. Yani öznitelik üretimi de, kuantizasyon da, padding de host PC'de yapılıyor. Bu, "Ethernet'ten piyasa verisi gelir → karar çıkar" anlatısını ciddi biçimde zayıflatır: sistem piyasa verisi değil, hazır öznitelik vektörü alıyor.

Ayrıca **128 baytlık bir `memcpy` için 0.70 µs** (667 MHz Cortex-A9'da ~470 çevrim) fizikî olarak açıklanamaz; bu değer büyük ölçüde iki `XTime_GetTime()` çağrısının kendi maliyetidir (bkz. M4).

**Yapılması gereken:** Ya gerçek öznitelik hesaplamasını (normalizasyon, kuantizasyon, pencereleme) PS'e taşıyın ve maliyetini ölçün, ya da makaleyi dürüstçe yeniden çerçeveleyin: "PS performs packet reception and buffer handoff; feature engineering and quantization are performed upstream on the host." Tablo 10'daki satırın adını da "packet parsing" olarak değiştirin.

### M4. Ölçüm enstrümantasyonu karakterize edilmemiş ve sonuçları kirletiyor

`main.c`'de `ENABLE_STAGE_TIMING 1` ile derlenmiş yolda:

- Kritik yola **5 adet 64-bit Global Timer okuması** ekleniyor (her biri hi/lo/hi retry döngüsü ile, `main.c:36-43`).
- **Yalnızca enstrümantasyon aktifken** çalışan ek bir meşgul bekleme var: `while (XAxiDma_Busy(&AxiDma, ...)) { }` (`main.c:165`). Bu, ölçümsüz yolda **olmayan** bir senkronizasyon noktasıdır.
- Yanıt paketi 1 bayt yerine **21 bayt** oluyor.

Yani Tablo 10'un ürediği koşum ile Tablo 8'in ürediği koşum farklı ikili dosyalardır. Bu, aşağıdaki M5'teki çelişkiyi de büyük olasılıkla açıklıyor.

**Yapılması gereken:** (a) Boş bir ölçüm çifti (`XTime_GetTime` → `XTime_GetTime`) ile timer okuma yükünü ölçüp raporlayın ve aşama değerlerinden çıkarın; (b) Enstrümantasyonlu ve enstrümantasyonsuz derlemelerin uçtan uca gecikmesini yan yana verin ki okuyucu gözlemci etkisini görsün; (c) Global Timer'ın çözünürlüğünü (CPU/2 ≈ 333.3 MHz → 3 ns) ve XPAR ile alınan gerçek frekansı makalede belirtin.

### M5. İki farklı uçtan uca gecikme, açıklanmadan yan yana duruyor

| Kaynak | Koşum boyutu | Ortalama | Medyan | p99 |
|---|---|---|---|---|
| Tablo 8 (`tab:latency_metrics`) | 120,883 | 65.6 µs | 66.3 µs | 79.6 µs |
| Tablo 10 (`tab:latency_breakdown`) | 1,004,229 | 68.56 µs | 68.50 µs | 80.92 µs |

Aynı büyüklük için iki farklı sayı veriliyor, aralarındaki ilişki hiç kurulmuyor. Hakem bunu "hangi sayıya inanacağız?" diye soracaktır. (Muhtemel cevap M4'te.)

**Yapılması gereken:** Tek bir referans koşum tanımlayın, diğerini açıkça farklı bir konfigürasyon olarak etiketleyin ve farkı açıklayın.

### M6. "Ethernet packet reception" ölçümü, iddia edilen şeyi ölçmüyor

Tablo 2 bunu *"PS-side NIC-to-buffer time"*, Tablo 10 *"Ethernet packet reception (EMAC + lwIP)"* olarak tanımlıyor. Kodda (`main.c:47`, `main.c:298`):

```c
static XTime g_t_poll;   /* taken in main loop right before xemacif_input */
...
XTime_GetTime(&g_t_poll);   // ana döngüde, her turda
...
XTime_GetTime(&t_cb);       // UDP callback'te
stg[0] = t_cb - g_t_poll;
```

Bu, "paketin geliş anından buffer'a yazılışına kadar geçen süre" **değildir**. Bu, *"ana döngünün son yoklamasından callback'e kadar geçen süre"*dir — yani paketin varış anının poll döngüsü fazına göre nereye düştüğüne bağlı bir artefakttır. Makale zaten "bimodal, reflecting the phase of the polling loop" diyerek bunu itiraf ediyor ama etiketi düzeltmiyor. 7.59 µs ortalama, EMAC/lwIP maliyeti olarak yorumlanamaz.

**Yapılması gereken:** Ya etiketi dürüstçe değiştirin ("polling-loop detection latency"), ya da gerçek alım süresini ölçün (PL'de bir GPIO/timestamp yakalayıcı, ya da EMAC RX kesmesinden itibaren zaman damgası). Bu düzeltilirse "board subtotal 14.4 µs" rakamı da değişecektir.

### M7. p99 değerlerinin toplanması istatistiksel olarak geçersiz

Tablo 10'da "Board subtotal p99 = 21.03" satırı, aşama p99'larının toplanmasıyla elde edilmiş görünüyor (14.18+0.86+3.78+1.72+0.97 = 21.51). Yüzdelikler toplanamaz; bir koşumdaki p99'ların hepsi aynı pakette gerçekleşmez. Bu satır ya paket-başına toplamların gerçek p99'u olarak yeniden hesaplanmalı (ham veriden yapılabilir, tüm aşamalar aynı pakette kaydediliyor), ya da kaldırılmalıdır. Aynı şey p50 satırı için de geçerli.

### M8. Adil bir yazılım karşılaştırması yok — makalenin merkezî iddiası desteksiz

Makale 768 ns'lik **çekirdek** gecikmesini, 66–476 µs'lik **uçtan uca ağ round-trip** ile karşılaştırıyor. Bunlar aynı şey değil; ikincisinin içinde host NIC, kablo, lwIP, PS yazılımı var. Bu karşılaştırma "FPGA çıkarımı CPU çıkarımından hızlıdır" iddiasını **kanıtlamaz**.

Ayrıca Bölüm 5.4'teki Linux-vs-Windows karşılaştırması bir *inference* taban çizgisi değil, bir *host ağ yığını* karşılaştırmasıdır. "Software Baseline: OS-Induced Latency" başlığı yanıltıcı.

**Gereken taban çizgileri (en az ikisi):**

1. Aynı 40-64-32-16-3 MLP'nin **PS'in kendi Cortex-A9'unda** (bare-metal, aynı Q8.8, NEON'lu ve NEON'suz) çıkarım süresi. Aynı çip, aynı model, aynı veri — en adil karşılaştırma budur.
2. Bir masaüstü CPU'da tek örneklik (batch=1) çıkarım süresi (NumPy/PyTorch/ONNX Runtime, hangisiyse belirtin).
3. **README'nizde zaten var ve makalede yok:** *"Original Sequential FSM Latency: ~56 µs over AXI-Lite"*. Bu mükemmel bir kendi-içinde taban çizgisidir: aynı takım, aynı kart, aynı model, seri FSM → 56 µs, paralel pipeline → 0.768 µs, **73×**. Bunu makaleye koymamak büyük bir kayıp. Ölçüm koşullarıyla birlikte ekleyin.

### M9. Veri kümesi ve sınıflandırma sonuçları raporlanmamış — %61.7 anlamsız

Makale şunların **hiçbirini** vermiyor:

- Veri kümesinin ne olduğu (enstrüman, borsa, dönem, örnekleme frekansı, kaynak)
- 40 özniteliğin ne olduğu (tek bir örnek bile yok)
- Etiketlemenin nasıl yapıldığı (BUY/HOLD/SELL eşikleri, horizon)
- Sınıf dağılımı
- Eğitim/doğrulama/test bölünmesi ve boyutları (yalnızca "164,627" bir tabloda geçiyor, tanımlanmadan)
- **Taban çizgisi doğruluk** (çoğunluk sınıfı tahmincisi)
- Karışıklık matrisi, sınıf bazlı precision/recall
- Herhangi bir işlem-anlamlı metrik (P&L, Sharpe, hit rate, ya da en azından makro-F1'in tam tablosu)

3-sınıflı, muhtemelen dengesiz bir problemde **%61.74 doğruluk, çoğunluk sınıfı taban çizgisinden ayırt edilemez olabilir.** Bu haliyle "the trained model" ifadesi boştur ve hakem "model hiçbir şey öğrenmemiş olabilir" diyecektir. Makalenin kuantizasyon iddiası (float ≈ Q8.8) da anlamını yitirir: iki model de aynı derecede işe yaramıyorsa aynı çıktıyı vermeleri sürpriz değildir.

**Yapılması gereken:** Tam bir "Dataset and Task" alt bölümü ekleyin. En azından çoğunluk-sınıfı ve rastgele taban çizgilerini, sınıf dağılımını ve karışıklık matrisini verin. Model tahmini gerçekten taban çizgisinin üstündeyse bunu açıkça gösterin; değilse makaleyi dürüstçe "the ML task is a placeholder to exercise the framework" diye çerçeveleyin (bu kabul edilebilir bir konumdur, gizlemek değildir).

### M10. Kaynakça 3 adet — JSA için tek başına ret sebebi

`references.bib` içinde yalnızca `Brown2021`, `Umuroglu2017`, `sparknoc` var; dosya hâlâ şablon yorumlarını taşıyor (*"Add your bibliographic entries here"*). Bir Elsevier Q1 dergisinde 3 kaynaklı bir "Related Work" bölümü editör masasında elenir.

**En az 25-35 kaynağa çıkarılmalı.** Kapsanması gereken başlıklar:

- FPGA tabanlı finansal hızlandırma / düşük gecikmeli ticaret (Lockwood ve ark. NetFPGA tabanlı trading, Leber/Geib/Litz FPGA algorithmic trading, Morris ve ark., Tang & Song, Denholm ve ark.)
- Sabit noktalı / düşük bit-genişlikli NN çıkarımı (Courbariaux, Jacob ve ark. quantization-aware training, Gholami quantization survey)
- FPGA NN framework'leri — burada rakipsiz değilsiniz: **hls4ml** (Duarte ve ark. 2018, JINST) doğrudan sizin sub-µs MLP nişinizde ve karşılaştırılmalı; FINN-R, Vitis-AI, DNNWeaver, Caffeine, Angel-Eye
- Zynq PS-PL veri yolu / AXI-DMA gecikme çalışmaları
- Ağ yığını ve OS jitter literatürü (kernel bypass, DPDK, solarflare/onload) — Bölüm 5.4'ün iddiasını desteklemek için
- Zaman serisi / limit order book tahmini (DeepLOB, Ntakaris ve ark. FI-2010 benchmark) — hem görev tanımı hem taban çizgisi için

**Özellikle hls4ml'i atlamayın.** Hakem kesinlikle soracaktır: "hls4ml zaten Q formatlı MLP'leri FPGA'da sub-µs çalıştırıyor; sizin farkınız ne?" Cevabınız hazır olmalı (cevap muhtemelen: hls4ml her model için yeniden sentez ister, sizinki ağırlıkları çalışma anında yükler — bu gerçek bir fark ve M11'de değinilmesi gereken).

### M11. "Yeniden sentez gerekmez" iddiası kodla çelişiyor (iki yönden)

Bölüm 5.9: *"one reconfigurable core hosts any model that fits the 192-DSP budget, without re-synthesis."*

Kod bunun **hem daha azını hem daha fazlasını** söylüyor:

**Daha azı — iddia fazla geniş.** `framework_pkg.vhd`'de derleme zamanı sabitleri:
```vhdl
constant MAX_INPUTS       : integer := 64;
constant MAX_NEURONS      : integer := 64;
constant NUM_LAYERS       : integer := 4;
constant PARALLEL_NEURONS : integer := 3;
```
`mlp_engine.vhd`'de `layer_idx : integer range 1 to 4`, dört ayrı `cfg_layerN_out` portu ve ping-pong parite mantığı katman sayısına sabit kodlu. Yani yeniden sentez olmadan desteklenen küme aslında: **en fazla 4 katman, her katman ≤64 nöron, her katman ≤64 giriş**. "192-DSP bütçesine sığan her model" değil. Bu dürüstçe yazılmalı.

**Daha fazlası — kendi katkınızı küçümsüyorsunuz.** Sonuç bölümü *"Future work includes runtime weight loading"* diyor. Oysa çalışma anı ağırlık yükleme **zaten uygulanmış**: `mlp_weight_loader.h` AXI-Lite üzerinden 192 BRAM'e ağırlık basıyor, RTL'de `w_wr_en/w_wr_bram/w_wr_addr` yolu ve `reg_update_flag` ile stream kilitleme mevcut, host GUI'de "model yükle (.bin)" paneli var (Şekil 5c). Bu doğrudan bir iç çelişki ve makalenin en özgün özelliğini gizliyor.

**Yapılması gereken:** Runtime weight loading'i **katkı olarak** öne çıkarın ve ölçün: bir modelin yüklenmesi kaç AXI-Lite yazması ve kaç ms sürüyor? (Kabaca (22+11+6+1)×3×64 ≈ 7,680 ağırlık + 120 bias yazması.) Bu sayı, "hls4ml'den farkımız nedir" sorusunun somut cevabıdır. Sonuç bölümündeki "future work" ifadesini kaldırın.

### M12. Mimarinin çalışma prensibi makalede eksik — sayılar yeniden üretilemez

Makale "192 parallel DSP-based MAC units in a 13-stage pipeline" diyor ama **çevrim başına 3 nöron işlendiğini hiç söylemiyor**. Bu olmadan Tablo 13'teki çevrim sayıları havadan gelmiş görünüyor.

RTL'den çıkan analitik model (`mlp_engine.vhd`, ST_ISSUE + ST_DRAIN_LAYER):

```
cycles(layer) = ceil(N_out / 3) + PIPELINE_DEPTH + 1,   PIPELINE_DEPTH = 13
```

| Katman | N_out | ceil(N/3) | + drain | Makaledeki ölçüm |
|---|---|---|---|---|
| L1 (40→64) | 64 | 22 | 35 | 35 (280 ns) ✔ |
| L2 (64→32) | 32 | 11 | 25 | 25 (200 ns) ✔ |
| L3 (32→16) | 16 | 6 | 20 | 20 (160 ns) ✔ |
| L4 (16→3)  | 3  | 1 | 15 | 15 (118 ns) ✔ |
| **Toplam** | | | **95** | 96 (768 ns) |

Ölçümler modelle mükemmel uyuşuyor — bu makalenin güçlü bir yanı ve **mutlaka bu formülle birlikte sunulmalı**. Ancak:

**(a) 768 vs 758 ns farkının açıklaması yanlış.** Makale diyor ki: *"the difference between the total and the sum of the layer times corresponds to the input-streaming and output-decision stages."* Bu doğru olamaz. `dbg_data_in_pulse` motorun ST_IDLE durumunda `start='1'` görüldüğünde atılıyor (`mlp_engine.vhd`) — yani **veri akışı zaten bitmişken**. Dolayısıyla 768 ns içinde input streaming **yok**. Fark aslında 1 çevrim (8 ns) + osiloskop okuma yuvarlaması (118 vs 120 ns). Bunu düzeltin.

**(b) Tablo 13'ün "Measured Cycles" sütunu ölçülmemiş, türetilmiş.** Süre × 125 MHz ile geri hesaplanmış. Başlığı "Derived cycles (t × f_clk)" yapın veya doğrudan bir sayaçla ölçün.

**(c) Kendi XDC'nizdeki sayılar makaleyle çelişiyor.** `zedboard_mlp.xdc:65-70` şunu diyor:
```
CH1 → JA1, CH2 → JA7 : Toplam PL Inference Gecikmesi (92 cycle = 736 ns)
Layer 1: 35 cycle (280 ns) | Layer 2: 24 cycle (192 ns)
Layer 3: 19 cycle (152 ns) | Layer 4: 14 cycle (112 ns)
```
Makale ise 96 / 25 / 20 / 15 diyor. İki artefakt arasında tutarsızlık var; birini düzeltin (analitik model makaleyi destekliyor, XDC yorumu 1 çevrim eksik sayıyor).

**(d) Boru hattı her katmanda tamamen boşaltılıyor** (`ST_DRAIN_LAYER` → `pipeline_empty`). Katman 4'te 15 çevrimin 13'ü saf drain. Toplam 95 çevrimin ~52'si drain. Bu, tasarımın gerçek bir özelliği ve makalede tartışılmalı: neden katmanlar arası örtüşme yapılmadı (cevap: ping-pong buffer'a yazma ile sonraki katmanın okuması arasındaki bağımlılık), ve bunun maliyeti ne? Dürüst tartışma makaleyi güçlendirir.

### M13. Verimlilik ve throughput hiç raporlanmamış

Makale hiçbir yerde GOP/s ya da çıkarım/saniye vermiyor — ama Tablo 1'de FINN'i "12.3 M cls./s" ve SparkNoC'u "337.2 GOP/s" ile listeliyor. Kendi işiniz için karşılaştırılabilir bir sütun yok; "Main Metric" sütunu elmalarla armutları karşılaştırıyor.

Hesaplanabilir değerler:

- **Tepe hesaplama gücü:** 192 çarpıcı × 2 op × 125 MHz = **48 GOP/s**
- **Faydalı MAC/çıkarım:** 40·64 + 64·32 + 32·16 + 16·3 = 5,168 MAC
- **Yayınlanan çarpma/çıkarım (padding dahil):** 7,680 → **padding verimliliği %67**
- **Ulaşılan hız:** 5,168 × 2 / 768 ns ≈ **13.5 GOP/s** → **tepe değerin %28'i**
- **Çekirdek throughput:** 1/768 ns ≈ **1.30 M çıkarım/s**
- **Sistem throughput (stream + wait dahil, wrapper FSM `ST_WAIT` nedeniyle örtüşme yok):** ~1/1.3 µs ≈ **0.77 M çıkarım/s**

Bu %28 verim (drain + padding kaynaklı) makalenin "fully unrolled, fully parallel" retoriğiyle çelişiyor. Sayıları verin ve nedenini açıklayın — hakem zaten hesaplayacak.

### M14. BRAM analizi yanıltıcı: darboğaz DSP değil, bellek organizasyonu

Makale: *"BRAM usage is 70.36%, leaving room for larger feature sets or networks."*

`mlp_engine.vhd` her (nöron-slotu × giriş) çifti için ayrı bir BRAM üretiyor:
```vhdl
gen_w_brams: for i in 0 to (PARALLEL_NEURONS * MAX_INPUTS) - 1 generate  -- 192 adet
```
Her biri 128×16 bit = 2 Kbit, yani bir RAMB18'in (18 Kbit) yalnızca **~%12'si** dolu. 192 RAMB18 ≈ 96 RAMB36 eşdeğeri + bias → 98.5. Yani **derinlik neredeyse bedava, ama BRAM *sayısı* `PARALLEL_NEURONS × MAX_INPUTS`'e kilitli.**

Sonuç: daha büyük öznitelik kümesi (>64 giriş) veya daha fazla paralel nöron istemek **doğrusal olarak daha fazla BRAM bloğu** ister ve 140'lık bütçeyi hemen aşar. Yani gerçek ölçeklenme sınırı DSP (%87) değil, BRAM blok sayısıdır — ve mevcut derinliğin %88'i boş. Makale bunun tam tersini ima ediyor.

**Yapılması gereken:** Bu analizi dürüstçe yazın ve bir çözüm önerin (birkaç girişi tek BRAM satırında paketlemek, ya da daha geniş BRAM konfigürasyonu kullanmak). Bu, makaleye gerçek bir mimari içgörü katar.

### M15. Güç değeri ölçüm değil, araç tahmini; karşılaştırma tabanı tutarsız

*"The implemented on-chip power is 2.781 W"* — bu Vivado'nun **tahmini** (`power_onchip.jpeg` bir Vivado ekran görüntüsü). Ölçülmüş güç değil, ve switching activity varsayımı (varsayılan %12.5 toggle rate mi, SAIF mi?) belirtilmemiş.

Ayrıca Tablo 14'te 2.78 W (PS7'nin 1.535 W'ı **dahil**) SparkNoC'un 7.6 W'ıyla karşılaştırılıyor — ama makale SparkNoC için "compute power" diyor. Farklı tabanlar. Kendi PL-only rakamınız (~1.25 W) karşılaştırma için doğru olan.

**Yapılması gereken:** "estimated" kelimesini ekleyin, vectorless/SAIF olduğunu belirtin, ideal olarak ZedBoard'un güç rayından (INA/shunt) gerçek ölçüm alın, ve karşılaştırmayı PL-only tabanında yapın.

### M16. Tablo 1 (Related Work) kendi aleyhinize kurulmuş

FINN satırı **0.31 µs** gösteriyor, sizinki "Sub-µs core latency" diyor — yani FINN sizden hızlı ve bu tabloda görünüyor ama hiç tartışılmıyor. Hakem bunu hemen yakalar.

Doğru çerçeve şu olmalı: FINN binarize edilmiş ağlar için, her model için yeniden sentez gerektiren, Ethernet'siz bir akıştır. Sizinki 16-bit doğrulukta, yeniden sentezsiz ağırlık değişimi yapan, ağ-bağlantılı bir sistemdir. Bunu tabloya ve metne açıkça yazın. Ayrıca hls4ml satırı ekleyin (M10).

Tablo 1'e ayrıca şu sütunlar eklenmeli: **Precision (bit)**, **Model değiştirmek için yeniden sentez gerekir mi**, **Throughput (inf/s)** — böylece karşılaştırma anlamlı olur.

---

## MINOR — Düzeltilmesi gereken ama ret sebebi olmayan

### m1. Şablon kalıntıları hâlâ metinde

- Bölüm 4.1: *"values known from the model study are filled, **the rest are to be completed**."* — Bu cümle gönderilecek metinde olamaz. Kaldırın.
- `main.tex:4-6` yorumları: *"DRAFT v1"*, *"TBD = data not yet available; to be filled by the authors."*
- `\todo{}` ve `\writinggap{}` komutları tanımlı; Acknowledgments bölümü `\writinggap[1.0cm]` ile boş bırakılmış.
- `references.bib` içindeki şablon yorumları ("Add your bibliographic entries here", "The Related Work table lists the references to be filled").

### m2. Zynq parça numarası hiçbir yerde yok

"Zynq-7000 SoC" 20 farklı parçayı kapsar. Kaynak sayılarından (53,200 LUT / 220 DSP / 140 BRAM) ve XDC dosyasından bunun **XC7Z020-1CLG484 / Digilent ZedBoard** olduğu anlaşılıyor. Speed grade ile birlikte açıkça yazın — timing closure iddiası speed grade olmadan doğrulanamaz.

### m3. PS'in bare-metal olduğu hiç söylenmemiş

Vitis projesi `lwip_echo_server` — kartta işletim sistemi yok, raw lwIP + bare-metal. Makale Bölüm 5.4'ü "OS-induced latency" üzerine kuruyor ve okuyucu kartta da bir OS olduğunu sanabilir. **Bu aslında lehinize:** kart tarafında OS jitter'ı yok, tüm jitter host tarafında. Bunu açıkça yazın (lwIP sürümü, raw API mi socket API mi, PS clock 666.67 MHz, cache konfigürasyonu).

### m4. PL saat frekansında belirsizlik

Block design PS7 konfigürasyonu `PCW_FPGA0_PERIPHERAL_FREQMHZ = 130.000000` istiyor; makale 125 MHz diyor; `mlp_tb.vhd` 10 ns periyot (100 MHz) kullanıyor; block design'daki reset bloğunun adı `rst_ps7_0_100M`. Muhtemelen gerçek FCLK 1000/8 = 125 MHz (130 istenip en yakın elde edilebilir değere yuvarlanmış) ve makale doğru — ama bunu Vivado'nun raporladığı **gerçek** FCLK ile teyit edip makalede belirtin. Osiloskop ölçümlerinin çevrime dönüşümü tamamen buna bağlı.

### m5. Fmax 127 MHz düşük — kritik yol raporlanmalı

Tam pipeline'lanmış DSP48E1'ler (A/B reg → M reg → P reg, kodda `in_reg`/`w_reg` → `mult_mreg` → `mult_preg`) -1 speed grade'de 400+ MHz'e çıkabilir. 127 MHz demek, kritik yol DSP'lerde değil demek — muhtemelen 40-bit toplayıcı ağacının ilk kademesi veya `current_inputs` için 64×16 bitlik 2:1 buffer mux'ı. Vivado'nun kritik yol raporunu verin ve neden 125 MHz'de kaldığınızı açıklayın. Bu, "daha yüksek saat = daha düşük gecikme" için doğal bir gelecek çalışma maddesi de sağlar.

### m6. DSP'ler MAC değil, sadece çarpıcı olarak kullanılıyor

Makale "192 parallel DSP-based **MAC** units" diyor. Kodda DSP48E1'in akümülatörü kullanılmıyor; toplama 64→1 LUT tabanlı bir toplayıcı ağacında yapılıyor (Stage 5-10). Donanım hakemi bunu yakalar. "192 DSP-based multipliers followed by a fabric adder tree" daha doğru — ve 14.5K LUT kullanımını da açıklar.

### m7. `convert.py` çalışmıyor ve akışla tutarsız

- Sabit kodlanmış Windows yolları: `r"d:\vivado projects\hft\..."` → yeniden üretilemez.
- Girdi dosyası `weight_rom.vhd` ve çıktı `weights_pkg.vhd` **depoda yok**.
- Ürettiği şey bir **derleme-zamanı VHDL paketi** — yani yeniden sentez gerektirir. Bu, makalenin "no re-synthesis" iddiasıyla ve fiilen kullanılan runtime AXI-Lite yükleme yoluyla (`mlp_weight_loader.h`) çelişiyor. Muhtemelen eski bir akış artığı.

Makale Tablo 4'te "Deployment flow: Automatic weight/bias memory regeneration" diyor ama bu akışın gerçek uygulaması depoda yok. Gerçek akışı (PyTorch → .bin → GUI → UDP → PS → AXI-Lite → BRAM) belgeleyin ve `convert.py`'ı ya güncelleyin ya kaldırın.

### m8. Simülasyon/doğrulama metodolojisi makalede yok

`mlp_tb.vhd` (148 satır) var ama makale hiç bahsetmiyor. RTL'in nasıl doğrulandığı (kaç test vektörü, altın referansa karşı bit-exact mi, kapsam) bir "Verification" alt bölümünde anlatılmalı. M1'in cevabı da büyük olasılıkla buradan çıkar.

### m9. Robustluk sorunları (bir "trading" sistemi için önemli)

`main.c`'de:
- `XAxiDma_SimpleTransfer` başarısız olursa (`status != XST_SUCCESS`) kod yine de `while ((mlp_read_reg(0x04) & 0x01) == 0)` döngüsüne giriyor → **sonsuz kilitlenme**. Timeout yok.
- `memcpy(inputs, payload + 4, 128)` doğrudan `p->payload` üzerinden; parçalanmış pbuf zincirinde `pbuf_copy_partial` kullanılmalı (kodda 111. satırda büyük paketlerin bölündüğü zaten not edilmiş).
- Paket doğrulama yok (sıra numarası, sağlama, tekrar tespiti).

Makale gecikme belirlenimciliği iddiasında bulunuyorsa, hata yollarının belirlenimliliği de ele alınmalı. En azından bir "Limitations" paragrafında belirtin.

### m10. AXI-Lite done-polling maliyeti gecikme atfını bozuyor

Tablo 10 "AXI-Stream receive + MLP core (PL) = 1.46 µs" diyor ve parantezde "core 768 ns" ekliyor. Kalan ~690 ns'nin ne olduğu söylenmiyor: bu, stream FSM'in ikişer çevrimde bir kelime alması (32 kelime × 2 çevrim = 512 ns, `mlp_axi_wrapper.vhd` ST_RCV_EVEN/ODD döngüsü) **artı** PS'in `mlp_read_reg(0x04)` ile yaptığı AXI-Lite yoklamasının granülaritesidir. Bunu ayrıştırıp yazın — çünkü stream'in 2 çevrimde 1 kelime alması düzeltilebilir bir tasarım kaybıdır (tek çevrimde alınabilir) ve iyi bir gelecek-çalışma maddesidir.

### m11. Sonuçlarda istatistiksel titizlik yok

Hiçbir yerde güven aralığı, tekrar sayısı, ya da koşumlar arası değişkenlik yok. Beş model için tek seed mi, beş seed mi belli değil. Doğruluk farkları (0.0164–0.2174 puan) çok küçük; bunların gürültüden ayırt edilebilir olduğunu göstermek için tekrarlı eğitim ve standart sapma gerekiyor.

### m12. Yazım / biçim

- **Yazar bloğu elsarticle formatında değil.** `\author{}` içine `\centering` ve `tabular` gömülmüş, "Advisor" etiketi manuel. Elsevier `\author[label]{Name}` + `\address[label]{}` + `\corref` yapısını ister. Mevcut haliyle üretim aşamasında geri döner. Ayrıca danışman muhtemelen yazar listesinde olmalı, ayrı bir "Advisor" satırı olarak değil.
- **E-posta muhtemelen hatalı:** `ahmet.ozakner@bilgiedu.net` — soyadı "Özkaner" ise `ozkaner` olmalı. Kontrol edin.
- `\renewcommand{\bfdefault}{\mddefault}` tüm kalın yazıyı devre dışı bırakıyor. Elsevier stilinin başlık/tablo tipografisini bozar; kaldırın.
- Her yerde `[H]` float konumlandırması kullanılmış; Elsevier `[t]`/`[htbp]` tercih eder ve iki sütunlu düzende `[H]` kötü sayfa kırılmaları üretir.
- **Vivado ekran görüntüleri figür olarak kabul edilmez.** `util_table.jpeg`, `power_onchip.jpeg`, `timing_setup.jpeg`, `model_comparison.jpeg` — hepsi araç ekran görüntüsü. JSA bunları vektör grafik veya tablo olarak yeniden çizmenizi isteyecektir. Ayrıca Tablo 12 ile Şekil 11 (util_table) **aynı veriyi iki kez** veriyor; birini silin. Aynı şey Tablo 6/Şekil 6 ve Tablo 13/Şekil 8 için de geçerli.
- Şekil 5 (host GUI) ekran görüntüsü olarak kalabilir ama araç sürümü/ölçek bilgisi eklenmeli.
- Abstract'ta "$\approx$0.2\%" deniyor; Tablo 7'de en büyük fark 0.2174 **yüzde puanı**. "percentage point" ile "percent" ayrımını her yerde netleştirin.

### m13. Reproducibility beyanı yok

JSA giderek kod/veri erişilebilirliği bekliyor. VHDL, Vitis firmware, host GUI ve dönüştürme betikleri elinizde — bir "Code and Data Availability" bölümü ile GitHub/Zenodo DOI'si ekleyin. Bu, M1/M9'daki güven sorunlarını da kısmen telafi eder.

### m14. Ünvan/etik notları

- Anahtar kelimeler iyi; ancak "Framework" iddiası M11'de daraltıldıktan sonra başlıktaki "Customizable ... Framework" ifadesinin hâlâ savunulabilir olduğundan emin olun.
- HFT bağlamında finansal tavsiye/performans iması yapmayın; makale şu an bunu yapmıyor, iyi. Ancak M9'da bir P&L metriği eklerseniz, backtest sınırlamalarını (slippage, transaction cost, look-ahead bias) mutlaka belirtin.

---

## Öncelik Sırası (yazar için eylem planı)

**Blocker — bunlar olmadan göndermeyin:**

1. **M10** — Kaynakçayı 25-35'e çıkarın, hls4ml'i mutlaka ekleyin ve karşılaştırın.
2. **M9** — Veri kümesi + taban çizgisi + karışıklık matrisi bölümü yazın.
3. **M1** — `float_to_q88`'i round'a çevirin, ölçümü tekrarlayın, %96.85'i açıklayın.
4. **M2, M3, M11** — Metin-kod çelişkilerini giderin (argmax, feature prep, runtime weight loading, "no re-synthesis").
5. **m1** — Tüm şablon kalıntılarını temizleyin.

**Yüksek etki, orta efor:**

6. **M8** — README'deki 56 µs seri FSM taban çizgisini + PS Cortex-A9 yazılım çıkarımını ekleyin. Bu tek başına makalenin en güçlü sonucu olur (73×).
7. **M12** — Analitik çevrim modelini (`ceil(N/3) + 14`) makaleye koyun; 768/758 açıklamasını düzeltin; XDC-makale tutarsızlığını giderin.
8. **M13, M14** — Throughput/GOP-s ve BRAM organizasyonu analizini ekleyin.
9. **M4, M5, M6, M7** — Ölçüm metodolojisini temizleyin ve tek bir referans koşum tanımlayın.

**Cila:**

10. **M15, M16, m2-m14** — Güç etiketi, Tablo 1'in yeniden kurgusu, parça numarası, elsarticle formatı, figürlerin yeniden çizimi, availability beyanı.

---

## Kapanış Notu

Makalenin çekirdeği gerçek ve savunulabilir: 40-64-32-16-3 bir MLP'yi 96 çevrimde, ölçülmüş 768 ns'de, ~1.25 W PL gücüyle, 200 dolarlık bir kartta çalıştırıyorsunuz — ve bunu osiloskopla, analitik modelle birebir uyuşan biçimde kanıtlıyorsunuz. Bu iyi bir sonuç.

Sorun sunumda: makale, **kanıtlayabildiğinden fazlasını iddia ediyor** (argmax donanımda, PS öznitelik hazırlıyor, yeniden sentez gerekmez, "any model") ve **kanıtlayabildiği bazı şeyleri iddia etmiyor** (73× seri-FSM hızlanması, runtime ağırlık yükleme, analitik gecikme modeli, bit-exact doğrulama potansiyeli). İddiaları koda hizalayın ve eksik bilimsel çerçeveyi (literatür, veri kümesi, taban çizgi) tamamlayın — o zaman bu makale JSA'da yayınlanabilir bir çalışma olur.
