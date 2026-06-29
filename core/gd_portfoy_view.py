# core/gd_portfoy_view.py  v3
# GD Kişisel Portföy Görünümü — sade kart, gizlenebilir filtre, minik istatistik
# components.html YOK — DOM çakışması yok

import streamlit as st
import pandas as pd
import html as _html
from datetime import datetime

try:
    import sys, os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.supabase_client import get_client
except Exception:
    pass

# ── Yardımcılar ───────────────────────────────────────────────────────────────
def _gun(v):
    for alan in ("ilan_tarihi","olusturma_tarihi"):
        s = v.get(alan,"")
        if not s: continue
        for fmt in ("%d.%m.%Y","%Y-%m-%d","%Y-%m-%dT%H:%M:%S.%f",
                    "%Y-%m-%dT%H:%M:%S","%Y-%m-%d %H:%M:%S"):
            try:
                d = datetime.strptime(str(s)[:len(fmt)], fmt)
                return max((datetime.now()-d).days, 0)
            except: continue
    return None

def _tarih_et(g):
    if g is None: return "—"
    if g == 0:   return "Bugün"
    if g <= 7:   return f"{g}g"
    if g <= 30:  return f"{g//7}h"
    return f"{g//30}ay"

def _gun_renk(g):
    if g is None: return "#94a3b8","#f1f5f9"
    if g <= 7:   return "#166534","#dcfce7"
    if g <= 30:  return "#92400e","#fef3c7"
    if g <= 90:  return "#c2410c","#ffedd5"
    return "#991b1b","#fee2e2"

def _fiyat(v):
    f = v.get("fiyat","") or ""
    if not f or str(f).strip() in ("","None","-"): return ""
    try:
        fn = float(str(f).replace(".","").replace(",",".").replace("₺","").replace("TL","").strip())
        return f"{fn:,.0f} ₺".replace(",",".")
    except: return str(f)

def _bdg(et):
    if not et or et in ("Belirsiz","None",""): return ""
    c = {"Satılık":("#A32D2D","#FCEBEB"),"Kiralık":("#854F0B","#FAEEDA"),
         "Konut":("#475569","#f1f5f9"),"İşyeri":("#475569","#f1f5f9"),
         "Arsa":("#3B6D11","#EAF3DE")}.get(et,("#475569","#f1f5f9"))
    return (f'<span style="display:inline-flex;align-items:center;padding:2px 8px;'
            f'border-radius:20px;font-size:10.5px;font-weight:600;'
            f'color:{c[0]};background:{c[1]};margin-right:3px;">{et}</span>')

def _ilce(v):
    lst=[i for i in (v.get("ilceler") or []) if i and i!="Diğer Bölge"]
    return " · ".join(lst[:2]) if lst else (v.get("ilce","") or v.get("mahalle","") or "")

def _baslik(v):
    ozet = v.get("ozet","") or ""
    if ozet and str(ozet).strip() not in ("","None","nan","--"):
        s = str(ozet).strip()
        return s.title() if s.isupper() or s.islower() else s
    isl = v.get("islem_tipi","") or ""
    mulk = v.get("mulk_tipi","") or ""
    return f"{isl} {mulk}".strip() or "Portföy"

def _dan(v):
    d = v.get("talep_eden_danisan","") or ""
    return d.split("<")[0].strip().strip('"') if d else ""


# ── ANA FONKSİYON ─────────────────────────────────────────────────────────────
def gd_portfoy_goster(veriler: list, prefix: str = "gd"):
    if not veriler:
        st.info("Bu GD'ye ait portföy bulunamadı.")
        return

    gunler = [_gun(v) for v in veriler]
    toplam = len(veriler)
    yeni7  = sum(1 for g in gunler if g is not None and g <= 7)
    _g_lst = [g for g in gunler if g is not None]
    ort_g  = int(sum(_g_lst)/len(_g_lst)) if _g_lst else 0
    yetki  = sum(1 for g in gunler if g is not None and 70 <= g <= 90)

    # ── Minik istatistik + Filtre toggle ──────────────────────────────────────
    _warn  = f" · ⚠️ {yetki} yetki" if yetki > 0 else ""
    _yeni  = f" · 🆕 {yeni7}" if yeni7 > 0 else ""
    _ort   = f" · ⏱ ort {ort_g}g" if ort_g > 0 else ""

    _c1, _c2 = st.columns([6, 1])
    with _c1:
        st.markdown(
            f'<div style="font-size:11px;color:#94a3b8;padding:4px 0;">'
            f'<b style="color:#355C7D">{toplam} portföy</b>{_yeni}{_ort}{_warn}'
            f'</div>',
            unsafe_allow_html=True
        )
    with _c2:
        _ac = st.session_state.get(f"{prefix}_filtre_ac", False)
        if st.button("⚙" if not _ac else "✕",
                     key=f"{prefix}_filtre_toggle",
                     use_container_width=True,
                     type="primary" if _ac else "secondary"):
            st.session_state[f"{prefix}_filtre_ac"] = not _ac
            st.rerun()

    # Filtreler — gizlenebilir
    ara      = st.session_state.get(f"{prefix}_ara_v", "")
    ilce_sec = st.session_state.get(f"{prefix}_ilce_v", "Tümü")
    islem_sec= st.session_state.get(f"{prefix}_islem_v", "Tümü")
    sir_sec  = st.session_state.get(f"{prefix}_sir_v", "Tarih ↓")

    if st.session_state.get(f"{prefix}_filtre_ac", False):
        with st.container(border=True):
            fa, fb, fc, fd = st.columns([2.5, 1.5, 1.5, 1.5])
            with fa:
                ara = st.text_input("Ara", value=ara,
                    placeholder="Başlık, ilçe, mahalle...",
                    key=f"{prefix}_ara", label_visibility="collapsed")
                st.session_state[f"{prefix}_ara_v"] = ara

            ilce_opts = ["Tümü"] + sorted(set(
                str(v.get("ilce","") or "").strip() for v in veriler
                if v.get("ilce","") and str(v.get("ilce","")).strip() not in ("","None")
            ))
            with fb:
                ilce_sec = st.selectbox("İlçe", ilce_opts,
                    index=ilce_opts.index(ilce_sec) if ilce_sec in ilce_opts else 0,
                    key=f"{prefix}_ilce", label_visibility="collapsed")
                st.session_state[f"{prefix}_ilce_v"] = ilce_sec

            islem_opts = ["Tümü"] + sorted(set(
                v.get("islem_tipi","") for v in veriler if v.get("islem_tipi","")
            ))
            with fc:
                islem_sec = st.selectbox("İşlem", islem_opts,
                    index=islem_opts.index(islem_sec) if islem_sec in islem_opts else 0,
                    key=f"{prefix}_islem", label_visibility="collapsed")
                st.session_state[f"{prefix}_islem_v"] = islem_sec

            sir_opts = ["Tarih ↓","Tarih ↑","Fiyat ↑","Fiyat ↓"]
            with fd:
                sir_sec = st.selectbox("Sırala", sir_opts,
                    index=sir_opts.index(sir_sec) if sir_sec in sir_opts else 0,
                    key=f"{prefix}_sir", label_visibility="collapsed")
                st.session_state[f"{prefix}_sir_v"] = sir_sec

            if st.button("Temizle", key=f"{prefix}_temizle"):
                for k in [f"{prefix}_ara_v",f"{prefix}_ilce_v",
                          f"{prefix}_islem_v",f"{prefix}_sir_v"]:
                    st.session_state.pop(k, None)
                st.rerun()

    # ── Filtreleme ────────────────────────────────────────────────────────────
    f = veriler[:]
    if ara:
        al = ara.lower()
        f = [v for v in f if any(al in str(v.get(k,"")).lower()
             for k in ["ozet","ilce","mahalle","bolge_mahalle",
                       "talep_eden_danisan","ozellikler"])]
    if ilce_sec != "Tümü":
        f = [v for v in f if v.get("ilce","") == ilce_sec]
    if islem_sec != "Tümü":
        f = [v for v in f if v.get("islem_tipi","") == islem_sec]

    def _sf(v):
        try: return float(str(v.get("fiyat","")).replace(".","").replace(",",".").replace("₺","").replace("TL","").strip())
        except: return float("inf")

    if "↓" in sir_sec and "Fiyat" not in sir_sec:
        f = sorted(f, key=lambda v: (_gun(v) or 9999))
    elif "↑" in sir_sec and "Fiyat" not in sir_sec:
        f = sorted(f, key=lambda v: (_gun(v) or 0), reverse=True)
    elif "Fiyat ↑" in sir_sec:
        f = sorted(f, key=_sf)
    elif "Fiyat ↓" in sir_sec:
        f = sorted(f, key=_sf, reverse=True)

    if not f:
        st.info("Filtrelere uyan portföy bulunamadı.")
        return

    # ── Kart listesi ──────────────────────────────────────────────────────────
    for v in f:
        g         = _gun(v)
        g_fg,g_bg = _gun_renk(g)
        baslik    = _baslik(v)
        fiyat     = _fiyat(v)
        ilce_txt  = _ilce(v)
        dan_txt   = _dan(v)
        isl       = v.get("islem_tipi","") or ""
        mulk      = v.get("mulk_tipi","") or ""
        oda       = v.get("oda_sayisi_m2","") or ""
        m2        = str(v.get("m2","") or "")
        link      = v.get("ilan_linki","") or v.get("startkey_detay_link","") or ""
        ofis      = v.get("ofis_label","") or v.get("kaynak","") or ""
        ozet_alt  = v.get("ozellikler","") or ""
        kid       = str(v.get("id","") or id(v))

        bdr = "#1E3A5F" if "sat" in isl.lower() else ("#0d9488" if "kir" in isl.lower() else "#e2e8f0")
        etiket = _bdg(isl) + _bdg(mulk)

        # Kayıtlı not varsa göster
        _not = st.session_state.get(f"not_{kid}","")

        st.markdown(
            f'<div style="border:1px solid #e2e8f0;border-left:4px solid {bdr};'
            f'border-radius:12px;background:#fff;margin-bottom:6px;overflow:hidden;">'
            f'<div style="padding:11px 15px 9px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;">'
            f'<span style="font-size:11px;font-weight:700;color:#355C7D;'
            f'text-transform:uppercase;letter-spacing:.04em;">'
            f'{_html.escape(ilce_txt or "—")}</span>'
            f'<span style="background:{g_bg};color:{g_fg};padding:1px 7px;'
            f'border-radius:999px;font-size:10px;font-weight:700;">'
            f'{_tarih_et(g)}</span>'
            f'</div>'
            f'<div style="font-size:13px;font-weight:700;color:#0F172A;'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:3px;">'
            f'{_html.escape(baslik[:70])}</div>'
            f'<div style="display:flex;gap:8px;align-items:center;'
            f'flex-wrap:wrap;font-size:11px;color:#64748B;">'
            +(f'<span style="font-size:13px;font-weight:800;color:#0F172A;">'
              f'{_html.escape(fiyat)}</span>' if fiyat else "")
            +(f'<span>{_html.escape(oda)}</span>' if oda else "")
            +(f'<span>{_html.escape(m2)} m²</span>'
              if m2 and m2 not in ("","None","nan") else "")
            +f'<span style="color:#94a3b8;">{_html.escape(dan_txt)}</span>'
            +f'</div>'
            +(_not and f'<div style="font-size:11px;color:#355C7D;margin-top:4px;'
              f'background:#EEF4FA;border-radius:6px;padding:3px 8px;">'
              f'📝 {_html.escape(_not[:80])}</div>' or "")
            +f'</div>'
            f'<div style="border-top:1px solid #f1f5f9;padding:6px 15px;'
            f'background:#f8fafc;display:flex;justify-content:space-between;align-items:center;">'
            f'<div>{etiket}</div>'
            f'<span style="font-size:10px;font-weight:700;color:#94a3b8;">'
            f'{_html.escape(str(ofis).upper())}</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        # Aksiyon butonları
        _b1, _b2, _b3, _b4, _ = st.columns([1.3, 1.6, 1.4, 1.4, 2.3])

        with _b1:
            if st.button("📊 Sunum", key=f"{prefix}_sunum_{kid}",
                         use_container_width=True, type="primary"):
                st.session_state["sunum_portfoy"] = v
                st.session_state["sunum_kaynak"]  = "gd_kokpit"
                st.switch_page("pages/Sunum_Merkezi_V2_Demo.py")

        with _b2:
            _not_ac = st.session_state.get(f"{prefix}_not_ac_{kid}", False)
            _not_lbl = "📝 Notu Düzenle" if _not else "📝 Not Ekle"
            if st.button(_not_lbl, key=f"{prefix}_not_btn_{kid}",
                         use_container_width=True):
                st.session_state[f"{prefix}_not_ac_{kid}"] = not _not_ac
                st.rerun()

        with _b3:
            takipte = st.session_state.get(f"takip_{kid}", False)
            if st.button("⭐ Takipte" if takipte else "☆ Takip",
                         key=f"{prefix}_takip_{kid}",
                         use_container_width=True):
                st.session_state[f"takip_{kid}"] = not takipte
                st.toast("✅ Takip listesine eklendi!" if not takipte else "Takipten çıkarıldı.")
                st.rerun()

        with _b4:
            if link:
                st.link_button("🔗 İlan", link, use_container_width=True)

        # Not formu
        if st.session_state.get(f"{prefix}_not_ac_{kid}", False):
            with st.container(border=True):
                yeni_not = st.text_area(
                    "Notunuz", value=_not, height=70,
                    placeholder="Bu portföy hakkında özel notunuz...",
                    key=f"{prefix}_not_text_{kid}"
                )
                nc1, nc2 = st.columns([1, 4])
                with nc1:
                    if st.button("💾 Kaydet", key=f"{prefix}_not_kaydet_{kid}",
                                 type="primary"):
                        st.session_state[f"not_{kid}"] = yeni_not
                        st.session_state[f"{prefix}_not_ac_{kid}"] = False
                        st.toast("✅ Not kaydedildi!")
                        st.rerun()
                with nc2:
                    if st.button("İptal", key=f"{prefix}_not_iptal_{kid}"):
                        st.session_state[f"{prefix}_not_ac_{kid}"] = False
                        st.rerun()

        st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)
