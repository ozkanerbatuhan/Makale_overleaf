# Yapılacaklar

Güncelleme: 29 Temmuz 2026. RTL düzeltildi ve doğrulandı, sentez alındı, makale JSA formatına geçirildi.

---

## A. Kart — sizde

**A1.** ✅ Sentez tamamlandı, WNS pozitif (0,038 ns), raporlar `reports/` altında.

**A2.** Vitis: `mlp_platform` → **Update Hardware Specification** → yeni `.xsa` → **Build**.
> Geçen sefer tam burada koptu: `.xsa` yenilendi, `.bit` Mayıs 1 sürümünde kaldı.

**A3.** `lwip_echo_server` → **Clean + Build**.

**A4.** BOOT.bin:
```
cd D:\vitis_projects\lwip_echo_server
bootgen -image ..\verify_boot.bif -arch zynq -o BOOT.bin -w on
```
Boyut ~4,8 MB olmalı. 1,3 MB çıkarsa bitstream paketlenmemiştir.

**A5.** Paketlenen `.bit`'in md5'i yeni sentezinkiyle aynı mı — kontrol edin.

**A6.** `BIF_HFT.bif`'i silin.

**A7.** Dört doğrulama koşumunu tekrarlayın (`HFT_LOG` ile ayrı loglar).

> **Neden tekrar:** Mevcut %100 sonuçları 01:41–01:44'teki bitstream'den. Sentez 02:19'da yeni bir bitstream üretti ve makaleye onun sayıları yazıldı (14.445 LUT, WNS 0,038 ns, 2,718 W). Şu an makale bir bitstream'i doğrulayıp başkasını raporluyor. Tekrar koşum bunu tek bitstream'e indirir. Mantık değişmediği için yine %100 bekliyorum.

---

## B. Makale — tamamlananlar

- **Format** JSA'ya uygun: `[final,5p,times,twocolumn]`, `elsarticle-num`, iki sütun
- **Yazar bloğu** düzgün elsarticle yapısında (`\author[]`, `\ead`, `\corref`, `\address`)
- **Son bölümler** JSA sırasında: CRediT → Declaration of competing interest → Data availability → Acknowledgments
- **Highlights** ayrı dosyada, 5 madde, hepsi 85 karakter altında
- **Anahtar kelimeler** 8 → 5
- **Kaynakça** 3 → **18**, hepsi doğrulanmış
- **Related Work** dört alt bölüme çıktı, hls4ml dahil rakipler ele alındı
- **Tablo 1** yeniden kuruldu: Precision, Re-synthesis, Network I/O sütunları
- **Bölüm 5.2 Functional Verification** (yeni) + iki tablo
- **Bölüm 5.9 Run-Time Reconfigurability** (yeniden yazıldı)
- **Kaynak/timing/güç** üç Vivado ekran görüntüsü yerine üç tablo, yeni sentez sayılarıyla
- **Analitik çevrim modeli** denklem (1) + tahmin/ölçüm karşılaştırma tablosu
- **Throughput/verimlilik** paragrafı (48 GOP/s tepe, 13,5 ulaşılan, %28)
- **Kritik yol analizi** — Fmax'ın neden 125,6 MHz'de kaldığı ölçülmüş veriyle
- **Metin-kod çelişkileri** giderildi: argmax → PS, feature preparation → hand-off, "MAC" → çarpıcı + fabric adder tree
- **Şablon kalıntıları** temizlendi (TBD, DRAFT, `\writinggap`, `\bfdefault`, boş Acknowledgments)
- 14 adet `[H]` float → `[htbp]`
- Parça numarası (XC7Z020-1CLG484) ve bare-metal lwIP bilgisi eklendi

---

## C. Makale — kalan 5 `\todo`

| # | Yer | Ne gerekiyor |
|---|---|---|
| 1 | Tablo 1 | Puranik metriği — makaleden bakın |
| 2 | Tablo 1 | Angel-Eye GOP/s — makaleden bakın |
| 3 | CRediT | Rolleri yazarlar arasında paylaştırın (taslak var) |
| 4 | Data availability | Depo URL'si / Zenodo DOI |
| 5 | Acknowledgments | Fon bilgisi veya bölümü silin |

Leber (2,6 µs) ve hls4ml (~100 ns) doğrulandı ve dolduruldu.

---

## D. Sonraki tur — öncelikli

**D1. Kaynakçayı 18 → 25-30.** JSA için hâlâ az. Eklenebilecek kümeler: kernel bypass / DPDK ağ gecikmesi, HFT piyasa mikroyapısı, Zynq PS-PL gecikme karakterizasyonu, sabit noktalı DSP tasarımı.

**D2. Kod deposu.** VHDL, `mlp_verify_tb.vhd`, `sim_model.py`, `verify_bitexact.py`, `make_verify_stream.py` → GitHub + Zenodo DOI. Bölüm 5.2'nin ağırlığı buna dayanıyor.

**D3. Şekiller.** `model_comparison.jpeg` hâlâ ekran görüntüsü; Tablo 7 ile aynı veriyi veriyor. Birini silin ya da grafiği vektör olarak yeniden çizin.

**D4. Bölüm 5.4 (Linux/Windows).** Başlığı "Software Baseline: OS-Induced Latency" yanıltıcı — bu bir *inference* taban çizgisi değil, host ağ yığını karşılaştırması. Yeniden adlandırılmalı.

**D5. README'deki 56 µs taban çizgisi.** Seri FSM → paralel pipeline = **73×**. Aynı takım, aynı kart, aynı model. Makalede hâlâ yok, en güçlü karşılaştırmanız.

---

## E. Açık kalan konu

Tablo 7'deki **FPGA** doğrulukları düzeltilmeden önceki donanımda ölçüldü. Kararınız "kalsın" oldu.

A7'den sonra kart zaten elinizde olacak; gerçek veri setinizi bir kez daha akıtmak ~20 dakika. Yaparsanız Tablo 7 tartışmasız hale gelir. Yapmazsak, hakem "üç hizalama hatası bulmuşsunuz, FPGA doğrulukları hangi donanımda ölçüldü" derse cevabımız olmaz.
