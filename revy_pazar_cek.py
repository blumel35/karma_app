"""
core/revy_pazar_cek.py
----------------------
Revy pazar veri çekme motoru.
Karma App core klasörüne kopyala: core/revy_pazar_cek.py
"""

import time, requests, openpyxl, pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ─────────────────────────────────────────
# İZMİR İLÇELERİ
# ─────────────────────────────────────────
IZMIR_ILCELER = {
    "Aliağa":487,"Balçova":488,"Bayındır":489,"Bayraklı":490,
    "Bergama":491,"Beydağ":492,"Bornova":493,"Buca":494,
    "Çeşme":495,"Çiğli":496,"Dikili":497,"Foça":498,
    "Gaziemir":499,"Güzelbahçe":500,"Karabağlar":501,"Karaburun":502,
    "Karşıyaka":503,"Kemalpaşa":504,"Kınık":505,"Kiraz":506,
    "Konak":507,"Menderes":508,"Menemen":509,"Narlıdere":510,
    "Ödemiş":511,"Seferihisar":512,"Selçuk":513,"Tire":514,
    "Torbalı":515,"Urla":516,
}

MULK_TIPLERI  = {"konut":"1","ticari":"2","arsa":"3"}
ISLEM_TIPLERI = {"satilik":"sale","kiralik":"rent"}
DURUM_TIPLERI = {"aktif":"active","yayindan_kalkan":"suspended"}
LIMIT   = 1000
CITY_ID = "41"

MARKALAR = {
    "startkey":  ["startkey"],
    "remax":     ["re/max","remax","re max"],
    "turpa":     ["turpa"],
    "turyap":    ["turyap"],
    "coldwell":  ["coldwell","cb "],
    "kw":        ["kw ","keller williams"],
    "alesta":    ["alesta"],
    "viya":      ["viya"],
    "orsa":      ["orsa"],
    "century21": ["century 21","century21"],
}

def marka_tespit(ofis):
    if pd.isna(ofis) or str(ofis).strip()=="": return "mulk_sahibi"
    ofis = str(ofis).lower()
    for m, kls in MARKALAR.items():
        if any(k in ofis for k in kls): return m
    return "bagimsiz"

# ─────────────────────────────────────────
# AYARLAR
# ─────────────────────────────────────────
def ayarlari_oku(dosya_yolu=None):
    if dosya_yolu is None:
        # Karma App kök dizininden bak
        dosya_yolu = Path(__file__).parent.parent / "ayarlar.txt"
    ayarlar = {}
    try:
        with open(dosya_yolu, "r", encoding="utf-8") as f:
            for satir in f:
                satir = satir.strip()
                if not satir or satir.startswith("#"): continue
                if "=" in satir:
                    k, v = satir.split("=", 1)
                    ayarlar[k.strip()] = v.strip()
    except Exception as e:
        raise FileNotFoundError(f"ayarlar.txt bulunamadı: {e}")
    return ayarlar

# ─────────────────────────────────────────
# HEADLESS SELENIUM LOGIN
# ─────────────────────────────────────────
def selenium_cookie_al(kullanici, sifre, giris_url, headless=True, progress_cb=None):
    """
    headless=True → Chrome penceresi açılmaz (Karma App için varsayılan)
    progress_cb   → ilerleme mesajı callback: progress_cb("mesaj")
    """
    options = Options()
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1280,800")
    for arg in ["--no-first-run","--no-default-browser-check",
                "--disable-popup-blocking","--disable-notifications",
                "--remote-allow-origins=*"]:
        options.add_argument(arg)

    if progress_cb: progress_cb("🌐 Revy'ye bağlanılıyor...")
    driver = webdriver.Chrome(options=options)
    wait   = WebDriverWait(driver, 20)
    try:
        driver.get(giris_url)
        time.sleep(2)
        giris_ac = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(., 'Giriş')] | //a[contains(., 'Giriş')]")))
        driver.execute_script("arguments[0].click();", giris_ac)
        time.sleep(2)

        inputs = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//input")))
        telefon = sifre_input = None
        for inp in inputs:
            try:
                tip = (inp.get_attribute("type") or "").lower()
                ph  = (inp.get_attribute("placeholder") or "").lower()
                if tip == "password": sifre_input = inp
                elif "cep" in ph or "telefon" in ph or tip in ["text","tel"]:
                    if inp.is_displayed() and inp.is_enabled(): telefon = inp
            except: pass

        for field, val in [(telefon, kullanici), (sifre_input, sifre)]:
            driver.execute_script("arguments[0].focus();", field)
            driver.execute_script("arguments[0].value='';", field)
            driver.execute_script("arguments[0].value=arguments[1];", field, val)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input',{bubbles:true}));", field)
            driver.execute_script("arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", field)

        giris_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(., 'Giriş Yap')]")))
        driver.execute_script("arguments[0].click();", giris_btn)

        if progress_cb: progress_cb("🔐 Giriş yapılıyor...")
        time.sleep(6)
        cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
        if progress_cb: progress_cb(f"✅ Bağlantı kuruldu ({len(cookies)} cookie)")
        return cookies
    finally:
        driver.quit()

def session_olustur(cookie_dict):
    xsrf = cookie_dict.get("XSRF-TOKEN","")
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "X-XSRF-TOKEN": xsrf,
        "Referer": "https://revy.com.tr/app/portfoy/ilanlar",
    }
    session = requests.Session()
    for n, v in cookie_dict.items():
        session.cookies.set(n, v, domain="revy.com.tr")
    return session, headers

# ─────────────────────────────────────────
# ÇEKME
# ─────────────────────────────────────────
def _parca_cek(session, headers, params, kayit_yolu):
    try:
        r = session.get(
            "https://revy.com.tr/app/portfoy/ilanlar/ajax",
            params=params, headers=headers, timeout=60
        )
        if r.status_code == 200 and (
            "spreadsheet" in r.headers.get("Content-Type","")
            or r.content[:4] == b"PK\x03\x04"
        ):
            Path(kayit_yolu).write_bytes(r.content)
            satir = openpyxl.load_workbook(kayit_yolu).active.max_row - 1
            return satir, satir >= LIMIT
        return 0, False
    except Exception:
        return 0, False

def _tarih_parcala(session, headers, base_params, klasor, prefix, baslangic, bitis):
    """[baslangic, bitis] tarih aralığını aylık parçalara böler ve her birini çeker."""
    dosyalar = []
    ay_basi = baslangic.replace(day=1)
    while ay_basi <= bitis:
        ay_sonu = min((ay_basi + relativedelta(months=1)) - timedelta(days=1), bitis)
        fd, ld = max(ay_basi, baslangic).strftime("%Y-%m-%d"), ay_sonu.strftime("%Y-%m-%d")
        params = {**base_params, "advertisement_first_date": fd, "advertisement_last_date": ld}
        dosya  = str(klasor / f"{prefix}_{fd}.xlsx")
        satir, _ = _parca_cek(session, headers, params, dosya)
        if satir > 0:
            dosyalar.append(dosya)
        time.sleep(1.2)
        ay_basi = ay_basi + relativedelta(months=1)
    return dosyalar

# ─────────────────────────────────────────
# ANA FONKSİYON
# ─────────────────────────────────────────
def pazar_cek(cookie_dict, filtre, cikti_klasor=None, progress_cb=None):
    """
    filtre = {
        "ilce":  ["Karşıyaka","Bornova"],
        "mulk":  ["konut","ticari","arsa"],
        "islem": ["satilik","kiralik"],
        "durum": ["aktif"],
        "ay":    3,
    }
    Döndürür: {"aktif": DataFrame, "yayindan_kalkan": DataFrame}
    """
    if cikti_klasor is None:
        cikti_klasor = Path(__file__).parent.parent / "revy_pazar_cikti"
    klasor = Path(cikti_klasor)
    klasor.mkdir(exist_ok=True)
    zaman  = datetime.now().strftime("%Y%m%d_%H%M%S")

    session, headers = session_olustur(cookie_dict)

    secilen_ilceler  = [(ad, IZMIR_ILCELER[ad]) for ad in filtre.get("ilce",[]) if ad in IZMIR_ILCELER]
    secilen_mulkler  = [(ad, MULK_TIPLERI[ad]) for ad in filtre.get("mulk",[]) if ad in MULK_TIPLERI]
    secilen_islemler = [(ad, ISLEM_TIPLERI[ad]) for ad in filtre.get("islem",[]) if ad in ISLEM_TIPLERI]
    secilen_durumlar = [(ad, DURUM_TIPLERI[ad]) for ad in filtre.get("durum",["aktif"]) if ad in DURUM_TIPLERI]

    # Tarih aralığı — sadece yayından kalkanlar için, seçildiyse kullanılır
    bugun = datetime.now()
    bas_str = filtre.get("baslangic")
    bit_str = filtre.get("bitis")
    baslangic = datetime.strptime(bas_str, "%Y-%m-%d") if bas_str else None
    bitis     = datetime.strptime(bit_str, "%Y-%m-%d") if bit_str else None
    # Yayından kalkan için tarih zorunlu — seçilmemişse son 3 ay varsayılan
    bas_suspended = baslangic or (bugun - relativedelta(months=3))
    bit_suspended = bitis or bugun
    bas_s = bas_suspended.strftime("%Y-%m-%d")
    bit_s = bit_suspended.strftime("%Y-%m-%d")

    toplam = len(secilen_ilceler) * len(secilen_mulkler) * len(secilen_islemler) * len(secilen_durumlar)
    if progress_cb: progress_cb(f"📡 {len(secilen_ilceler)} ilçe × {len(secilen_mulkler)} mülk × {len(secilen_islemler)} işlem = {toplam} kombinasyon")

    parca_durum = {d[0]: [] for d in secilen_durumlar}

    tamamlanan = 0
    for durum_ad, durum_val in secilen_durumlar:
        for ilce_ad, ilce_id in secilen_ilceler:
            for mulk_ad, mulk_id in secilen_mulkler:
                for islem_ad, islem_val in secilen_islemler:
                    tamamlanan += 1
                    prefix = f"{durum_ad}_{ilce_id}_{mulk_ad}_{islem_ad}"
                    base_params = {
                        "export":"1", "city_id":CITY_ID,
                        "district_id[]":str(ilce_id),
                        "advertisement_status":durum_val,
                        "property_type_id[]":mulk_id,
                        "transaction_type":islem_val,
                    }
                    if durum_val == "suspended":
                        base_params["tab"] = "archive"
                        base_params["advertisement_first_date"] = bas_s
                        base_params["advertisement_last_date"]  = bit_s
                    elif bas_s and bit_s:
                        # Aktif ilanlar: giriş tarihi filtresi opsiyonel
                        base_params["advertisement_first_date"] = bas_s
                        base_params["advertisement_last_date"]  = bit_s

                    dosya = str(klasor / f"{prefix}.xlsx")
                    if progress_cb:
                        progress_cb(f"📥 {ilce_ad}/{mulk_ad}/{islem_ad} ({tamamlanan}/{toplam})")

                    satir, limitli = _parca_cek(session, headers, base_params, dosya)

                    if satir > 0 and not limitli:
                        parca_durum[durum_ad].append(dosya)
                    elif satir > 0 and limitli:
                        Path(dosya).unlink(missing_ok=True)
                        alt = _tarih_parcala(session, headers, base_params, klasor, prefix,
                                             baslangic or bas_suspended, bitis or bit_suspended)
                        parca_durum[durum_ad].extend(alt)
                    time.sleep(1)

    # Birleştir
    sonuc = {}
    for durum_ad, parca_dosyalar in parca_durum.items():
        if not parca_dosyalar: continue

        if progress_cb: progress_cb(f"🔗 {durum_ad} birleştiriliyor...")
        df_list = []
        for d in parca_dosyalar:
            try:
                df_list.append(pd.read_excel(d))
                Path(d).unlink(missing_ok=True)
            except: pass

        if not df_list: continue
        birlesik = pd.concat(df_list, ignore_index=True)

        url_col = next((c for c in birlesik.columns if "url" in c.lower()), None)
        if url_col:
            birlesik = birlesik.drop_duplicates(subset=[url_col])

        # Marka tespiti
        ofis_col = next((c for c in birlesik.columns if c.lower() == "ofis"), None)
        birlesik["MARKA"] = birlesik[ofis_col].apply(marka_tespit) if ofis_col else "mulk_sahibi"

        # Yayından kalkış tarihi
        tarih_col = "İlan tarihi" if "İlan tarihi" in birlesik.columns else None
        sure_col  = "İlan Yayın Süresi" if "İlan Yayın Süresi" in birlesik.columns else None
        if tarih_col and sure_col:
            birlesik["Yayından Kalkış Tarihi"] = (
                pd.to_datetime(birlesik[tarih_col], format="%d.%m.%Y", errors="coerce")
                + pd.to_timedelta(pd.to_numeric(birlesik[sure_col], errors="coerce"), unit="D")
            )
            if durum_ad == "yayindan_kalkan":
                bas_ts, bit_ts = pd.Timestamp(bas_suspended), pd.Timestamp(bit_suspended) + pd.Timedelta(days=1)
                birlesik = birlesik[
                    birlesik["Yayından Kalkış Tarihi"].notna() &
                    (birlesik["Yayından Kalkış Tarihi"] >= bas_ts) &
                    (birlesik["Yayından Kalkış Tarihi"] < bit_ts)
                ]

        # Excel kaydet
        dosya_yolu = str(klasor / f"pazar_{durum_ad}_{zaman}.xlsx")
        birlesik.to_excel(dosya_yolu, index=False)
        if progress_cb: progress_cb(f"✅ {durum_ad}: {len(birlesik):,} kayıt")

        sonuc[durum_ad] = birlesik

    return sonuc

# ─────────────────────────────────────────
# STARTKEY İLAN ÇEKİCİ
# ─────────────────────────────────────────

def startkey_ilan_cek(cookie_dict, filtre=None, cikti_klasor=None, progress_cb=None):
    if filtre is None:
        filtre = {}
    if cikti_klasor is None:
        cikti_klasor = Path(__file__).parent.parent / "revy_startkey_cikti"
    klasor = Path(cikti_klasor)
    klasor.mkdir(exist_ok=True)
    zaman = datetime.now().strftime("%Y%m%d_%H%M%S")

    session, headers = session_olustur(cookie_dict)

    secilen_durumlar = filtre.get("durum", ["aktif"])
    bugun = datetime.now()
    bas_str = filtre.get("baslangic")
    bit_str = filtre.get("bitis")
    baslangic = datetime.strptime(bas_str, "%Y-%m-%d") if bas_str else (bugun - relativedelta(months=3))
    bitis     = datetime.strptime(bit_str, "%Y-%m-%d") if bit_str else bugun

    sonuc = {}

    for durum_ad in secilen_durumlar:
        durum_val = DURUM_TIPLERI.get(durum_ad, "active")
        if progress_cb:
            progress_cb(f"📡 Startkey {durum_ad} ilanları çekiliyor...")

        base_params = {
            "export": "1",
            "area": "all",
            "keyword": "startkey",
            "advertisement_status": durum_val,
            "save": "false",
        }
        if durum_val == "suspended":
            base_params["tab"] = "archive"
            base_params["advertisement_first_date"] = baslangic.strftime("%Y-%m-%d")
            base_params["advertisement_last_date"]  = bitis.strftime("%Y-%m-%d")

        dosya = str(klasor / f"startkey_{durum_ad}_{zaman}.xlsx")
        satir, limitli = _parca_cek(session, headers, base_params, dosya)

        if satir == 0:
            if progress_cb: progress_cb(f"⚠️ {durum_ad}: veri gelmedi")
            continue

        if limitli:
            if progress_cb: progress_cb(f"⚠️ limit aşıldı, parçalanıyor...")
            Path(dosya).unlink(missing_ok=True)
            parca_dosyalar = _tarih_parcala(
                session, headers, base_params, klasor,
                f"startkey_{durum_ad}", baslangic, bitis
            )
            if not parca_dosyalar: continue
            df_list = []
            for d in parca_dosyalar:
                try:
                    df_list.append(pd.read_excel(d))
                    Path(d).unlink(missing_ok=True)
                except: pass
            if not df_list: continue
            birlesik = pd.concat(df_list, ignore_index=True)
        else:
            if progress_cb: progress_cb(f"✅ {durum_ad}: {satir:,} ilan")
            birlesik = pd.read_excel(dosya)
            Path(dosya).unlink(missing_ok=True)

        url_col = next((c for c in birlesik.columns if "url" in c.lower()), None)
        if url_col:
            birlesik = birlesik.drop_duplicates(subset=[url_col])

        ofis_col = next((c for c in birlesik.columns if c.lower() == "ofis"), None)
        birlesik["MARKA"] = birlesik[ofis_col].apply(marka_tespit) if ofis_col else "startkey"

        tarih_col = "İlan tarihi" if "İlan tarihi" in birlesik.columns else None
        sure_col  = "İlan Yayın Süresi" if "İlan Yayın Süresi" in birlesik.columns else None
        if tarih_col and sure_col:
            birlesik["Yayından Kalkış Tarihi"] = (
                pd.to_datetime(birlesik[tarih_col], format="%d.%m.%Y", errors="coerce")
                + pd.to_timedelta(pd.to_numeric(birlesik[sure_col], errors="coerce"), unit="D")
            )

        if progress_cb: progress_cb(f"✅ {durum_ad}: {len(birlesik):,} kayıt hazır")
        sonuc[durum_ad] = birlesik

    return sonuc
