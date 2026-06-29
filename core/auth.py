# core/auth.py
# Supabase Auth wrapper — giriş, çıkış, oturum yönetimi

import streamlit as st
import os

def _get_supa(use_service_key: bool = False):
    try:
        from supabase import create_client
        url = (os.environ.get("SUPABASE_URL")
               or st.secrets.get("SUPABASE_URL", "")
               or st.secrets.get("supabase", {}).get("url", ""))
        if use_service_key:
            # Storage yüklemesi için service/secret key kullan
            key = (os.environ.get("SUPABASE_SERVICE_KEY")
                   or st.secrets.get("supabase", {}).get("secret_key", "")
                   or st.secrets.get("supabase", {}).get("service_key", ""))
        else:
            key = (os.environ.get("SUPABASE_KEY")
                   or st.secrets.get("SUPABASE_KEY", "")
                   or st.secrets.get("supabase", {}).get("publishable_key", "")
                   or st.secrets.get("supabase", {}).get("secret_key", ""))
        if url and key:
            return create_client(url, key)
    except Exception:
        pass
    return None


def giris_yap(email: str, sifre: str) -> dict | None:
    """
    E-posta ve şifre ile giriş yap.
    Başarılıysa kullanıcı dict döndürür, değilse None.
    """
    supa = _get_supa()
    if not supa:
        return None
    try:
        res = supa.auth.sign_in_with_password({"email": email, "password": sifre})
        if res.user:
            # Supabase user id ile kullanicilar tablosundan profil çek
            profil = _profil_cek(supa, res.user.id)
            kullanici = {
                "id":           res.user.id,
                "email":        res.user.email,
                "access_token": res.session.access_token,
                "refresh_token":res.session.refresh_token,
                "ad":           profil.get("ad", email.split("@")[0]) if profil else email.split("@")[0],
                "rol":          profil.get("rol", "danisan") if profil else "danisan",
                "ofis_id":      profil.get("ofis_id", "") if profil else "",
                "ofis_adi":     profil.get("ofis_adi", "") if profil else "",
                "foto_url":     profil.get("foto_url", "") if profil else "",
                "logo_url":     profil.get("logo_url", "") if profil else "",
                "foto_bytes":   None,
                "logo_bytes":   None,
            }
            # Giriş sırasında fotoğrafı indir — session boyunca kalır
            _foto_url = kullanici["foto_url"]
            if _foto_url and _foto_url.startswith("http"):
                try:
                    import urllib.request as _ur
                    with _ur.urlopen(_foto_url, timeout=4) as _r:
                        kullanici["foto_bytes"] = _r.read()
                except Exception:
                    pass
            elif _foto_url and _foto_url.startswith("data:"):
                try:
                    import base64 as _b64
                    kullanici["foto_bytes"] = _b64.b64decode(_foto_url.split(",", 1)[1])
                except Exception:
                    pass
            return kullanici
    except Exception as e:
        st.error(f"Giriş hatası: {e}")
    return None


def cikis_yap():
    """Oturumu kapat, session_state ve local session dosyasını temizle."""
    # Local login session dosyasını sil
    try:
        from core.personel_manager import clear_login_session
        clear_login_session()
    except Exception:
        pass

    supa = _get_supa()
    if supa:
        try:
            supa.auth.sign_out()
        except Exception:
            pass
    for k in ["kullanici", "danisман_profil"]:
        st.session_state.pop(k, None)


def sifremi_sifirla(email: str) -> bool:
    supa = _get_supa()
    if not supa:
        return False
    try:
        supa.auth.reset_password_email(email)
        return True
    except Exception:
        return False


def _profil_cek(supa, user_id: str) -> dict | None:
    try:
        res = (supa.table("kullanicilar")
                   .select("*")
                   .eq("id", user_id)
                   .single()
                   .execute())
        return res.data
    except Exception:
        return None


def profil_guncelle(user_id: str, data: dict) -> bool:
    supa = _get_supa()
    if not supa:
        return False
    try:
        supa.table("kullanicilar").upsert({"id": user_id, **data}).execute()
        return True
    except Exception as e:
        st.error(f"Profil güncelleme hatası: {e}")
        return False


def foto_yukle(user_id: str, raw: bytes, dosya_adi: str, content_type: str) -> str | None:
    """
    Fotoğrafı önce Storage'a yüklemeyi dene.
    Başarısız olursa base64 data URI olarak döndür (tabloya kaydedilir).
    """
    supa = _get_supa(use_service_key=True)
    if not raw:
        return None

    # Storage'a yüklemeyi dene
    if supa:
        try:
            path = f"{user_id}/{dosya_adi}"
            supa.storage.from_("danismanlar").upload(
                path, raw, {"content-type": content_type, "upsert": "true"}
            )
            url = supa.storage.from_("danismanlar").get_public_url(path)
            if url:
                return url
        except Exception:
            pass

    # Storage başarısız — base64 data URI olarak döndür
    import base64
    b64 = base64.b64encode(raw).decode("utf-8")
    return f"data:{content_type};base64,{b64}"


def tum_kullanicilar(ofis_id: str | None = None) -> list[dict]:
    """
    Tüm kullanıcıları çek. ofis_id verilirse sadece o ofisin kullanıcıları.
    Yönetici için ofis_id=None (hepsini getirir).
    """
    supa = _get_supa()
    if not supa:
        return []
    try:
        q = supa.table("kullanicilar").select("*")
        if ofis_id:
            q = q.eq("ofis_id", ofis_id)
        res = q.order("ad").execute()
        return res.data or []
    except Exception:
        return []


def oturum_kontrol() -> bool:
    """
    Session'da geçerli kullanıcı var mı?
    Yoksa giris sayfasına yönlendir.
    """
    return bool(st.session_state.get("kullanici"))
