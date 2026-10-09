"""
pages/Danisman_Rehberim.py

Rehberim — kişisel kişi defteri (13.08.2026). Hamburger menüden
erişilir. Talep/Portföy tablolarından TAMAMEN BAĞIMSIZ — "Yeni Talep/
Portföy Ekle" formunda müşteri adı girildiğinde buraya OTOMATİK
senkronize edilir (core.danisman_ortak._musteri_senkronize), ama bu
sayfadan elle de kişi eklenebilir (iş ortağı, kiraya veren vb. — bir
talep/portföye bağlı olmak zorunda değil).

BİLİNÇLİ TASARIM: Şimdilik KİŞİSEL — sadece kaydı ekleyen danışmana
görünür, ofis geneli paylaşılmıyor (ileride ihtiyaç olursa
genişletilebilir). "İlanlar silinse de müşteriler kayıtlı kalsın"
isteği, bu tablonun talep/portföy ile hiçbir foreign key/cascade
ilişkisi olmamasıyla sağlanıyor.

DÜZELTME (13.08.2026 — 3. tur, kompaktlaştırma): Büyük her-zaman-açık
kartlar yerine gerçek bir adres defteri hissi: üstte Talep/Portföy
panolarındaki A-Z hızlı gezinme çubuğuyla AYNI görsel dil (aktif harf
koyu/tıklanabilir link, boş harf soluk), her kişi TEK satırda (ad +
tip + telefon + not/sil aksiyonu aynı satırda st.popover ile — expander
gibi ayrı bir satır işgal etmiyor), "+ Yeni Kişi Ekle" filtre satırının
sağına, kompakt bir popover butonu olarak taşındı.
"""

import streamlit as st
from html import escape as _esc
from datetime import date as _date, datetime as _dt, time as _time, timedelta as _td, timezone as _tz

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import oturum_kontrol
from core.ajanda_ui import ajanda_sekmesi, geciken_alarmlar
from core.danisman_ortak import (
    su_anki_danisman, musterileri_cek, musteri_ekle, musteri_guncelle,
    musteri_sil, rehber_takip_ayarla, takip_ozelligi_var, rehber_alarm_kur, rehber_alarm_kaldir, rehber_gorusme_ekle, rehber_gorusme_sil, render_topbar, hide_sidebar_css, IZMIR_ILCELERI, _tip_listele,
    _tr_lower,
)

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()
render_topbar("Ajandam ve Rehberim", ikon="📅", geri_hedefi="pages/Danisman_Secim.py")

TIP_SECENEKLERI = ["Alıcı", "Satıcı", "Kiraya Veren", "Kiracı", "İş Ortağı", "FSBO", "Diğer"]
TUM_HARFLER = list("ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ")


_WA_SVG = (
    "<svg viewBox='0 0 24 24'><path d='M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.85.5 3.58 1.36 5.06L2 22l5.2-1.37a9.87 9.87 0 0 0 4.84 1.24h.01"
    "c5.46 0 9.9-4.45 9.9-9.91C21.96 6.45 17.5 2 12.04 2zm5.8 14.03c-.24.68-1.4 1.3-1.93 1.34-.5.04-1 .23-3.36-.7"
    "-2.84-1.13-4.63-3.98-4.77-4.16-.14-.19-1.14-1.52-1.14-2.9 0-1.38.72-2.05.98-2.33.26-.28.56-.35.75-.35h.54"
    "c.17 0 .4-.03.62.48.24.55.8 1.9.87 2.04.07.14.12.3.02.49-.09.19-.14.3-.28.46-.14.16-.29.36-.42.48-.14.14"
    "-.28.29-.12.57.16.28.71 1.17 1.52 1.9 1.05.94 1.93 1.23 2.2 1.37.28.14.44.12.6-.07.16-.19.68-.79.86-1.06"
    ".18-.28.36-.23.6-.14.25.09 1.6.75 1.87.89.28.14.46.21.53.32.07.12.07.68-.17 1.36z'/></svg>"
)
_TIP_SINIF = {"Alıcı": "al", "Satıcı": "sa", "Kiraya Veren": "ki", "Kiracı": "ki",
              "İş Ortağı": "is", "FSBO": "fs", "Diğer": "di"}


def _telefon_goster(telefon):
    """Telefonu tek biçimde gösterir: 0533 444 44 44. 10 haneli (5xx...) ya da
    başında 0 olan 11 haneli numaralar biçimlenir; başka bir şey (yurt dışı
    numara, eksik/fazla hane) olduğu gibi gösterilir. Kayıtlar DEĞİŞMEZ."""
    ham = (telefon or "").strip()
    r = "".join(ch for ch in ham if ch.isdigit())
    if len(r) == 11 and r.startswith("0"):
        r = r[1:]
    if len(r) == 10 and r.startswith("5"):
        return f"0{r[:3]} {r[3:6]} {r[6:8]} {r[8:]}"
    return ham


def _telefon_blok_html(telefon):
    """Numara + yuvarlak ara / WhatsApp düğmeleri (13.08.2026'daki wa.me /
    tel: yönlendirmesi aynen; yalnızca görünüm sadeleştirildi)."""
    if not (telefon or "").strip():
        return "<div class='dp-tel'></div>"
    rakamlar = "".join(ch for ch in telefon if ch.isdigit())
    son10 = rakamlar[-10:] if len(rakamlar) >= 10 else rakamlar
    e164 = "90" + son10
    return (
        f"<div class='dp-tel'><span class='dp-num'>{_esc(_telefon_goster(telefon))}</span>"
        f"<a class='dp-ib dp-call' href='tel:+{e164}' title='Ara'>✆</a>"
        f"<a class='dp-ib dp-wa' href='https://wa.me/{e164}' target='_blank' rel='noopener noreferrer' title='WhatsApp'>{_WA_SVG}</a></div>"
    )


st.markdown("""
<style>
/* REHBERİM LİSTESİ — sade, sütunlu satır tasarımı (09.10.2026, Meltem:
   "daha kompakt, estetik, okunaklı, takibi kolay"). Her kişi tek bir
   ızgara satırı: avatar | isim + rozetler | telefon + ara/WhatsApp |
   bilgi etiketleri (alarm, son görüşme, bölge). "⋮" menüsü satırın
   sağ ucuna sabit. Dar ekranda satır iki kata iner. */
.dp-k-al { --kc:#e0f2fe; --kt:#075985; }
.dp-k-sa { --kc:#e6efe8; --kt:#2f5d3a; }
.dp-k-is { --kc:#ede9fe; --kt:#5b21b6; }
.dp-k-fs { --kc:#f7f0df; --kt:#7a5a12; }
.dp-k-ki { --kc:#fde8e6; --kt:#9f2d1f; }
.dp-k-di { --kc:#eceef2; --kt:#3d4457; }
div[class*="st-key-dp_mus_row_"] {
    position: relative; gap: 0 !important;
    border-bottom: 1px solid #d3d8e0; background: #fff;
}
div[class*="st-key-dp_mus_row_"]:hover { background: #fbfbfc; }
.dp-row {
    display: grid; align-items: center; column-gap: 12px; row-gap: 4px;
    grid-template-columns: 38px minmax(0,1.25fr) minmax(0,1fr) minmax(0,1.35fr);
    padding: 9px 52px 9px 8px;
}
.dp-row.dp-dense { padding-top: 5px; padding-bottom: 8px; }
.dp-av {
    width: 36px; height: 36px; border-radius: 50%;
    display: grid; place-items: center;
    font-weight: 800; font-size: 12.5px; background: var(--kc); color: var(--kt);
}
.dp-dense .dp-av { width: 30px; height: 30px; font-size: 11px; }
.dp-yildiz { color: #b98a2c; font-size: 12px; }
.dp-nm { font-weight: 700; font-size: 14.5px; color: #1b2540; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dp-sub { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-top: 2px; font-size: 12px; color: #6b7385; }
.dp-tg { font-size: 10.5px; font-weight: 800; border-radius: 5px; padding: 1px 7px; background: var(--kc); color: var(--kt); }
.dp-tel { display: flex; align-items: center; gap: 8px; }
.dp-num { font-variant-numeric: tabular-nums; font-size: 13.5px; color: #1b2540; white-space: nowrap; }
.dp-ib {
    width: 30px; height: 30px; border-radius: 50%; display: inline-grid; place-items: center;
    text-decoration: none !important; color: #fff !important; font-size: 13px; flex: none;
}
.dp-dense .dp-ib { width: 26px; height: 26px; font-size: 12px; }
.dp-ib.dp-call { background: #1c2b47; }
.dp-ib.dp-wa { background: #25d366; }
.dp-ib svg { width: 15px; height: 15px; fill: #fff; }
.dp-pin { font-size: 12px; color: #6b7385; white-space: nowrap; }
/* NOT KAĞIDI (09.10.2026): sağdaki sarı not — alarm, son görüşme ve kişi notu
   tek yerde. Zamanı gelen alarm kırmızı/kalın; kişi notu en fazla 2 satır. */
.dp-note {
    position: relative; min-width: 0; text-align: left;
    background: #fff7c2; border: 1px solid #ecdc86; border-radius: 4px 4px 10px 4px;
    padding: 6px 10px 7px; font-size: 12.5px; line-height: 1.35; color: #4a4220;
    box-shadow: 0 2px 0 rgba(120,100,0,.12), 2px 3px 6px rgba(120,100,0,.10);
    transform: rotate(-.4deg);
}
.dp-note::before {
    content: ""; position: absolute; top: -5px; left: 50%; margin-left: -14px;
    width: 28px; height: 9px; background: rgba(180,160,60,.28); border-radius: 2px;
}
.dp-ln { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dp-ln + .dp-ln { margin-top: 2px; }
.dp-ln.dp-al { color: #b42318; font-weight: 800; }
.dp-ln.dp-fu { color: #8a5d00; font-weight: 800; }
.dp-ln.dp-tx { white-space: normal; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.dp-dense .dp-note .dp-ln.dp-tx { -webkit-line-clamp: 1; }
details.dp-fs { grid-column: 2 / -1; font-size: 12px; margin-top: 2px; padding-bottom: 2px; }
details.dp-fs summary { cursor: pointer; color: #b8892f; font-weight: 700; list-style: none; width: fit-content; }
details.dp-fs summary::-webkit-details-marker { display: none; }
.dp-mus-fsbo {
    margin: 4px 0 2px 0; padding: 6px 10px; border-left: 3px solid #b8892f;
    background: #faf7f0; border-radius: 0 6px 6px 0;
    font-size: 12.5px; line-height: 1.55; color: #3d4457;
}
.dp-mus-fsbo a { color: #1b2540; font-weight: 600; word-break: break-all; }
.dp-mus-fsbo .dp-fsbo-ilan + .dp-fsbo-ilan { margin-top: 6px; padding-top: 6px; border-top: 1px dashed #e4dccb; }
.dp-mus-harf-baslik {
    background: #f7f8fa; border-top: 1px solid #ecebe5; border-bottom: 1px solid #ecebe5;
    font-size: 11px; font-weight: 800; color: #b8892f; letter-spacing: .5px;
    margin: 10px 0 0 0; padding: 4px 8px;
}
.dp-mus-az { display: flex; flex-wrap: wrap; gap: 2px; margin: 4px 0 8px 0; }
.dp-mus-az a { font-size: 12px; font-weight: 800; color: #1b2540; text-decoration: none; padding: 2px 5px; border-radius: 5px; }
.dp-mus-az a:hover { background: rgba(27,37,64,.08); }
.dp-mus-az span { font-size: 12px; color: #cfcabf; padding: 2px 5px; }
/* "⋮" menüsü: satırın sağ ucuna sabit, ok simgesi yok */
div[class*="st-key-dp_mus_aksiyon_"] {
    position: absolute !important; top: 50%; right: 4px; transform: translateY(-50%);
    width: 40px !important; min-width: 40px !important; z-index: 2;
}
div[class*="st-key-dp_mus_aksiyon_"] button {
    width: 40px !important; min-width: 40px !important; padding: 0 !important;
    border: 0 !important; background: transparent !important; box-shadow: none !important;
}
div[class*="st-key-dp_mus_aksiyon_"] button:hover { background: #eef0f3 !important; }
div[class*="st-key-dp_mus_aksiyon_"] button [data-testid="stIconMaterial"],
div[class*="st-key-dp_mus_aksiyon_"] button svg { display: none !important; }
div[class*="st-key-dp_mus_ekle_pop"] button { white-space: nowrap !important; }
@media (max-width: 700px) {
    .dp-row {
        grid-template-columns: 36px minmax(0,1fr);
        padding: 10px 46px 16px 4px;
    }
    .dp-row .dp-av { grid-row: 1 / span 2; align-self: start; margin-top: 2px; }
    .dp-row .dp-tel { grid-column: 2; }
    .dp-row .dp-num { margin-right: auto; }
    .dp-row .dp-note { grid-column: 1 / -1; transform: none; margin-top: 4px; }
    details.dp-fs { grid-column: 1 / -1; }
    div[class*="st-key-dp_mus_aksiyon_"] { top: 22px; transform: none; right: 0; }
    div[class*="st-key-dp_mus_ekle_pop"] { width: auto !important; min-width: 0 !important; margin-left: auto !important; }
    div[class*="st-key-dp_mus_ekle_pop"] button { width: auto !important; min-width: 0 !important; }
}
</style>
""", unsafe_allow_html=True)

def _tarih_oku(v):
    try:
        return _dt.strptime(str(v)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _bugun():
    try:
        from zoneinfo import ZoneInfo
        return _dt.now(ZoneInfo("Europe/Istanbul")).date()
    except Exception:
        return _date.today()


def _alarm_oku(m):
    """alarm_zamani (UTC) -> Türkiye saatiyle naive datetime; yoksa None."""
    ham = m.get("alarm_zamani")
    if not ham:
        return None
    try:
        from zoneinfo import ZoneInfo
        d = _dt.fromisoformat(str(ham).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=_tz.utc)
        return d.astimezone(ZoneInfo("Europe/Istanbul")).replace(tzinfo=None)
    except Exception:
        return None


def _simdi_yerel():
    try:
        from zoneinfo import ZoneInfo
        return _dt.now(ZoneInfo("Europe/Istanbul")).replace(tzinfo=None)
    except Exception:
        return _dt.now()


def _kisalt(metin, n):
    metin = (metin or "").strip()
    return metin if len(metin) <= n else metin[:n].rstrip() + "…"


def _alarm_html(m):
    """Alarm etiketi (zamanı geldiyse kırmızı, değilse sarı)."""
    z = _alarm_oku(m)
    if not z:
        return ""
    geldi = z <= _simdi_yerel()
    metin = z.strftime("%d.%m %H:%M")
    nt = _kisalt(m.get("alarm_notu"), 40)
    etiket = (f"⏰ Zamanı geldi · {metin}" if geldi else f"⏰ Ara: {metin}") + (f" · {nt}" if nt else "")
    return f'<span class="dp-ln {"dp-al" if geldi else "dp-fu"}">{_esc(etiket)}</span>'


def _fsbo_blok_html(m):
    """FSBO kaydının ilan özeti (konum · tür · fiyat · oda/m² · ilan tarihi · link).
    İlan özeti dış kaynaktan (ilan verisi) geldiği için HER satır kaçışlanır."""
    ozet = (m.get("ilan_ozeti") or "").strip()
    if not ozet:
        return ""
    parcalar = []
    for blok in [b for b in ozet.split("\n\n") if b.strip()]:
        satirlar = []
        for ln in blok.split("\n"):
            ln = ln.strip()
            if ln.startswith("http://") or ln.startswith("https://"):
                satirlar.append(f'<a href="{_esc(ln)}" target="_blank" rel="noopener noreferrer">↗ İlana git</a>')
            elif ln:
                satirlar.append(_esc(ln))
        parcalar.append(f'<div class="dp-fsbo-ilan">{"<br>".join(satirlar)}</div>')
    return f'<div class="dp-mus-fsbo">{"".join(parcalar)}</div>' if parcalar else ""


def _gorusmeler(m):
    """Görüşme günlüğü, en yeni üstte. Girdi: {id, tarih, not, olusturma}."""
    g = [x for x in (m.get("gorusme_gecmisi") or []) if isinstance(x, dict) and x.get("tarih")]
    return sorted(g, key=lambda x: (x.get("tarih") or "", x.get("olusturma") or ""), reverse=True)


def _gorusme_satiri_html(m):
    """'Son görüşme 07.10 (3) · son notun başı' etiketi."""
    g = _gorusmeler(m)
    t = _tarih_oku(g[0]["tarih"]) if g else _tarih_oku(m.get("son_gorusme_tarihi"))
    if not t:
        return ""
    metin = f"Son görüşme {t.strftime('%d.%m.%y' if t.year != _bugun().year else '%d.%m')}"
    if len(g) > 1:
        metin += f" ({len(g)})"
    nt = _kisalt((g[0].get("not") or "") if g else "", 60)
    if nt:
        metin += " · " + nt
    return f'<span class="dp-ln">📞 {_esc(metin)}</span>'


def _satir_html(m, kompakt=False, yildiz=False):
    """Bir kişinin tek ızgara satırı (tek satırlık HTML — boş satır/girinti
    bırakılmaz, Markdown kod bloğuna çevirmesin)."""
    ad = (m.get("ad") or "").strip()
    tipler = _tip_listele(m.get("tip")) or ["Diğer"]
    sinif = _TIP_SINIF.get(tipler[0], "di")
    parcalar = (ad.split() or ["?"])
    bas = (parcalar[0][0] + (parcalar[1][0] if len(parcalar) > 1 else "")).upper()
    rozet = "".join(
        f"<span class='dp-tg dp-k-{_TIP_SINIF.get(t, 'di')}'>{_esc(t)}</span>" for t in tipler
    )
    uz = f"<span>· {_esc(m['uzmanlik'])}</span>" if m.get("uzmanlik") else ""
    yildiz_html = "<span class='dp-yildiz'>★</span> " if yildiz else ""
    bolge = f"<span class='dp-pin'>📍 {_esc(', '.join(m['bolgeler']))}</span>" if m.get("bolgeler") else ""
    nt = (m.get("notlar") or "").strip()
    # FSBO'da (SQL öncesi geri dönüş) 'notlar' ilan özetini taşıyabilir — ilan özeti
    # zaten ayrı gösterildiği için o durumda kişi notu olarak tekrar yazılmaz.
    if nt and (m.get("ilan_ozeti") or "").strip():
        nt = "" if nt in (m.get("ilan_ozeti") or "") else nt
    not_satirlari = _alarm_html(m) + _gorusme_satiri_html(m) + (
        f'<span class="dp-ln dp-tx">{_esc(nt)}</span>' if nt else "")
    kagit = f"<div class='dp-note'>{not_satirlari}</div>" if not_satirlari else ""
    fsbo = _fsbo_blok_html(m)
    detay = f"<details class='dp-fs'><summary>▾ İlan özeti</summary>{fsbo}</details>" if fsbo else ""
    return (
        f"<div class='dp-row dp-k-{sinif}{' dp-dense' if kompakt else ''}'>"
        f"<div class='dp-av'>{_esc(bas)}</div>"
        f"<div><div class='dp-nm'>{yildiz_html}{_esc(ad)}</div><div class='dp-sub'>{rozet}{uz}{bolge}</div></div>"
        f"{_telefon_blok_html(m.get('telefon'))}"
        f"{kagit}{detay}</div>"
    )


su_kullanici = su_anki_danisman()
tum_musteriler = musterileri_cek(su_kullanici)
_takip_var = takip_ozelligi_var()


def _takip_sirasi(m):
    """Takibimdekiler sırası: önce alarmı olanlar (en yakın/geciken üstte), sonra
    en uzun süredir aranmayanlar (hiç aranmamış en üstte), sonra ada göre."""
    z = _alarm_oku(m)
    if z:
        return (0, z.isoformat(), "")
    g = _gorusmeler(m)
    son = g[0]["tarih"] if g else str(m.get("son_gorusme_tarihi") or "")[:10]
    return (1, son or "0000-00-00", _tr_lower((m.get("ad") or "").strip()))


# DEĞİŞTİ (09.10.2026, Meltem: "Ajandam ve Rehberim — 2 sekme"): sayfa iki
# sekmeli. 1. sekme Ajandam (hafta/ay takvimi + olay ekle + zamanı gelen
# alarm şeridi; bildirime dokununca bu sekme açılır), 2. sekme Rehberim.
_geciken = geciken_alarmlar(tum_musteriler)
_ajanda_etiket = "📅 Ajandam" + (f" ({len(_geciken)}⏰)" if _geciken else "")
sekme_ajanda, sekme_rehber = st.tabs([_ajanda_etiket, "📇 Rehberim"])

with sekme_ajanda:
    ajanda_sekmesi(su_kullanici, tum_musteriler)

with sekme_rehber:
    st.caption("Kişisel kişi defterin — sadece sana görünür, ofis geneli paylaşılmaz.")

    # ── ÜST ARAÇ ÇUBUĞU: arama | bölge | + Yeni Kişi (tek satır) ────────────
    col_arama, col_bolge, col_ekle = st.columns([5, 2.2, 1.4])
    with col_arama:
        arama_metni = st.text_input(
            "Ara", key="dp_mus_arama",
            placeholder="🔎 İsim, meslek veya not içinde ara…",
            label_visibility="collapsed",
        )
    with col_bolge:
        bolge_filtre = st.multiselect(
            "Bölgeye göre filtrele", IZMIR_ILCELERI,
            key="dp_mus_bolge_filtre", placeholder="📍 Bölge",
            label_visibility="collapsed",
        )
    with col_ekle:
        with st.container(key="dp_mus_ekle_pop"):
            with st.popover("+ Yeni Kişi", use_container_width=True):
                with st.form("dp_mus_yeni_form", clear_on_submit=True):
                    f_ad = st.text_input("Ad Soyad", key="dp_mus_ad")
                    f_tip = st.multiselect(
                        "Tip (birden fazla seçilebilir)", TIP_SECENEKLERI,
                        default=["Alıcı"], key="dp_mus_tip",
                    )
                    f_telefon = st.text_input("Telefon (opsiyonel)", key="dp_mus_telefon")
                    # YENİ (13.08.2026, 2. tur): "kim ne iş yapıyor, nerede
                    # çalışıyor" sorusuna notları açmadan cevap verebilmek için
                    # — özellikle İş Ortağı'nda fark yaratıyor (örn.
                    # "Ender Böncü — Gayrimenkul Değerleme Uzmanı — Bornova").
                    f_uzmanlik = st.text_input(
                        "Uzmanlık / Meslek (opsiyonel)", key="dp_mus_uzmanlik",
                        placeholder="örn. Gayrimenkul Değerleme Uzmanı, Boyacı, Nakliyeci",
                    )
                    f_bolgeler = st.multiselect(
                        "Çalıştığı Bölge(ler) (opsiyonel)", IZMIR_ILCELERI, key="dp_mus_bolgeler",
                    )
                    f_not = st.text_area("Not (opsiyonel)", key="dp_mus_not", height=68)
                    f_takip = st.checkbox("⭐ Takibe al", key="dp_mus_takip_yeni") if _takip_var else False
                    if st.form_submit_button("Kaydet", type="primary", use_container_width=True):
                        if not f_ad.strip():
                            st.error("Ad Soyad zorunlu.")
                        elif not f_tip:
                            st.error("En az bir tip seçimi zorunlu.")
                        else:
                            musteri_ekle(su_kullanici, f_ad, f_telefon, f_tip, f_not, f_uzmanlik, f_bolgeler, takipte=f_takip)
                            st.success("✅ Eklendi.")
                            st.rerun()

    # ── TİP ÇİPLERİ (kişi sayılı; boş tipler gizli) ─────────────────────────
    _tip_sayi = {t: sum(1 for m in tum_musteriler if t in _tip_listele(m.get("tip")))
                 for t in TIP_SECENEKLERI}
    _cipler = ["Tümü"] + [t for t in TIP_SECENEKLERI if _tip_sayi[t]]
    tip_filtre = st.pills(
        "Tip", _cipler, selection_mode="single", default="Tümü",
        format_func=lambda t: f"{t} {len(tum_musteriler) if t == 'Tümü' else _tip_sayi[t]}",
        key="dp_mus_pill", label_visibility="collapsed",
    ) or "Tümü"

    if tip_filtre != "Tümü":
        gosterilecek = [m for m in tum_musteriler if tip_filtre in _tip_listele(m.get("tip"))]
    else:
        gosterilecek = tum_musteriler

    if bolge_filtre:
        gosterilecek = [
            m for m in gosterilecek
            if set(m.get("bolgeler") or []) & set(bolge_filtre)
        ]

    if arama_metni.strip():
        arama_lower = _tr_lower(arama_metni.strip())
        gosterilecek = [
            m for m in gosterilecek
            if arama_lower in _tr_lower(m.get("ad") or "")
            or arama_lower in _tr_lower(m.get("uzmanlik") or "")
            or arama_lower in _tr_lower(m.get("notlar") or "")
        ]

    kayitlar_tum = sorted(gosterilecek, key=lambda m: _tr_lower((m.get("ad") or "").strip()))

    c_say, c_yog = st.columns([3, 2])
    with c_say:
        st.caption(f"{len(kayitlar_tum)} kişi")
    with c_yog:
        _yog = st.segmented_control(
            "Satır yoğunluğu", ["Rahat", "Kompakt"], default="Rahat",
            key="dp_mus_yogunluk", label_visibility="collapsed",
        ) or "Rahat"
    _kompakt = _yog == "Kompakt"

    def _listeyi_ciz(kayitlar, onek, harfli=True, bos_mesaj=""):
        """Kişi listesini çizer. İki görünümde (Takibimdekiler / Tüm rehberim) aynı
        kişi çıkabildiği için tüm widget anahtarlarına 'onek' eklenir."""
        # ── A-Z HIZLI GEZİNME (aynı sayfa içi çapa) ──────────────────────────
        if harfli:
            mevcut_harfler = {
                (m.get("ad") or "").strip()[0].upper()
                for m in kayitlar if (m.get("ad") or "").strip()
            }
            az_parcalari = []
            for harf in TUM_HARFLER:
                if harf in mevcut_harfler:
                    az_parcalari.append(f'<a href="#dp-mus-harf-{onek}-{harf}">{harf}</a>')
                else:
                    az_parcalari.append(f'<span>{harf}</span>')
            st.markdown(f'<div class="dp-mus-az">{"".join(az_parcalari)}</div>', unsafe_allow_html=True)

        if not kayitlar:
            st.info(bos_mesaj)

        su_anki_harf = None
        for m in kayitlar:
            ad = m.get("ad", "").strip()
            ilk_harf = ad[0].upper() if ad else "#"
            if harfli and ilk_harf != su_anki_harf:
                su_anki_harf = ilk_harf
                st.markdown(
                    f"<div id='dp-mus-harf-{onek}-{ilk_harf}' class='dp-mus-harf-baslik'>{ilk_harf}</div>",
                    unsafe_allow_html=True,
                )

            # Satır: tek key'li container — "⋮" menüsü CSS ile satırın sağ ucuna
            # sabitlenir (mobilde de alt satıra düşmez).
            with st.container(key=f"dp_mus_row_{onek}{m['id']}"):
                st.markdown(_satir_html(m, _kompakt, yildiz=(harfli and bool(m.get('takipte')))), unsafe_allow_html=True)
                with st.container(key=f"dp_mus_aksiyon_{onek}{m['id']}"):
                    with st.popover("⋮", use_container_width=True):
                        if m.get("kaynak") == "otomatik":
                            st.caption("↻ Talep/Portföy eklerken otomatik senkronize edildi")
                        if _takip_var:
                            _tk = bool(m.get("takipte"))
                            if st.button("★ Takibi bırak" if _tk else "☆ Takibe al",
                                         key=f"dp_mus_takip_{onek}{m['id']}", use_container_width=True,
                                         type="secondary" if _tk else "primary"):
                                rehber_takip_ayarla(m["id"], not _tk)
                                st.rerun()
                        _gecmis_var = "gorusme_gecmisi" in m          # SQL çalıştırıldıysa
                        _alarm_alani = "alarm_zamani" in m
                        _gecmis = _gorusmeler(m)
                        _sekmeler = ["Bilgiler"]
                        if _gecmis_var:
                            _sekmeler.append(f"Görüşmeler ({len(_gecmis)})" if _gecmis else "Görüşmeler")
                        if _alarm_alani:
                            _sekmeler.append("⏰ Alarm" + (" •" if m.get("alarm_zamani") else ""))
                        _tablar = st.tabs(_sekmeler)
                        _tab_i = iter(_tablar)

                        # ── Bilgiler ─────────────────────────────────────────────
                        with next(_tab_i):
                            yeni_tipler = st.multiselect(
                                "Tip", TIP_SECENEKLERI,
                                default=[t for t in _tip_listele(m.get("tip")) if t in TIP_SECENEKLERI],
                                key=f"dp_mus_tip_duzenle_{onek}{m['id']}",
                            )
                            yeni_uzmanlik = st.text_input(
                                "Uzmanlık / Meslek", value=m.get("uzmanlik") or "",
                                key=f"dp_mus_uzmanlik_duzenle_{onek}{m['id']}",
                            )
                            yeni_bolgeler = st.multiselect(
                                "Çalıştığı Bölge(ler)", IZMIR_ILCELERI, default=m.get("bolgeler") or [],
                                key=f"dp_mus_bolgeler_duzenle_{onek}{m['id']}",
                            )
                            yeni_telefon = st.text_input(
                                "Telefon", value=m.get("telefon") or "",
                                key=f"dp_mus_telefon_duzenle_{onek}{m['id']}",
                            )
                            yeni_not = st.text_area(
                                "Not", value=m.get("notlar") or "",
                                key=f"dp_mus_not_duzenle_{onek}{m['id']}", height=68,
                                label_visibility="collapsed",
                                placeholder="Bu kişi için genel not (opsiyonel)...",
                            )
                            bp1, bp2 = st.columns(2)
                            with bp1:
                                if st.button("Kaydet", key=f"dp_mus_not_kaydet_{onek}{m['id']}", use_container_width=True):
                                    musteri_guncelle(m["id"], {
                                        "notlar": yeni_not.strip() or None,
                                        "tip": yeni_tipler or ["Diğer"],
                                        "uzmanlik": yeni_uzmanlik.strip() or None,
                                        "bolgeler": yeni_bolgeler,
                                        "telefon": yeni_telefon.strip() or None,
                                    })
                                    st.success("Kaydedildi.")
                                    st.rerun()
                            with bp2:
                                if st.button("Sil", key=f"dp_mus_sil_{onek}{m['id']}", use_container_width=True):
                                    musteri_sil(m["id"])
                                    st.rerun()

                        # ── Görüşmeler (geçmiş) ──────────────────────────────────
                        if _gecmis_var:
                            with next(_tab_i):
                                _gt = st.date_input(
                                    "Görüşme tarihi", value=_bugun(), max_value=_bugun(),
                                    format="DD.MM.YYYY", key=f"dp_mus_g_tarih_{onek}{m['id']}",
                                )
                                _gn = st.text_area(
                                    "Görüşme notu", height=80, key=f"dp_mus_g_not_{onek}{m['id']}",
                                    placeholder="Ne konuşuldu, bir sonraki adım ne? (boş bırakılabilir)",
                                )
                                if st.button("Görüşmeyi kaydet", key=f"dp_mus_g_kaydet_{onek}{m['id']}",
                                             type="primary", use_container_width=True):
                                    rehber_gorusme_ekle(m["id"], _gt, _gn)
                                    st.rerun()
                                if not _gecmis:
                                    st.caption("Henüz görüşme kaydı yok.")
                                else:
                                    st.markdown("**Geçmiş**")
                                    with st.container(height=min(60 + 70 * len(_gecmis), 320)):
                                        for _g in _gecmis:
                                            _c1, _c2 = st.columns([8, 1])
                                            with _c1:
                                                _t = _tarih_oku(_g["tarih"])
                                                st.markdown(
                                                    "<div style='white-space:pre-wrap;font-size:13.5px;line-height:1.5'>"
                                                    f"<b>{_esc(_t.strftime('%d.%m.%Y') if _t else str(_g['tarih']))}</b>"
                                                    + (f" — {_esc(_g.get('not') or '')}" if (_g.get("not") or "").strip() else "")
                                                    + "</div>",
                                                    unsafe_allow_html=True,
                                                )
                                            with _c2:
                                                if st.button("🗑", key=f"dp_mus_g_sil_{onek}{m['id']}_{_g.get('id')}",
                                                             help="Bu görüşme kaydını sil"):
                                                    rehber_gorusme_sil(m["id"], _g.get("id"))
                                                    st.rerun()

                        # ── Alarm ────────────────────────────────────────────────
                        if _alarm_alani:
                            with next(_tab_i):
                                _az = _alarm_oku(m)
                                _a1, _a2 = st.columns(2)
                                with _a1:
                                    _alarm_gun = st.date_input(
                                        "Alarm günü",
                                        value=(_az.date() if _az else (_bugun() + _td(days=1))),
                                        min_value=min(_bugun(), _az.date()) if _az else _bugun(),
                                        format="DD.MM.YYYY", key=f"dp_mus_alarm_gun_{onek}{m['id']}",
                                    )
                                with _a2:
                                    _alarm_saat = st.time_input(
                                        "Saat", value=(_az.time() if _az else _time(10, 0)),
                                        step=1800, key=f"dp_mus_alarm_saat_{onek}{m['id']}",
                                    )
                                _alarm_not = st.text_input(
                                    "Alarm notu", value=m.get("alarm_notu") or "",
                                    placeholder="örn. Cumartesi tekrar ara",
                                    key=f"dp_mus_alarm_not_{onek}{m['id']}",
                                )
                                if st.button("Alarmı kur", key=f"dp_mus_alarm_kur_{onek}{m['id']}",
                                             type="primary", use_container_width=True):
                                    _hedef = _dt.combine(_alarm_gun, _alarm_saat)
                                    if _hedef <= _simdi_yerel():
                                        st.error("Alarm zamanı geçmişte — ileri bir gün/saat seç.")
                                    else:
                                        rehber_alarm_kur(m["id"], _hedef, _alarm_not)
                                        st.rerun()
                                st.caption("Hızlı kur (saat 10:00):")
                                _h1, _h2, _h3 = st.columns(3)
                                for _kol, _etiket, _gun in ((_h1, "Yarın", 1), (_h2, "3 gün", 3), (_h3, "1 hafta", 7)):
                                    with _kol:
                                        if st.button(_etiket, key=f"dp_mus_alarm_h{_gun}_{onek}{m['id']}", use_container_width=True):
                                            _t = _dt.combine(_bugun() + _td(days=_gun), _time(10, 0))
                                            rehber_alarm_kur(m["id"], _t, _alarm_not)
                                            st.rerun()
                                if _az and st.button("Alarmı kaldır", key=f"dp_mus_alarm_kaldir_{onek}{m['id']}",
                                                     use_container_width=True):
                                    rehber_alarm_kaldir(m["id"])
                                    st.rerun()
                                st.caption("Bildirim, kurduğun saatten en geç ~30 dakika sonra telefonuna gelir.")


    _bos_tum = ("Bu filtrede kayıtlı kişi yok. Yukarıdan yeni kişi ekleyebilir, ya da bir "
                "talep/portföy eklerken müşteri bilgisi girerek otomatik ekleyebilirsin.")
    if _takip_var:
        _takipliler = sorted([m for m in kayitlar_tum if m.get("takipte")], key=_takip_sirasi)
        _toplam_takip = sum(1 for m in tum_musteriler if m.get("takipte"))
        sekme_takip, sekme_tum = st.tabs([
            f"⭐ Takibimdekiler ({_toplam_takip})", f"📇 Tüm rehberim ({len(tum_musteriler)})",
        ])
        with sekme_takip:
            _listeyi_ciz(_takipliler, "t", harfli=False, bos_mesaj=(
                "Takibe alınmış kişi yok (ya da filtreyle eşleşen yok). Kişinin ⋮ menüsünden "
                "☆ Takibe al'a dokun; alarm kurduğun veya FSBO'dan eklediğin kişiler buraya kendiliğinden girer."))
        with sekme_tum:
            _listeyi_ciz(kayitlar_tum, "r", harfli=True, bos_mesaj=_bos_tum)
    else:
        _listeyi_ciz(kayitlar_tum, "r", harfli=True, bos_mesaj=_bos_tum)
