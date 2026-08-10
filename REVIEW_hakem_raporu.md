# Hakem Raporu — v2 (kod incelemesi + ampirik doğrulama sonrası)

**Makale:** An Ethernet-Enabled Customizable Neural Inference Framework on Low-Cost FPGA SoC for High-Frequency Trading
**Hedef:** Journal of Systems Architecture (Elsevier, Q1)
**Kapsam:** `main.tex`, `references.bib`, VHDL (`hft.srcs/sources_1/new/`), Vitis firmware (`lwip_echo_server/src/`), host araçları (`pc_test/`)
**Kısıt:** RTL değişikliği yok, yeni ölçüm tercihen yok
**Tarih:** 28 Temmuz 2026

> **v1'den farkı:** v1'deki M1 (yuvarlama hatası) ve M7 (p99 toplama) teşhisleri **yanlış çıktı**, geri çekildi. Kök neden ampirik olarak saptandı ve aşağıda K1'de. Gecikme sonuçlarının ham logdan yeniden üretilebildiği doğrulandı.

---

## 0. Yönetici Özeti

Makale iki yarıya ayrılıyor ve bu iki yarının durumu birbirinden tamamen farklı:

**Donanım yarısı sağlam ve savunulabilir.** Gecikme, timing, kaynak ve güç sonuçlarının hepsini bağımsız olarak doğruladım. Tablo 10'un tüm hücrelerini 1,004,229 satırlık ham logdan yeniden hesapladım — birebir tutuyor. RTL'den türettiğim analitik çevrim modeli osiloskop ölçümleriyle dört katmanda da birebir uyuşuyor. Bu kısım yayınlanabilir.

**ML yarısı desteklenmiyor.** Öznitelik boru hattında normalizasyon yok; karta giden vektör 64 elemanın 63'ü sıfır, biri taşma artefaktı. Tablo 6 ve Tablo 7 mevcut dosyalardan yeniden üretilemiyor. Bu haliyle Bölüm 5.2 ve abstract'taki doğruluk iddiaları savunulamaz.

**Tavsiye:** Makaleyi donanım/gecikme/framework makalesine daraltın ve doğruluk iddialarını çıkarın. Bu, sıfır kart zamanı ve sıfır RTL değişikliğiyle mümkün. İsteğe bağlı olarak ~1 saatlik kısa bir tezgâh koşumu, "bit-exact doğrulanmış" iddiasını geri kazandırır (bkz. Bölüm 3, Yol B).

---

## 1. Kök Neden Analizi

### K1. Öznitelik boru hattında normalizasyon yok — tek kök neden

Zincirin tamamı ampirik olarak izlendi:

**(a) Eğitim verisi normalize edilmemiş.** `pc_test/data_prep_binance.py` 40 özniteliği doğru üretiyor (son 20 işlem × fiyat/miktar) ama normalizasyon yorum satırında:

```python
# Normalizasyon veya Scaling gerekliyse buraya eklenebilir.
# Orn: feature_df = (feature_df - feature_df.mean()) / feature_df.std()
```

Sonuç: ham BTC fiyatı (~76,834) ile işlem miktarı (~0.00065) aynı vektörde, aralarında ~10⁸ kat ölçek farkı var.

**(b) Bunun izi eğitilmiş ağırlıklarda görünüyor.** `best_model_32_16_8_t00005.pth` içindeki W1 (32×40) matrisinde:

```
Öznitelik  0–18 :  ağırlıkların ~%88'i tam olarak ±0.25'te  (clamp sınırı)
Öznitelik 19–39 :  ~%0                                      (normal, iç bölgede)
```

Keskin bir sınır. 1. katmanın %42'si doymuş durumda ve doygunluk tamamen ilk 19 öznitelikte yoğunlaşmış. Ardışık aggTrades satırlarında fiyatın neredeyse hiç değişmemesi (`76834.36, 76834.36, 76834.36`) ile birebir tutarlı.

Modeller **rastgele değil, gerçekten eğitilmiş** (kırpılmamış değerlerin dağılımı çan eğrisi, satır normları tutarlı) — ama birinci katmanları normalize edilmemiş girdi yüzünden clamp'e dayanmış.

**(c) Çıkarımda ikinci bir taşma.** `linux/hft_engine_linux.cpp:99`:

```cpp
q88_features.push_back(static_cast<int16_t>(val * 256.0f));
if (q88_features.size() < 64) q88_features.resize(64, 0);
```

Doygunluk yok, sessiz sarmalanma var. Koşumda kullanılan `temp_stream_converted.csv` ham aggTrades dosyası (hazırlanmış 40-öznitelik dosyası değil), 8 sütunlu:

```
ham   : 3960683683, 76834.36, 0.00065, 6308590618, 6308590618, 1779235200183703, False, True
Q8.8  : [0, 8796, 0, 0, 0, 0, 0, ... 0]        (58'i sıfır dolgu)
```

- `agg_trade_id`, `first/last_trade_id`, `timestamp` → ×256 int32'yi aşıyor → **0**
- `quantity` 0.00065 × 256 = 0.166 → budanıyor → **0**
- `price` 76834.36 × 256 = 19,669,596 → int16'ya sarmalanıyor → **8796** = `price mod 256`

Tek canlı öznitelik, fiyatın 256'ya modu — testere dişi, kesintili, ve fiyat sabitken sabit.

Not: Q8.8'in aralığı ±127.996. Hazırlanmış 40-öznitelik dosyası kullanılsaydı bile BTC fiyatı aralığın **600 katı** dışında kalacağı için aynı taşma yaşanırdı. Yani sorun dosya seçimi değil, ölçekleme.

**(d) Sonuç FPGA logunda:**

```
HOLD   917,781   91.39%
BUY     67,065    6.68%
SELL    19,383    1.93%
```

### K2. Tablo 6 mevcut dosyalardan yeniden üretilemiyor

`quantization_analysis.py`'ı diskteki tüm modeller × her iki etiket eşlemesi için (8 kombinasyon) 40,000 paket üzerinde koşturdum:

| Model | Eşleme | Match | Emülatör dağılımı |
|---|---|---|---|
| `linux/best_model_new` | legacy | **91.41%** | [40000, 0, 0] — hepsine aynı sınıf |
| `best_model_new` | legacy | 52.92% | [21837, 18163, 0] |
| `best_model_64_64_32` | fixed | 48.17% | [266, 19576, 20158] |
| `best_model_32_16_8` | fixed | 47.88% | [474, 19439, 20087] |
| `best_model_10_16_8` | fixed | 47.34% | [913, 19210, 19877] |
| `temp_weights.bin` (=32_16_8) | legacy | 5.95% | [2023, 63900, 54077] |

Hiçbiri makaledeki %96.85'i vermiyor. En yüksek değer olan %91.41, **her girdiye aynı sınıfı veren dejenere bir modelden** geliyor ve logun HOLD oranı (%91.39) ile çakışmasından ibaret — eşleşme değil.

**Logu üreten model/veri kombinasyonu diskte mevcut değil.** `pc_test/yapılacaklar.txt` de logun karışık olduğunu not ediyor ("eski + bugünkü permütasyonlu etiketli satırlar var").

Ayrıca `quantization_analysis.py`'ın başlığındaki not, host motorunda bir **sınıf permütasyon hatası** olduğunu belgeliyor (2026-07-12 öncesi motorlar `0→HOLD, 1→BUY, 2→SELL` çözüyordu, firmware ise `0→SELL, 1→HOLD, 2→BUY`). Tablo 7'deki doğruluklar bu hata düzeltilmeden ölçüldüyse geçersizdir.

### K3. Dağıtılan model makalede yazandan farklı

`temp_weights.bin`'in sıfır deseni tamamen yapısal:

| Blok | Sıfır | Anlamı |
|---|---|---|
| W1 satır 0–31 | %37.5 | 40 gerçek giriş + 24 dolgu |
| **W1 satır 32–63** | **%100** | Katman 1'de 32 nöron |
| W2 / W3 / W4 | %75 / %75 / %50 | 16 / 8 / 3 nöron |

Yani dosyadaki model **40→32→16→8→3**, makale ise 40→64→32→16→3 diyor. Dolgunun kendisi matematiksel olarak doğru (ölü nöronların ağırlık+bias'ı sıfır → ReLU(0)=0). `.pth → .bin` dönüştürücüsünün çıktısı `.pth` ile **bit-birebir aynı** (doğrulandı) — export hattında hata yok.

### K4. Beş modelin topolojileri farklı — ve bu iyi haber

`.pth` tensör boyutlarından:

| Dosya | Topoloji |
|---|---|
| `best_model_new` | 40→64→32→16→3 *(makaledeki)* |
| `best_model_64_64_32_t00005` | 40→64→64→32→3 |
| `best_model_32_16_8_t00005` | 40→32→16→8→3 |
| `best_model_10_16_8_t00005` | 40→10→16→8→3 |

Bölüm 5.9: *"the five evaluated models share one identical hardware configuration ... only the weights, and hence the accuracy, differ."* — Topolojiler de farklı.

**Bu düzeltilmesi gereken bir hata değil, öne çıkarılması gereken bir sonuç.** Aynı bitstream'in dört farklı topolojiyi yeniden sentez olmadan çalıştırması, makalenin "framework" iddiasının en güçlü kanıtı ve şu an anlatılmıyor.

---

## 2. Doğrulanmış Sağlam Sonuçlar

Bu bölümdeki her şeyi bağımsız olarak yeniden hesapladım. Hepsi geçerli ve makalede kalmalı.

### D1. Tablo 10 birebir yeniden üretiliyor

1,004,229 satırlık `execution_log_linux.csv`'nin ham tick sütunlarından, paket bazında:

```
Aşama                 mean     p50     p99   p99.9
recv (EMAC+lwIP)      7.59    2.56   14.18   14.29
parse/memcpy          0.70    0.69    0.86    0.92
AXI-DMA               3.70    3.70    3.78    3.81
AXIS+MLP core         1.46    1.46    1.72    1.74
AXI-Lite readout      0.96    0.96    0.97    0.98
BOARD TOPLAM         14.40    9.41   21.03   21.16
```

Makaledeki değerlerin aynısı. **v1'deki M7 itirazım yanlıştı ve geri çekiliyor** — p99 aşama p99'larının toplamı değil (o 21.49 verirdi), paket bazında doğru hesaplanmış.

### D2. Analitik çevrim modeli ölçümle birebir uyuşuyor

`mlp_engine.vhd`'nin FSM'inden (ST_ISSUE + ST_DRAIN_LAYER) türettim:

```
cycles(layer) = ceil(N_out / 3) + 14
```

| Katman | N_out | ceil(N/3) | Model | Ölçülen |
|---|---|---|---|---|
| L1 (40→64) | 64 | 22 | 35 | 35 (280 ns) ✔ |
| L2 (64→32) | 32 | 11 | 25 | 25 (200 ns) ✔ |
| L3 (32→16) | 16 | 6 | 20 | 20 (160 ns) ✔ |
| L4 (16→3) | 3 | 1 | 15 | 15 (118 ns) ✔ |

Dört katmanda da tutuyor. **Bu formül makaleye girmeli** — ölçümlerin rastgele değil, mimariden türeyen değerler olduğunu kanıtlıyor ve tek başına bir katkı.

### D3. Kaynak / timing / güç tutarlı

- 192 DSP = `PARALLEL_NEURONS(3) × MAX_INPUTS(64)` ✔
- 98.5 BRAM ≈ 192 RAMB18 / 2 + bias ✔
- Fmax 127 MHz ↔ WNS 0.118 ns @ 8 ns ✔ (1/(8−0.118) = 126.9)
- 13 kademe ↔ `valid_pipe(0..12)` ✔

---

## 3. Üç Yol

### Yol A — Donanım makalesine daralt *(kısıtınıza uyan, önerilen)*

**Maliyet:** 0 kart zamanı, 0 RTL değişikliği, 0 yeniden ölçüm.

Doğruluk/kuantizasyon iddialarını tamamen çıkarın. Kalan katkı seti hâlâ güçlü:

1. Sub-µs, belirlenimli çıkarım çekirdeği — mimariden türetilmiş analitik modelle **ve** osiloskopla doğrulanmış
2. Yeniden sentez gerektirmeden dört farklı topoloji çalıştırabilen çalışma-anı yapılandırılabilir framework
3. 1M paket üzerinden aşama bazlı, yeniden üretilebilir uçtan uca gecikme dökümü
4. Düşük maliyetli SoC'de tam sistem entegrasyonu (Ethernet → PS → DMA → PL → karar)

Başlık ve abstract'tan "accuracy/faithful to the trained model" ifadeleri çıkar; makale "an FPGA inference *datapath* and its latency characterization" olarak konumlanır. `Q8.8` bir tasarım tercihi olarak anlatılır, doğruluk iddiası olmadan.

**Risk:** Hakem "ağın doğru çalıştığını nereden biliyoruz?" diye sorabilir. Cevap: D2'deki analitik model + `mlp_tb.vhd` simülasyon doğrulaması (bu şu an makalede hiç anlatılmıyor — eklenmeli). Bu genelde yeterli olur ama Yol B kadar güçlü değil.

### Yol B — Yol A + kısa bir tezgâh koşumu *(en iyi maliyet/fayda)*

**Maliyet:** ~1 saat tezgâh. RTL değişikliği **yok**, yeniden sentez **yok**, yeniden eğitim **yok**, mevcut bitstream ve firmware aynen kullanılır.

Yapılacaklar:
1. Bilinen tek bir `.bin` yükle (hangisi olduğunu not et)
2. Bilinen tek bir CSV akıt, ~100k paket logla (1M gerekmez)
3. `python3 quantization_analysis.py --log <yeni> --fixed-log` koş

Bu, "1M/100k çıkarım üzerinde donanım, altın yazılım modeliyle bit-birebir doğrulandı" iddiasını geri kazandırır. Bu **doğruluk iddiası değil** — modelin iyi olup olmadığından bağımsız, saf bir donanım-doğruluğu iddiası. Q8.8 hattının hatasız çalıştığını kanıtlar ve hakemin en olası sorusunu kapatır.

İki küçük ön koşul (host tarafı, kartla ilgisi yok):
- `hft_engine_linux.cpp`'de cast'e doygunluk ekle (sarmalanma → clamp), böylece emülatör ile host aynı davranır:
  ```cpp
  static inline int16_t f2q88(float v){
      int32_t x = (int32_t)lrintf(v * 256.0f);
      return (int16_t)(x > 32767 ? 32767 : x < -32768 ? -32768 : x);
  }
  ```
  *(Not: emülatördeki `cpp_float_to_int16` da buna göre güncellenmeli, yoksa bit-exact kalmaz.)*
- Sınıf permütasyon hatası düzeltilmiş motorla koştuğundan emin ol (`--fixed-log`)

### Yol C — Tam düzeltme *(en güçlü makale, en çok iş)*

Yol B + normalizasyon ekle + yeniden eğit + yeniden akıt. Ancak o zaman Tablo 6/7 ve Bölüm 5.2 gerçek olur.

**Gerekli:** `data_prep_binance.py`'de normalizasyonu aç ve scaler'ı diske kaydet (eğitimde ve çıkarımda **aynı** scaler); ham fiyat yerine log-getiri + normalize hacim kullan; yeniden eğit; `.bin`'i yeniden üret ve hiçbir ağırlığın ±0.25'te olmadığını doğrula; yeniden akıt.

**Ek olarak gereken (K5):** Doğruluk iddiası yapacaksanız veri kümesi bölümü de şart — sınıf dağılımı, çoğunluk-sınıfı taban çizgisi, karışıklık matrisi, etiketleme eşiği (`t00005` = 0.00005 görünüyor), eğitim/test bölünmesi. %61.74, taban çizgisi verilmeden anlamsız.

**Eksik:** Eğitim betiği hiçbir klasörde yok. Bulunmadan bu yol başlatılamaz.

---

## 4. Yol A/B İçin Yapılacaklar — kart gerektirmeyen düzeltmeler

Aşağıdakilerin hepsi masa başı. Sıra, etki/efor oranına göre.

### Öncelik 1 — Bloker

**Y1. Kaynakça: 3 → 25-35.** `references.bib` hâlâ şablon yorumları taşıyor. Elsevier Q1'de 3 kaynaklı Related Work editör masasında elenir.

Kapsanması gerekenler: FPGA finansal hızlandırma (Lockwood/NetFPGA, Leber-Geib-Litz, Morris, Denholm); sabit noktalı NN çıkarımı (Jacob ve ark., Gholami survey); FPGA NN framework'leri — **özellikle hls4ml (Duarte ve ark. 2018, JINST)**, FINN-R, Vitis-AI, Angel-Eye; Zynq AXI-DMA gecikme çalışmaları; kernel bypass / OS jitter (DPDK, Onload); limit order book tahmini (DeepLOB, FI-2010).

hls4ml'i atlamayın — doğrudan sizin sub-µs MLP nişinizde. Farkınız net: hls4ml her model için yeniden sentez ister, sizinki ağırlıkları ve topolojiyi çalışma anında değiştirir (K4).

**Y2. Metin-kod çelişkileri.**

| Nerede | Makale diyor | Gerçek |
|---|---|---|
| Tablo 5, Böl. 3 | Argmax → PL (hardware) | `main.c:177-189` — **PS yazılımında**. Üstelik bu, Tablo 10'daki 0.96 µs "readout" kaleminin ta kendisi |
| Abstract, Böl. 3.1, Tablo 5 | PS "feature preparation" yapar | Sadece `memcpy(inputs, payload+4, 128)`. Öznitelik üretimi, kuantizasyon ve dolgu host'ta |
| Sonuç | *"Future work includes runtime weight loading"* | **Zaten uygulanmış** — `mlp_weight_loader.h`, RTL'de `w_wr_en` yolu, GUI'de model yükleme paneli |
| Böl. 5.9 | *"any model that fits the 192-DSP budget, without re-synthesis"* | Gerçek sınır: ≤4 katman, her katman ≤64 nöron ve ≤64 giriş (`framework_pkg.vhd` derleme-zamanı sabitleri) |
| Böl. 5.9 | Beş model aynı topoloji, sadece ağırlıklar farklı | Topolojiler de farklı (K4) — bu daha güçlü bir sonuç |

**Y3. Şablon kalıntıları.** Böl. 4.1'deki *"the rest are to be completed"*; `main.tex:4-6`'daki "DRAFT v1 / TBD"; `\todo{}` ve `\writinggap{}`; boş Acknowledgments; `references.bib` yorumları.

### Öncelik 2 — Yüksek etki

**Y4. Analitik çevrim modelini ekle (D2).** `cycles = ceil(N_out/3) + 14` formülünü ve tabloyu koyun. Ayrıca:
- Makale çevrim başına **3 nöron** işlendiğini hiç söylemiyor — bu olmadan Tablo 13 havadan gelmiş görünüyor
- **768 vs 758 ns açıklaması yanlış:** makale farkı "input-streaming and output-decision" diye açıklıyor. `dbg_data_in_pulse` motor ST_IDLE'da `start='1'` gördüğünde atılıyor, yani **akış zaten bitmişken** — 768 ns içinde streaming yok. Fark 1 çevrim (8 ns) + osiloskop yuvarlaması (118 vs 120 ns)
- Tablo 13'ün "Measured Cycles" sütunu ölçülmemiş, süre×125 MHz ile türetilmiş → başlığı düzeltin
- `zedboard_mlp.xdc:65-70` makaleyle çelişiyor (92/35/24/19/14 çevrim diyor). Analitik model makaleyi destekliyor; XDC yorumunu düzeltin
- Boru hattı her katmanda tamamen boşaltılıyor (95 çevrimin ~52'si drain). Bunu dürüstçe tartışın ve nedenini açıklayın (ping-pong bağımlılığı)

**Y5. README'deki 56 µs taban çizgisini ekle.** *"Original Sequential FSM Latency: ~56 µs over AXI-Lite"* → paralel pipeline 0.768 µs = **73×**. Aynı takım, aynı kart, aynı model. Sahip olduğunuz en adil ve en güçlü karşılaştırma ve makalede yok. (İdealde PS Cortex-A9 üzerinde aynı MLP'nin yazılım süresi de eklenmeli — ama bu ek ölçüm gerektirir, Yol A'da atlanabilir.)

**Y6. Throughput / verimlilik ekle.** Makale hiç GOP/s ya da çıkarım/s vermiyor ama Tablo 1'de FINN'i "12.3 M cls/s", SparkNoC'u "337.2 GOP/s" ile listeliyor. Mevcut sayılardan hesaplanabilir:

- Tepe: 192 × 2 × 125 MHz = **48 GOP/s**
- Faydalı MAC/çıkarım: 40·64 + 64·32 + 32·16 + 16·3 = **5,168**
- Yayınlanan çarpma (dolgu dahil): 7,680 → dolgu verimliliği **%67**
- Ulaşılan: 5,168 × 2 / 768 ns ≈ **13.5 GOP/s** = tepenin **%28'i**
- Çekirdek throughput: **1.30 M çıkarım/s**; sistem (wrapper `ST_WAIT` nedeniyle örtüşme yok): **~0.77 M/s**

%28 verim, "fully unrolled/parallel" retoriğiyle çelişiyor — drain + dolgu kaynaklı. Sayıyı verin ve açıklayın; hakem zaten hesaplayacak.

**Y7. BRAM analizini düzeltin.** Makale: *"BRAM 70.36%, leaving room for larger feature sets."* Gerçek: `gen_w_brams` her (nöron-slotu × giriş) için ayrı BRAM üretiyor (192 adet), her biri 128×16 bit = bir RAMB18'in **~%12'si**. Derinlik neredeyse bedava; BRAM **sayısı** `PARALLEL_NEURONS × MAX_INPUTS`'e kilitli. Yani gerçek ölçeklenme sınırı DSP (%87) değil, BRAM blok sayısı — makale tersini ima ediyor. Bir çözüm de önerin (birden fazla girişi tek satırda paketlemek).

**Y8. Tablo 1'i yeniden kurun.** Şu an FINN **0.31 µs** gösteriyor, sizinki "sub-µs" — yani FINN daha hızlı ve bu tabloda görünüyor, hiç tartışılmıyor. Doğru çerçeve: FINN binarize ağlar için, her model için yeniden sentez, Ethernet yok; sizinki 16-bit, yeniden sentezsiz topoloji değişimi, ağ bağlantılı. Eklenmesi gereken sütunlar: **Precision (bit)**, **Model değişimi için yeniden sentez?**, **Throughput**. hls4ml satırı ekleyin.

### Öncelik 3 — Cila

**Y9.** Güç değerine "estimated" ekleyin (Vivado tahmini, ölçüm değil; vectorless mi SAIF mi belirtin). Tablo 14'te 2.78 W (PS7'nin 1.535 W'ı dahil) SparkNoC'un "compute power" 7.6 W'ıyla karşılaştırılıyor — farklı tabanlar; PL-only (~1.25 W) kullanın.

**Y10.** Zynq parça numarası hiçbir yerde yok. Kaynaklardan ve XDC'den **XC7Z020-1CLG484 / Digilent ZedBoard**. Speed grade ile yazın — timing closure iddiası onsuz doğrulanamaz.

**Y11.** PS'in **bare-metal** olduğu (lwIP, OS yok) hiç söylenmemiş. Bu lehinize: kart tarafında OS jitter'ı yok, tüm jitter host tarafında. Açıkça yazın (lwIP sürümü, raw/socket API, PS 666.67 MHz, cache konfigürasyonu).

**Y12.** Saat frekansı belirsizliği: BD `PCW_FPGA0_PERIPHERAL_FREQMHZ = 130`, makale 125 MHz, `mlp_tb.vhd` 100 MHz, reset bloğu adı `rst_ps7_0_100M`. Muhtemelen gerçek FCLK = 1000/8 = 125 MHz ve makale doğru — ama Vivado'nun raporladığı gerçek değerle teyit edip yazın. Tüm çevrim dönüşümleri buna bağlı.

**Y13.** Fmax 127 MHz düşük. Tam pipeline'lı DSP48E1 (`in_reg`/`w_reg` → `mult_mreg` → `mult_preg`) çok daha hızlı olabilirdi; kritik yol muhtemelen 40-bit toplayıcı ağacı veya `current_inputs`'un 64×16 bit 2:1 mux'ı. Vivado kritik yol raporunu verin — doğal bir gelecek-çalışma maddesi.

**Y14.** "192 DSP-based **MAC** units" yanlış: DSP48E1'in akümülatörü kullanılmıyor, toplama LUT tabanlı ağaçta (Stage 5-10). "192 DSP multipliers followed by a fabric adder tree" doğru — 14.5K LUT kullanımını da açıklar.

**Y15.** `mlp_tb.vhd` (148 satır) var ama makale hiç bahsetmiyor. Yol A'da bu **kritik** — fonksiyonel doğruluğun tek kanıtı olacak. Bir "Verification" alt bölümü yazın: kaç test vektörü, altın referansa karşı bit-exact mi, kapsam.

**Y16. Biçim.**
- Yazar bloğu elsarticle formatında değil (`\author{}` içine `tabular` gömülmüş, "Advisor" manuel). Elsevier `\author[label]{}` + `\address[label]{}` yapısını ister. Danışman muhtemelen yazar listesinde olmalı.
- E-posta muhtemelen hatalı: `ahmet.ozakner@` → soyadı Özkaner ise `ozkaner@`
- `\renewcommand{\bfdefault}{\mddefault}` tüm kalın yazıyı kapatıyor → kaldırın
- Her yerde `[H]`; Elsevier iki sütunda `[t]`/`[htbp]` tercih eder
- **Vivado ekran görüntüleri figür olarak kabul edilmez:** `util_table.jpeg`, `power_onchip.jpeg`, `timing_setup.jpeg`, `model_comparison.jpeg` → tablo/vektör grafik olarak yeniden çizin. Ayrıca Tablo 12 ↔ Şekil 11, Tablo 6 ↔ Şekil 6, Tablo 13 ↔ Şekil 8 **aynı veriyi iki kez** veriyor; birer tanesini silin
- "percentage point" ile "percent" ayrımını netleştirin (abstract "≈0.2%", Tablo 7 "0.2174 puan")

**Y17.** Reproducibility beyanı yok. VHDL, firmware, host araçları elinizde — "Code and Data Availability" bölümü + GitHub/Zenodo DOI ekleyin.

**Y18. Robustluk (Limitations paragrafı).** `main.c`'de: DMA başarısız olursa (`status != XST_SUCCESS`) kod yine de done-polling döngüsüne giriyor → **sonsuz kilitlenme**, timeout yok. `memcpy` doğrudan `p->payload` üzerinden (parçalanmış pbuf için `pbuf_copy_partial` gerekir). Paket doğrulama yok (sıra no, sağlama). Gecikme belirlenimliliği iddiası varsa hata yollarının belirlenimliliği de ele alınmalı.

---

## 5. Kaldırılan / Geri Çekilen Maddeler (v1)

| v1 maddesi | Durum |
|---|---|
| M1 — `float_to_q88` yuvarlama hatası | **Geri çekildi.** Python emülatörü firmware'in budamasını bilerek taklit ediyor; ikisi tutarlı. Gerçek kök neden K1. |
| M7 — p99'ların toplanması | **Geri çekildi.** Ham logdan doğrulandı: Tablo 10 p99'u paket bazında doğru hesaplanmış. |
| M1-alt — sequence number hipotezi | **Geri çekildi.** Uyuşmazlık hizalama kaynaklı değil; log ile ağırlık dosyası eşleşmiyor (K2). |

---

## 6. Kapanış

Elinizde iki ayrı makale var. Donanım makalesi **hazır ve sağlam** — ölçümleri bağımsız olarak yeniden ürettim, analitik model ölçümle birebir tutuyor, ve şu an makalenin anlatmadığı gerçek katkılar (73× seri-FSM hızlanması, çalışma-anı topoloji değişimi, mimariden türeyen gecikme modeli) var. ML makalesi ise henüz yok; öznitelik boru hattı düzeltilip yeniden eğitilmeden yazılamaz.

Kısıtınız göz önüne alındığında: **Yol A veya B'yi seçin, Bölüm 4'teki Y1-Y18'i uygulayın, doğruluk iddialarını Yol C'ye erteleyin.** Makale bu şekilde JSA'ya gidebilir ve ML tarafı ikinci bir çalışmaya kalır.
