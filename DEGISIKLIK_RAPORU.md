# Değişiklik Raporu

*An Ethernet-Enabled Customizable Neural Inference Framework on Low-Cost FPGA SoC for High-Frequency Trading*

İlk hakem incelemesinden bugüne yapılan tüm değişiklikler. Üç başlıkta toplanıyor: donanım ve yazılımda bulunan gerçek hatalar, sıfırdan kurulan doğrulama altyapısı, ve makalenin yeniden yazımı.

---

## 1. Başlangıç durumu ve neyin yanlış olduğu

İnceleme, makale ile kod arasındaki tutarlılığı kontrol etmek için başladı. Kısa sürede tutarsızlıktan daha ciddi bir şeye dönüştü: makaledeki merkezi doğruluk iddiası ölçülebilir bir şey ölçmüyordu.

**İddia:** FPGA çıktısı yazılım modeliyle %96.85 oranında eşleşiyor.

**Gerçek:** Öznitelikler hiçbir yerde normalize edilmiyordu. Ham BTCUSDT fiyatları (~76.834) Q8.8 aralığının yaklaşık 600 katı dışındaydı. Host tarafındaki `static_cast<int16_t>(v * 256.0f)` taşan değerleri sessizce sarmalıyordu, yani fiyat efektif olarak `fiyat mod 256` oluyordu. Sonuç: 64 özniteliğin 63'ü sıfırdı, çıktı %91.4 oranında tek bir sınıfta toplanmıştı ve "%96.85 eşleşme" aslında iki tarafın da aynı dejenere sınıfı üretmesiydi. Böyle bir sayı, veri yolu tamamen bozuk olsa bile yüksek çıkardı.

Bu keşif, doğrulamanın baştan kurulmasını gerektirdi. Kurulunca da donanımda üç ayrı hata ortaya çıktı.

---

## 2. RTL'de bulunan ve düzeltilen hatalar

`hft.srcs/sources_1/new/mlp_engine.vhd`

| Sabit | Önce | Sonra | Etki |
|---|---|---|---|
| `BIAS_STAGE` | 11 | **9** | Bias, toplayıcı ağacına yanlış kademede ekleniyordu |
| `WB_STAGE` | 12 | **11** | Geri yazma yanlış token kademesini kullanıyordu |
| `MUX_STAGE` | 2 | **1** | Ping-pong mux yanlış tamponu okuyordu (katman 2 `buf_A`'dan, katman 3 `buf_B`'den) |

Üçü de boru hattı hizalama hatası. Sentez bunları yakalayamaz, çünkü tasarım geçerli VHDL. Uçtan uca test de yakalayamamıştı, çünkü test verisi dejenereydi.

**Neden daha önce bulunamamışlardı:** Tasarım hiç simüle edilmemişti. Simülasyonu engelleyen bir çoklu sürücü (multiple driver) hatası vardı: `valid_pipe`, `layer_pipe` ve `iter_pipe` token kaydırması iki ayrı süreçten sürülüyordu. Bu düzeltildi (kaydırma Issue FSM sürecine taşındı) ve simülasyon ilk kez çalıştı.

**Eklenen:** 16 bitlik çevrim sayacı (`cyc_run` / `cyc_hold`). `start` kabul edilince sıfırlanır, denetleyici boşta olmadığı her çevrimde artar, son katman `done` verdiğinde mandallanır.

`mlp_axi_wrapper.vhd` — sayaç AXI-Lite `0x10` adresinden okunabilir hale getirildi.

---

## 3. Host ve firmware değişiklikleri

### `pc_test/linux/hft_engine_linux.cpp`

- **Doygun tip dönüşümü.** `static_cast<int16_t>` yerine `f2q88()`: taşan değerler artık sessizce sarmalanmıyor, RTL'in `saturate()` davranışını birebir taklit ediyor. Kök nedenin host tarafındaki yarısı bu.
- **`HFT_LOG` ortam değişkeni.** Her koşum kendi log dosyasına yazıyor, manuel silme derdi kalktı.
- **Log kolonları.** `out0,out1,out2` (ham logit'ler) ve `cycles` eklendi. Karar eşleşmesi zayıf bir kontrol; logit karşılaştırması veri yolunun her bitini sınıyor.

### `lwip_echo_server/src/main.c`

- **UDP yanıtı 21 → 27 → 29 bayt.** Sırasıyla ham logit'ler ve çevrim sayacı eklendi.
- **ARM Cortex-A9 baseline'ı.** Aynı ağ, aynı Q8.8 aritmetiği (aynı 40 bit akümülasyon, aynı kaydırma, aynı doygunluk, aynı ReLU, aynı argmax), bare-metal, Global Timer ile ölçülüyor.
- **`__attribute__((optimize("O3")))`.** Vitis uygulamayı varsayılan olarak `-O0 -g3` ile derliyor. Optimizasyonsuz bir yazılım baseline'ı karşılaştırmayı haksız kılardı; bu nitelik global bayraktan bağımsız olarak ilgili fonksiyonları `-O3` derletiyor.
- **Açılışta koşma.** Ölçüm model yüklemeden, host olmadan, kart açılır açılmaz UART'a basılıyor.
- **Dağılım ölçümü.** Ortalamanın yanında min / p50 / p99 / max.

---

## 4. Sıfırdan kurulan doğrulama altyapısı

Hiçbiri önceden yoktu.

| Dosya | İşlevi |
|---|---|
| `hft.srcs/sources_1/new/mlp_verify_tb.vhd` | Kendi kendini denetleyen testbench. T1 veri yolu, T2 bias boru hattı, T3 geri yazma indeksleme. Girdiler zehirli değerlerle seçildi, böylece eksik bir geri yazma "geçti" gibi görünemiyor |
| `sim_model.py` | `mlp_engine`'in çevrim doğru Python modeli. Vivado'yu birebir üretti; `(BIAS, WB, MUX)` üçlüsünü taramak ve sayacın doğru okuduğunu doğrulamak için kullanıldı |
| `pc_test/verify/make_verify_stream.py` | Test akışı üreteci (seed 20260728). Q8.8'e sığan, ama doygunluk, ReLU kesme, işaret geçişi ve sıfır dolgu yollarını bilinçli olarak zorlayan uyaranlar |
| `pc_test/verify/verify_bitexact.py` | Bağımsız altın model. Ağırlık kuantizasyonu, ileri yayılım, argmax; donanım çıktısıyla bit düzeyinde karşılaştırır |
| `pc_test/verify/analyze_jitter.py` | Çevrim sayacı dağılımı analizi |
| `pc_test/verify/models/` | Dört topoloji, dejenere olan `rejected/` altına ayrıldı |
| `rebuild_all.tcl` | Bozuk `run_synth.tcl` / `build_bitstream.tcl` yerine. Parantezli yollar, mutlak rapor yolları, util/timing/power/clock/critical_paths raporları ve `.xsa` üretir |

---

## 5. Ölçüm sonuçları

### Bit-exact doğrulama

| | Önce | Sonra |
|---|---|---|
| İddia | %96.85 karar eşleşmesi | **%100.0000** |
| Kapsam | Tek model, dejenere veri | 4 topoloji × 100.000 çıkarım |
| Karşılaştırma | Sadece karar | Karar **ve** ham logit'ler |
| Toplam | — | 400.000 çıkarım, 1.200.000 int16 karşılaştırması |

Dört topoloji de tek ve değişmemiş bir bitstream'e AXI-Lite üzerinden yüklendi, aralarında sentez adımı yok. Bu aynı zamanda makalenin "framework" iddiasının kanıtı; daha önce hiç yazılmamıştı.

### Determinizm

Çevrim sayacı, 100.000 ardışık çıkarım:

```
min = max = 95 çevrim,  std = 0,  tek farklı değer
```

Sayaç 95 okuyor, analitik model 96 diyor. Fark enstrüman tanımından: sayaç yalnızca boşta olmayan çevrimleri sayıyor ve `start`'ın örneklendiği çevrimi kaçırıyor. `95 + 1 = 96`, hem modelle hem osiloskobun 768 ns'siyle uyuşuyor.

Bu ölçüm öncesinde "deterministic" kelimesi makalede on kereden fazla geçiyor ve kanıtı tek bir osiloskop görüntüsüydü.

### ARM Cortex-A9 baseline'ı

| Derleme | Ortalama |
|---|---|
| `-O0` (Vitis varsayılanı) | 302.1 µs |
| `-O3` | **52.4 µs** |

Dağılım (n = 1000, bare-metal, tek çekirdek, sıcak cache, işletim sistemi ve ağ yok):

| | Donanım | Yazılım |
|---|---|---|
| min | 95 çevrim | 51.2 µs |
| p50 | 95 | 52.0 µs |
| p99 | 95 | 52.6 µs |
| max | 95 | 67.1 µs |
| **yayılım** | **0** | **15.9 µs** |

FPGA 768 ns, yani **68 kat** hızlı. Ama asıl sonuç ortalamada değil: yazılımın en iyi ve en kötü durumu arasındaki 15.9 µs, tüm donanım çıkarımının yirmi katından fazla. Medyan ile p99 arası tek başına 570 ns, donanımın tamamına yakın.

Ek gözlem: aynı rutin eğitilmiş ağırlıklarla ~%2 farklı süre veriyor, çünkü ReLU karşılaştırması veriye bağlı bir dallanma. Donanımda bunun karşılığı yok.

---

## 6. Makale değişiklikleri

### Format ve künye

- IEEE düzeninden **JSA / elsarticle** formatına çevrildi
- Yazar sırası: Ahmet Batuhan Özkaner, Mustafa Alper Ilık, Baykal Sarıoğlu
- CRediT beyanı, competing interest, data availability, **funding beyanı** (fon alınmadığı açıkça yazıldı) eklendi
- Metin içinde kalın yazı yok, em/en dash yok, `-ise` / `-ize` tutarlı hale getirildi
- Highlights: 5 madde, en uzunu 77 karakter (Elsevier sınırı 85)
- Abstract 241 kelime (sınır ~250)

### Kaynaklar

**3 → 27.** Hepsinin cilt, sayfa ve DOI bilgisi kaynağından doğrulandı, uydurma yok. Eklenen başlıca gruplar: FPGA'da finansal hızlandırma, sinir ağı çıkarım framework'leri (FINN, hls4ml, Angel-Eye), kuantizasyon, limit order book tahmini, overlay literatürü, LUT tabanlı nanosaniye ölçekli çalışmalar (PolyLUT, NeuraLUT).

### Yeniden yazılan bölümler

**Related Work** — Overlay literatürü (§2.3) ve LUT tabanlı çalışmalar (§2.4) eklendi. Konumlandırma kendi aleyhine dürüst hale getirildi: run-time programlanabilirliğin bu makaleye ait olmadığı, LogicNets ve türevlerinin bir ila iki kat daha hızlı olduğu açıkça yazıldı. Özgünlük iddiası tek bir özellik yerine dört özelliğin birlikteliği olarak yeniden kuruldu.

**Verification (yeni bölüm)** — Üç seviyeli metodoloji: bağımsız bit doğru referans model, yönlendirilmiş RTL simülasyonu, donanım üzerinde karşılaştırma. Bulunan üç hata ve düzeltmeleri raporlandı. Bir hatayı bulup yazmak, hiç hata bulmamış gibi yapmaktan güçlü.

**Determinism (yeni bölüm)** — Sayaç tanımı, 100.000 çıkarımlık tek noktalı dağılım, 95/96 farkının açıklaması.

**Software Inference on the Same SoC (yeni bölüm)** — ARM baseline'ı, dağılımıyla birlikte. `-O0`'ın 302 µs olduğu ve varsayılan ayarlarla bırakılmış bir baseline'ın hızlanmayı altı kat abartacağı kendiliğinden yazıldı.

### Düzeltilen tutarsızlıklar

| Sorun | Durum |
|---|---|
| Denklem (1) katman 1 için 36 çevrim diyor, Tablo 13'te 35 yazıyordu | Tablo düzeltildi, toplam 96 çevrim / 768 ns |
| Abstract yeniden sentez öncesi rakamları taşıyordu (WNS 0.118, 2.78 W, %27.3) | Tablolarla senkronize edildi (0.038 ns, 2.72 W, %27.2) |
| Katkı listesi "dört katmanda da tam uyuşuyor" diyordu, Tablo 13 bunu yalanlıyordu | İddia gerçeğe uyarlandı, sayaçla desteklendi |
| §6.6 "sapmaların işaretleri zıt" diyordu, ikisi de negatifti | Yanlış gerekçe kaldırıldı, 758/768 farkı dürüstçe açıklandı |
| Abstract "≈%0.2" diyordu, doğrusu 0.22 yüzde puanı | Düzeltildi |
| Tablo 11 (N=120.883) ve Tablo 12 (N=1.004.229) uzlaştırılmamıştı | İki koşunun farkı §6.1'de açıklandı, setup tablosuna ikinci satır eklendi |
| Tablo 12'nin yüzdelik satırı açıklanmamıştı | Hesap yöntemi dipnot olarak eklendi |
| Sonuç bölümü 67× karşılaştırmasını hiç anmıyordu | Bağımsız baseline ile açılacak şekilde yeniden düzenlendi |

### Kaldırılan ve kısaltılanlar

- **Tablo 17** (nitel maliyet karşılaştırması) — ölçülmemiş platformlar için nitel etiketler; kaldırıldı
- **Tablo 2** (measurement plan) — Tablo 12'nin yuvarlanmış ve dağılımsız kopyasıydı; kaldırıldı
- **Linux/Windows karşılaştırması** — bir bölümden bir paragrafa indirildi, şekli kaldırıldı
- **GUI şekli** — yarım sayfadan çeyrek sayfaya indirildi, başlığı on satırdan dörde düşürüldü ve run-time reconfigurability iddiasına bağlandı

### Atıfsız iddiaların kapatılması

- "higher-order functions and deeper topologies" → PolyLUT (ICFPT 2023) ve NeuraLUT (FPL 2024) isimle atıflandı
- "Commercial deployments follow the same model" → AMD DPU somut olarak anlatıldı
- "We are not aware of an overlay below one microsecond" → kapsamla sınırlandı ve tiled-dataflow gerekçesine bağlandı

---

## 7. Geri çekilen kendi iddialarım

Kayda geçmesi için, süreç boyunca yanlış olduğu ortaya çıkan teşhislerim:

| İddia | Neden yanlıştı |
|---|---|
| Uyumsuzluğun sebebi `float_to_q88` yuvarlaması | `quantization_analysis.py` zaten kasten aynı kesmeyi yapıyordu |
| Sıra numarası hizalama sorunu var | Timeout satırları da loglanıyor, konumsal hizalama geçerli |
| Eski bitstream yüklü | Yeni bitstream bayt bayt aynı logit'leri üretti |
| Tablo 10'un p99'u aşama p99'larının toplamı | 1M satırlık logdan yeniden hesaplandı, paket bazında doğru hesaplanmıştı (21.03, toplansaydı 21.49) |

Ayrıca makaleye ben yazmıştım: "sapmaların işaretleri zıt" cümlesi olgusal olarak yanlıştı. Bir de toptan `-ise`/`-ize` değişimi "optimistic" kelimesini bozmuştu; tarayıp düzelttim.

---

## 8. Kalan işler

1. **Veri kümesi ve sınıflandırma değerlendirmesi.** Etiketleme kuralı (ufuk ve eşik), sınıf dağılımı, çoğunluk sınıfı baseline'ı, zamansal bölünme beyanı, karışıklık matrisi. Eğitim kodu bekleniyor. Kabul için tek gerçek engel bu.
2. **Zenodo DOI.** Depolar public, kalıcı tanımlayıcı henüz yok.
3. **İsteğe bağlı:** hls4ml karşılaştırması, bellek konsolidasyonu deneme sentezi, sabit nokta format taraması. Hiçbiri gönderiyi engellemiyor.

---

*Makale şu an 14 sayfa, 27 referans, hatasız derleniyor.*
