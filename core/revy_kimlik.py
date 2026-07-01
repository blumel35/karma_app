# core/revy_kimlik.py
# Kullanıcı bazlı Revy kimlik bilgilerini şifreli şekilde
# Supabase'in "kullanicilar" tablosunda saklar.
#
# Kolonlar (Supabase'de manuel eklenmeli):
#   revy_kullanici       (text)
#   revy_sifre_sifreli   (text)  — Fernet ile şifrelenmiş

import streamlit as st
import os


def _get_fernet():
    """secrets.toml'daki [revy_encryption] key'i ile Fernet nesnesi döndür."""
    try:
        from cryptography.fernet import Fernet
        key = (
            os.environ.get("REVY_ENCRYPTION_KEY")
            or st.secrets.get("revy_encryption", {}).get("key", "")
        )
        if not key:
            return None
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception:
        return None


def sifrele(plain: str) -> str | None:
    """Düz metni şifrele, base64 string döndür."""
    if not plain:
        return None
    f = _get_fernet()
    if not f:
        return None
    try:
        return f.encrypt(plain.encode("utf-8")).decode("utf-8")
    except Exception:
        return None


def coz(token: str) -> str | None:
    """Şifreli metni çöz, düz metin döndür."""
    if not token:
        return None
    f = _get_fernet()
    if not f:
        return None
    try:
        return f.decrypt(token.encode("utf-8")).decode("utf-8")
    except Exception:
        return None


def _get_supa():
    try:
        from supabase import create_client
        url = (os.environ.get("SUPABASE_URL")
               or st.secrets.get("SUPABASE_URL", "")
               or st.secrets.get("supabase", {}).get("url", ""))
        key = (os.environ.get("SUPABASE_KEY")
               or st.secrets.get("SUPABASE_KEY", "")
               or st.secrets.get("supabase", {}).get("publishable_key", "")
               or st.secrets.get("supabase", {}).get("secret_key", ""))
        if url and key:
            return create_client(url, key)
    except Exception:
        pass
    return None


def revy_hesap_kaydet(user_id: str, revy_kullanici: str, revy_sifre: str) -> bool:
    """
    Kullanıcının kendi Revy hesabını şifreleyip Supabase'e yazar.

    NOT: upsert() değil UPDATE kullanılır — kullanicilar.id kolonunda
    unique/primary key constraint garanti olmadığından, upsert() çakışmayı
    tespit edemeyip "ad" gibi NOT NULL alanları boş bırakan yeni bir satır
    eklemeye çalışabilir. UPDATE ile bu risk tamamen ortadan kalkar; satır
    yoksa (0 satır etkilenir) net bir hata döneriz.
    """
    if not user_id or not revy_kullanici or not revy_sifre:
        return False

    sifreli = sifrele(revy_sifre)
    if not sifreli:
        st.error("Şifreleme başarısız — secrets.toml içinde [revy_encryption] key tanımlı mı kontrol edin.")
        return False

    supa = _get_supa()
    if not supa:
        return False

    try:
        res = (supa.table("kullanicilar")
                   .update({
                       "revy_kullanici": revy_kullanici.strip(),
                       "revy_sifre_sifreli": sifreli,
                   })
                   .eq("id", user_id)
                   .execute())
        if not res.data:
            st.error(f"Revy hesabı kaydedilemedi: kullanicilar tablosunda id={user_id} ile eşleşen kayıt bulunamadı.")
            return False
        return True
    except Exception as e:
        st.error(f"Revy hesabı kaydedilemedi: {e}")
        return False


def revy_hesap_sil(user_id: str) -> bool:
    """Kullanıcının kayıtlı Revy hesabını temizle (UPDATE — upsert değil)."""
    supa = _get_supa()
    if not supa or not user_id:
        return False
    try:
        supa.table("kullanicilar").update({
            "revy_kullanici": None,
            "revy_sifre_sifreli": None,
        }).eq("id", user_id).execute()
        return True
    except Exception:
        return False


def revy_hesap_getir(user_id: str) -> dict | None:
    """
    Kullanıcının kayıtlı Revy hesabını Supabase'den çek ve çöz.
    Returns: {"revy1_kullanici": ..., "revy1_sifre": ...} ya da None.
    """
    supa = _get_supa()
    if not supa or not user_id:
        return None
    try:
        res = (supa.table("kullanicilar")
                   .select("revy_kullanici, revy_sifre_sifreli")
                   .eq("id", user_id)
                   .single()
                   .execute())
        data = res.data
        if not data:
            return None
        ku = data.get("revy_kullanici")
        sf = data.get("revy_sifre_sifreli")
        if not ku or not sf:
            return None
        cozulmus = coz(sf)
        if not cozulmus:
            return None
        return {
            "revy1_kullanici": ku,
            "revy1_sifre": cozulmus,
            "revy_giris_url": "https://revy.com.tr",
        }
    except Exception:
        return None
