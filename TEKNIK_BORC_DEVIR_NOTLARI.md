# Karma App — İkinci Tur Teknik Borç İncelemesi: Devir Notları

**Tarih:** 16 Temmuz 2026
**Amaç:** Bu belge, `SECURITY_NOTES.md`'deki ilk üç turun (güvenlik sertleştirme,
RBAC, navigasyon/performans) devamı olarak, **başka bir AI tarafından yapılan
33 dosyalık kapsamlı teknik borç incelemesinin** sentezidir. Konuşma penceresi
dolmadan önce, gelecekte (yeni bir Claude oturumunda ya da Meltem'in kendisi
tarafından) buradan devam edilebilmesi için hazırlandı.

**Önemli çerçeve:** Bu belgedeki bulguların büyük çoğunluğu **henüz koda
bakılarak doğrulanmadı** — ikinci AI'nın metin incelemeleri, çoğunlukla kaynak
kod eşliğinde değil, yalnızca inceleme raporu olarak geldi. Kod ekli gelen
dosyalarda (aşağıdaki tabloda "✅ kod var" işaretli) doğrulama yapıldı veya
yapılabilir durumda. Kalanlar **iddia** olarak değerlendirilmeli, uygulamaya
geçmeden önce mutlaka gerçek kodla karşılaştırılmalı.

---

## ✅ ÇÖZÜLDÜ: `portfoylerím.py` login guard eksikliği

**Durum: Doğrulandı ve düzeltildi (16 Temmuz 2026).** Meltem'in GitHub'daki
gerçek, güncel dosyasında (sonradan yoğun şekilde geliştirilmiş — Kapalı/Köprü
portföy sınıflandırması, mülk sahibi yönetimi, AI ile metin ayrıştırma
eklenmiş) login guard gerçekten **yoktu**. Muhtemel sebep: dosya login-guard
turundan sonra AI ile yoğun şekilde yeniden geliştirilirken en üstteki guard
bloğu düşmüş/unutulmuş.

**Ne yapıldı:** Dosyanın import bloğunun hemen ardına şu eklendi (dosyanın
geri kalanına hiç dokunulmadı):

```python
from core.auth import oturum_kontrol

if not oturum_kontrol():
    st.switch_page("pages/giris.py")
```

Test edildi (ekran görüntüsüyle doğrulandı — sayfa normal açılıyor, tüm
sınıflandırma/mülk sahibi/fotoğraf özellikleri çalışıyor) ve push edildi.

**Çıkarılan ders:** Bu, listedeki "tekrar eden desen"lerden bağımsız, ayrı
bir kategori: **AI ile yoğun geliştirme sırasında önceden eklenmiş güvenlik
kontrollerinin sessizce kaybolabilmesi.** Diğer sayfalarda da (özellikle
üzerinde en çok AI ile çalışılan `taleplerim.py`, `2_Talep_Tablosu.py`,
`3_Portfoy_Tablosu.py` gibi büyük/aktif geliştirilen dosyalarda) periyodik
olarak "hâlâ `oturum_kontrol()` çağrısı var mı" diye hızlı bir kontrol
yapmakta fayda var — özellikle bir dosyayı AI ile büyük çaplı yeniden
yazdırdıktan sonra.

---

## Bu turun genel çerçevesi

İkinci bir AI, `SECURITY_NOTES.md`'de belgelenen ilk üç turdan sonra proje
genelinde 33 dosyayı sırayla inceledi (kod + yorum şeklinde, dosya dosya).
Son olarak hem bir "önceliklendirilmiş düzeltme planı" hem de genel bir
"proje değerlendirmesi" (ürün/güvenlik/veri bütünlüğü puanlaması) sundu.

**Genel değerlendirme özeti (ikinci AI'nın puanlaması, doğrulanmamış ama
makul):**

| Alan | Puan |
|---|---:|
| İş değeri / ürün fikri | 8/10 |
| Özellik kapsamı | 8/10 |
| Kullanıcı deneyimi | 7/10 |
| Kod organizasyonu | 5/10 |
| Veri bütünlüğü | 4/10 |
| Operasyonel dayanıklılık | 4/10 |
| Güvenlik olgunluğu | 3/10 |
| Gelecek potansiyeli | 9/10 |

**Bizim yorumumuz:** Sayılar kesin ölçüm değil, genel bir izlenim. Değerli
olan puanlar değil, altındaki **tekrar eden somut desenler** (aşağıda). Proje
"kurtarılmaya muhtaç dağınık bir prototip değil, sağlamlaştırılmaya muhtaç
değerli bir ürün" — bu çerçeveye katılıyoruz. **Yeniden yazmaya gerek yok.**

**Meltem'in durumu için önemli bağlam:** Bu değerlendirme, sanki büyük bir
mühendislik ekibi tarafından kurumsal ölçekte kullanılacakmış gibi bir dille
yazılmış ("merkezi permission servisi", "distributed lock + heartbeat",
"staging snapshot + transaction merge"). Meltem üç aydır kod yazan, tek başına
AI ile geliştirme yapan bir kişi. Bu belgedeki öneriler **doğru yönde** ama
"Sprint 1-5" formatıyla değil, bugüne kadar kanıtlanmış çalışma tarzıyla
(küçük, izole, tek dosyalık, test edilebilir adımlar) uygulanmalı.

---

## Tekrar eden desenler (en güvenilir bulgular)

Bunlar, **birden fazla bağımsız dosya incelemesinde, birbirinden habersiz
şekilde tekrar tekrar çıkan** örüntüler — bu yüzden tekil bir dosyadaki
iddiadan daha güvenilir kabul edilmeli.

### 1. `secret_key`, `publishable_key`'den önce/yerine kullanılıyor
Bunu `core/auth.py`'de zaten bir kez bulup düzeltmiştik (RLS bypass riski).
Aynı desen şu dosyalarda da tespit edildi:
- **`core/supabase_client.py`** → `get_client()` **koşulsuz** `secret_key`
  kullanıyor (kod doğrulandı — dosya sadece 7 satır, gerçekten böyle)
- `pazar_analiz.py`, `pazar_raporu.py` → kendi `_supa()`'ları var, secret_key
  publishable_key'den **önce** tercih ediliyor
- `revy_kimlik.py` → aynı fallback zinciri (kod doğrulandı)
- `rehber_app.py`, `revy_sync.py`, `startkey_portfoy_listesi.py` → benzer
  iddialar (kod görülmedi, doğrulanmalı)

**Bu, en kolay ve en yüksek etkili düzeltme** — `auth.py`'de yaptığımız
işlemin birebir tekrarı, zaten bildiğimiz bir iş.

### 2. İsim (substring) eşleşmesiyle kayıt sahipliği
`portfoylerím.py`, `taleplerim.py`, `gd_calisma_alani.py` ve hatta
`mail_fetcher.py`'nin doğrulanmamış `From` başlığı — hepsi "Ali ↔ Ali Yılmaz"
tipi yanlış eşleşmeye açık `a in b or b in a` deseni kullanıyor. Bu,
sahipliğin `owner_user_id` gibi sabit bir UUID yerine değişebilir bir isim
metnine dayanmasından kaynaklanıyor. Kök neden: **mail'den gelen `From`
başlığı hiç doğrulanmadan `talep_eden_danisan` alanına yazılıyor**
(`mail_fetcher.py`), sonra bütün sahiplik/görünüm mantığı bu güvenilmez
isim üzerine kuruluyor.

### 3. Sessiz toplu pasifleştirme (en ciddi veri bütünlüğü riski)
`startkey_portfoy_listesi.py` ve `revy_sync.py`'de **bağımsız olarak aynı
hata**: dış kaynaktan (Revy/Startkey) eksik veya boş bir veri seti gelirse,
"export'ta yok = artık aktif değil" mantığıyla **gerçekten aktif olan
kayıtlar toplu halde pasife alınabiliyor**. Doğrulanmış/tam bir snapshot
kontrolü yok. Bu, tek bir eksik Excel indirmesiyle yüzlerce doğru kaydın
yanlışlıkla kapatılabileceği anlamına geliyor.

### 4. Impersonation gerçek kimliği eziyor
`kullanici_sec.py`'nin kodunu zaten gördük ve doğruladık: `st.session_state["kullanici"]`
impersonation sırasında hedef kişiyle **tamamen değiştiriliyor**, gerçek
aktör (`auth_user`) ayrı tutulmuyor. Bu, mail/RBAC turlarımızda kısmen
ele alındı (rol kontrolleri artık var) ama impersonation sırasında
**mutasyonların (düzenleme/silme/mail gönderme) engellenmediği** hâlâ geçerli.

### 5. `pickle.load()` + path traversal (arşiv sistemlerinde)
`pazar_analiz.py`, `pazar_raporu.py`, `startkey_portfoy_listesi.py`'nin
yerel "geçmiş arama" arşivleri — üçü de aynı deseni paylaşıyor: `index.json`
içinden gelen dosya adı doğrulanmadan path'e ekleniyor (`../../` riski) ve
`pickle.load()` ile açılıyor (güvenilmeyen veri = potansiyel kod çalıştırma).
Ayrıca bu arşivler **tüm kullanıcılar arasında ortak** (kullanıcıya özel değil).

### 6. Ham hata/traceback kullanıcıya gösteriliyor
Bunu `giris.py`/`app.py`'de zaten defalarca düzelttik. Aynı desen
`4_Ofis_Paneli.py`, `5_Mail_Islem.py`, `pazar_analiz.py`, `pazar_raporu.py`,
`revy_sync.py`, `rehber_app.py` gibi birçok dosyada tekrarlanıyor — bildiğimiz
bir düzeltme, sadece daha fazla yerde uygulanmalı.

### 7. `select("*")` + tüm tabloyu belleğe çekme
Performans turumuzda `3_Portfoy_Tablosu.py`/`2_Talep_Tablosu.py` için zaten
bildiğimiz bu desen, incelenen hemen her dosyada (rehber, arşiv, mail,
pazar, ofis paneli) tekrarlanıyor.

---

## Dosya dosya durum tablosu

| # | Dosya | Kod elimizde mi? | Not |
|---|---|---|---|
| 1 | `core/auth.py` | ✅ (biz yazdık) | Zaten düzeltildi (3 tur boyunca) |
| 2 | `core/personel_manager.py` | ✅ (biz yazdık) | Zaten düzeltildi |
| 3 | `pages/kullanici_sec.py` | ✅ (biz yazdık) | RBAC var; impersonation mutasyon engeli yok |
| 4 | `core/ui_helpers.py` | ✅ (biz yazdık) | Navigasyon turu tamamlandı |
| 5 | `app.py` | ✅ (biz yazdık) | Session-sync merkezi |
| 6 | `pages/giris.py` | ✅ (biz yazdık) | Debug temizliği yapıldı |
| 7 | `pages/profil.py` | ✅ (biz yazdık) | ad_soyad düzeltmesi yapıldı — **incelemedeki "regresyon" iddiası muhtemelen eski kopyaya bakılarak yazılmış, bizim son halimizde `ad_soyad` zaten Supabase payload'ından çıkarılmıştı** |
| 8 | `core/revy_kimlik.py` | ✅ kod var | secret_key fallback'i doğrulandı, düzeltilmedi |
| 9 | `pages/pazar_analiz.py` | ⚠️ kısmi (disk'te var, incelemede kod yok) | secret_key + pickle arşivi iddiaları doğrulanmalı |
| 10 | `core/revy_pazar_cek.py` | ❌ sadece inceleme | URL doğrulaması, checkpoint sorunları iddia edildi |
| 11 | `pages/startkey_portfoy_listesi.py` | ❌ sadece inceleme | **Sessiz toplu pasifleştirme** — öncelikli doğrulanmalı |
| 12 | `core/supabase_client.py` | ✅ kod var (7 satır) | **Koşulsuz secret_key — doğrulandı, en kolay düzeltme** |
| 13 | `pages/pazar_raporu.py` | ❌ sadece inceleme | Dönem/tampon veri karışması iddiası; "root'ta ikinci kopya var" iddiası **AI tarafından geri çekildi** (yanlış yorumlanmış upload yolu) |
| 14 | `pages/ana_sayfa.py` | ✅ (biz yazdık) | Bugün üzerinde çalıştık, HTML escape eksikliği hâlâ geçerli olabilir |
| 15 | `pages/3_Portfoy_Tablosu.py` | ⚠️ disk'te eski kopya var | Ofis/sahiplik filtresi yok iddiası — kendi incelememizle tutarlı |
| 16 | `pages/2_Talep_Tablosu.py` | ⚠️ disk'te eski kopya var | Aynı mimari desen (Portföy ile "kopya kod") |
| 17 | `pages/arsiv_merkezi.py` | ⚠️ disk'te eski kopya var | Mutasyon yok (salt okunur), ama select(*) + service-key geçerli |
| 18 | `pages/portfoylerím.py` | ✅ **düzeltildi ve push edildi** | Login guard eklendi, test edildi (ekran görüntüsüyle doğrulandı) |
| 19 | `pages/taleplerim.py` | ❌ sadece inceleme | İsim eşleşmesi + şablon deposu ortak/güvensiz |
| 20 | `core/match_engine.py` | ❌ sadece inceleme | `aktif is False` vs `is not True` ayrımı — mail_parser ile zincirleme risk |
| 21 | `core/mail_paylas.py` | ❌ sadece inceleme | Başka danışman adına mail, "Herkese Gönder" yetkisiz |
| 22 | `pages/gd_calisma_alani.py` | ✅ (biz yazdık) | İsim eşleşmesiyle sayım, 1000/1500 limit |
| 23 | `pages/rehber_app.py` | ❌ sadece inceleme | **`logo_dosya` ile keyfi dosya okuma iddiası — ciddi, öncelikli doğrulanmalı** |
| 24 | `pages/5_Mail_Islem.py` | ✅ (biz yazdık) | RBAC bugünkü haliyle uyumlu, job lock/audit yok |
| 25 | `core/mail_job.py` | ✅ kod var | Checkpoint/duplicate/transaction sorunları doğrulanabilir durumda |
| 26 | `core/mail_fetcher.py` | ✅ kod var | **`From` başlığı doğrulanmadan `talep_eden_danisan`'a yazılıyor — doğrulandı** |
| 27 | `core/mail_parser.py` | ❌ sadece inceleme | AI'nin `kapali_portfoy`/`aktif` alanlarını belirlemesi — match_engine ile zincir |
| 28 | `scripts/mail_auto_job.py` | ✅ kod var | AI varsayılan kapalı — doğrulandı, iyi haber |
| 29 | `.github/workflows/mail_auto_fetch.yml` | ✅ kod var | AI kapalı (workflow seviyesinde de) — doğrulandı |
| 30 | `pages/4_Ofis_Paneli.py` | ⚠️ disk'te eski kopya var | **Revy Sync butonu rol kontrolsüz — kendi bugünkü RBAC deseniyle hızlıca kapatılabilir** |
| 31 | `revy_sync.py` | ❌ sadece inceleme | Sessiz toplu pasifleştirme (Startkey ile aynı aile) |
| 32 | `pages/pazar_raporu.py` (tekrar) | — | "Root kopya" iddiası geri çekildi, tek dosya var |
| 33 | Genel değerlendirme/plan | — | Puanlama + Sprint planı; çerçeve olarak faydalı, uygulama biçimi olarak fazla ağır |

---

## Önerilen ilk adımlar (küçük, bağımsız, sırayla)

Bugüne kadarki çalışma tarzımızla uyumlu — her biri tek oturumda bitebilecek,
test edilebilir boyutta. **Sprint değil, tek tek adım.**

1. **`core/supabase_client.py`'yi düzelt** — `get_client()`'ın secret_key
   yerine publishable_key kullanmasını sağla (auth.py'deki düzeltmenin
   birebir tekrarı, 7 satırlık dosya, çok düşük risk)
2. **`4_Ofis_Paneli.py`'nin Revy Sync butonuna rol kontrolü ekle** — bugünkü
   RBAC deseniyle (`_rol not in (...)`) aynı, hızlı
3. **`4_Ofis_Paneli.py` ve `revy_sync.py`'deki ham traceback'leri temizle**
   — `giris.py`/`app.py`'de yaptığımızın tekrarı
4. **`rehber_app.py`'deki `logo_dosya` path traversal iddiasını doğrula** —
   gerçek dosyayı görüp kontrol etmek gerekiyor, ciddiye alınmalı
5. **`startkey_portfoy_listesi.py` ve `revy_sync.py`'deki "sessiz toplu
   pasifleştirme" mantığını incele** — bu, gerçek kodu görmeden düzeltilecek
   kadar basit değil, önce mevcut davranışı doğrulamak lazım
6. **Diğer aktif geliştirilen sayfalarda da login guard'ı hızlıca kontrol et**
   — `taleplerim.py`, `2_Talep_Tablosu.py`, `3_Portfoy_Tablosu.py` gibi
   üzerinde çok AI ile çalışılan dosyalarda `portfoylerím.py`'deki gibi bir
   kayıp olmadığından emin ol (tek tek dosyayı açıp `oturum_kontrol` araması
   yeterli, 5 dakikalık bir iş)

Bunlardan sonrası (impersonation salt-okunur yapma, isim yerine UUID
sahiplik, distributed lock, AI candidate/review modeli) **gerçek mimari
değişiklikler** — bunlar için ayrı, sakin, adım adım planlanmış turlar
gerekiyor. Şimdilik bu 6 maddeyle başlamak, hem gerçek risk azaltır hem de
bugüne kadarki başarılı çalışma temposunu korur.

---

## Bilinen düzeltmeler / geri çekilen iddialar

- **"Root'ta ikinci bir `pazar_raporu.py` var"** — AI kendi hatasını fark edip
  geri çekti; yükleme yolu proje klasör yapısını yansıtmadığı için yanlış
  yorumlanmış. Tek dosya var: `pages/pazar_raporu.py`.
- **`profil.py`'deki "ad_soyad regresyonu" iddiası** — muhtemelen bizim
  düzeltmemizden önceki bir kopyaya bakılarak yazılmış. Bizim elimizdeki son
  sürümde `ad_soyad` zaten Supabase payload'ından çıkarılmış durumda
  (`PGRST204` hatasını bulup düzelttiğimiz tur). Yine de bir kez elle
  kontrol etmekte fayda var.
- **`portfoylerím.py`'deki "login guard yok" iddiası** — **doğrulandı ve
  düzeltildi.** Meltem'in gerçek GitHub dosyasında guard gerçekten yoktu
  (dosya sonradan AI ile yoğun geliştirilirken kaybolmuş olmalı). Guard
  eklendi, test edildi, push edildi. Bkz. yukarıdaki "✅ ÇÖZÜLDÜ" bölümü.

---

## Bir sonraki oturuma not

Eğer bu belgeyi yeni bir Claude oturumunda okuyorsan: Meltem üç aydır kod
yazıyor, AI ile pair-programming yapıyor, `karma_app` adlı bir Streamlit +
Supabase CRM'i tek başına geliştiriyor (Startkey Zeta gayrimenkul ofisi
için). Şimdiye kadar üç güvenlik/performans turu tamamlandı
(`SECURITY_NOTES.md`'de kayıtlı), bu belge dördüncü turun (kapsamlı teknik
borç taraması) özeti. Çalışma tarzı: **her adım küçük, tek dosyalık, test
edilip onaylandıktan sonra bir sonrakine geçiliyor — asla toplu, büyük
değişiklik paketleri yapılmıyor.** Bu disiplini bozma.
