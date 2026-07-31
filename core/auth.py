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
            # KA-AUTH-001-R4 — BAŞARILI GİRİŞ TANIMI: yalnız res.user
            # varlığı yeterli değildir. Kullanılabilir bir res.session
            # ve okunabilir token alanları da GEREKİR — aksi hâlde
            # "doğrulanmış giriş" sayılmaz, kilit KORUNUR ve None
            # döndürülür. Bu kontrol bilerek açık yazıldı (dolaylı bir
            # AttributeError/except Exception'a güvenilmiyor) çünkü
            # kilit kaldırma kararı gibi güvenlik açısından kritik bir
            # sonucun, örtük bir hata yakalamaya değil, açık bir iş
            # kuralına dayanması gerekir.
            if (
                not res.session
                or not getattr(res.session, "access_token", None)
                or not getattr(res.session, "refresh_token", None)
            ):
                return None

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

            # KA-AUTH-001-R5 — GEÇERLİ AKTÖR DOĞRULAMASI: yalnız
            # kullanılabilir session/token yeterli değildir. Oluşan
            # `kullanici` sözlüğünün kendisi de gerçek bir kimlik
            # taşımalıdır (id/email/user_key). Aksi hâlde (ör.
            # res.user.id/email boş — bozuk/beklenmeyen bir Supabase
            # cevabı) kilit KORUNUR, giriş başarısız sayılır. Bu kontrol
            # olmadan, kimliksiz bir sözlük kilidi kaldırıp döndürülüyor,
            # set_session_fields() onu daha SONRA reddediyordu — ama o
            # noktada güvenlik kilidi zaten kalkmış oluyordu (R4 hatası,
            # İnceleyici + Gözlemci AI tarafından bulundu).
            if not _valid_actor(kullanici):
                return None

            # KA-AUTH-001-R4 — GÜVENLİ KİLİT KURTARMA (doğru konum):
            # bu satıra yalnız kullanılabilir VE geçerli aktör kimliği
            # taşıyan bir kullanici sözlüğü başarıyla kurulduktan SONRA,
            # return'den hemen önce ulaşılır. res.session yoksa/bozuksa
            # veya kullanici kimliksizse yukarıdaki erken `return None`
            # dallarından biri zaten devreye girmiş olur ve bu satıra
            # HİÇ gelinmez — bu yüzden kilit yalnız gerçekten
            # tamamlanmış, kullanılabilir VE kimlikli bir Supabase auth
            # sonucunda kaldırılır. Başarısız giriş denemeleri veya
            # local session restore (bu fonksiyonu hiç çağırmaz) kilidi
            # KALDIRAMAZ — yalnız burası ve cikis_yap() kaldırabilir.
            _clear_identity_lock_on_verified_auth()
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
              "kullanici_id", "danisман_profil",
              # KA-AUTH-001-R1 — merkezi kimlik bağlamı ve impersonation alanları
              "auth_user", "view_as_user",
              "auth_user_id", "auth_role",
              "view_user_id", "view_role",
              "identity_context_valid",
              "_impersonate_active", "_impersonate_original", "_impersonated_name",
              # KA-AUTH-001-R2 — çakışma kilidi; yalnız gerçek logout kaldırır
              "_identity_locked"]:
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


# ─────────────────────────────────────────────────────
# KA-AUTH-001-R1 — MERKEZİ KİMLİK BAĞLAMI
#
# auth_user  → gerçekten oturum açan kullanıcı. Yetki/rol/yazma izni/audit
#              kimliği buradan gelmeli (bu R1'de henüz hiçbir tüketici
#              sayfa buna taşınmadı — bkz. KA-AUTH-001-R1 Delta).
#              Impersonation sırasında DEĞİŞMEZ.
# view_as_user → ekranda verisi görüntülenen kullanıcı. Yetki kazandırmaz,
#              audit kimliği değildir.
#
# Bu blok yalnız KA-AUTH-001-R1 kapsamında eklendi. Aşağıdaki legacy
# alanlar (kullanici/user_role/user_name/user_initials/kullanici_id) bu
# R1'de HİÇBİR ŞEKİLDE değiştirilmedi — set_session_fields()'ın onları
# yazan kısmı R1 öncesiyle birebir aynı kaldı. Yeni bağlam bunlara ek
# olarak, ayrı bir adım halinde kuruluyor.
#
# auth_user ve view_as_user HER ZAMAN shallow dict() kopyasıdır — session
# içindeki mutable sözlüğün doğrudan referansı asla tutulmaz/döndürülmez.
# Gerekçe: profil.py mevcut "kullanici" sözlüğünü .update() ile yerinde
# değiştirebiliyor; aynı nesne paylaşılsaydı auth ve view bağlamı birlikte
# sessizce değişebilirdi. Mevcut kullanıcı sözlükleri düz (nested mutable
# alan yok) olduğu için shallow copy bu R1 için yeterlidir — iç içe
# mutable alan eklenirse KA-AUTH-001 yeniden açılmalıdır.
# ─────────────────────────────────────────────────────

def _identity_key(user: dict | None) -> str | None:
    """
    Kararlı kullanıcı kimliği. Öncelik: dolu id -> normalize email ->
    user_key -> hiçbiri yoksa None (geçersiz).

    Yalnız id'ye dayanılmıyor: impersonation hedefi dict'lerinde id
    alanı bilerek boş bırakılıyor (bkz. pages/kullanici_sec.py, "Seç"
    butonu) — bu gerçek koddan doğrulanmış bir durumdur.
    """
    if not user:
        return None
    _id = str(user.get("id") or "").strip()
    if _id:
        return f"id:{_id}"
    _email = str(user.get("email") or "").strip().lower()
    if _email:
        return f"email:{_email}"
    _uk = str(user.get("user_key") or "").strip().lower()
    if _uk:
        return f"user_key:{_uk}"
    return None


def _same_user(a: dict | None, b: dict | None) -> bool:
    """İki kullanıcı sözlüğü aynı gerçek kişiyi mi temsil ediyor?"""
    ka = _identity_key(a)
    kb = _identity_key(b)
    return ka is not None and ka == kb


def _valid_actor(user: dict | None) -> bool:
    """
    KA-AUTH-001-R2: Bir sözlük geçerli bir AKTÖR (gerçek, kimlik taşıyan
    ve kendisi impersonation hedefi olmayan) mi?

    İki koşul birden gerekli:
      - _identity_key(user) dolu olmalı (kimliksiz sözlük aktör olamaz)
      - user["_impersonated"] True olmamalı (impersonation hedefi
        kendisi asla auth_user kaynağı olamaz)
    """
    if not user:
        return False
    if user.get("_impersonated"):
        return False
    return _identity_key(user) is not None


def _invalidate_identity_context() -> None:
    """
    KA-AUTH-001-R2: Kimlik bağlamını geçersiz kıl. Eski/stale auth_user,
    view_as_user ve türetilmiş scalar alanlar (auth_user_id, auth_role,
    view_user_id, view_role) yetki kaynağı olarak session'da KALMAZ —
    hepsi temizlenir. Bu sayede get_auth_user()/get_auth_role() vb.
    geçersiz bağlamda eski bir yetkiyi sızdırmaz.
    """
    st.session_state["identity_context_valid"] = False
    st.session_state.pop("auth_user", None)
    st.session_state.pop("view_as_user", None)
    st.session_state["auth_user_id"] = ""
    st.session_state["auth_role"]    = ""
    st.session_state["view_user_id"] = ""
    st.session_state["view_role"]    = ""


def _derive_identity_ids() -> None:
    """auth_user/view_as_user'dan türetilmiş scalar alanları yaz.

    Bu alanlar (auth_user_id, auth_role, view_user_id, view_role)
    bağımsız kimlik kaynağı değildir — her zaman ana sözlüklerden
    türetilir, ayrıca set edilmezler.
    """
    _au = st.session_state.get("auth_user")
    _vu = st.session_state.get("view_as_user")
    st.session_state["auth_user_id"] = (_au or {}).get("id", "") or ""
    st.session_state["auth_role"]    = (_au or {}).get("rol", "") or ""
    st.session_state["view_user_id"] = (_vu or {}).get("id", "") or ""
    st.session_state["view_role"]    = (_vu or {}).get("rol", "") or ""


def _resolve_identity_context(incoming_user: dict) -> None:
    """
    KA-AUTH-001-R1 kararlı aktör çözümü. Kural kaynağı: KA-AUTH-001-R1
    mutabakat sözleşmesi (Uygulayıcı + İnceleyici + Gözlemci AI).

    incoming_user, set_session_fields()'a o an gelen ham sözlüktür —
    normal giriş, local restore veya (app.py'nin her-rerun çağrısı
    üzerinden) impersonation hedefi olabilir. incoming_user'ın kendisi
    hiçbir zaman doğrudan saklanmaz; her zaman dict() kopyası alınır.
    """
    current_auth = st.session_state.get("auth_user")
    incoming_impersonated = bool(incoming_user.get("_impersonated"))

    if incoming_impersonated:
        # İmpersonation hedefi hiçbir koşulda auth_user kaynağı olamaz.
        if _valid_actor(current_auth):
            # Kural 1 — mevcut GEÇERLİ auth_user korunur. (R2 fix 1:
            # yalnız "current_auth truthy" yeterli değil — kimliksiz
            # veya kendisi impersonation hedefi olan bir sözlük geçerli
            # aktör sayılmaz, bkz. _valid_actor().)
            st.session_state["auth_user"] = dict(current_auth)
            st.session_state["view_as_user"] = dict(incoming_user)
            st.session_state["identity_context_valid"] = True
            _derive_identity_ids()
            return

        # current_auth yok VEYA geçersiz — Kural 5: yalnız geçerli ve
        # impersonated OLMAYAN _impersonate_original üzerinden kurtarma
        # yapılabilir.
        _orig = st.session_state.get("_impersonate_original")
        if _valid_actor(_orig):
            st.session_state["auth_user"] = dict(_orig)
            st.session_state["view_as_user"] = dict(incoming_user)
            st.session_state["identity_context_valid"] = True
            _derive_identity_ids()
            return

        # Kural 6 — degenere durum. Hedef aktöre yükseltilmez.
        _invalidate_identity_context()
        return

    # Incoming impersonation hedefi değil — gerçek (ya da restore
    # edilmiş) bir kullanıcı.
    if _identity_key(incoming_user) is None:
        # R2 fix 2 — kimliksiz normal incoming asla doğrudan aktör
        # yapılmaz; current_auth'un durumundan bağımsız olarak geçersiz.
        _invalidate_identity_context()
        return

    if _valid_actor(current_auth):
        if _same_user(current_auth, incoming_user):
            # Kural 2 — aynı gerçek kullanıcı; güncel bilgilerle yenile.
            st.session_state["auth_user"] = dict(incoming_user)
            st.session_state["view_as_user"] = dict(incoming_user)
            st.session_state["identity_context_valid"] = True
            _derive_identity_ids()
            return
        # Kural 3 — farklı bir gerçek kullanıcı. Sessiz aktör değişimi
        # YOK; logout yapılmadan mevcut auth_user'ın yerini alamaz.
        # KİLİT: yalnız identity_context_valid=False yeterli değil —
        # _invalidate_identity_context() auth_user'ı session'dan
        # SİLDİĞİ için, bir sonraki set_session_fields() çağrısında
        # current_auth boş görünür ve "ilk kurulum" sanılabilir
        # (özellikle oturum_kontrol()'ün aynı çakışan kullanıcıyı aynı
        # rerun içinde tekrar set_session_fields()'a geçirmesi
        # senaryosunda gerçek bir hata olarak doğrulandı). Bu yüzden
        # gerçek çakışma tespit edildiğinde kalıcı bir kilit bırakılır;
        # yalnız cikis_yap() bu kilidi kaldırabilir.
        st.session_state["_identity_locked"] = True
        _invalidate_identity_context()
        return

    if st.session_state.get("_identity_locked"):
        # Daha önce gerçek bir çakışma (Kural 3) nedeniyle kilitlendi.
        # current_auth artık boş görünse bile (temizlendiği için) bunu
        # "ilk kurulum" sayıp incoming'i sessizce aktör yapmayız —
        # yalnız gerçek logout (cikis_yap) bu kilidi kaldırabilir.
        _invalidate_identity_context()
        return

    # Kural 4 — ilk kurulum (normal giriş / local restore; daha önce
    # hiç gerçek bir çakışma yaşanmamış).
    st.session_state["auth_user"] = dict(incoming_user)
    st.session_state["view_as_user"] = dict(incoming_user)
    st.session_state["identity_context_valid"] = True
    _derive_identity_ids()


def get_auth_user() -> dict | None:
    """
    Gerçek oturum sahibinin kopyasını döndürür (referans değil).
    KA-AUTH-001-R2: identity_context_valid True değilse None döner —
    geçersiz bağlamda eski/stale bir kimlik asla sızdırılmaz.
    """
    if st.session_state.get("identity_context_valid") is not True:
        return None
    au = st.session_state.get("auth_user")
    return dict(au) if au else None


def get_auth_role() -> str:
    """
    Gerçek oturum sahibinin rolü. KA-AUTH-001-R2: identity_context_valid
    True değilse "" döner.
    """
    if st.session_state.get("identity_context_valid") is not True:
        return ""
    return st.session_state.get("auth_role", "") or ""


def get_view_user() -> dict | None:
    """
    Ekranda görüntülenen kullanıcının kopyasını döndürür (referans değil).
    KA-AUTH-001-R2: identity_context_valid True değilse None döner.
    """
    if st.session_state.get("identity_context_valid") is not True:
        return None
    vu = st.session_state.get("view_as_user")
    return dict(vu) if vu else None


def get_view_role() -> str:
    """
    Ekranda görüntülenen kullanıcının rolü. KA-AUTH-001-R2:
    identity_context_valid True değilse "" döner.
    """
    if st.session_state.get("identity_context_valid") is not True:
        return ""
    return st.session_state.get("view_role", "") or ""


def is_impersonating() -> bool:
    """
    True yalnız şu üçü birden sağlanınca döner:
      - identity_context_valid == True
      - auth_user ve view_as_user farklı gerçek kullanıcılar (_same_user)
      - impersonation durumu aktif (_impersonate_active bayrağı)
    """
    if not st.session_state.get("identity_context_valid"):
        return False
    au = st.session_state.get("auth_user")
    vu = st.session_state.get("view_as_user")
    if not au or not vu:
        return False
    if _same_user(au, vu):
        return False
    return bool(st.session_state.get("_impersonate_active"))


def _clear_invalid_session_identity() -> None:
    """
    Kimlik bağlamı geçersiz olduğunda legacy `kullanici` alanını (ve
    diğer legacy/yeni kimlik + impersonation alanlarını) dolu BIRAKMAZ.

    Gerekçe (R2): giris.py, `st.session_state.get("kullanici")` doluysa
    "Oturumunuz açık" diyerek ana sayfaya yönlendirme butonu gösteriyor.
    identity_context_valid=False olduğu hâlde `kullanici` dolu kalırsa,
    kullanıcı giriş ekranına düşer ama orada "oturumunuz açık" görüp tekrar
    ana sayfaya yönlendirilebilir — ana sayfa da oturum_kontrol()'ü tekrar
    çağırıp yine False döneceği için bir yönlendirme döngüsü oluşabilir.

    R3 güncellemesi: artık yalnız oturum_kontrol()'den değil,
    set_session_fields() içinden ATOMİK olarak da çağrılıyor (bkz. Bölüm 3
    — invalid sonuç aynı fonksiyon çağrısı içinde temizlenir, dışarı
    sızdırılmaz). Impersonation alanları (_impersonate_active,
    _impersonate_original, _impersonated_name) da artık temizleniyor —
    geçersiz bağlamda eski impersonation state kalmasın.

    `_identity_locked` BURADA POPLANMAZ — çakışma güvenlik kilidi yalnız
    gerçek doğrulanmış giriş (`_clear_identity_lock_on_verified_auth()`)
    veya tam `cikis_yap()` ile kaldırılabilir (bkz. Bölüm 2).

    Local login session dosyası (.streamlit/login_session.json) burada
    SİLİNMEZ — gerçek kullanıcı, geçerli bir local restore ile güvenle
    yeniden kurulabilir; bu davranış bilerek korundu.
    """
    for k in ["kullanici", "user_role", "user_name", "user_initials",
              "kullanici_id",
              "auth_user", "view_as_user",
              "auth_user_id", "auth_role",
              "view_user_id", "view_role",
              "_impersonate_active", "_impersonate_original", "_impersonated_name"]:
        st.session_state.pop(k, None)
    st.session_state["identity_context_valid"] = False


def _clear_identity_lock_on_verified_auth() -> None:
    """
    KA-AUTH-001-R4 — Güvenli kilit kurtarma (düzeltilmiş konum).

    Yalnız GERÇEK, kullanılabilir bir Supabase auth başarısından sonra
    çağrılır — giris_yap() içinde, kullanılabilir `kullanici` sözlüğü
    başarıyla kurulduktan SONRA, `return kullanici` satırının hemen
    öncesinde. `res.user` varlığı TEK BAŞINA yeterli değildir; res.session
    ve token alanları da okunabilir olmalıdır (R3'te bu çağrı yanlışlıkla
    `res.user` doğrulanır doğrulanmaz, token okuma ve sözlük kurma
    denemelerinden ÖNCE yapılıyordu — İnceleyici AI'nın bulduğu R3 hatası
    buydu: eksik/bozuk res.session durumunda bile kilit temizleniyordu).

    Hiçbir başka yerden çağrılmamalıdır — özellikle local session restore
    akışı (oturum_kontrol()'ün restore dalı) bu fonksiyonu ÇAĞIRMAZ, bu
    yüzden çakışma kilidini kaldıramaz (bilerek; Bölüm 5).

    `_identity_locked` dahil önceki çakışmadan kalan tüm eski/geçersiz
    kimlik, legacy ve impersonation state'ini temizler — böylece yeni
    doğrulanmış kullanıcı set_session_fields() tarafından ilk aktör
    olarak (Kural 4) kurulabilir.
    """
    for k in ["_identity_locked",
              "auth_user", "view_as_user",
              "auth_user_id", "auth_role",
              "view_user_id", "view_role",
              "identity_context_valid",
              "kullanici", "user_role", "user_name", "user_initials", "kullanici_id",
              "_impersonate_active", "_impersonate_original", "_impersonated_name"]:
        st.session_state.pop(k, None)


def set_session_fields(kullanici: dict) -> bool:
    """
    Standart session_state alanlarını güvenli şekilde yaz.
    Tüm dosyalarda (giris.py, app.py, profil.py, oturum_kontrol) aynı
    mantık kullanılsın diye merkezi hale getirildi — session_state'e
    kullanıcı adı/rolü/baş harfleri yazan HER yer bu fonksiyonu
    çağırmalı, kendi kopyasını yazmamalı.

    KA-AUTH-001-R3: Artık bool döner (önceki sürümlerde dönüş değeri
    None idi ve hiçbir mevcut çağıran onu kullanmıyordu — bu değişiklik
    hiçbir çağıran dosyayı bozmaz).

      True  -> kimlik bağlamı geçerli kuruldu (auth_user/view_as_user
               tutarlı).
      False -> kimlik bağlamı kurulamadı; bu DURUMDA legacy alanlar
               (kullanici/user_role/user_name/user_initials/kullanici_id),
               auth/view alanları ve impersonation state'i AYNI fonksiyon
               çağrısı içinde atomik olarak temizlendi — geçersiz sonuç
               hiçbir şekilde "yetkiliymiş gibi" dışarı sızdırılmaz,
               çağıran kod dönüş değerini kullanmasa bile.
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

    # KA-AUTH-001-R1 — merkezi kimlik bağlamı (auth_user/view_as_user).
    # Yukarıdaki legacy alan yazımları bu R1'de değiştirilmedi; bu çağrı
    # onlara ek, ayrı bir adımdır.
    _resolve_identity_context(kullanici)

    # KA-AUTH-001-R3 — ATOMİKLİK (Bölüm 3, Seçenek B): mevcut sıra
    # (önce legacy yaz, sonra çöz) korunuyor; ancak sonuç geçersizse
    # legacy/auth/view/impersonation state AYNI çağrı içinde temizlenir.
    if st.session_state.get("identity_context_valid") is not True:
        _clear_invalid_session_identity()
        return False
    return True


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
        # KA-AUTH-001-R3: set_session_fields() artık atomik bool
        # döndürüyor (Bölüm 3) — invalid durumda gerekli temizliği
        # kendi içinde zaten yapıyor, burada tekrar etmeye gerek yok.
        return set_session_fields(st.session_state["kullanici"])

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

        # KA-AUTH-001-R3: yalnız gerçek doğrulanmış giriş
        # (_clear_identity_lock_on_verified_auth, giris_yap() içinde)
        # veya cikis_yap() çakışma kilidini kaldırabilir — local restore
        # bunlardan biri DEĞİL, bu yüzden kilit varsa burası da bloke
        # kalır (bilerek; Bölüm 5).
        return set_session_fields(kullanici)
    except Exception:
        return False
