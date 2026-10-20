# core/ozellik_erisim.py
# -*- coding: utf-8 -*-
"""
Özellik anahtarı (feature flag) — yeni bir ekranı önce sadece seçili
kullanıcılara açmak, diğerlerine eski ekranı göstermek için.

Veri: Supabase 'ozellik_erisim' tablosu (bkz. sql/ozellik_erisim.sql).
  kullanici = e-posta veya kullanıcı adı ('*' = herkes), aktif = true/false.

Kullanım:
    from core.ozellik_erisim import ozellik_acik_mi
    if ozellik_acik_mi("yeni_ana_sayfa"):
        ...yeni ekran...

GÜVENLİ VARSAYILAN: tablo yoksa, Supabase'e ulaşılamazsa ya da herhangi
bir hata olursa False döner → kullanıcı ESKİ ekranı görür, uygulama bozulmaz.

Kontrol edilen kimlik: su_anki_danisman() (giriş adı) VE oturumdaki
e-posta, ikisi de küçük harfe çevrilerek. "Kullanıcı Görünümü" ile bir
danışman olarak bakıyorsan, o danışmanın yetkisine göre davranır (testte
işe yarar).

Test için: adres sonuna ?eski=1 eklersen, yetkili olsan bile eski ekranı
görürsün (karşılaştırma için).
"""

import streamlit as st

from core.supabase_client import get_client
from core.danisman_ortak import su_anki_danisman


@st.cache_data(ttl=60, show_spinner=False)
def _yetkili_kullanicilar(ozellik):
    resp = (
        get_client()
        .table("ozellik_erisim")
        .select("kullanici")
        .eq("ozellik", ozellik)
        .eq("aktif", True)
        .execute()
    )
    return sorted({
        (r.get("kullanici") or "").strip().lower()
        for r in (resp.data or [])
        if (r.get("kullanici") or "").strip()
    })


def ozellik_acik_mi(ozellik):
    try:
        if st.query_params.get("eski") == "1":
            return False
        liste = _yetkili_kullanicilar(ozellik)
        if not liste:
            return False
        if "*" in liste:
            return True
        adaylar = {
            (su_anki_danisman() or "").strip().lower(),
            (st.session_state.get("kullanici", {}).get("email") or "").strip().lower(),
        }
        adaylar.discard("")
        return bool(adaylar & set(liste))
    except Exception:
        return False
