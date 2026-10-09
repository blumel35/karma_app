"""
core/ajanda_ui.py

Ajandam sekmesinin Streamlit tarafı (09.10.2026): takvim bileşeni, zamanı
gelen alarm şeridi, "Olay ekle" ve olay detayı pencereleri (st.dialog).
Rehberim sayfası (pages/Danisman_Rehberim.py) ilk sekmede bunu çağırır.
"""
import time as _zaman
from html import escape as _esc
from datetime import datetime as _dt, date as _date, time as _time, timedelta as _td

import streamlit as st

from core.ajanda import (
    TURLER, HATIRLATMA_SECENEKLERI, olaylari_cek, olay_ekle, olay_ertele,
    olay_tamamla, olay_sil, takvim_olaylari, simdi_yerel, bugun_yerel, _alarm_yerel,
)
from core.ajanda_bilesen import ajanda_takvimi
from core.danisman_ortak import (
    rehber_alarm_kur, rehber_alarm_kaldir, rehber_gorusme_ekle, _isim_normalize,
)

_AY = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
       "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
_GUN = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
_TUR_RENK = {"fsbo": "#b98a2c", "gos": "#5f8266", "ran": "#0369a1", "ara": "#6d28d9", "dig": "#6b7385"}


def geciken_alarmlar(kisiler):
    """Zamanı gelmiş Rehberim alarmları (en eskisi üstte)."""
    simdi = simdi_yerel()
    return sorted(
        [m for m in kisiler if _alarm_yerel(m) and _alarm_yerel(m) <= simdi],
        key=lambda m: _alarm_yerel(m),
    )


def _tarih_yazi(t):
    return f"{t.day} {_AY[t.month - 1]} {_GUN[t.weekday()]}"


def _kisi_bul(kisiler, kisi_id=None, kisi_ad=""):
    if kisi_id:
        for m in kisiler:
            if str(m.get("id")) == str(kisi_id):
                return m
    ad = (kisi_ad or "").strip().lower()
    if ad:
        for m in kisiler:
            if (m.get("ad") or "").strip().lower() == ad:
                return m
    return None


def _kisi_karti(ad, kayit):
    """Kişi adı + (Rehberim'de telefonu varsa) ara / WhatsApp bağlantıları."""
    tel = (kayit or {}).get("telefon") or ""
    rak = "".join(ch for ch in tel if ch.isdigit())
    butonlar = ""
    if len(rak) >= 10:
        e164 = "90" + rak[-10:]
        butonlar = (
            f"<a href='tel:+{e164}' style='text-decoration:none;display:inline-flex;width:34px;height:34px;"
            "border-radius:50%;background:#1c2b47;color:#fff;align-items:center;justify-content:center'>✆</a>"
            f"<a href='https://wa.me/{e164}' target='_blank' rel='noopener noreferrer' style='text-decoration:none;"
            "display:inline-flex;width:34px;height:34px;border-radius:50%;background:#25d366;color:#fff;"
            "align-items:center;justify-content:center'>✉</a>"
        )
    alt = _esc(tel) if tel else ("Rehberim'de kayıtlı değil" if not kayit else "Telefon yok")
    st.markdown(
        "<div style='display:flex;gap:10px;align-items:center;background:#f7f8fa;border:1px solid #e1e4e9;"
        "border-radius:12px;padding:10px 12px;margin:6px 0'>"
        f"<div><b>{_esc(ad)}</b><br><span style='font-size:12.5px;color:#6b7385'>{alt}</span></div>"
        f"<div style='margin-left:auto;display:flex;gap:6px'>{butonlar}</div></div>",
        unsafe_allow_html=True,
    )


# ── Olay ekle ──────────────────────────────────────────────────────────
@st.dialog("Olay ekle")
def _ekle_penceresi(tarih_iso, danisman, kisiler, tablo_hatasi):
    if tablo_hatasi:
        st.error("Ajanda tablosu henüz yok. Supabase SQL Editor'de "
                 "`sql/ajanda_olaylari.sql` dosyasını çalıştır, sonra tekrar dene.")
    try:
        varsayilan = _dt.strptime(tarih_iso, "%Y-%m-%d").date()
    except Exception:
        varsayilan = bugun_yerel()
    tur = st.radio("Tür", list(TURLER), format_func=lambda k: TURLER[k],
                   horizontal=True, key="aj_e_tur")
    baslik = st.text_input("Başlık", key="aj_e_baslik",
                           placeholder=f"örn. {TURLER[tur]} — Buca dükkan (boşsa tür adı yazılır)")
    adlar = sorted({(m.get("ad") or "").strip() for m in kisiler if (m.get("ad") or "").strip()},
                   key=lambda x: x.lower())
    secim = st.selectbox("Kişi (Rehberim'den)", ["— Seçme —"] + adlar, key="aj_e_kisi")
    serbest = st.text_input("Rehberim'de yoksa kişi adı yaz", key="aj_e_kisi_yaz")
    c1, c2 = st.columns(2)
    with c1:
        gun = st.date_input("Tarih", value=varsayilan, format="DD.MM.YYYY", key="aj_e_tarih")
    with c2:
        saat = st.time_input("Saat", value=_time(10, 0), step=900, key="aj_e_saat")
    yer = st.text_input("Yer / konum", key="aj_e_yer", placeholder="örn. Buca / Kuruçeşme")
    notu = st.text_area("Not", key="aj_e_not", height=80, placeholder="Hazırlık, gündem, hatırlatma…")
    hat = st.selectbox("Hatırlat", list(HATIRLATMA_SECENEKLERI), index=2, key="aj_e_hat")
    st.caption("Hatırlatma telefonuna bildirim olarak gelir; en geç ~30 dakika gecikebilir.")
    if st.button("Kaydet", type="primary", use_container_width=True, key="aj_e_kaydet",
                 disabled=bool(tablo_hatasi)):
        kisi_ad = _isim_normalize(serbest) if serbest.strip() else ("" if secim.startswith("—") else secim)
        kayit = _kisi_bul(kisiler, None, kisi_ad)
        try:
            kuruldu = olay_ekle(
                danisman, baslik, tur, gun, saat, kisi_ad=kisi_ad,
                kisi_id=(kayit or {}).get("id"), yer=yer, notlar=notu,
                hatirlat_dk=HATIRLATMA_SECENEKLERI[hat],
            )
        except Exception as e:
            st.error(f"Kaydedilemedi: {e}")
            return
        st.session_state["aj_git"] = {"t": gun.isoformat(), "n": int(_zaman.time() * 1000)}
        mesaj = f"✓ Olay eklendi — {gun.day} {_AY[gun.month - 1]}"
        if HATIRLATMA_SECENEKLERI[hat] is not None and not kuruldu:
            mesaj += " (hatırlatma zamanı geçmiş olduğu için kurulmadı)"
        st.session_state["aj_mesaj"] = mesaj
        st.rerun()


# ── Olay detayı ────────────────────────────────────────────────────────
@st.dialog("Olay")
def _detay_penceresi(olay_id, danisman, olaylar, kisiler):
    if olay_id.startswith("a:"):
        _alarm_detay(olay_id[2:], kisiler)
        return
    o = next((x for x in olaylar if str(x["id"]) == olay_id), None)
    if not o:
        st.info("Bu olay artık yok (silinmiş olabilir).")
        return
    tur = o.get("tur") if o.get("tur") in TURLER else "dig"
    try:
        t = _dt.strptime(str(o["tarih"])[:10], "%Y-%m-%d").date()
    except Exception:
        t = bugun_yerel()
    st.markdown(
        f"<span style='font-size:10px;font-weight:800;border-radius:5px;padding:2px 8px;"
        f"background:{_TUR_RENK[tur]}22;color:{_TUR_RENK[tur]}'>{_esc(TURLER[tur])}</span>"
        f"<div style='font-size:19px;font-weight:800;margin:6px 0 4px'>{_esc(o.get('baslik') or '')}</div>"
        f"<div style='font-size:14px'>🗓 {_esc(_tarih_yazi(t))} · {_esc(str(o.get('saat') or '')[:5])}</div>"
        + (f"<div style='font-size:14px'>📍 {_esc(o['yer'])}</div>" if o.get("yer") else "")
        + (f"<div style='font-size:14px;margin-top:6px;white-space:pre-wrap'>{_esc(o['notlar'])}</div>" if o.get("notlar") else ""),
        unsafe_allow_html=True,
    )
    kayit = _kisi_bul(kisiler, o.get("kisi_id"), o.get("kisi_ad"))
    if o.get("kisi_ad"):
        _kisi_karti(o["kisi_ad"], kayit)
    gorusme = ""
    if kayit:
        gorusme = st.text_area(
            "Görüşme notu (kişinin Rehberim görüşme geçmişine yazılır)", height=80,
            key=f"aj_d_not_{o['id']}", placeholder="Ne konuşuldu, sonuç ne oldu? (boş bırakılabilir)")
    b1, b2, b3 = st.columns(3)
    with b1:
        if o.get("tamamlandi"):
            if st.button("↩ Geri al", key=f"aj_d_geri_{o['id']}", use_container_width=True):
                olay_tamamla(o["id"], False)
                st.rerun()
        elif st.button("✓ Tamamlandı", key=f"aj_d_bit_{o['id']}", type="primary", use_container_width=True):
            if kayit and gorusme.strip():
                rehber_gorusme_ekle(kayit["id"], bugun_yerel(), gorusme)
            olay_tamamla(o["id"], True)
            st.rerun()
    with b2:
        if st.button("⏱ Yarına", key=f"aj_d_er_{o['id']}", use_container_width=True):
            olay_ertele(o)
            st.rerun()
    with b3:
        if st.button("Sil", key=f"aj_d_sil_{o['id']}", use_container_width=True):
            olay_sil(o["id"])
            st.rerun()


def _alarm_detay(kisi_id, kisiler):
    kayit = _kisi_bul(kisiler, kisi_id)
    z = _alarm_yerel(kayit) if kayit else None
    if not kayit or not z:
        st.info("Bu alarm artık yok (kaldırılmış olabilir).")
        return
    st.markdown(
        "<span style='font-size:10px;font-weight:800;border-radius:5px;padding:2px 8px;"
        f"background:{_TUR_RENK['ara']}22;color:{_TUR_RENK['ara']}'>Yeniden ara</span>"
        f"<div style='font-size:19px;font-weight:800;margin:6px 0 4px'>Yeniden ara — {_esc(kayit.get('ad') or '')}</div>"
        f"<div style='font-size:14px'>⏰ {_esc(_tarih_yazi(z.date()))} · {z.strftime('%H:%M')}</div>"
        + (f"<div style='font-size:14px;margin-top:6px'>{_esc(kayit['alarm_notu'])}</div>" if kayit.get("alarm_notu") else "")
        + "<div style='font-size:12px;color:#6d28d9;background:#ede9fe;border-radius:8px;padding:6px 10px;margin-top:8px'>"
        "Rehberim'de kurduğun alarm — ikisi aynı kayıttır.</div>",
        unsafe_allow_html=True,
    )
    _kisi_karti(kayit.get("ad") or "", kayit)
    gorusme = st.text_area("Görüşme notu", height=80, key=f"aj_a_not_{kisi_id}",
                           placeholder="Ne konuşuldu, sonuç ne oldu? (boş bırakılabilir)")
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("✓ Aradım", key=f"aj_a_bit_{kisi_id}", type="primary", use_container_width=True,
                     help="Görüşmeyi kaydeder ve alarmı kaldırır"):
            rehber_gorusme_ekle(kayit["id"], bugun_yerel(), gorusme)
            rehber_alarm_kaldir(kayit["id"])
            st.rerun()
    with b2:
        if st.button("⏱ Yarına", key=f"aj_a_er_{kisi_id}", use_container_width=True):
            yeni = _dt.combine(max(z.date(), bugun_yerel()) + _td(days=1), z.time())
            rehber_alarm_kur(kayit["id"], yeni, kayit.get("alarm_notu") or "")
            st.rerun()
    with b3:
        if st.button("Kaldır", key=f"aj_a_kal_{kisi_id}", use_container_width=True):
            rehber_alarm_kaldir(kayit["id"])
            st.rerun()


# ── Zamanı gelen alarm şeridi ──────────────────────────────────────────
def _alarm_seridi(geciken):
    if not geciken:
        return
    with st.container(border=True):
        st.markdown(f"**⏰ Yeniden aranacak kişiler ({len(geciken)})**")
        st.caption("Alarm zamanı gelen kişiler. Aradıktan sonra alarmı kaldır; ne konuştuğunu "
                   "takvimde olaya dokunarak ya da Rehberim'de kişinin ⋮ menüsünden yazabilirsin.")
        for gm in geciken:
            gz = _alarm_yerel(gm)
            c1, c2, c3 = st.columns([5, 2, 2])
            with c1:
                satir = f"**{_esc(gm.get('ad') or '—')}** · alarm: {gz.strftime('%d.%m.%Y %H:%M')}"
                gn = (gm.get("alarm_notu") or "").strip()
                if gn:
                    satir += f"  \n{_esc(gn)}"
                st.markdown(satir)
            with c2:
                if st.button("Yarına ertele", key=f"aj_gec_er_{gm['id']}", use_container_width=True):
                    rehber_alarm_kur(gm["id"], _dt.combine(bugun_yerel() + _td(days=1), _time(10, 0)),
                                     gm.get("alarm_notu") or "")
                    st.rerun()
            with c3:
                if st.button("Alarmı kaldır", key=f"aj_gec_kal_{gm['id']}", use_container_width=True):
                    rehber_alarm_kaldir(gm["id"])
                    st.rerun()


# ── Sekme ──────────────────────────────────────────────────────────────
def ajanda_sekmesi(danisman, kisiler):
    olaylar, hata = olaylari_cek(danisman)
    if hata:
        st.warning("Ajanda tablosu henüz oluşturulmamış — `sql/ajanda_olaylari.sql` dosyasını "
                   "Supabase'de çalıştırınca olay ekleyebilirsin. Rehberim alarmların takvimde yine görünür.")
    if st.session_state.get("aj_mesaj"):
        st.success(st.session_state.pop("aj_mesaj"))

    _alarm_seridi(geciken_alarmlar(kisiler))

    simdi = simdi_yerel()
    tk = takvim_olaylari(olaylar, kisiler)
    sonuc = ajanda_takvimi(
        tk, bugun=simdi.date().isoformat(), simdi=simdi.strftime("%Y-%m-%dT%H:%M"),
        gorunum0=st.session_state.get("aj_v", "hafta"),
        tarih0=st.session_state.get("aj_d"),
        git=st.session_state.get("aj_git"),
    )
    if sonuc and sonuc.get("n") != st.session_state.get("aj_son_n"):
        st.session_state["aj_son_n"] = sonuc.get("n")
        if sonuc.get("v"):
            st.session_state["aj_v"] = sonuc["v"]
        if sonuc.get("d"):
            st.session_state["aj_d"] = sonuc["d"]
        if sonuc.get("k") == "ekle":
            _ekle_penceresi(sonuc.get("t") or simdi.date().isoformat(), danisman, kisiler, hata)
        elif sonuc.get("k") == "olay" and sonuc.get("id"):
            _detay_penceresi(str(sonuc["id"]), danisman, olaylar, kisiler)
