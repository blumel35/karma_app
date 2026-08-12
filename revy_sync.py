"""
revy_sync.py
Revy'den Zeta ofis portföylerini çeker, Supabase'e yazar.
revy_otomasyon.py'nin Selenium kısmı korundu, Excel yerine Supabase kullanılır.
"""

import os
import re
import time
import shutil
from pathlib import Path
from datetime import datetime
from email.utils import format_datetime

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# =============================================
# TUR 2B — Hesap doğrulama
# =============================================
# Revy'de her ofis hesabı belirli bir kullanıcı adına açılıyor. Sayfada bu
# adın gerçekten göründüğünü kontrol ederek "doğru hesaba/ofise girdik mi"
# sorusuna somut bir cevap üretiyoruz. İsim değişirse burası güncellenmeli.
REVY_HESAP_ADLARI = {
    1: "Meltem Bulu",
    2: "Pınar Can",
}

# Hesap numarasının hangi ofis kaynağına karşılık geldiğinin sabit
# eşlemesi. tek_ofis_sync()'in başında, export/DB işlemine hiç
# girmeden önce parametre tutarlılığını doğrulamak için kullanılıyor —
# yanlış hesap_no/kaynak_ofis/hedef_url kombinasyonuyla çağrılırsa
# (örn. bir kod hatası sonucu) Zeta 1 verisinin Zeta 2 kaynağına
# yazılmasını engelliyor. Bu, gerçek DOM tabanlı ofis doğrulamasının
# (ilani_urline_git() içindeki "Merhaba, {isim}" kontrolü) yerine
# geçmez — o hâlâ ayrıca çalışıyor.
REVY_HESAP_OFIS_ESLESMESI = {
    1: "zeta1",
    2: "zeta2",
}

# Tüm URL kolon adı adaylarının tek, paylaşılan kaynağı. Eskiden
# df_to_supabase() ve tek_ofis_sync() farklı listeler kullanıyordu
# (tek_ofis_sync()'in duplicate temizliğinde "Link" eksikti) — bu da
# "Link" başlıklı bir export'ta aynı ilanın iki kez insert edilmesine
# yol açabiliyordu.
URL_KOLON_ADAYLARI = ["İlan Url", "İlan Linki", "URL", "Link"]

# TUR 2B — kontrollü pasifleştirme HENÜZ ÜRETİME AÇILMADI.
# İki bağımsız AI incelemesinin ortak, kesin talebi: reactivation (pasif
# ilan tekrar gelirse aktifleştirme), canonical ilan kimliği (ham URL
# karşılaştırması yerine), ve mevcut kayıtların sayfalı/eksiksiz çekilmesi
# tamamlanmadan bu sabit False kalacak. evaluate_snapshot_eligibility()
# teorik olarak can_deactivate=True dönse bile, bu sabit onu geçersiz
# kılıyor — "karar modeli doğru ama koşullar henüz sağlanmadı" ayrımını
# somutlaştırıyor. Yalnızca aşağıdaki üçü tamamlanınca True yapılmalı:
#   1. Mevcut aktif+pasif kayıtlar sayfalı (.range()) ve eksiksiz çekiliyor
#   2. Canonical ilan kimliği (ilan_no_cek() gerçekten kullanılıyor)
#   3. Reactivation: pasif kayıt tekrar gelirse aynı ID üzerinde aktif=True
PASIFLESTIRME_URETIME_HAZIR = False

# =============================================
# AYARLAR — önce Streamlit Secrets ([revy]), yoksa ayarlar.txt (mevcut yapı)
# =============================================
def ayarlari_oku():
    # Streamlit Community Cloud'da ayarlar.txt dosyası deploy ortamında
    # bulunmuyor. Önce Secrets içindeki [revy] bölümünü deniyoruz; bu
    # başarısız olursa (local çalıştırma, Streamlit dışı çalıştırma veya
    # [revy] tanımlı değilse) mevcut ayarlar.txt davranışına aynen düşülüyor.
    # NOT: Secrets içeriği hiçbir şekilde loglanmıyor/yazdırılmıyor.
    try:
        import streamlit as st
        if "revy" in st.secrets:
            return dict(st.secrets["revy"])
    except Exception:
        pass

    # DÜZELTME (12.08.2026 — GitHub Actions entegrasyonu): Streamlit
    # Secrets yoksa (CI dahil), ikinci öncelik olarak environment
    # variable'lardan okunuyor — geçici dosya YOK, secret değerleri hiç
    # diske yazılmıyor. Bu katman SADECE ilgili env var'lardan en az biri
    # set edilmişse devreye girer (yani sıradan local çalıştırmada devre
    # dışı kalır, mevcut ayarlar.txt davranışını etkilemez). Zorunlu Revy
    # alanlarından biri eksikse SESSİZCE DEVAM ETMİYOR — anlaşılır bir
    # hata fırlatıp veri yazma işlemine hiç geçmiyor. Hiçbir secret
    # değeri (yalnızca hangi ayarın eksik olduğu) hata mesajına giriyor.
    _env_eslesme = {
        "revy_giris_url": "REVY_GIRIS_URL",
        "revy1_kullanici": "REVY1_KULLANICI",
        "revy1_sifre": "REVY1_SIFRE",
        "revy1_ofis_aktif_url": "REVY1_OFIS_AKTIF_URL",
        "revy2_kullanici": "REVY2_KULLANICI",
        "revy2_sifre": "REVY2_SIFRE",
        "revy2_ofis_aktif_url": "REVY2_OFIS_AKTIF_URL",
        "supabase_url": "SUPABASE_URL",
        "supabase_key": "SUPABASE_SECRET_KEY",
    }
    _revy_env_adlari = [
        v for k, v in _env_eslesme.items() if k not in ("supabase_url", "supabase_key")
    ]
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true" or any(
        os.environ.get(env_adi) for env_adi in _revy_env_adlari
    ):
        ayarlar = {
            yerel_ad: os.environ[env_adi]
            for yerel_ad, env_adi in _env_eslesme.items()
            if os.environ.get(env_adi)
        }
        _revy_zorunlu = [
            "revy_giris_url", "revy1_kullanici", "revy1_sifre",
            "revy1_ofis_aktif_url", "revy2_kullanici", "revy2_sifre",
            "revy2_ofis_aktif_url",
        ]
        eksikler = [k for k in _revy_zorunlu if not ayarlar.get(k)]
        if eksikler:
            raise RuntimeError(
                "Environment variable modu tespit edildi ama zorunlu Revy "
                f"ayarlarından {len(eksikler)} tanesi eksik: "
                f"{', '.join(_env_eslesme[k] for k in eksikler)}. "
                "Veri yazma işlemine geçilmiyor."
            )
        return ayarlar

    base_dir = os.path.dirname(os.path.abspath(__file__))
    ayar_dosyasi = os.path.join(base_dir, "ayarlar.txt")
    if not os.path.exists(ayar_dosyasi):
        ayar_dosyasi = os.path.join(os.path.dirname(base_dir), "ayarlar.txt")

    ayarlar = {}
    with open(ayar_dosyasi, "r", encoding="utf-8") as f:
        for satir in f:
            satir = satir.strip()
            if not satir or satir.startswith("#"):
                continue
            if "=" in satir:
                k, v = satir.split("=", 1)
                ayarlar[k.strip()] = v.strip()
    return ayarlar


# =============================================
# SUPABASE CLIENT
# =============================================
def get_supabase():
    from supabase import create_client
    try:
        # Streamlit secrets'tan oku (karma_app içinden çağrıldığında)
        import streamlit as st
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["secret_key"]
    except Exception:
        # Standalone çalıştırıldığında (local ayarlar.txt VEYA GitHub
        # Actions environment variable'ları) ayarlari_oku() üzerinden
        # oku — env var desteği zaten orada tanımlı, burada AYRICA
        # tekrarlanmıyor (tek kaynak, minimal diff).
        ayarlar = ayarlari_oku()
        url = ayarlar.get("supabase_url", "")
        key = ayarlar.get("supabase_key", "")
    if not url or not key:
        raise Exception("Supabase bilgileri bulunamadı!")
    return create_client(url, key)


# =============================================
# DOSYA / KLASÖR
# =============================================
def klasor_hazirla(ana_klasor, alt_klasor):
    klasor = Path(ana_klasor) / alt_klasor
    klasor.mkdir(parents=True, exist_ok=True)
    return str(klasor.resolve())


def export_klasorunu_temizle(klasor):
    klasor = Path(klasor)
    klasor.mkdir(parents=True, exist_ok=True)
    for f in klasor.glob("*"):
        try:
            if f.is_file() and f.suffix.lower() in [".xlsx", ".xls", ".csv", ".crdownload"]:
                f.unlink()
        except Exception:
            pass


# =============================================
# SELENIUM DRIVER
# =============================================
def driver_olustur(indirilen_klasor):
    # DÜZELTME (12.08.2026 — GitHub Actions entegrasyonu): CI ortamının
    # (GitHub Actions runner'ı) ekranı/görüntü sunucusu yok — normal
    # (headful) Chrome orada hiç açılamaz. GITHUB_ACTIONS ortam
    # değişkeni GitHub'ın kendi runner'larında OTOMATİK "true" olarak
    # set edilir (resmi dokümantasyon) — bu yüzden elle bir bayrak
    # eklemeye gerek yok, CI'da mı çalıştığımızı buradan güvenilir
    # şekilde anlıyoruz. Yerelde (VS Code) hiçbir şey değişmiyor,
    # tarayıcı eskisi gibi görünür açılmaya devam ediyor — headless
    # SADECE CI'da devreye giriyor.
    ci_ortami = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"

    options = Options()
    prefs = {
        "download.default_directory": str(Path(indirilen_klasor).resolve()),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-allow-origins=*")

    if ci_ortami:
        # "--headless=new" (eski "--headless" değil) modern Chrome'un
        # gerçek Chrome render motorunu kullanıyor — eski headless
        # modda bazı sitelerin bot-tespiti/JS davranışı farklılaşabiliyordu.
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    if not ci_ortami:
        driver.maximize_window()
    return driver


# =============================================
# LOGIN
# =============================================
def revy_login(driver, wait, ayarlar, hesap_no):
    driver.get(ayarlar["revy_giris_url"])
    time.sleep(2)

    giris_ac = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Giriş')] | //a[contains(., 'Giriş')]"))
    )
    driver.execute_script("arguments[0].click();", giris_ac)
    time.sleep(2)

    inputs = wait.until(
        EC.presence_of_all_elements_located(
            (By.XPATH, "//div[contains(@class,'modal') or contains(@class,'popup') or @role='dialog']//input | //input")
        )
    )

    telefon = None
    sifre = None

    for inp in inputs:
        try:
            tip = (inp.get_attribute("type") or "").lower()
            placeholder = (inp.get_attribute("placeholder") or "").lower()
            if tip == "password":
                sifre = inp
            elif "cep" in placeholder or "telefon" in placeholder or tip in ["text", "tel"]:
                if inp.is_displayed() and inp.is_enabled():
                    telefon = inp
        except Exception:
            pass

    if telefon is None:
        raise Exception("Telefon alanı bulunamadı.")
    if sifre is None:
        raise Exception("Şifre alanı bulunamadı.")

    driver.execute_script("arguments[0].focus();", telefon)
    driver.execute_script("arguments[0].value = '';", telefon)
    driver.execute_script("arguments[0].value = arguments[1];", telefon, ayarlar[f"revy{hesap_no}_kullanici"])
    driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles:true}));", telefon)
    driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}));", telefon)

    driver.execute_script("arguments[0].focus();", sifre)
    driver.execute_script("arguments[0].value = '';", sifre)
    driver.execute_script("arguments[0].value = arguments[1];", sifre, ayarlar[f"revy{hesap_no}_sifre"])
    driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles:true}));", sifre)
    driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}));", sifre)

    giris_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Giriş Yap')] | //button[contains(., 'Giriş')]"))
    )
    driver.execute_script("arguments[0].click();", giris_btn)

    # TUR 2B: sabit "5 saniye bekle, başarılı say" yerine, giriş formunun
    # (şifre alanı) sayfadan kaybolmasını bekliyoruz — bu, önceki koddan
    # daha güçlü ama hâlâ kesin olmayan bir sinyal. Asıl doğrulama
    # ilani_urline_git()'te hesap adı kontrolüyle yapılıyor.
    try:
        wait.until(EC.invisibility_of_element_located((By.XPATH, "//input[@type='password']")))
    except Exception:
        pass
    time.sleep(2)


# =============================================
# SAYFA GİT
# =============================================
def ilani_urline_git(driver, wait, hedef_url, beklenen_hesap_adi=None):
    driver.get(hedef_url)
    time.sleep(5)
    wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//*[contains(text(),'İlan')] | //table | //div[contains(@class,'table')]")
        )
    )
    print(f"Sayfaya gidildi: {hedef_url}")

    # TUR 2B: sayfada beklenen hesap adının gerçekten göründüğünü kontrol
    # et. Yalnızca ismin sayfanın herhangi bir yerinde geçmesi yeterli
    # değil (bir danışman/müşteri kaydında aynı isim geçebilir) — Revy'nin
    # sağ üst köşesindeki "Merhaba, {isim}" karşılama metnini arıyoruz.
    # Bu, isim + "Merhaba" kelimesinin yakın mesafede birlikte geçmesini
    # şart koşarak yanlış pozitif riskini büyük ölçüde azaltıyor.
    if not beklenen_hesap_adi:
        return False
    try:
        sayfa_metni = driver.find_element(By.TAG_NAME, "body").text
        return _merhaba_deseni_gecer_mi(sayfa_metni, beklenen_hesap_adi)
    except Exception:
        return False


def _merhaba_deseni_gecer_mi(sayfa_metni: str, beklenen_ad: str) -> bool:
    """"Merhaba, {isim}" / "Merhaba {isim}" karşılama metninin sayfada
    gerçekten geçip geçmediğini kontrol eder. İsmin tek başına sayfanın
    herhangi bir yerinde geçmesinden (yanlış pozitif riski) daha güvenilir
    bir sinyal — "Merhaba" ile isim arasında en fazla birkaç karakter
    (virgül/boşluk) olmasını şart koşuyor."""
    if not sayfa_metni or not beklenen_ad:
        return False
    desen = re.compile(
        r"merhaba[,\s]{0,3}" + re.escape(beklenen_ad),
        re.IGNORECASE,
    )
    return bool(desen.search(sayfa_metni))


# =============================================
# EXCEL AKTAR
# =============================================
def excel_aktar(driver, wait):
    time.sleep(2)
    xpathler = [
        "//*[contains(text(), 'Excel') and contains(text(), 'Aktar')]",
        "//*[contains(text(), \"Excel'e Aktar\")]",
        "//a[contains(., 'Excel')]",
        "//button[contains(., 'Excel')]",
    ]
    for xp in xpathler:
        try:
            eleman = wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", eleman)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", eleman)
            print("Excel'e Aktar butonuna basıldı.")
            return
        except Exception:
            pass
    raise Exception("Excel'e Aktar butonu bulunamadı.")


def indirilen_dosyayi_bekle(indirilen_klasor, hedef_ad, tiklama_zamani, timeout=180):
    klasor = Path(indirilen_klasor)
    baslangic = time.time()
    while time.time() - baslangic < timeout:
        dosyalar = [f for f in klasor.glob("*") if f.is_file()]
        if any(str(f).lower().endswith(".crdownload") for f in dosyalar):
            time.sleep(2)
            continue
        uygunlar = [
            f for f in dosyalar
            if f.suffix.lower() in [".xlsx", ".xls", ".csv"]
            and f.stat().st_mtime >= tiklama_zamani
        ]
        if uygunlar:
            en_yeni = max(uygunlar, key=lambda x: x.stat().st_mtime)
            hedef_yol = klasor / hedef_ad
            if hedef_yol.exists():
                hedef_yol.unlink()
            shutil.move(str(en_yeni), str(hedef_yol))
            print(f"Dosya kaydedildi: {hedef_yol}")
            return str(hedef_yol)
        time.sleep(2)
    raise Exception(f"Dosya {timeout} saniyede indirilemedi.")


def export_al(driver, wait, klasor, hedef_ad):
    export_klasorunu_temizle(klasor)
    tiklama_zamani = time.time()
    excel_aktar(driver, wait)
    return indirilen_dosyayi_bekle(klasor, hedef_ad, tiklama_zamani)


# =============================================
# EXCEL OKUMA
# =============================================
def excel_oku(dosya_yolu):
    ext = Path(dosya_yolu).suffix.lower()
    if ext == ".csv":
        try:
            return pd.read_csv(dosya_yolu, encoding="utf-8-sig")
        except Exception:
            return pd.read_csv(dosya_yolu, encoding="latin1")
    return pd.read_excel(dosya_yolu)


def kolon_bul(df, adaylar):
    mevcut = {str(col).strip().lower(): col for col in df.columns}
    for aday in adaylar:
        if aday.strip().lower() in mevcut:
            return mevcut[aday.strip().lower()]
    return None


def gecerli_http_url_mi(value) -> bool:
    """
    Gerçek, satır bazlı URL doğrulaması — eski `.str.startswith("http")`
    kontrolü "httpjunk" gibi geçersiz değerleri de kabul ediyordu.
    `urlparse` ile şema (http/https) ve netloc (domain) kontrolü yapılıyor.
    Portal linkleri farklı domainlerden gelebileceği için tek bir domain
    allowlist'i zorunlu tutulmuyor, yalnızca yapısal geçerlilik aranıyor.
    """
    from urllib.parse import urlparse
    try:
        parsed = urlparse(str(value).strip())
        return parsed.scheme.lower() in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def ilan_no_cek(url):
    try:
        return str(url).strip().rstrip("/").split("/")[-1]
    except Exception:
        return None


# =============================================
# SUPABASE'E YAZMA
# =============================================
# =============================================
# TUR 2B — Saf karar fonksiyonu (DB/Selenium'dan bağımsız, test edilebilir)
# =============================================
def evaluate_snapshot_eligibility(metadata: dict) -> dict:
    """
    Hiçbir veritabanı işlemi yapmadan, yalnızca girdi metadata'sına bakarak
    yazma ve pasifleştirme izinlerini hesaplar. Gerçek Revy/Supabase
    bağlantısına ihtiyaç duymadan tablo şeklinde test edilebilir.

    Beklenen metadata alanları:
        source_valid, account_verified, office_verified, schema_valid,
        full_scope, all_segments_succeeded: bool
        valid_record_count, parse_error_count, write_error_count: int
        anomaly_check_passed: bool

    Döner:
        {
            "can_write": bool,
            "can_deactivate": bool,
            "snapshot_status": "complete" | "partial" | "invalid",
            "skip_reasons": [str, ...],  # kod tabanlı, makine okunabilir
        }
    """
    source_valid = bool(metadata.get("source_valid", False))
    account_verified = bool(metadata.get("account_verified", False))
    office_verified = bool(metadata.get("office_verified", False))
    schema_valid = bool(metadata.get("schema_valid", False))
    full_scope = bool(metadata.get("full_scope", False))
    all_segments_succeeded = bool(metadata.get("all_segments_succeeded", False))
    valid_record_count = int(metadata.get("valid_record_count", 0))
    parse_error_count = int(metadata.get("parse_error_count", 0))
    write_error_count = int(metadata.get("write_error_count", 0))
    anomaly_check_passed = bool(metadata.get("anomaly_check_passed", False))

    skip_reasons = []
    if not source_valid:
        skip_reasons.append("source_invalid")
    if not account_verified:
        skip_reasons.append("account_unverified")
    if not office_verified:
        skip_reasons.append("office_unverified")
    if not schema_valid:
        skip_reasons.append("schema_invalid")

    can_write = source_valid and account_verified and office_verified and schema_valid

    if not full_scope:
        skip_reasons.append("scope_incomplete")
    if not all_segments_succeeded:
        skip_reasons.append("segment_failure")
    if parse_error_count > 0:
        skip_reasons.append("parse_errors_present")
    if write_error_count > 0:
        skip_reasons.append("write_errors_present")
    if valid_record_count <= 0:
        skip_reasons.append("no_valid_records")
    if not anomaly_check_passed:
        skip_reasons.append("anomalous_record_drop")

    can_deactivate = (
        can_write
        and full_scope
        and all_segments_succeeded
        and valid_record_count > 0
        and parse_error_count == 0
        and write_error_count == 0
        and anomaly_check_passed
    )

    if not can_write:
        snapshot_status = "invalid"
    elif can_deactivate:
        snapshot_status = "complete"
    else:
        snapshot_status = "partial"

    return {
        "can_write": can_write,
        "can_deactivate": can_deactivate,
        "snapshot_status": snapshot_status,
        "skip_reasons": skip_reasons,
    }


def build_sync_result(**overrides) -> dict:
    """
    Tüm erken/normal dönüşlerin AYNI alanları taşıması için tek, paylaşılan
    sonuç şablonu. Varsayılanlar "en güvenli durum" (hiçbir şey yazılmadı,
    hiçbir şey pasiflenmedi) — bir çağıran yeni bir alan eklemeyi unutursa
    bile sonuç güvenli tarafta kalır.
    """
    result = {
        "durum": "failed",
        "snapshot_status": "invalid",
        "mode": "blocked",
        "sync_run_id": None,
        "takip_kodu": None,
        "eklenen": 0,
        "guncellenen": 0,
        "raw_record_count": 0,
        "duplicate_record_count": 0,
        "runtime_duplicate_count": 0,
        "unique_record_count": 0,
        "valid_record_count": 0,
        "existing_record_count": 0,
        "deactivation_candidate_count": 0,
        "parse_error_count": 0,
        "write_error_count": 0,
        "deactivation_error_count": 0,
        "reactivated": 0,
        "deactivated": 0,
        "hesap_dogrulandi": False,
        # Panelin neden kodlarını çözmeden karar detaylarını okuyabilmesi
        # için açık doğrulama alanları (inceleyici + gözlemleyici AI, madde 3):
        "source_valid": False,
        "schema_valid": False,
        "account_verified": False,
        "office_verified": False,
        "full_scope": False,
        "all_segments_succeeded": False,
        "anomaly_check_passed": False,
        "can_write": False,
        "can_deactivate": False,
        "can_deactivate_theoretical": False,
        "pasiflestirme_atlandi": True,
        "deactivation_skip_reasons": [],
    }
    result.update(overrides)
    return result


def df_to_supabase(df, kaynak_ofis, supabase_client, log_fn=None, hesap_dogrulandi=False, sync_run_id=None,
                    raw_record_count=None, duplicate_record_count=0):
    """
    DataFrame'i portfoyler tablosuna yazar. URL bazlı: varsa günceller,
    yoksa ekler.

    TUR 2B sözleşmesi:
    - can_write=False  → hiçbir insert/update/pasifleştirme yapılmaz.
    - can_write=True, can_deactivate=False → yalnız insert/update yapılır.
    - can_deactivate=True → kontrollü pasifleştirme de yapılabilir (şu an
      PASIFLESTIRME_URETIME_HAZIR=False olduğu için fiilen hiç çalışmıyor).

    NOT (bilinen sınırlama): 'account_verified' ve 'office_verified' aynı
    sinyalden ("Merhaba, {isim}" karşılaması) geliyor.
    NOT (bilinen eksik): Reactivation henüz yok, pasif ilan tekrar gelirse
    yeni satır olarak insert edilmeye çalışılıyor.
    NOT (bu turda full_scope=False sabitlendi): Gerçek kapsam doğrulaması
    (Revy ekranındaki toplam sayı ile export satır sayısının karşılaştırılması)
    kurulana kadar snapshot hiçbir zaman "complete" sayılmıyor.

    ÖNEMLİ: "portfoyler" tablosunda "aktif" (boolean, varsayılan true)
    sütununun var olması gerekiyor.
    """
    import uuid as _uuid_mod
    sync_run_id = sync_run_id or str(_uuid_mod.uuid4())[:8]

    def log(msg):
        print(msg)
        if log_fn:
            log_fn(msg)

    # Düzeltme (inceleyici AI): raw_record_count verilmezken duplicate_record_count
    # verilmişse, eskiden raw=len(df) (unique sayı) kullanılıyordu — bu, iki
    # sayı arasında tutarsızlık yaratıyordu. Artık raw verilmemişse
    # unique+duplicate olarak hesaplanıyor.
    unique_record_count = len(df)
    if raw_record_count is None:
        raw_record_count = unique_record_count + max(0, int(duplicate_record_count or 0))

    # ── Ön kontrol 1: hesap/ofis doğrulanmadıysa hiçbir DB işlemine girme ──
    on_kontrol = evaluate_snapshot_eligibility({
        "source_valid": True,
        "account_verified": hesap_dogrulandi,
        "office_verified": hesap_dogrulandi,
        "schema_valid": True,
        "full_scope": False,
        "all_segments_succeeded": True,
        "valid_record_count": 1,
        "parse_error_count": 0,
        "write_error_count": 0,
        "anomaly_check_passed": True,
    })
    if not on_kontrol["can_write"]:
        log(f"⛔ [{sync_run_id}] {kaynak_ofis}: hesap/ofis doğrulanamadı — "
            f"hiçbir veri yazılmadı. Nedenler: {', '.join(on_kontrol['skip_reasons'])}")
        return build_sync_result(
            sync_run_id=sync_run_id,
            raw_record_count=raw_record_count,
            duplicate_record_count=duplicate_record_count,
            unique_record_count=unique_record_count,
            hesap_dogrulandi=hesap_dogrulandi,
            account_verified=hesap_dogrulandi,
            office_verified=hesap_dogrulandi,
            deactivation_skip_reasons=on_kontrol["skip_reasons"],
        )

    # Kolon eşleştirme
    url_col     = kolon_bul(df, URL_KOLON_ADAYLARI)
    baslik_col  = kolon_bul(df, ["İlan Başlığı", "İlan Baslığı", "Ilan Basligi"])
    danisman_col= kolon_bul(df, ["İlan sahibi", "Ilan sahibi"])
    islem_col   = kolon_bul(df, ["İşlem tipi", "Islem tipi"])
    mulk_tip_col= kolon_bul(df, ["Mülk tipi", "Mulk tipi"])
    mulk_tur_col= kolon_bul(df, ["Mülk türü", "Mulk turu"])
    il_col      = kolon_bul(df, ["İl", "Il"])
    ilce_col    = kolon_bul(df, ["İlçe", "Ilce"])
    mahalle_col = kolon_bul(df, ["Mahalle"])
    fiyat_col   = kolon_bul(df, ["Fiyat"])
    m2_col      = kolon_bul(df, ["M2", "m²", "Metrekare"])
    oda_col     = kolon_bul(df, ["Oda sayısı", "Oda Sayısı"])
    tarih_col   = kolon_bul(df, ["İlan tarihi", "İlan Tarihi"])
    sure_col    = kolon_bul(df, ["İlan Yayın Süresi", "Yayin Suresi"])
    bina_col    = kolon_bul(df, ["Bina Yaşı", "Bina Yasi"])
    kat_col     = kolon_bul(df, ["Bulunduğu kat", "Kat"])
    site_col    = kolon_bul(df, ["Site içerisinde", "Site Ici"])
    kullanim_col= kolon_bul(df, ["Kullanım Durumu", "Kullanim Durumu"])
    esyali_col  = kolon_bul(df, ["Eşyalı", "Esyali"])
    durum_col   = kolon_bul(df, ["İlan Durumu", "Ilan Durumu"])

    # Düzeltme (her iki inceleme, madde 3): schema_valid artık yalnızca URL
    # kolonuna değil, Revy export'unu tanımlayan birkaç temel alana bakıyor.
    # Kill-switch yalnızca PASİFLEŞTİRMEYİ kapatıyor, insert/update'i değil
    # — yani yalnızca URL kolonu + tesadüfen geçerli bir link içeren, Revy
    # ile hiç ilgisi olmayan bir tablo bile eskiden bu kapıdan geçip
    # yazılabiliyordu.
    schema_valid = all([
        url_col is not None,
        danisman_col is not None,
        islem_col is not None,
        mulk_tip_col is not None,
    ])

    # ── Ön kontrol 2: gerçek source_valid — sabit True yerine ölçülen bir
    # sinyal. Gerçek `urlparse` tabanlı doğrulayıcı (`gecerli_http_url_mi`)
    # hem burada hem aşağıdaki yazma döngüsünde AYNI şekilde kullanılıyor.
    _gecerli_http_url_sayisi = 0
    if schema_valid:
        try:
            _gecerli_http_url_sayisi = int(
                df[url_col].apply(gecerli_http_url_mi).sum()
            )
        except Exception:
            _gecerli_http_url_sayisi = 0

    source_valid = (
        isinstance(df, pd.DataFrame)
        and not df.empty
        and schema_valid
        and _gecerli_http_url_sayisi > 0
    )

    if not source_valid or not schema_valid:
        _neden = "schema_invalid" if not schema_valid else "source_invalid"
        log(f"⛔ [{sync_run_id}] {kaynak_ofis}: kaynak/şema doğrulanamadı ({_neden}) — "
            f"hiçbir veri yazılmadı.")
        # Düzeltme (her iki inceleme, madde 1): eskiden bu erken dönüşte
        # parse_error_count=0, unique_record_count=len(df) gibi yanlış
        # sayılar dönüyordu — normal akıştaki tanımla çelişiyordu. Artık
        # zaten hesaplanmış _gecerli_http_url_sayisi'ndan türetilen gerçek
        # sayılar kullanılıyor. (schema_invalid durumunda url_col hiç
        # olmayabilir, bu yüzden _gecerli_http_url_sayisi zaten 0 kalıyor —
        # bu da doğru: şema geçersizse hiçbir satır "geçerli" sayılmaz.)
        _gecersiz_url_sayisi = len(df) - _gecerli_http_url_sayisi
        return build_sync_result(
            sync_run_id=sync_run_id,
            raw_record_count=raw_record_count,
            duplicate_record_count=duplicate_record_count,
            unique_record_count=_gecerli_http_url_sayisi,
            valid_record_count=_gecerli_http_url_sayisi,
            parse_error_count=_gecersiz_url_sayisi,
            hesap_dogrulandi=hesap_dogrulandi,
            account_verified=hesap_dogrulandi,
            office_verified=hesap_dogrulandi,
            source_valid=source_valid,
            schema_valid=schema_valid,
            deactivation_skip_reasons=[_neden],
        )

    kaynak_key = kaynak_ofis.lower().replace(" ", "")

    # Mevcut AKTİF URL'leri çek — pasifleme kıyaslaması için gerekli.
    # Sayfalı çekiliyor (.range()) — PostgREST'in varsayılan sayfa limiti
    # nedeniyle 1000+ aktif kayıtta bir kısmı hiç dönmeyebilir.
    mevcut_url_map = {}
    _mevcut_sayfalama_tam = True
    _mevcut_takip_kodu = None
    _bas = 0
    _sayfa_boyu = 1000
    while True:
        try:
            mevcut = supabase_client.table("portfoyler")\
                .select("id,ilan_linki")\
                .in_("kaynak", [kaynak_key])\
                .eq("aktif", True)\
                .range(_bas, _bas + _sayfa_boyu - 1)\
                .execute()
        except Exception as e:
            import logging, uuid
            _mevcut_takip_kodu = str(uuid.uuid4())[:8]
            logging.getLogger(__name__).exception(
                "[%s] Mevcut kayıtlar çekilemedi (takip kodu: %s): %s",
                sync_run_id, _mevcut_takip_kodu, e,
            )
            log(f"⚠️ [{sync_run_id}] Mevcut kayıtlar tam çekilemedi. Takip kodu: {_mevcut_takip_kodu}")
            _mevcut_sayfalama_tam = False
            break
        _parca = mevcut.data or []
        for r in _parca:
            if r.get("ilan_linki"):
                mevcut_url_map[r["ilan_linki"]] = r["id"]
        if len(_parca) < _sayfa_boyu:
            break
        _bas += _sayfa_boyu

    # Sayfalama yarıda kesilirse yazma döngüsüne hiç girilmiyor.
    if not _mevcut_sayfalama_tam:
        log(f"⛔ [{sync_run_id}] {kaynak_ofis}: mevcut kayıtlar eksiksiz çekilemedi — "
            f"hiçbir insert/update/pasifleştirme yapılmadı.")
        # Düzeltme (her iki inceleme, madde 2): bu noktada hesap/kaynak/şema
        # zaten doğrulanmış durumda — tek sorun mevcut DB kayıtlarının
        # eksiksiz çekilememesi. Eskiden ortak şablonun güvenli
        # varsayılanları (hepsi False) bu gerçek durumu yanlış yansıtıyordu
        # — panel "hesap doğrulanamadı" sanabilirdi. Artık takip kodu da
        # sözleşmeye aktarılıyor.
        return build_sync_result(
            sync_run_id=sync_run_id,
            takip_kodu=_mevcut_takip_kodu,
            raw_record_count=raw_record_count,
            duplicate_record_count=duplicate_record_count,
            unique_record_count=unique_record_count,
            existing_record_count=len(mevcut_url_map),
            hesap_dogrulandi=hesap_dogrulandi,
            source_valid=True,
            schema_valid=True,
            account_verified=hesap_dogrulandi,
            office_verified=hesap_dogrulandi,
            full_scope=False,
            all_segments_succeeded=False,
            anomaly_check_passed=False,
            can_write=False,
            can_deactivate=False,
            can_deactivate_theoretical=False,
            deactivation_skip_reasons=["existing_records_incomplete"],
        )

    eklenen = guncellenen = 0
    parse_hatasi_sayisi = 0
    yazma_hatasi_sayisi = 0
    taranan_urller = set()
    # Düzeltme (inceleyici AI, madde 6): çağıran (tek_ofis_sync) duplicate
    # temizliğini unutursa/eksik yaparsa diye, yazıcının kendi çalışma
    # zamanı (runtime) duplicate savunması. Canonical ilan kimliğinin
    # yerine geçmez — yalnızca aynı çalıştırmadaki birebir URL tekrarını
    # engeller.
    runtime_seen_urls = set()
    runtime_duplicate_count = 0

    for _, row in df.iterrows():
        url = str(row.get(url_col, "") or "").strip()

        # Düzeltme (her iki inceleme, madde 1): gerçek, satır bazlı URL
        # doğrulaması. Eskiden yalnızca "boş mu" kontrol ediliyordu — bu
        # yüzden "ABC-123" gibi geçersiz bir değer de normal bir kayıt
        # gibi işlenip DB'ye yazılabiliyordu. Artık her satır
        # `gecerli_http_url_mi()` ile doğrulanıyor, geçmeyenler
        # `parse_hatasi_sayisi`'na eklenip atlanıyor — DB'ye hiç gitmiyor.
        if not gecerli_http_url_mi(url):
            parse_hatasi_sayisi += 1
            continue

        # URL yalnızca doğrulamadan SONRA runtime kümelerine ekleniyor —
        # geçersiz bir değer asla "taranan"/"görülen" sayılmıyor.
        if url in runtime_seen_urls:
            runtime_duplicate_count += 1
            continue
        runtime_seen_urls.add(url)

        taranan_urller.add(url)

        def val(col):
            if col is None:
                return None
            v = row.get(col)
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return None
            return str(v).strip() if str(v).strip() not in ["nan","None",""] else None

        def int_val(col):
            v = val(col)
            try:
                return int(float(v)) if v else None
            except Exception:
                return None

        veri = {
            "kaynak": kaynak_key,
            "giren_gd": kaynak_ofis,
            "ilan_linki": url,
            "ozet": val(baslik_col),
            "talep_eden_danisan": val(danisman_col),
            "islem_tipi": val(islem_col),
            "mulk_tipi": val(mulk_tip_col),
            "mulk_turu": val(mulk_tur_col),
            "il": val(il_col),
            "ilce": val(ilce_col),
            "mahalle": val(mahalle_col),
            "fiyat": val(fiyat_col),
            "oda_sayisi_m2": val(oda_col),
            "m2": val(m2_col),
            "ilan_tarihi": val(tarih_col),
            "ilan_suresi": int_val(sure_col),
            "bina_yasi": val(bina_col),
            "kat": val(kat_col),
            "site_icerisinde": val(site_col),
            "kullanim_durumu": val(kullanim_col),
            "esyali": val(esyali_col),
            "ilan_durumu": val(durum_col),
            # DÜZELTME (12.08.2026, 2. tur): İlk denemede .isoformat()
            # kullanılmıştı ("2026-08-12T14:30:00") — ama bunu okuyan
            # _tarihte_mi() (core/danisman_ortak.py) parsedate_to_datetime()
            # kullanıyor, yani RFC822 MAIL tarih formatı bekliyor
            # ("Wed, 12 Aug 2026 14:30:00 +0000"), ISO DEĞİL. ISO string
            # verilince parser sessizce hata verip kaydı yine filtreye
            # takılı bırakıyordu (canlıda doğrulandı — düzeltme sonrası
            # hâlâ görünmüyordu). format_datetime() ile doğru formatta
            # yazılıyor artık.
            "kayit_tarihi": format_datetime(datetime.now()),
            "guncelleme_tarihi": datetime.now().isoformat(),
            "aktif": True,
        }
        veri = {k: v for k, v in veri.items() if v is not None or k == "aktif"}

        try:
            if url in mevcut_url_map:
                kid = mevcut_url_map[url]
                supabase_client.table("portfoyler").update(veri).eq("id", kid).execute()
                guncellenen += 1
            else:
                veri["olusturma_tarihi"] = datetime.now().isoformat()
                supabase_client.table("portfoyler").insert(veri).execute()
                eklenen += 1
        except Exception as e:
            import logging, uuid
            _yazma_takip_kodu = str(uuid.uuid4())[:8]
            logging.getLogger(__name__).exception(
                "[%s] revy_sync yazma hatası (%s, takip kodu: %s): %s",
                sync_run_id, url[:60], _yazma_takip_kodu, e,
            )
            log(f"⚠️ [{sync_run_id}] Bir kayıt yazılamadı. Takip kodu: {_yazma_takip_kodu}")
            yazma_hatasi_sayisi += 1

    if runtime_duplicate_count:
        log(f"🧹 [{sync_run_id}] Çalışma zamanında {runtime_duplicate_count} tekrarlı URL atlandı.")

    # ── Anormal düşüş kontrolü (ikinci emniyet, ana koşulun yerine geçmez) ──
    onceki_aktif_sayisi = len(mevcut_url_map)
    gecerli_kayit_sayisi = len(taranan_urller)
    _dusus_miktari = max(0, onceki_aktif_sayisi - gecerli_kayit_sayisi)
    _MUTLAK_PASIFLEME_TAVANI = 5
    anomaly_check_passed = (
        _mevcut_sayfalama_tam
        and (
            onceki_aktif_sayisi == 0
            or (
                gecerli_kayit_sayisi >= onceki_aktif_sayisi * 0.70
                and _dusus_miktari <= _MUTLAK_PASIFLEME_TAVANI
            )
        )
    )

    uygunluk = evaluate_snapshot_eligibility({
        "source_valid": True,
        "account_verified": hesap_dogrulandi,
        "office_verified": hesap_dogrulandi,
        "schema_valid": True,
        "full_scope": False,             # gerçek kapsam doğrulaması kurulana kadar sabit False
        "all_segments_succeeded": True,  # tek parça, tarih bölme yok
        "valid_record_count": gecerli_kayit_sayisi,
        "parse_error_count": parse_hatasi_sayisi,
        "write_error_count": yazma_hatasi_sayisi,
        "anomaly_check_passed": anomaly_check_passed,
    })

    if gecerli_kayit_sayisi == 0:
        log(f"⛔ [{sync_run_id}] {kaynak_ofis}: geçerli kayıt bulunamadı "
            f"(taranan {len(df)} satır, {parse_hatasi_sayisi} geçersiz URL) — "
            f"sonuç geçersiz sayıldı, hiçbir pasifleştirme değerlendirilmedi.")
        return build_sync_result(
            durum="failed", snapshot_status="invalid", mode="blocked",
            sync_run_id=sync_run_id,
            eklenen=eklenen, guncellenen=guncellenen,
            raw_record_count=raw_record_count,
            duplicate_record_count=duplicate_record_count,
            runtime_duplicate_count=runtime_duplicate_count,
            unique_record_count=len(runtime_seen_urls),
            existing_record_count=len(mevcut_url_map),
            parse_error_count=parse_hatasi_sayisi,
            write_error_count=yazma_hatasi_sayisi,
            hesap_dogrulandi=hesap_dogrulandi,
            source_valid=True, schema_valid=True,
            account_verified=hesap_dogrulandi, office_verified=hesap_dogrulandi,
            full_scope=False, all_segments_succeeded=True,
            anomaly_check_passed=anomaly_check_passed,
            can_write=True,
            deactivation_skip_reasons=uygunluk["skip_reasons"],
        )

    fiili_can_deactivate = uygunluk["can_deactivate"] and PASIFLESTIRME_URETIME_HAZIR

    _neden_listesi = list(uygunluk["skip_reasons"])
    if uygunluk["can_deactivate"] and not PASIFLESTIRME_URETIME_HAZIR:
        _neden_listesi.append("feature_not_production_ready")

    kapanan_urller = set(mevcut_url_map.keys()) - taranan_urller
    kapanan = 0
    pasiflestirme_hata_sayisi = 0

    if kapanan_urller:
        if fiili_can_deactivate:
            for kapanan_url in kapanan_urller:
                try:
                    supabase_client.table("portfoyler").update({
                        "aktif": False,
                        "guncelleme_tarihi": datetime.now().isoformat(),
                    }).eq("id", mevcut_url_map[kapanan_url]).execute()
                    kapanan += 1
                except Exception as e:
                    import logging, uuid
                    _pasif_takip_kodu = str(uuid.uuid4())[:8]
                    logging.getLogger(__name__).exception(
                        "[%s] Pasifleştirme hatası (takip kodu: %s): %s",
                        sync_run_id, _pasif_takip_kodu, e,
                    )
                    log(f"⚠️ [{sync_run_id}] Bir kayıt pasifleştirilemedi. Takip kodu: {_pasif_takip_kodu}")
                    pasiflestirme_hata_sayisi += 1
            log(f"🔒 [{sync_run_id}] {kapanan} ilan pasife alındı (doğrulanmış tam snapshot).")
        else:
            log(f"ℹ️ [{sync_run_id}] {len(kapanan_urller)} ilan export'ta görünmüyor ama "
                f"pasifleştirilmedi. Nedenler: {', '.join(_neden_listesi)}")

    # Düzeltme (inceleyici AI, madde 3): tüm geçerli kayıtların yazması
    # başarısız olduysa (eklenen=guncellenen=reactivated=0 ama yazma_hatasi
    # var), bu "kısmen başarılı" değil, tamamen başarısız bir çalıştırmadır.
    basarili_yazma_sayisi = eklenen + guncellenen  # + reactivated (henüz yok, hep 0)
    if yazma_hatasi_sayisi > 0 and basarili_yazma_sayisi == 0:
        durum = "failed"
    elif (parse_hatasi_sayisi + yazma_hatasi_sayisi + pasiflestirme_hata_sayisi) > 0:
        durum = "partial_success"
    else:
        durum = "success"

    log(f"{'✅' if durum == 'success' else '⚠️'} [{sync_run_id}] {kaynak_ofis}: "
        f"{eklenen} yeni, {guncellenen} güncellendi, {kapanan} pasife alındı, "
        f"{parse_hatasi_sayisi} ayrıştırma hatası, {yazma_hatasi_sayisi} yazma hatası "
        f"(snapshot: {uygunluk['snapshot_status']})")

    return build_sync_result(
        durum=durum,
        snapshot_status=uygunluk["snapshot_status"],
        mode="controlled_deactivation" if fiili_can_deactivate else "non_destructive_sync",
        sync_run_id=sync_run_id,
        eklenen=eklenen,
        guncellenen=guncellenen,
        raw_record_count=raw_record_count,
        duplicate_record_count=duplicate_record_count,
        runtime_duplicate_count=runtime_duplicate_count,
        # Düzeltme (her iki inceleme, madde 4): unique_record_count artık
        # döngü SONRASI gerçek sonucu (len(runtime_seen_urls)) gösteriyor —
        # eskiden döngü başında sabitlenmiş len(df) kullanılıyordu, bu da
        # runtime dedup/URL doğrulamasının atladığı satırları yansıtmıyordu.
        unique_record_count=len(runtime_seen_urls),
        valid_record_count=gecerli_kayit_sayisi,
        existing_record_count=len(mevcut_url_map),
        deactivation_candidate_count=len(kapanan_urller),
        parse_error_count=parse_hatasi_sayisi,
        write_error_count=yazma_hatasi_sayisi,
        deactivation_error_count=pasiflestirme_hata_sayisi,
        deactivated=kapanan,
        hesap_dogrulandi=hesap_dogrulandi,
        source_valid=True,
        schema_valid=True,
        account_verified=hesap_dogrulandi,
        office_verified=hesap_dogrulandi,
        full_scope=False,
        all_segments_succeeded=True,
        anomaly_check_passed=anomaly_check_passed,
        can_write=True,
        can_deactivate=fiili_can_deactivate,
        can_deactivate_theoretical=uygunluk["can_deactivate"],
        pasiflestirme_atlandi=not fiili_can_deactivate,
        deactivation_skip_reasons=_neden_listesi,
    )


# =============================================
# TEK OFİS SYNC
# =============================================
def tek_ofis_sync(ayarlar, hesap_no, hedef_url, klasor_adi, kaynak_ofis, supabase_client, log_fn=None):
    import uuid as _uuid_mod
    sync_run_id = str(_uuid_mod.uuid4())[:8]

    def log(msg):
        print(msg)
        if log_fn:
            log_fn(msg)

    # ── Ön kontrol: hesap_no ↔ kaynak_ofis ↔ hedef_url tutarlılığı ──────
    # (inceleyici AI + gözlemleyici AI, ortak talep). Bu, gerçek DOM tabanlı
    # ofis doğrulamasının (aşağıdaki "Merhaba, {isim}" kontrolü) yerine
    # geçmez — onu tamamlıyor. Amaç: bir kod hatası sonucu yanlış
    # parametre kombinasyonuyla çağrılırsa (örn. hesap_no=1 ama
    # kaynak_ofis="zeta2"), export/DB işlemine hiç girmeden bunu yakalamak.
    # Selenium'a hiç gerek olmadığı için driver oluşturulmadan ÖNCE kontrol
    # ediliyor.
    beklenen_ofis = REVY_HESAP_OFIS_ESLESMESI.get(hesap_no)
    _kaynak_normalize = str(kaynak_ofis).lower().replace(" ", "")
    _beklenen_url = ayarlar.get(f"revy{hesap_no}_ofis_aktif_url")
    # Düzeltme (her iki inceleme, ortak talep): eksik ayar artık GEÇMİYOR
    # (fail-closed). Eskiden `_beklenen_url is None` durumunda kontrol
    # atlanıyordu ("geriye dönük uyumluluk" gerekçesiyle) — ama normal
    # sync_tum_ofisler() akışı bu ayarı zaten zorunlu kullanıyor, yani bu
    # "uyumluluk" hiçbir gerçek senaryoyu korumuyordu, sadece riski açık
    # bırakıyordu.
    context_valid = (
        beklenen_ofis is not None
        and beklenen_ofis == _kaynak_normalize
        and bool(_beklenen_url)
        and _beklenen_url == hedef_url
    )
    if not context_valid:
        log(f"⛔ [{sync_run_id}] Parametre tutarsızlığı: hesap_no={hesap_no}, "
            f"kaynak_ofis={kaynak_ofis} (beklenen: {beklenen_ofis}) — "
            f"export/DB işlemine girilmedi.")
        return build_sync_result(
            sync_run_id=sync_run_id,
            deactivation_skip_reasons=["office_context_invalid"],
        )

    ana_klasor = ayarlar.get("indirilen_klasor", str(Path.home() / "Downloads"))
    export_klasoru = klasor_hazirla(ana_klasor, klasor_adi)

    driver = None
    try:
        log(f"🔐 [{sync_run_id}] {kaynak_ofis} için Revy'ye giriş yapılıyor...")
        driver = driver_olustur(export_klasoru)
        wait = WebDriverWait(driver, 20)

        revy_login(driver, wait, ayarlar, hesap_no)
        log("📨 Giriş formu gönderildi.")

        beklenen_hesap_adi = REVY_HESAP_ADLARI.get(hesap_no)
        hesap_dogrulandi = ilani_urline_git(driver, wait, hedef_url, beklenen_hesap_adi)
        log(f"📄 İlan sayfasına gidildi")

        if beklenen_hesap_adi and hesap_dogrulandi:
            log(f"✅ Giriş başarılı, hesap doğrulandı: sayfada \"{beklenen_hesap_adi}\" bulundu.")
        elif beklenen_hesap_adi:
            log(f"⚠️ Hesap doğrulanamadı — sayfada \"{beklenen_hesap_adi}\" bulunamadı. "
                f"Hesap/ofis doğrulanamadığı için hiçbir veri yazılmayacak.")
        else:
            log("⚠️ Bu hesap için beklenen isim tanımlı değil (REVY_HESAP_ADLARI). "
                "Hesap/ofis doğrulanamadığı için hiçbir veri yazılmayacak.")

        # Hesap doğrulanamadıysa Excel indirme/okuma adımlarına hiç girilmiyor.
        if not hesap_dogrulandi:
            return build_sync_result(
                sync_run_id=sync_run_id,
                hesap_dogrulandi=False,
                deactivation_skip_reasons=["account_unverified", "office_unverified"],
            )

        ham_dosya = export_al(
            driver=driver,
            wait=wait,
            klasor=export_klasoru,
            hedef_ad=f"{klasor_adi}_ham.xlsx"
        )
        log(f"📥 Excel dosyası başarıyla indirildi ({Path(ham_dosya).name}).")

        df = excel_oku(ham_dosya)
        log(f"📊 {len(df)} satır okundu")
        _ham_kayit_sayisi = len(df)

        # Duplicate temizle — ortak URL_KOLON_ADAYLARI sabiti kullanılıyor
        # (eskiden burada "Link" eksikti, df_to_supabase()'inkiyle
        # tutarsızdı).
        url_col = kolon_bul(df, URL_KOLON_ADAYLARI)
        if url_col:
            df = df.drop_duplicates(subset=[url_col])
        _duplicate_sayisi = _ham_kayit_sayisi - len(df)
        if _duplicate_sayisi:
            log(f"🧹 {_duplicate_sayisi} tekrarlı satır temizlendi.")

        eklenen_sonuc = df_to_supabase(
            df, kaynak_ofis, supabase_client, log_fn,
            hesap_dogrulandi=hesap_dogrulandi,
            sync_run_id=sync_run_id,
            raw_record_count=_ham_kayit_sayisi,
            duplicate_record_count=_duplicate_sayisi,
        )
        return eklenen_sonuc

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        time.sleep(2)


# =============================================
# ANA SYNC FONKSİYONU (Streamlit'ten çağrılır)
# =============================================
def sync_tum_ofisler(ayarlar=None, log_fn=None):
    """
    Her iki Zeta ofisini senkronize eder.
    log_fn: opsiyonel callback — her adımda çağrılır (Streamlit progress için)
    """
    if ayarlar is None:
        ayarlar = ayarlari_oku()

    supabase_client = get_supabase()

    sonuclar = {}

    # ZETA 1
    try:
        sonuclar["zeta1"] = tek_ofis_sync(
            ayarlar=ayarlar,
            hesap_no=1,
            hedef_url=ayarlar["revy1_ofis_aktif_url"],
            klasor_adi="zeta1_sync",
            kaynak_ofis="zeta1",
            supabase_client=supabase_client,
            log_fn=log_fn
        )
    except Exception as ex:
        import logging, uuid
        _takip_kodu = str(uuid.uuid4())[:8]
        logging.getLogger(__name__).exception(
            "ZETA 1 sync hatası (takip kodu: %s): %s", _takip_kodu, ex
        )
        sonuclar["zeta1"] = build_sync_result(
            sync_run_id=_takip_kodu,
            takip_kodu=_takip_kodu,
            deactivation_skip_reasons=["exception"],
        )
        if log_fn:
            log_fn(f"❌ ZETA 1 işlemi tamamlanamadı. Takip kodu: {_takip_kodu}")

    time.sleep(2)

    # ZETA 2
    try:
        sonuclar["zeta2"] = tek_ofis_sync(
            ayarlar=ayarlar,
            hesap_no=2,
            hedef_url=ayarlar["revy2_ofis_aktif_url"],
            klasor_adi="zeta2_sync",
            kaynak_ofis="zeta2",
            supabase_client=supabase_client,
            log_fn=log_fn
        )
    except Exception as ex:
        import logging, uuid
        _takip_kodu = str(uuid.uuid4())[:8]
        logging.getLogger(__name__).exception(
            "ZETA 2 sync hatası (takip kodu: %s): %s", _takip_kodu, ex
        )
        sonuclar["zeta2"] = build_sync_result(
            sync_run_id=_takip_kodu,
            takip_kodu=_takip_kodu,
            deactivation_skip_reasons=["exception"],
        )
        if log_fn:
            log_fn(f"❌ ZETA 2 işlemi tamamlanamadı. Takip kodu: {_takip_kodu}")

    return sonuclar


# =============================================
# KOMUT SATIRI (standalone çalıştırma)
# =============================================
if __name__ == "__main__":
    print("Revy Sync başlıyor...")
    ayarlar = ayarlari_oku()
    sonuclar = sync_tum_ofisler(ayarlar)
    print("\nSonuçlar:", sonuclar)

    # DÜZELTME (12.08.2026 — GitHub Actions entegrasyonu): input() CI'da
    # (stdin yok/etkileşimsiz ortam) SONSUZA KADAR TAKILI KALIRDI —
    # workflow hiç bitmez, "timeout-minutes" dolana kadar (30 dk) boşuna
    # runner tüketirdi. GITHUB_ACTIONS ortam değişkeni GitHub'ın kendi
    # runner'larında otomatik "true" olduğu için (driver_olustur()'daki
    # AYNI tespit yöntemi), CI'da bu adım atlanıyor — yerelde (VS Code)
    # hiçbir şey değişmiyor, "Enter'a bas" istemi eskisi gibi çalışıyor.
    # Ayrıca: herhangi bir ofis "failed" durumundaysa, GitHub Actions'ın
    # bunu KIRMIZI (başarısız) olarak işaretlemesi için process exit
    # code'u 1 döndürülüyor — aksi halde script "hata olmadan" bitmiş
    # gibi görünür ve başarısızlık Actions sekmesinde fark edilmeyebilir.
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        basarisiz_var = any(
            (sonuc or {}).get("durum") == "failed"
            for sonuc in sonuclar.values()
        )
        if basarisiz_var:
            print("\n⚠️ En az bir ofis senkronizasyonu başarısız oldu — "
                  "GitHub Actions bu çalıştırmayı BAŞARISIZ olarak işaretleyecek.")
            raise SystemExit(1)
    else:
        input("\nKapatmak için Enter...")