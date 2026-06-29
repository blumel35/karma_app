"""
rehber_sync.py
startkey.com.tr → Supabase sync.
Aylık veya ihtiyaç duyuldukça terminalden çalıştırılır.

Kullanım:
    python rehber_sync.py

Ne yapar:
- startkey.com.tr/tr/ofisler sayfalarını tarar
- Her ofis için danışman listesini çeker
- Supabase'e upsert eder (yeni → ekler, değişen → günceller)
- Artık listede olmayan ofisleri aktif=False yapar
- Logo URL'lerini günceller

Çalışma süresi: ~10-15 dk (80 ofis, tüm danışmanlar)
"""

import os
import re
import time
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY", "")

BASE_URL = "https://www.startkey.com.tr"
HEADERS  = {"User-Agent": "Mozilla/5.0"}

AKS_HARITASI = {
    "bayraklı":    ("İzmir", "İzmir Merkez"),
    "bornova":     ("İzmir", "İzmir Merkez"),
    "buca":        ("İzmir", "İzmir Merkez"),
    "gaziemir":    ("İzmir", "İzmir Merkez"),
    "karabağlar":  ("İzmir", "İzmir Merkez"),
    "konak":       ("İzmir", "İzmir Merkez"),
    "karşıyaka":   ("İzmir", "Kuzey Aksı"),
    "çiğli":       ("İzmir", "Kuzey Aksı"),
    "menemen":     ("İzmir", "Kuzey Aksı"),
    "foça":        ("İzmir", "Kuzey Aksı"),
    "aliağa":      ("İzmir", "Kuzey Aksı"),
    "dikili":      ("İzmir", "Kuzey Aksı"),
    "bergama":     ("İzmir", "Kuzey Aksı"),
    "güzelbahçe":  ("İzmir", "Yarımada / Batı Aksı"),
    "narlıdere":   ("İzmir", "Yarımada / Batı Aksı"),
    "balçova":     ("İzmir", "Yarımada / Batı Aksı"),
    "urla":        ("İzmir", "Yarımada / Batı Aksı"),
    "çeşme":       ("İzmir", "Yarımada / Batı Aksı"),
    "menderes":    ("İzmir", "Güney Aksı"),
    "torbalı":     ("İzmir", "Güney Aksı"),
    "selçuk":      ("İzmir", "Güney Aksı"),
    "tire":        ("İzmir", "Doğu / Dış Aks"),
    "ödemiş":      ("İzmir", "Doğu / Dış Aks"),
}


# ── HTTP yardımcıları ─────────────────────────────────────────────────────────

def get(url, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            if attempt == retries - 1:
                print(f"  HATA: {url} → {e}")
                return None
            time.sleep(2)


# ── Ofis listesi çek ─────────────────────────────────────────────────────────

def ofis_listesini_cek():
    """
    /tr/ofisler sayfasından ofis adı + logo + link eşleşmesi döndürür.
    Döndürür: [{ofis_adi, ofis_link, logo_url}]
    """
    ofisler = []
    logo_haritasi = {}  # href → logo_url

    for sayfa in range(1, 11):
        url = f"{BASE_URL}/tr/ofisler" if sayfa == 1 else f"{BASE_URL}/tr/ofisler?pageIndex={sayfa}"
        soup = get(url)
        if soup is None:
            break

        # Logo bağlantılarını topla
        for a in soup.find_all("a", href=True):
            img = a.find("img")
            if img is None:
                continue
            src = img.get("src", "")
            if "officelogo" not in src.lower():
                continue
            href = urljoin(BASE_URL, a["href"])
            logo_haritasi[href] = urljoin(BASE_URL, src)

        if not logo_haritasi:
            break

        # Ofis adlarını logo ile eşleştir
        eslesen = 0
        for h in soup.find_all(["h2", "h3", "h4"]):
            a = h.find("a", href=True)
            if not a:
                continue
            href = urljoin(BASE_URL, a["href"])
            ad   = a.get_text(strip=True)
            if href in logo_haritasi and ad:
                ofisler.append({
                    "ofis_adi":  ad,
                    "ofis_link": href,
                    "logo_url":  logo_haritasi[href],
                })
                eslesen += 1

        print(f"  Sayfa {sayfa}: {eslesen} ofis")
        time.sleep(0.4)

    return ofisler


# ── Ofis detay sayfasından telefon/adres çek ─────────────────────────────────

def ofis_detay_cek(ofis_link):
    """Ofis sayfasından telefon, mail, adres, il, ilce bilgisi çeker."""
    soup = get(ofis_link)
    if soup is None:
        return {}

    bilgi = {"telefon": "", "mail": "", "adres": "", "il": "", "ilce": "", "mahalle": ""}

    # Telefon
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("tel:"):
            bilgi["telefon"] = href.replace("tel:", "").strip()
            break

    # Mail
    for a in soup.find_all("a", href=True):
        if "mailto:" in a["href"]:
            bilgi["mail"] = a["href"].replace("mailto:", "").strip()
            break

    # Adres (genellikle bir p veya address tag'inde)
    for el in soup.find_all(["address", "p"]):
        text = el.get_text(separator=" ", strip=True)
        if len(text) > 20 and any(c.isdigit() for c in text):
            bilgi["adres"] = text[:300]
            break

    return bilgi


# ── Danışman listesi çek ──────────────────────────────────────────────────────

def danisman_listesi_cek(ofis_adi, ofis_link):
    """Ofis sayfasındaki danışman listesini döndürür."""
    soup = get(ofis_link)
    if soup is None:
        return []

    danismanlar = []
    for kart in soup.find_all("div", class_=lambda c: c and "agent" in c.lower()):
        isim = ""
        unvan = ""
        telefon = ""
        mail = ""
        foto_url = ""
        profil_link = ""

        # İsim
        for tag in kart.find_all(["h2", "h3", "h4", "strong"]):
            t = tag.get_text(strip=True)
            if len(t) > 2:
                isim = t
                break

        # Fotoğraf
        img = kart.find("img")
        if img:
            foto_url = urljoin(BASE_URL, img.get("src", ""))

        # Profil link
        a = kart.find("a", href=True)
        if a:
            profil_link = urljoin(BASE_URL, a["href"])

        # Telefon / mail
        for a in kart.find_all("a", href=True):
            if "tel:" in a["href"] and not telefon:
                telefon = a["href"].replace("tel:", "").strip()
            if "mailto:" in a["href"] and not mail:
                mail = a["href"].replace("mailto:", "").strip()

        if isim:
            danismanlar.append({
                "ofis_adi":    ofis_adi,
                "isim":        isim,
                "unvan":       unvan or "Gayrimenkul Danışmanı",
                "telefon":     telefon,
                "mail":        mail,
                "foto_url":    foto_url,
                "profil_link": profil_link,
                "aktif":       True,
                "guncelleme_tar": datetime.utcnow().isoformat(),
            })

    return danismanlar


# ── Bolge aksi tahmini ────────────────────────────────────────────────────────

def bolge_tahmin(il, ilce):
    """İlçe adına göre bolge_aksi tahmini döndürür."""
    ilce_lower = ilce.strip().lower()
    for anahtar, (bolge_il, bolge_aksi) in AKS_HARITASI.items():
        if anahtar in ilce_lower:
            return "İzmir", bolge_aksi
    if il.strip() in ("İzmir", "izmir"):
        return "İzmir", "İzmir Merkez"
    return "İzmir Dışı", "İzmir Dışı"


# ── Supabase işlemleri ────────────────────────────────────────────────────────

def supabase_client():
    from supabase import create_client
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("HATA: SUPABASE_URL / SUPABASE_KEY tanımlı değil.")
        sys.exit(1)
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def mevcut_ofis_adlari(supa):
    """Supabase'deki aktif ofis adlarını çek."""
    res = supa.table("rehber_ofisler").select("ofis_adi").eq("aktif", True).execute()
    return {r["ofis_adi"] for r in (res.data or [])}


def ofisleri_guncelle(supa, ofisler):
    """Ofisleri upsert et."""
    now = datetime.utcnow().isoformat()
    kayitlar = []
    for o in ofisler:
        bolge_tipi, bolge_aksi = bolge_tahmin(o.get("il", ""), o.get("ilce", ""))
        kayitlar.append({
            "ofis_adi":       o["ofis_adi"],
            "ofis_link":      o["ofis_link"],
            "logo_url":       o.get("logo_url", ""),
            "telefon":        o.get("telefon", ""),
            "mail":           o.get("mail", ""),
            "adres":          o.get("adres", ""),
            "il":             o.get("il", ""),
            "ilce":           o.get("ilce", ""),
            "mahalle":        o.get("mahalle", ""),
            "bolge_tipi":     bolge_tipi,
            "bolge_aksi":     bolge_aksi,
            "aktif":          True,
            "guncelleme_tar": now,
        })

    supa.table("rehber_ofisler").upsert(kayitlar, on_conflict="ofis_adi").execute()
    print(f"  ✓ {len(kayitlar)} ofis güncellendi.")


def kapanan_ofisleri_pasifle(supa, eski_adlar, yeni_adlar):
    """Artık listede olmayan ofisleri aktif=False yap."""
    kapananlar = eski_adlar - yeni_adlar
    if not kapananlar:
        return
    for ofis_adi in kapananlar:
        supa.table("rehber_ofisler").update({
            "aktif": False,
            "guncelleme_tar": datetime.utcnow().isoformat()
        }).eq("ofis_adi", ofis_adi).execute()
    print(f"  ⚠ {len(kapananlar)} ofis pasife alındı: {kapananlar}")


def danismanlari_guncelle(supa, danismanlar, ofis_adi):
    """Ofis danışmanlarını upsert et, artık olmayanları pasifle."""
    if not danismanlar:
        return

    # Mevcut aktif danışmanlar
    res = (
        supa.table("rehber_danismanlar")
        .select("isim")
        .eq("ofis_adi", ofis_adi)
        .eq("aktif", True)
        .execute()
    )
    eski_isimler = {r["isim"] for r in (res.data or [])}
    yeni_isimler = {d["isim"] for d in danismanlar}

    # Upsert
    supa.table("rehber_danismanlar").upsert(
        danismanlar, on_conflict="ofis_adi,isim"
    ).execute()

    # Ayrılanları pasifle
    ayrilanlar = eski_isimler - yeni_isimler
    if ayrilanlar:
        for isim in ayrilanlar:
            supa.table("rehber_danismanlar").update({
                "aktif": False,
                "guncelleme_tar": datetime.utcnow().isoformat()
            }).eq("ofis_adi", ofis_adi).eq("isim", isim).execute()
        print(f"    ↳ {len(ayrilanlar)} danışman pasife alındı")


# ── Ana akış ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Startkey Rehber Sync — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 55)

    supa = supabase_client()
    eski_adlar = mevcut_ofis_adlari(supa)
    print(f"Mevcut Supabase'de {len(eski_adlar)} aktif ofis var.")

    print("\n── Ofis listesi çekiliyor...")
    ofisler = ofis_listesini_cek()
    print(f"  {len(ofisler)} ofis bulundu.")

    # Ofisleri güncelle
    print("\n── Ofisler Supabase'e yazılıyor...")
    ofisleri_guncelle(supa, ofisler)

    # Kapananları pasifle
    yeni_adlar = {o["ofis_adi"] for o in ofisler}
    kapanan_ofisleri_pasifle(supa, eski_adlar, yeni_adlar)

    # Danışmanları güncelle (her ofis için ayrı)
    print("\n── Danışmanlar güncelleniyor...")
    toplam_dan = 0
    for i, ofis in enumerate(ofisler, 1):
        print(f"  [{i}/{len(ofisler)}] {ofis['ofis_adi']}...")
        danismanlar = danisman_listesi_cek(ofis["ofis_adi"], ofis["ofis_link"])
        danismanlari_guncelle(supa, danismanlar, ofis["ofis_adi"])
        toplam_dan += len(danismanlar)
        time.sleep(0.5)

    print(f"\n✅ Sync tamamlandı. {len(ofisler)} ofis, {toplam_dan} danışman işlendi.")
    print(f"   Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
