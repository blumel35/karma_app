# Karma App — Güvenlik & Session Sertleştirme Notları

**Başlangıç:** 15 Temmuz 2026
**Kapsam:** `app.py`, `ui_helpers.py` teknik borç incelemesiyle başlayan, oturum yönetimi ve
erişim kontrolü etrafında yoğunlaşan bir düzeltme turu. Bu dosya, "neden böyle yapıldı"
bilgisini kaybetmemek için tutuluyor — ileride bir kod bloğuna bakıp "bu gerçekten
gerekli mi?" diye şüphelenmemek için.

---

## Neden bu tur başladı

`app.py` ve `ui_helpers.py` üzerinde yapılan bir teknik borç incelemesi, uygulamada
**sayfa bazlı giriş kontrolünün tutarsız** olduğunu ortaya çıkardı: bazı sayfalar
girişsiz erişime tamamen açıktı. Bu da bizi oturum yönetiminin temeline (`auth.py`,
`personel_manager.py`) götürdü ve orada iki gerçek güvenlik açığı bulundu (aşağıda
Adım 1 ve 2). Bunları düzeltmeden sayfalara login guard eklemenin bir anlamı yoktu —
temel sağlam olmadan üstüne inşa etmek riskliydi.

---

## Tamamlanan adımlar

### ✅ Adım 1 — Local session restore artık "fail-closed"

**Sorun neydi:**
`core/auth.py`'de `LOCAL_SESSION_RESTORE = True` sabit olarak açıktı. Bunun cloud'da
(Streamlit Community Cloud) otomatik kapanacağı varsayılıyordu çünkü
`core/personel_manager.py` içinde bir kontrol vardı:
```python
if os.environ.get("HOME", "").startswith("/home/adminuser"):
    return None
```
Bu kontrol **yanlış path'e bakıyordu** — Streamlit Community Cloud'da gerçek `HOME`
değeri `/home/appuser`'dır, `/home/adminuser` değil. Yani bu "otomatik kapanma"
hiçbir zaman tetiklenmiyordu ve dosya tabanlı session restore muhtemelen cloud'da da
aktif kalıyordu. Bu, geçmişte tam olarak "kullanıcı karışması" riskinden dolayı bir
kez kapatılmış olan bir özellikti — path heuristiğine güvenilerek yeniden açılmıştı
ama heuristik baştan yanlıştı.

**Ne yapıldı:**
- `LOCAL_SESSION_RESTORE` artık **varsayılan olarak kapalı**.
- Yalnızca açıkça, aşağıdaki yollardan biriyle etkinleştirilirse çalışıyor:
  ```toml
  # .streamlit/secrets.toml
  [app]
  local_session_restore = true
  ```
  ya da `LOCAL_SESSION_RESTORE=true` ortam değişkeni.
- Ayar tanımsızsa, hatalıysa veya `"1"`/`"yes"` gibi beklenmedik bir değerse **kapalı**
  kabul ediliyor — belirsizlik durumunda güvenli tarafta kalınıyor.
- `personel_manager.py`'deki HOME path kontrolü de doğru string'e (`/home/appuser`)
  düzeltildi, ama bu artık **ikincil bir savunma katmanı** — asıl güvenlik sınırı
  `auth.py`'deki bayrak.

**Değişen dosyalar:** `core/auth.py`, `core/personel_manager.py`

**Senin yapman gereken (lokal geliştirme için):**
Kendi makinende session restore'u kullanmaya devam etmek istiyorsan
`.streamlit/secrets.toml`'una `[app] local_session_restore = true` eklemen gerekiyor.
Cloud'da hiçbir şey eklemene gerek yok — orada kapalı kalması doğru davranış.

**Test edildi ve doğrulandı:** ✅ (15 Temmuz 2026 — sunucu yeniden başlatıldığında
bayraksız durumda tekrar giriş istedi, bayrak eklenince hatırladı)

---

### ✅ Adım 2 — Normal Supabase client'tan `secret_key` fallback'i kaldırıldı

**Sorun neydi:**
`core/auth.py`'deki `_get_supa()` fonksiyonu, normal (yetkisiz seviye) client için
anahtar ararken şu sırayı izliyordu:
```python
key = (SUPABASE_KEY env) or (secrets SUPABASE_KEY) or (publishable_key) or (secret_key)
```
Son basamak sorunluydu: eğer `publishable_key` secrets'ta tanımlı değilse (örn. bir
deploy hatası ya da eksik ayar yüzünden), uygulama **sessizce service/secret
anahtarıyla** çalışmaya devam edebiliyordu. Bu, Supabase'in RLS (row-level security)
korumasını fiilen devre dışı bırakabilecek bir durumdu — normalde her kullanıcının
sadece kendi/yetkili olduğu veriyi görmesini sağlayan katman.

**Ne yapıldı:**
`secret_key` fallback'i normal client'ın anahtar zincirinden kaldırıldı. Artık
`publishable_key` (veya `SUPABASE_KEY`) tanımlı değilse, `_get_supa()` sessizce
yüksek yetkiye düşmek yerine `None` döner — çağıran kodlar zaten `if not supa: ...`
ile bunu güvenli şekilde ele alıyor.

`use_service_key=True` ile çağrılan dal (Storage yüklemeleri için) **dokunulmadı** —
orası zaten bilerek yüksek yetki kullanması gereken yer.

**Değişen dosyalar:** `core/auth.py`

**Test edildi ve doğrulandı:** ✅ (15 Temmuz 2026 — `secrets.toml`'da `publishable_key`
zaten tanımlı olduğu için hiçbir davranış değişikliği gözlenmedi, giriş ve veri
sayfaları normal çalıştı)

---

### ✅ Adım 3 — Debug/ham hata çıktıları kullanıcıdan gizlendi

**Sorun neydi — üç ayrı yerde aynı desen:**

1. **`pages/giris.py`** — şifre yanlış girildiğinde kod, Supabase'e **ikinci bir auth
   denemesi** yapıp ham `res` (auth response) objesini `st.write()` ile ekrana
   basıyordu. Bu response normalde `access_token`/`refresh_token` içerir — nadir bir
   durumda bu ikinci deneme başarılı dönerse, oturum bilgileri **girişsiz herhangi bir
   ziyaretçinin ekranına** yazdırılabilirdi. Ayrıca başarısızlık durumunda da ham
   exception metni gösteriliyordu.

2. **`app.py`** — session restore sırasında `⏱ import:`, `⏱ load_login_session:` gibi
   zamanlama çıktıları her sayfa yüklemesinde herkese görünüyordu, ayrıca
   `st.warning(f"Session restore hatası: {e}")` ham exception metnini gösteriyordu
   (dosya yolu, altyapı detayı sızabilirdi).

3. **`core/auth.py`** — `giris_yap()` içinde `st.error(f"Giriş hatası: {e}")` yine ham
   exception metnini ekrana basıyordu.

**Ne yapıldı:**
Üçünde de kullanıcıya gösterilen mesaj sadeleştirildi (örn. "E-posta veya şifre
hatalı."), ham hata detayı `logging.exception()` ile **terminale/log'a** yazılıyor —
geliştirme sırasında sen görebiliyorsun, son kullanıcı göremiyor.
`giris.py`'deki gereksiz ikinci auth denemesi tamamen kaldırıldı.

**Değişen dosyalar:** `core/auth.py`, `pages/giris.py`, `app.py`

**Test durumu:** ✅ Tamamlandı ve push edildi (15 Temmuz 2026). Terminaldeki
`logging.exception()` çıktısıyla doğrulandı — yanlış şifre denemesinde kullanıcı
sadece "E-posta veya şifre hatalı." görüyor, ham hata terminalde kalıyor.

---

### ✅ Adım 4 — Eksik 9 sayfaya `oturum_kontrol()` dağıtımı

**Sorun neydi:**
Şu sayfalarda hiç login kontrolü yoktu, herhangi biri URL'yi bilse doğrudan
erişebiliyordu:
- `pages/2_Talep_Tablosu.py`, `pages/3_Portfoy_Tablosu.py`,
  `pages/4_Ofis_Paneli.py`, `pages/5_Mail_Islem.py`, `pages/arsiv_merkezi.py`,
  `pages/eslestirme_motoru.py`, `pages/portfoylerím.py`, `pages/rehber_app.py`,
  `pages/taleplerim.py`

**Ne yapıldı:**
Her sayfaya, `render_navbar()` çağrısından hemen önce şu guard eklendi:
```python
from core.auth import oturum_kontrol
if not oturum_kontrol():
    st.switch_page("pages/giris.py")
```
`4_Ofis_Paneli.py`'de `render_navbar()` bir `with h1:` sütun bloğunun içinde
çağrıldığı için guard oraya değil, dosyanın import bloğunun hemen ardına
(sayfa düzeni başlamadan önce) eklendi.

**Değişen dosyalar:** yukarıdaki 9 sayfa

**Test durumu:** ✅ Tamamlandı ve push edildi (15 Temmuz 2026). Normal giriş
akışı ve sayfa geçişleri doğrulandı. Test sırasında Talep/Portföy/Arşiv
sayfalarında ara sıra görülen "yasak işareti" davranışının bu değişiklikle
ilgisi olmadığı, sayfaların kendi ağırlığından (büyük veri çekimi, karmaşık
UI) kaynaklandığı doğrulandı — bkz. "Bu turun dışında bırakılan" bölümündeki
performans maddeleri.

---

### ✅ Adım 5 — Session-sync kodunun tekilleştirilmesi

**Sorun neydi:**
`core/auth.py`'de `_set_session_fields()` adında merkezi bir fonksiyon vardı
ama `giris.py`, `app.py`, `profil.py`, `ana_sayfa.py` aynı mantığı (kullanıcı
adı/rol/baş harf hesaplama) kendi içlerinde ayrı ayrı tekrar yazmıştı.

**Ne yapıldı:**
- `_set_session_fields()` genel kullanıma açıldı: `set_session_fields()`
  (alt çizgi kaldırıldı).
- 4 dosyadaki kopya kod blokları silindi, yerine `set_session_fields(kullanici)`
  çağrısı kondu.
- **Test sırasında bulunan yan hata:** `profil.py`'de "Bilgileri Kaydet"
  düzeltilirken `ad_soyad` diye bir Supabase kolonu olduğu varsayılmıştı —
  yanlıştı (`PGRST204: Could not find the 'ad_soyad' column` hatası verdi).
  Düzeltildi: `ad_soyad` artık sadece session (bellek) içinde tutuluyor,
  Supabase'e gönderilmiyor.
- **Bilinen kalıcılık sınırı (aksiyon gerektirmiyor, bilgi amaçlı):**
  `core/personel_manager.py`'deki `enrich_session_from_personel()`, isim
  bilgisini **Excel tabanlı bir personel listesinden** okuyup her girişte
  `ad`/`ad_soyad` üzerine yazıyor. Yani `profil.py`'den yapılan bir isim
  değişikliği o oturumda görünür ama bir sonraki girişte Excel'deki değer
  tekrar üste yazabilir. Bu, kalıcı bir isim değişikliği istenirse ayrıca ele
  alınması gereken bir konu — şu an için aksiyon alınmadı, sadece not edildi.

**Değişen dosyalar:** `core/auth.py`, `pages/giris.py`, `app.py`,
`pages/profil.py`, `pages/ana_sayfa.py`

**Test durumu:** ✅ Tamamlandı ve push edildi (15 Temmuz 2026).

---

### ✅ Adım 6 — Inline login kontrollerinin merkezi helper'a taşınması

**Sorun neydi:**
`gd_calisma_alani.py` ve `kullanici_sec.py`, `oturum_kontrol()` yerine kendi
inline `if not st.session_state.get("kullanici"): ...` kontrolünü yazmıştı.

**Ne yapıldı:**
İkisi de `oturum_kontrol()` çağrısına bağlandı. `kullanici_sec.py`'deki ek rol
kontrolü (`admin`/`broker` dışındakileri reddeden ikinci katman) olduğu gibi
korundu — sadece login kısmı merkezileştirildi.

**Değişen dosyalar:** `pages/gd_calisma_alani.py`, `pages/kullanici_sec.py`

**Test durumu:** ✅ Tamamlandı ve push edildi (15 Temmuz 2026).

---

## 🎉 Altı adımlık güvenlik ve oturum sağlamlaştırma turu tamamlandı

Tur boyunca elde edilenler:
- Cloud'da session karışması riski kapatıldı (fail-closed restore)
- Normal Supabase client artık sessizce yüksek yetkiye düşemiyor
- Kullanıcıya ham hata/debug bilgisi sızdırılmıyor
- Daha önce tamamen açık olan 9 sayfa artık girişsiz erişilemiyor
- Kullanıcı session bilgisi tek bir merkezi fonksiyondan (`set_session_fields`)
  yönetiliyor, 6 farklı kopya kod kaldırıldı
- Login kontrolü artık her yerde aynı fonksiyona (`oturum_kontrol`) dayanıyor

---

## Bu turun dışında bırakılan, ayrı bir tur olarak ele alınacak konular

- **RBAC / rol bazlı sayfa erişimi** — şu an sadece "giriş yapmış mı" kontrol
  ediliyor, "hangi rol neyi görebilir" henüz yok (`ui_helpers.py`'deki `_can_see`
  altyapısı var ama tüm izin listeleri boş `[]`)
- **3 navigasyon kaynağının tekilleştirilmesi** (`app.py`'deki `st.Page` kayıtları,
  `ui_helpers.py`'deki `_NAV_SECTIONS`, eski `get_panel_links()`) — bazı sayfalar
  sidebar'dan düşmüş durumda (`eslestirme_motoru.py`, `portfoy_listesi.py`)
- **HTML injection yüzeyinin kapatılması** — `unsafe_allow_html` içine escape'siz
  giren `user_name`, `role_label`, `_imp_ad` gibi alanlar
- **Kozmetik/performans maddeleri** — logo/avatar base64 cache'lenmiyor,
  `render_navbar()` 301 satırlık tek fonksiyon, `portfoylerím.py` dosya adındaki
  ASCII olmayan karakter, aktif sayfa CSS sarmalama tekniğinin güvenilirliği

---

## Genel prensip (bu tur boyunca izlenen)

Değişiklikler **tek tek, sırayla** uygulandı — hepsini tek pakette yapmak yerine her
adım ayrı test edilip onaylandıktan sonra bir sonrakine geçildi. Bu, bir şey ters
giderse hangi değişikliğin sebep olduğunu bulmayı kolaylaştırıyor ve production'da
(cloud) sürpriz bir kırılma riskini azaltıyor.
