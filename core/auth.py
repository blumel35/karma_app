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
            # ÖNEMLİ: Normal (yetkisiz seviye) client burada YALNIZCA
            # publishable/anon anahtar kullanmalı. Daha önce burada bir
            # `secret_key` fallback'i vardı — publishable_key secrets'ta
            # tanımlı değilse client sessizce service/secret yetkisine
            # düşüyordu, bu da RLS'i (row-level security) fiilen devre
            # dışı bırakabiliyordu. Artık publishable anahtar yoksa
            # `key` boş kalır, aşağıdaki `if url and key` False olur ve
            # fonksiyon None döner — çağıran kod zaten `if not supa: ...`
            # ile bunu güvenli şekilde ele alıyor.
            key = (os.environ.get("SUPABASE_KEY")
                   or st.secrets.get("SUPABASE_KEY", "")
                   or st.secrets.get("supabase", {}).get("publishable_key", ""))
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
        # Ham hata detayı kullanıcıya gösterilmez — terminale/log'a yazılır.
        # Kullanıcıya gösterilen genel mesaj giris.py'de "E-posta veya
        # şifre hatalı." olarak zaten var.
        import logging
        logging.getLogger(__name__).exception("Giriş hatası: %s", e)
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
    for k in ["kullanici", "user_role", "user_name", "user_initials",
              "kullanici_id", "danisман_profil"]:
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


# ─────────────────────────────────────────────────────
# LOCAL SESSION RESTORE FLAG — FAIL-CLOSED
#
# Cloud'da kullanıcı karışması riski nedeniyle local dosya
# tabanlı session restore var. Daha önce bu, ortamı bir
# HOME path heuristiğiyle tahmin ederek "cloud'da otomatik
# kapan" mantığına dayanıyordu — bu heuristik yanlıştı
# (Streamlit Community Cloud'da HOME=/home/appuser'dır,
# kontrol edilen /home/adminuser değil) ve bu yüzden
# özellik cloud'da da aktif kalabiliyordu.
#
# Artık varsayılan KAPALI. Yalnızca açıkça, aşağıdaki
# yollardan biriyle etkinleştirilirse (yalnızca yerel
# geliştirmede yapılmalı) restore çalışır:
#
#   secrets.toml:
#       [app]
#       local_session_restore = true
#
#   ya da ortam değişkeni:
#       LOCAL_SESSION_RESTORE=true
#
# Ayar tanımsızsa, okunamıyorsa ya da "true" dışında bir
# değerse (örn. "1", "yes") KAPALI kabul edilir — belirsizlik
# durumunda güvenli tarafta kalınır.
# ─────────────────────────────────────────────────────
def _local_restore_enabled() -> bool:
    val = None
    try:
        _app_section = st.secrets.get("app", {})
        val = _app_section.get("local_session_restore") if _app_section else None
        if val is None:
            val = st.secrets.get("local_session_restore")
    except Exception:
        val = None

    if val is None:
        val = os.environ.get("LOCAL_SESSION_RESTORE")

    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() == "true"
    return False


LOCAL_SESSION_RESTORE = _local_restore_enabled()


def set_session_fields(kullanici: dict) -> None:
    """
    Standart session_state alanlarını güvenli şekilde yaz.
    Tüm dosyalarda (giris.py, app.py, profil.py, oturum_kontrol) aynı
    mantık kullanılsın diye merkezi hale getirildi — session_state'e
    kullanıcı adı/rolü/baş harfleri yazan HER yer bu fonksiyonu
    çağırmalı, kendi kopyasını yazmamalı.
    """
    ad = (
        kullanici.get("ad_soyad")
        or kullanici.get("ad")
        or kullanici.get("email", "").split("@")[0]
    )
    rol = kullanici.get("rol") or "danisan"

    st.session_state["kullanici"]      = kullanici
    st.session_state["user_role"]      = rol
    st.session_state["user_name"]      = ad
    st.session_state["user_initials"]  = "".join(
        w[0].upper() for w in ad.split()[:2] if w
    )
    st.session_state["kullanici_id"]   = kullanici.get("id", "")


def oturum_kontrol() -> bool:
    """
    Session'da geçerli kullanıcı var mı?
    Yoksa (ve LOCAL_SESSION_RESTORE açıksa) local kayıtlı
    oturumu geri yüklemeyi dener.

    Returns:
        True  -> kullanıcı session'da var (ya da başarıyla geri yüklendi)
        False -> kullanıcı yok, giriş ekranına yönlendirilmeli
    """
    if st.session_state.get("kullanici"):
        # Session zaten var ama diğer alanlar eksik/tutarsız olabilir —
        # her ihtimale karşı standart alanları senkronize et.
        set_session_fields(st.session_state["kullanici"])
        return True

    if not LOCAL_SESSION_RESTORE:
        return False

    try:
        from core.personel_manager import load_login_session, enrich_session_from_personel

        saved = load_login_session()
        if not saved:
            return False

        # load_login_session sadece user_key/email/rol/ofis_id taşıyor,
        # enrich_session_from_personel Excel'den ad_soyad vb. tamamlar.
        kullanici = enrich_session_from_personel(dict(saved))

        if not kullanici.get("email") and not kullanici.get("user_key"):
            return False

        set_session_fields(kullanici)
        return True
    except Exception:
        return False
