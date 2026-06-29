# pages/kullanici_sec.py
# Admin — Kullanıcı Seç & İmpersonate
# Sadece admin rolündeki kullanıcılar erişebilir.

import io
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.personel_manager import load_personel_listesi, resolve_personel_photo
from core.ui_helpers import render_navbar, render_page_header

# ── Session sync ──────────────────────────────────────────────────────────────
_k = st.session_state.get("kullanici", {})
if _k:
    _ad = _k.get("ad_soyad") or _k.get("ad", "")
    st.session_state["user_role"]     = _k.get("rol", "danisan")
    st.session_state["user_name"]     = _ad
    st.session_state["user_initials"] = "".join(
        w[0].upper() for w in _ad.split()[:2] if w
    )

# ── Erişim kontrolü ──────────────────────────────────────────────────────────
if not st.session_state.get("kullanici"):
    st.switch_page("pages/giris.py")

_rol = st.session_state.get("kullanici", {}).get("rol", "")
if _rol not in ("admin", "broker"):
    st.error("Bu sayfaya erişim yetkiniz yok.")
    st.stop()

render_navbar(
    user_role=st.session_state.get("user_role", "danisan"),
    user_name=st.session_state.get("user_name", ""),
    user_initials=st.session_state.get("user_initials", ""),
)

render_page_header(
    "👁 Kullanıcı Görünümü",
    "Bir kullanıcı seçin ve sistemi onun gözünden görün.",
)

# ── Impersonate banner (zaten aktifse) ────────────────────────────────────────
_imp = st.session_state.get("_impersonate_active", False)
if _imp:
    _orig = st.session_state.get("_impersonate_original", {})
    _imp_ad = st.session_state["kullanici"].get("ad_soyad") or st.session_state["kullanici"].get("ad", "")
    col_info, col_btn = st.columns([3, 1])
    with col_info:
        st.warning(f"👁 **{_imp_ad}** olarak görüntülüyorsunuz. Gerçek oturumunuz askıya alındı.")
    with col_btn:
        if st.button("↩ Kendi oturumuma dön", type="primary", use_container_width=True):
            st.session_state["kullanici"]           = _orig
            st.session_state["user_role"]           = _orig.get("rol", "admin")
            st.session_state["user_name"]           = _orig.get("ad_soyad") or _orig.get("ad", "")
            st.session_state["user_initials"]       = "".join(
                w[0].upper() for w in (st.session_state["user_name"]).split()[:2] if w
            )
            st.session_state["_impersonate_active"] = False
            st.session_state.pop("_impersonate_original", None)
            st.rerun()
    st.markdown("---")

# ── Personel listesi ──────────────────────────────────────────────────────────
df = load_personel_listesi()

if df.empty:
    st.warning("Personel listesi yüklenemedi. Excel dosyasını kontrol edin.")
    st.stop()

# Kendi kaydını listeden çıkar (kendine impersonate gerekmez)
_my_email = st.session_state.get("kullanici", {}).get("email", "")
if _my_email and "email" in df.columns:
    df_liste = df[df["email"].str.strip().str.lower() != _my_email.strip().lower()].copy()
else:
    df_liste = df.copy()

# ── Filtre ────────────────────────────────────────────────────────────────────
col_ara, col_ofis, col_rol = st.columns([2, 1.5, 1.5])
with col_ara:
    arama = st.text_input("🔍 Ad / email ara", placeholder="Meltem, duygu...", key="imp_search")
with col_ofis:
    ofis_secenekler = ["Tümü"] + sorted(df_liste["ofis_adi"].dropna().unique().tolist()) if "ofis_adi" in df_liste.columns else ["Tümü"]
    ofis_filtre = st.selectbox("Ofis", ofis_secenekler, key="imp_ofis")
with col_rol:
    rol_secenekler = ["Tümü"] + sorted(df_liste["rol"].dropna().unique().tolist()) if "rol" in df_liste.columns else ["Tümü"]
    rol_filtre = st.selectbox("Rol", rol_secenekler, key="imp_rol")

# Filtreleri uygula
df_filtreli = df_liste.copy()
if arama:
    _ara = arama.strip().lower()
    _mask = (
        df_filtreli.get("ad_soyad", df_filtreli.get("ad", "")).str.lower().str.contains(_ara, na=False)
        | df_filtreli.get("email", "").str.lower().str.contains(_ara, na=False)
    )
    df_filtreli = df_filtreli[_mask]
if ofis_filtre != "Tümü" and "ofis_adi" in df_filtreli.columns:
    df_filtreli = df_filtreli[df_filtreli["ofis_adi"] == ofis_filtre]
if rol_filtre != "Tümü" and "rol" in df_filtreli.columns:
    df_filtreli = df_filtreli[df_filtreli["rol"] == rol_filtre]

st.caption(f"{len(df_filtreli)} kullanıcı gösteriliyor")
st.markdown("---")




# ── Kullanıcı listesi ────────────────────────────────────────────────────────
_ROL_LABEL = {
    "admin": "Admin", "broker": "Broker", "danisan": "Danışman",
    "gd": "Gayrimenkul Danışmanı", "yonetici": "Yönetici",
    "ofis_asistani": "Ofis Asistanı", "medya": "Medya",
}

# Seçim yapıldıysa üstte göster
if st.session_state.get("_impersonated_name"):
    _sel = st.session_state["_impersonated_name"]
    st.success(f"✅ **{_sel}** seçildi — sidebar güncellendu. Devam etmek için sol menüden sayfa seçin.")
    if st.button("→ Ana Sayfaya Git", type="primary"):
        st.session_state.pop("_impersonated_name", None)
        st.switch_page("pages/ana_sayfa.py")
    st.divider()

# Her kullanıcı için tek satır
for _, satir in df_filtreli.iterrows():
    satir_dict = satir.to_dict()
    ad     = str(satir_dict.get("ad_soyad") or satir_dict.get("ad", "—")).strip()
    rol    = str(satir_dict.get("rol", "")).strip().lower()
    ofis   = str(satir_dict.get("ofis_adi", "")).strip()
    email  = str(satir_dict.get("email", "")).strip()
    uk     = str(satir_dict.get("user_key", "")).strip()
    telefon = str(satir_dict.get("telefon", "")).strip()
    foto_p = resolve_personel_photo(satir_dict)

    c1, c2, c3, c4 = st.columns([3, 2, 2, 1.5])
    with c1:
        st.write(f"**{ad}**")
    with c2:
        st.caption(_ROL_LABEL.get(rol, rol))
    with c3:
        st.caption(ofis)
    with c4:
        if st.button("Seç", key=f"sel_{uk or email}", use_container_width=True):
            if not st.session_state.get("_impersonate_active"):
                st.session_state["_impersonate_original"] = dict(
                    st.session_state.get("kullanici", {})
                )
            _yeni = {
                "id": "", "email": email, "user_key": uk,
                "rol": rol, "ofis_id": str(satir_dict.get("ofis_id","")).strip(),
                "ofis_adi": ofis, "ad": ad, "ad_soyad": ad,
                "telefon": telefon,
                "yetki_no": str(satir_dict.get("yetki_no","")).strip(),
                "foto_url": "", "foto_bytes": None,
                "foto_path": foto_p or "",
                "logo_url": "", "logo_bytes": None,
                "access_token": "", "refresh_token": "",
                "_impersonated": True,
            }
            st.session_state["kullanici"]           = _yeni
            st.session_state["user_role"]           = rol
            st.session_state["user_name"]           = ad
            st.session_state["user_initials"]       = "".join(
                w[0].upper() for w in ad.split()[:2] if w
            )
            st.session_state["_impersonate_active"] = True
            st.session_state["_impersonated_name"]  = ad
            st.rerun()
