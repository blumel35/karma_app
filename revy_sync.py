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

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# =============================================
# AYARLAR — ayarlar.txt'den okur (mevcut yapı)
# =============================================
def ayarlari_oku():
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
        # Standalone çalıştırıldığında ayarlar.txt'den oku
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
    driver = webdriver.Chrome(options=options)
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
    time.sleep(5)


# =============================================
# SAYFA GİT
# =============================================
def ilani_urline_git(driver, wait, hedef_url):
    driver.get(hedef_url)
    time.sleep(5)
    wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//*[contains(text(),'İlan')] | //table | //div[contains(@class,'table')]")
        )
    )
    print(f"Sayfaya gidildi: {hedef_url}")


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


def ilan_no_cek(url):
    try:
        return str(url).strip().rstrip("/").split("/")[-1]
    except Exception:
        return None


# =============================================
# SUPABASE'E YAZMA
# =============================================
def df_to_supabase(df, kaynak_ofis, supabase_client, log_fn=None):
    """
    DataFrame'i portfoyler tablosuna yazar.
    URL bazlı: varsa günceller, yoksa ekler.
    """
    def log(msg):
        print(msg)
        if log_fn:
            log_fn(msg)

    # Kolon eşleştirme
    url_col     = kolon_bul(df, ["İlan Url", "İlan Linki", "URL", "Link"])
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

    if not url_col:
        raise Exception("URL kolonu bulunamadı — veri yazılamaz.")

    # Mevcut URL'leri çek
    mevcut = supabase_client.table("portfoyler")\
        .select("id,ilan_linki")\
        .in_("kaynak", [kaynak_ofis.lower().replace(" ","")])\
        .execute()
    mevcut_url_map = {
        r["ilan_linki"]: r["id"]
        for r in (mevcut.data or [])
        if r.get("ilan_linki")
    }

    eklenen = guncellenen = atlanan = 0

    for _, row in df.iterrows():
        url = str(row.get(url_col, "") or "").strip()
        if not url or url.lower() in ["nan", "none", ""]:
            atlanan += 1
            continue

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

        kaynak_key = kaynak_ofis.lower().replace(" ","")  # "zeta1" veya "zeta2"

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
            "guncelleme_tarihi": datetime.now().isoformat(),
        }
        # None değerleri çıkar
        veri = {k: v for k, v in veri.items() if v is not None}

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
            log(f"Yazma hatası ({url[:40]}): {e}")
            atlanan += 1

    log(f"✅ {kaynak_ofis}: {eklenen} yeni eklendi, {guncellenen} güncellendi, {atlanan} atlandı")
    return eklenen, guncellenen, atlanan


# =============================================
# TEK OFİS SYNC
# =============================================
def tek_ofis_sync(ayarlar, hesap_no, hedef_url, klasor_adi, kaynak_ofis, supabase_client, log_fn=None):
    def log(msg):
        print(msg)
        if log_fn:
            log_fn(msg)

    ana_klasor = ayarlar.get("indirilen_klasor", str(Path.home() / "Downloads"))
    export_klasoru = klasor_hazirla(ana_klasor, klasor_adi)

    driver = None
    try:
        log(f"🔐 {kaynak_ofis} için Revy'ye giriş yapılıyor...")
        driver = driver_olustur(export_klasoru)
        wait = WebDriverWait(driver, 20)

        revy_login(driver, wait, ayarlar, hesap_no)
        log(f"✅ Giriş başarılı")

        ilani_urline_git(driver, wait, hedef_url)
        log(f"📄 İlan sayfasına gidildi")

        
        ham_dosya = export_al(
            driver=driver,
            wait=wait,
            klasor=export_klasoru,
            hedef_ad=f"{klasor_adi}_ham.xlsx"
        )
        log(f"📥 Excel indirildi: {ham_dosya}")

        df = excel_oku(ham_dosya)
        log(f"📊 {len(df)} satır okundu")

        # Duplicate temizle
        url_col = kolon_bul(df, ["İlan Url", "İlan Linki", "URL"])
        if url_col:
            df = df.drop_duplicates(subset=[url_col])

        eklenen, guncellenen, atlanan = df_to_supabase(df, kaynak_ofis, supabase_client, log_fn)
        return eklenen, guncellenen, atlanan

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
        e, g, a = tek_ofis_sync(
            ayarlar=ayarlar,
            hesap_no=1,
            hedef_url=ayarlar["revy1_ofis_aktif_url"],
            klasor_adi="zeta1_sync",
            kaynak_ofis="zeta1",
            supabase_client=supabase_client,
            log_fn=log_fn
        )
        sonuclar["zeta1"] = {"eklenen": e, "guncellenen": g, "atlanan": a}
    except Exception as ex:
        sonuclar["zeta1"] = {"hata": str(ex)}
        if log_fn:
            log_fn(f"❌ ZETA 1 hatası: {ex}")

    time.sleep(2)

    # ZETA 2
    try:
        e, g, a = tek_ofis_sync(
            ayarlar=ayarlar,
            hesap_no=2,
            hedef_url=ayarlar["revy2_ofis_aktif_url"],
            klasor_adi="zeta2_sync",
            kaynak_ofis="zeta2",
            supabase_client=supabase_client,
            log_fn=log_fn
        )
        sonuclar["zeta2"] = {"eklenen": e, "guncellenen": g, "atlanan": a}
    except Exception as ex:
        sonuclar["zeta2"] = {"hata": str(ex)}
        if log_fn:
            log_fn(f"❌ ZETA 2 hatası: {ex}")

    return sonuclar


# =============================================
# KOMUT SATIRI (standalone çalıştırma)
# =============================================
if __name__ == "__main__":
    print("Revy Sync başlıyor...")
    ayarlar = ayarlari_oku()
    sonuclar = sync_tum_ofisler(ayarlar)
    print("\nSonuçlar:", sonuclar)
    input("\nKapatmak için Enter...")
