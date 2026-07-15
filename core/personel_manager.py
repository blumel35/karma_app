# core/personel_manager.py
# Personel yönetimi — Excel import, foto eşleştirme, login persistence, rol sistemi
# NOT: .streamlit/login_session.json dosyasını .gitignore'a ekleyin.

from __future__ import annotations

import json
import os
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# SABITLER
# ─────────────────────────────────────────────────────────────────────────────

# Proje kökü — çoklu strateji ile bulunur:
#   1. core/ dosyasının bir üstü (standart yapı: karma_app/core/personel_manager.py)
#   2. cwd (streamlit çalışma dizini)
# Excel ve foto klasörü karma_app/ ile aynı seviyede (proje kökünde) aranır.
def _find_root() -> Path:
    """
    Proje kökünü çoklu strateji ile bul.
    Her çağrıda runtime cwd'yi de kontrol eder — Streamlit
    rerun sırasında cwd değişebilir.
    """
    candidates = [
        Path(__file__).parent.parent,       # core/../  (karma_app/core/ yapısı)
        Path(__file__).parent,              # core/     (flat yapı)
        Path(os.getcwd()),                  # runtime cwd
        Path(os.getcwd()).parent,           # cwd'nin üstü
    ]
    for c in candidates:
        if (c / "zeta_personel_listesi.xlsx").exists():
            return c
        if (c / "karma_app" / "zeta_personel_listesi.xlsx").exists():
            return c / "karma_app"
    # Fallback — en mantıklı tahmin
    return Path(__file__).parent.parent


def _get_root() -> Path:
    """Her çağrıda path'i yeniden resolve et — import-time freeze'i önler."""
    return _find_root()


_ROOT = _find_root()

PERSONEL_EXCEL_PATH = _ROOT / "zeta_personel_listesi.xlsx"
FOTO_KLASOR_PATH    = _ROOT / "zeta_personel_fotolar"
SESSION_FILE_PATH   = _ROOT / ".streamlit" / "login_session.json"

SESSION_TTL_DAYS = 7

_BEKLENEN_KOLONLAR = [
    "ad_soyad", "user_key", "email", "telefon",
    "ofis_id", "ofis_adi", "rol", "yetki_no", "aktif", "foto_dosya_adi",
]

_FOTO_UZANTILARI = [".jpg", ".jpeg", ".png", ".webp", ".JPG", ".JPEG", ".PNG"]

# ─────────────────────────────────────────────────────────────────────────────
# EXCEL IMPORT
# ─────────────────────────────────────────────────────────────────────────────

def load_personel_listesi(force_reload: bool = False) -> pd.DataFrame:
    """
    Excel'den personel listesini yükle, normalize et, session cache'e al.
    force_reload=True ise cache'i görmezden gel.

    Returns:
        Normalize edilmiş, sadece aktif personeli içeren DataFrame.
        Excel bulunamazsa boş DataFrame döner.
    """
    cache_key = "_personel_df"

    if not force_reload and cache_key in st.session_state:
        return st.session_state[cache_key]

    excel_path = _get_root() / "zeta_personel_listesi.xlsx"
    if not excel_path.exists():
        warnings.warn(
            f"[personel_manager] Excel bulunamadı: {excel_path}",
            stacklevel=2,
        )
        empty = pd.DataFrame(columns=_BEKLENEN_KOLONLAR)
        st.session_state[cache_key] = empty
        return empty

    try:
        df = pd.read_excel(excel_path, dtype=str)
    except Exception as exc:  # noqa: BLE001
        warnings.warn(f"[personel_manager] Excel okunamadı: {exc}", stacklevel=2)
        empty = pd.DataFrame(columns=_BEKLENEN_KOLONLAR)
        st.session_state[cache_key] = empty
        return empty

    # Kolon isimlerini normalize et (boşluk, büyük harf temizle)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Eksik kolon uyarısı
    for kolon in _BEKLENEN_KOLONLAR:
        if kolon not in df.columns:
            warnings.warn(
                f"[personel_manager] Beklenen kolon eksik: '{kolon}'",
                stacklevel=2,
            )

    # Boş satırları temizle
    df.dropna(how="all", inplace=True)

    # Sadece aktif personel (aktif == "TRUE")
    if "aktif" in df.columns:
        df = df[df["aktif"].str.strip().str.upper() == "TRUE"].copy()

    # String kolonları strip et
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

    # foto_dosya_adi: .jpj typo fallback — normalize et
    if "foto_dosya_adi" in df.columns:
        df["foto_dosya_adi"] = df["foto_dosya_adi"].apply(_normalize_foto_adi)

    # ofis_adi: "ZETA2" → "ZETA 2", "ZETA1" → "ZETA 1" normalize et
    if "ofis_adi" in df.columns:
        import re as _re
        def _norm_ofis(v):
            if not isinstance(v, str):
                return v
            # "ZETA2" → "ZETA 2", "ZETA1" → "ZETA 1"
            import re as _re2
            return _re2.sub(r'([A-Za-z]+)(\d+)$',
                            lambda m: m.group(1) + " " + m.group(2),
                            v.strip())
        df["ofis_adi"] = df["ofis_adi"].apply(_norm_ofis)

    df.reset_index(drop=True, inplace=True)
    st.session_state[cache_key] = df
    return df


def _normalize_foto_adi(val: Any) -> str:
    """
    Bilinen typo'ları düzelt.
    Örnek: 'sumbul_gurel.jpj' → 'sumbul_gurel.jpg'
    """
    if not isinstance(val, str) or not val:
        return ""
    val = val.strip()
    # .jpj → .jpg
    if val.lower().endswith(".jpj"):
        val = val[:-4] + ".jpg"
    return val


# ─────────────────────────────────────────────────────────────────────────────
# FOTOĞRAF EŞLEŞTİRME
# ─────────────────────────────────────────────────────────────────────────────

def resolve_personel_photo(user_row: dict | pd.Series) -> str | None:
    """
    Personel satırına göre fotoğraf yolunu bul.

    Arama sırası:
      1. foto_dosya_adi alanı (tam dosya adı)
      2. user_key ile fuzzy eşleşme (jpg/jpeg/png/webp)

    Returns:
        Tam dosya yolu (string) ya da None.
    """
    foto_klasor = _get_root() / "zeta_personel_fotolar"
    if not foto_klasor.exists():
        return None

    # 1. foto_dosya_adi
    foto_adi = str(user_row.get("foto_dosya_adi") or "").strip()
    if foto_adi and foto_adi.lower() != "nan":
        tam_yol = foto_klasor / foto_adi
        if tam_yol.exists():
            return str(tam_yol)
        # Typo / uzantı uyumsuzluğu — aynı base adı tüm uzantılarla dene (case-insensitive)
        base = Path(foto_adi).stem
        # Önce tam eşleşme
        for uzanti in _FOTO_UZANTILARI:
            deneme = foto_klasor / (base + uzanti)
            if deneme.exists():
                return str(deneme)
        # Case-insensitive klasör taraması (Windows'ta gerekebilir)
        try:
            for dosya in foto_klasor.iterdir():
                if dosya.stem.lower() == base.lower() and dosya.suffix.lower() in [u.lower() for u in _FOTO_UZANTILARI]:
                    return str(dosya)
        except Exception:
            pass

    # 2. user_key ile eşleşme
    user_key = str(user_row.get("user_key") or "").strip()
    if user_key and user_key.lower() != "nan":
        for uzanti in _FOTO_UZANTILARI:
            deneme = foto_klasor / (user_key + uzanti)
            if deneme.exists():
                return str(deneme)
        # Case-insensitive klasör taraması
        try:
            for dosya in foto_klasor.iterdir():
                if dosya.stem.lower() == user_key.lower() and dosya.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                    return str(dosya)
        except Exception:
            pass

    return None


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN PERSISTENCE
# ─────────────────────────────────────────────────────────────────────────────

def save_login_session(user_data: dict) -> None:
    """
    Kullanıcı verilerini .streamlit/login_session.json'a yaz.
    Kaydedilen alanlar: id, user_key, email, rol, ofis_id, timestamp.
    """
    SESSION_FILE_PATH = _get_root() / ".streamlit" / "login_session.json"
    SESSION_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "id":        user_data.get("id", ""),
        "user_key":  user_data.get("user_key", ""),
        "email":     user_data.get("email", ""),
        "rol":       user_data.get("rol", ""),
        "ofis_id":   user_data.get("ofis_id", ""),
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }
    try:
        SESSION_FILE_PATH.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        warnings.warn(f"[personel_manager] Session kaydedilemedi: {exc}", stacklevel=2)


def load_login_session() -> dict | None:
    """
    login_session.json'ı oku. 7 günden eskiyse ya da dosya yoksa None döner.
    Cloud ortamında (Streamlit Cloud) dosya sistemi paylaşıldığı için devre dışı.

    Returns:
        {user_key, email, rol, ofis_id, timestamp} ya da None.
    """
    # NOT: Asıl güvenlik sınırı artık core/auth.py'deki
    # LOCAL_SESSION_RESTORE bayrağı — bu fonksiyon yalnızca
    # o bayrak açıkça etkinleştirilmişse çağrılır. Aşağıdaki
    # HOME kontrolü ek bir savunma katmanıdır, tek başına
    # güvenilmemelidir (path'ler değişebilir).
    # Streamlit Community Cloud'da HOME=/home/appuser olur.
    import os as _os
    if _os.environ.get("HOME", "").startswith("/home/appuser"):
        return None

    SESSION_FILE_PATH = _get_root() / ".streamlit" / "login_session.json"
    if not SESSION_FILE_PATH.exists():
        return None
    try:
        raw = SESSION_FILE_PATH.read_text(encoding="utf-8")
        payload = json.loads(raw)
        ts = datetime.fromisoformat(payload["timestamp"])
        if datetime.now(tz=timezone.utc) - ts > timedelta(days=SESSION_TTL_DAYS):
            SESSION_FILE_PATH.unlink(missing_ok=True)
            return None
        return payload
    except Exception:  # noqa: BLE001
        SESSION_FILE_PATH.unlink(missing_ok=True)
        return None


def clear_login_session() -> None:
    """login_session.json'ı sil."""
    try:
        session_path = _get_root() / ".streamlit" / "login_session.json"
        session_path.unlink(missing_ok=True)
    except OSError:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# CURRENT USER HELPER
# ─────────────────────────────────────────────────────────────────────────────

def get_current_user() -> dict | None:
    """
    st.session_state'deki aktif kullanıcıyı döndür.
    foto_path alanı resolve_personel_photo ile eklenir.

    Returns:
        {ad_soyad, rol, ofis_id, email, foto_path, ...} ya da None.
    """
    kullanici = st.session_state.get("kullanici")
    if not kullanici:
        return None

    result = {
        "ad_soyad":  kullanici.get("ad", ""),
        "rol":       kullanici.get("rol", ""),
        "ofis_id":   kullanici.get("ofis_id", ""),
        "email":     kullanici.get("email", ""),
        "user_key":  kullanici.get("user_key", ""),
        "foto_path": None,
    }

    # Fotoğrafı personel listesinden resolve et
    df = load_personel_listesi()
    if not df.empty and result["email"]:
        eslesme = df[df["email"] == result["email"]]
        if not eslesme.empty:
            row = eslesme.iloc[0].to_dict()
            result["foto_path"] = resolve_personel_photo(row)
            # user_key ve ofis_adi da taşı
            result.setdefault("ofis_adi", row.get("ofis_adi", ""))
            result.setdefault("user_key", row.get("user_key", ""))

    return result


# ─────────────────────────────────────────────────────────────────────────────
# ROL SİSTEMİ
# ─────────────────────────────────────────────────────────────────────────────

# Tüm ofislere erişebilen roller
_TUMU_ERISIM_ROLLERI = {"admin", "broker", "medya"}

def can_access_office(user: dict, office_id: str) -> bool:
    """
    Kullanıcının verilen ofise erişip erişemeyeceğini döndür.

    Kurallar:
      - admin, broker, medya  → tüm ofisler (True)
      - yonetici, gd, ofis_asistani → sadece kendi ofisi
    """
    rol = str(user.get("rol", "")).strip().lower()
    if rol in _TUMU_ERISIM_ROLLERI:
        return True
    kullanici_ofis = str(user.get("ofis_id", "")).strip().lower()
    return kullanici_ofis == str(office_id).strip().lower()


# ─────────────────────────────────────────────────────────────────────────────
# OFİS FİLTRE ALTYAPISI
# ─────────────────────────────────────────────────────────────────────────────

def filter_df_by_user_office(df: pd.DataFrame, user: dict) -> pd.DataFrame:
    """
    DataFrame'i kullanıcının rol ve ofisine göre filtrele.
    'ofis_id' kolonu kullanılır.

    - admin / broker / medya → tüm kayıtlar
    - diğerleri              → sadece kendi ofisi
    """
    if df.empty:
        return df

    rol = str(user.get("rol", "")).strip().lower()
    if rol in _TUMU_ERISIM_ROLLERI:
        return df

    if "ofis_id" not in df.columns:
        warnings.warn(
            "[personel_manager] filter_df_by_user_office: 'ofis_id' kolonu bulunamadı.",
            stacklevel=2,
        )
        return df

    kullanici_ofis = str(user.get("ofis_id", "")).strip().lower()
    return df[df["ofis_id"].str.strip().str.lower() == kullanici_ofis].copy()


# ─────────────────────────────────────────────────────────────────────────────
# SESSION ENRİCHMENT — login sonrası Excel verisini session'a yaz
# ─────────────────────────────────────────────────────────────────────────────

def enrich_session_from_personel(kullanici: dict) -> dict:
    """
    Supabase'den gelen kullanici dict'ini Excel personel kaydıyla zenginleştir.

    Arama önceliği: email → user_key
    Eşleşme bulunursa şu alanlar güncellenir (mevcut değer boşsa öncelikli yazar):
      ad_soyad, user_key, telefon, rol, ofis_id, ofis_adi, yetki_no, foto_path

    Returns:
        Güncellenmiş kullanici dict (in-place de güncellenir).
    """
    df = load_personel_listesi()
    if df.empty:
        return kullanici

    satir = None

    # 1. email eşleşmesi
    email = str(kullanici.get("email") or "").strip().lower()
    if email and "email" in df.columns:
        eslesme = df[df["email"].str.strip().str.lower() == email]
        if not eslesme.empty:
            satir = eslesme.iloc[0].to_dict()

    # 2. user_key eşleşmesi (fallback)
    if satir is None:
        uk = str(kullanici.get("user_key") or "").strip().lower()
        if uk and "user_key" in df.columns:
            eslesme = df[df["user_key"].str.strip().str.lower() == uk]
            if not eslesme.empty:
                satir = eslesme.iloc[0].to_dict()

    if satir is None:
        return kullanici  # Eşleşme yok — Supabase fallback

    # Alanları yaz — Excel her zaman önceliklidir
    kullanici["user_key"]  = str(satir.get("user_key") or "").strip()
    kullanici["telefon"]   = str(satir.get("telefon") or "").strip()
    kullanici["rol"]       = str(satir.get("rol") or kullanici.get("rol", "danisan")).strip().lower()
    kullanici["ofis_id"]   = str(satir.get("ofis_id") or "").strip()
    kullanici["ofis_adi"]  = str(satir.get("ofis_adi") or "").strip()
    kullanici["yetki_no"]  = str(satir.get("yetki_no") or "").strip()

    # ad_soyad → hem "ad_soyad" hem "ad" alanına yaz
    ad_soyad = str(satir.get("ad_soyad") or "").strip()
    if ad_soyad:
        kullanici["ad_soyad"] = ad_soyad
        kullanici["ad"]       = ad_soyad

    # foto_path — local fotoğraf yolu
    kullanici["foto_path"] = resolve_personel_photo(satir)

    return kullanici
