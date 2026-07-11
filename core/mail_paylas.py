"""
core/mail_paylas.py
─────────────────────────────────────────────────────────────────────────
Talep ve Portföy sayfalarında ORTAK kullanılan, Startkey ağına mail ile
paylaşım bileşeni.

Üç gönderim modu sunar:
  1) 🌐 Herkese Gönder        -> everybody@startkey.com.tr (Startkey ağı geneli)
  2) 📍 Bölge/Aks Seç         -> bölge seçilince o bölgedeki OFİS ADLARI
                                  gösterilir (hepsi işaretli gelir, istemediğin
                                  ofisi çıkarabilirsin) → seçili ofislerin
                                  danışman mailleri hesaplanır
  3) 👤 Ofis + Danışman        -> önce Ofis(ler) seç, SONRA sadece o ofis(ler)
                                  içindeki danışmanlar listelenir

Mail gövdesi YAPILANDIRILMIŞ alanlardan üretilir (serbest metin yerine):
  - baslik            : ilan/talep başlığı (h2)
  - rozetler          : küçük etiketler (örn. ["Buca","Konut","Kiralık"])
  - bilgi_satirlari   : [(etiket, değer), ...] — tablo satırları
  - ilan_linki        : varsa fotoğraflar TIKLANINCA bunu tarayıcıda açar
  - gorsel_urls       : fotoğraf küçük resimleri (public URL)
  - intro_metin / kapanis_metni : GD'nin serbestçe düzenleyebildiği iki kısa metin

── ÖNEMLİ TEKNİK SINIR ───────────────────────────────────────────────────
Mail istemcileri JavaScript çalıştırmaz — mail içinde açılan bir galeri/modal
YAPILAMAZ. Yapılabilen: fotoğrafa tıklayınca TARAYICIDA ilgili linkin
(ilan_linki varsa o, yoksa fotoğrafın kendisi) açılması.

── KULLANIM ──────────────────────────────────────────────────────────────
    from core.mail_paylas import render_mail_paylas_widget

    gonderildi = render_mail_paylas_widget(
        key_prefix=f"pm_paylas_{kid}",
        gd_isim=user_name,
        konu_ozet=ozet[:60],
        baslik=ozet,
        rozetler=[ilce, mulk, islem],
        bilgi_satirlari=[
            ("Lokasyon", f"{il} / {ilce} / {bolge}"),
            ("İşlem Tipi", f"{islem} {mulk}"),
            ("Oda Sayısı", oda),
            ("Fiyat", fiyat),
            ("Özellikler", ozellik),
        ],
        ilan_linki=link,
        gorsel_urls=foto_urls,
        on_success=lambda: kaynak_guncelle(kid),
    )
    if gonderildi:
        st.rerun()

NOT: st.secrets["email"]["user"/"password"/"smtp"/"smtp_port"] — mevcut
secrets, değişmedi.
"""

import html as _html
import streamlit as st
import streamlit.components.v1 as components
from core.supabase_client import get_client

EVERYBODY_MAIL = "everybody@startkey.com.tr"
VARSAYILAN_UNVAN = "Startkey Zeta Gayrimenkul"
ZETA_LOGO_URL = "https://lfpnkuldlirnljsrkkyf.supabase.co/storage/v1/object/public/danismanlar/logo.png"


@st.cache_data(ttl=3600)
def _personel_foto_haritasi():
    """personel_foto_url tablosundaki tüm kayıtlar (ad_soyad -> foto_url/telefon/mail)."""
    try:
        supa = get_client()
        res = supa.table("personel_foto_url").select("ad_soyad,foto_url,telefon,mail").execute()
        return res.data or []
    except Exception:
        return []


def _danisman_bilgisi(ad_soyad):
    """Verilen ada göre (case-insensitive) danışmanın foto_url/telefon/mail bilgisini
    döner (bulunamazsa None). '· Kapalı Portföy' gibi sınıf etiketleri isme karışmış
    olsa bile (temizlenmemiş eski değerler için) " · " öncesi kısımla da ayrıca dener."""
    if not ad_soyad:
        return None
    hedef = str(ad_soyad).strip().lower()
    hedef_temiz = hedef.split(" · ")[0].strip()
    for row in _personel_foto_haritasi():
        aday = str(row.get("ad_soyad", "")).strip().lower()
        if aday == hedef or aday == hedef_temiz:
            return row
    return None


@st.cache_data(ttl=3600)
def _rehber_yukle():
    try:
        supa = get_client()
        ofis_res = supa.table("rehber_ofisler").select("ofis_adi,bolge_aksi").eq("aktif", True).execute()
        dan_res = supa.table("rehber_danismanlar").select("ofis_adi,isim,mail").eq("aktif", True).execute()
        return ofis_res.data or [], dan_res.data or []
    except Exception:
        return [], []


def _bolge_secenekleri():
    ofisler, _ = _rehber_yukle()
    return sorted({o.get("bolge_aksi") for o in ofisler if o.get("bolge_aksi")})


def _ofisler_bolgede(bolge):
    ofisler, _ = _rehber_yukle()
    return sorted({o["ofis_adi"] for o in ofisler if o.get("bolge_aksi") == bolge and o.get("ofis_adi")})


def _tum_ofis_listesi():
    ofisler, _ = _rehber_yukle()
    return sorted({o["ofis_adi"] for o in ofisler if o.get("ofis_adi")})


def _danismanlar_ofislerde(ofis_adlari):
    _, danismanlar = _rehber_yukle()
    if not ofis_adlari:
        return []
    return sorted({
        f'{d["isim"]} ({d.get("ofis_adi","")})'
        for d in danismanlar
        if d.get("ofis_adi") in ofis_adlari and d.get("isim") and d.get("mail")
    })


def _benzer_ofis_uyarisi(ofis_adlari):
    _, danismanlar = _rehber_yukle()
    tum_ofis_adlari_dan = sorted({d.get("ofis_adi", "") for d in danismanlar if d.get("ofis_adi")})
    benzerler = set()
    for secilen in ofis_adlari:
        sl = secilen.strip().lower()
        if not sl:
            continue
        for aday in tum_ofis_adlari_dan:
            al = aday.strip().lower()
            if aday in ofis_adlari:
                continue
            if sl in al or al in sl:
                benzerler.add(aday)
    return sorted(benzerler)


def _mailleri_ofislerden(ofis_adlari):
    _, danismanlar = _rehber_yukle()
    return sorted({d["mail"] for d in danismanlar if d.get("ofis_adi") in ofis_adlari and d.get("mail")})


def _mailleri_secim_etiketlerinden(secim_etiketleri):
    _, danismanlar = _rehber_yukle()
    secilen_ciftler = set()
    for etiket in secim_etiketleri:
        if "(" in etiket and etiket.endswith(")"):
            isim = etiket[:etiket.rindex("(")].strip()
            ofis = etiket[etiket.rindex("(") + 1:-1].strip()
            secilen_ciftler.add((isim, ofis))
    return sorted({
        d["mail"] for d in danismanlar
        if (d.get("isim", "").strip(), d.get("ofis_adi", "").strip()) in secilen_ciftler and d.get("mail")
    })


def _html_govde(gd_isim, baslik, ara_metin, rozetler, bilgi_satirlari, ilan_linki, gorsel_urls,
                 intro_metin=None, kapanis_metni=None, unvan=VARSAYILAN_UNVAN):
    esc = lambda s: _html.escape(str(s)) if s is not None else ""
    _dan_bilgi = _danisman_bilgisi(gd_isim) or {}
    gd_foto_url = _dan_bilgi.get("foto_url")
    gd_telefon = _dan_bilgi.get("telefon")
    gd_mail = _dan_bilgi.get("mail")

    intro_html = "".join(
        f'<p style="margin:0 0 4px 0;">{esc(satir)}</p>'
        for satir in str(intro_metin or "").split("\n") if satir.strip()
    )

    rozet_html = "".join(
        f'<span style="background:#eef3f8;color:#1f3a5f;padding:5px 10px;'
        f'border-radius:12px;font-size:13px;margin:0 6px 6px 0;display:inline-block;">{esc(r)}</span>'
        for r in (rozetler or []) if r and str(r).strip() not in ("", "—", "-")
    )

    satir_html = "".join(
        f'<tr><td style="padding:10px 14px;width:35%;color:#6b7280;border-bottom:1px solid #eef1f5;">{esc(etiket)}</td>'
        f'<td style="padding:10px 14px;border-bottom:1px solid #eef1f5;"><strong>{esc(deger)}</strong></td></tr>'
        for etiket, deger in (bilgi_satirlari or [])
        if deger is not None and str(deger).strip() not in ("", "—", "-")
    )
    tablo_html = ""
    if satir_html:
        baslik_satiri = (
            '<tr><th style="padding:10px 14px;text-align:left;color:#374151;'
            'background:#eef2f7;font-size:13px;">Bilgi</th>'
            '<th style="padding:10px 14px;text-align:left;color:#374151;'
            'background:#eef2f7;font-size:13px;">Detay</th></tr>'
        )
        tablo_html = (
            f'<table style="width:100%;border-collapse:collapse;background:#f7f9fc;'
            f'border:1px solid #e1e7ef;border-radius:10px;overflow:hidden;">{baslik_satiri}{satir_html}</table>'
        )

    foto_html = ""
    if gorsel_urls:
        temiz_urls = [str(u).strip() for u in gorsel_urls[:6] if str(u).strip().startswith("http")]
        if temiz_urls:
            buyuk_hedef = ilan_linki if ilan_linki else None
            kutular = "".join(
                f'<a href="{esc(buyuk_hedef or u)}" target="_blank" style="text-decoration:none;">'
                f'<img src="{esc(u)}" style="width:160px;height:110px;object-fit:cover;'
                f'border-radius:8px;border:1px solid #d9e1ea;margin:0 8px 8px 0;"/></a>'
                for u in temiz_urls
            )
            foto_html = (
                f'<p style="margin-top:18px;margin-bottom:2px;">Portföy fotoğrafları aşağıda yer almaktadır.</p>'
                f'<p style="margin:0 0 12px 0;font-size:12px;color:#94a3b8;">Görselleri daha net incelemek için '
                f'fotoğrafların üzerine tıklayabilir, büyük hallerini tarayıcıda görüntüleyebilirsiniz.</p>'
                f'<div style="margin:0 0 22px 0;">{kutular}</div>'
            )

    return f"""
<div style="font-family:Arial,Helvetica,sans-serif;color:#2f3b4a;line-height:1.55;max-width:720px;margin:auto;">
  {intro_html}
  {f'<h2 style="color:#1f3a5f;margin:16px 0 6px;">{esc(baslik)}</h2>' if baslik else ""}
  {f'<p style="color:#475569;margin:0 0 10px 0;">{esc(ara_metin)}</p>' if ara_metin else ""}
  <div style="margin:6px 0 18px 0;">{rozet_html}</div>
  {tablo_html}
  {foto_html}
  {f'<p style="margin-top:14px;">{esc(kapanis_metni)}</p>' if kapanis_metni else ""}
  <p style="margin-top:20px;margin-bottom:0;">İyi çalışmalar,</p>
  <table style="margin-top:10px;border-top:1px solid #e5e9f0;padding-top:14px;width:100%;">
    <tr>
      <td style="vertical-align:middle;padding-right:12px;width:56px;">
        {f'<img src="{esc(gd_foto_url)}" style="width:52px;height:52px;border-radius:50%;object-fit:cover;object-position:center top;border:2px solid #eef3f8;display:block;">' if gd_foto_url else ''}
      </td>
      <td style="vertical-align:middle;">
        <p style="margin:0;font-weight:700;color:#1f3a5f;font-size:14px;">{esc(gd_isim)}</p>
        <p style="margin:0;font-size:12px;color:#6b7280;">{esc(unvan)}</p>
        {f'<p style="margin:2px 0 0 0;font-size:12px;color:#6b7280;">{esc(gd_telefon)}{" · " if gd_telefon and gd_mail else ""}{esc(gd_mail)}</p>' if (gd_telefon or gd_mail) else ""}
      </td>
      <td style="vertical-align:middle;text-align:right;">
        <img src="{esc(ZETA_LOGO_URL)}" style="height:38px;">
      </td>
    </tr>
  </table>
</div>
"""


def _text_govde(gd_isim, baslik, ara_metin, bilgi_satirlari, ilan_linki, intro_metin, kapanis_metni, unvan):
    satirlar = [s for s in str(intro_metin or "").split("\n") if s.strip()]
    if baslik:
        satirlar += ["", baslik]
    if ara_metin:
        satirlar += ["", ara_metin]
    for etiket, deger in (bilgi_satirlari or []):
        if deger is not None and str(deger).strip() not in ("", "—", "-"):
            satirlar.append(f"{etiket}: {deger}")
    if ilan_linki:
        satirlar += ["", f"İlan: {ilan_linki}"]
    if kapanis_metni:
        satirlar += ["", kapanis_metni]
    satirlar += ["", "İyi çalışmalar,", gd_isim, unvan]
    return "\n".join(satirlar)


def _mail_gonder(konu, govde_text, govde_html, alicilar):
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    user_mail = st.secrets["email"]["user"]
    password = st.secrets["email"]["password"]
    smtp_host = st.secrets["email"].get("smtp", "smtp.yandex.com")
    smtp_port = int(st.secrets["email"].get("smtp_port", 465))

    msg = MIMEMultipart("alternative")
    msg["Subject"] = konu
    msg["From"] = user_mail
    msg["To"] = ", ".join(alicilar)
    msg.attach(MIMEText(govde_text, "plain", "utf-8"))
    if govde_html:
        msg.attach(MIMEText(govde_html, "html", "utf-8"))

    with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
        server.login(user_mail, password)
        server.sendmail(user_mail, alicilar, msg.as_string())


def render_mail_paylas_widget(key_prefix, gd_isim, konu_ozet, on_success=None,
                               buton_etiketi="📧 Startkey ile Paylaş",
                               baslik=None, ara_metin=None, rozetler=None, bilgi_satirlari=None,
                               ilan_linki=None, gorsel_urls=None,
                               intro_metin=None,
                               kapanis_metni="Uygun bir müşteri eşleşmesi, randevu planlaması veya detaylı bilgi için benimle iletişime geçebilirsiniz.",
                               unvan=VARSAYILAN_UNVAN, icerik_kelime="portföyümü"):
    acik_key = f"{key_prefix}_acik"

    if not st.session_state.get(acik_key, False):
        if st.button(buton_etiketi, key=f"{key_prefix}_ac_btn", use_container_width=True):
            st.session_state[acik_key] = True
            st.rerun()
        return False

    _intro_verilmedi = intro_metin is None

    st.markdown("**📧 Startkey Ağına Gönder**")
    _gd_isim_temiz = str(gd_isim).split(" · ")[0].strip() if gd_isim and gd_isim != "—" else str(gd_isim or "")
    _gonderen_secenekleri = sorted({
        row.get("ad_soyad", "") for row in _personel_foto_haritasi() if row.get("ad_soyad")
    })
    if _gd_isim_temiz and _gd_isim_temiz not in _gonderen_secenekleri:
        _gonderen_secenekleri = sorted(_gonderen_secenekleri + [_gd_isim_temiz])
    _gonderen_idx = (
        _gonderen_secenekleri.index(_gd_isim_temiz) if _gd_isim_temiz in _gonderen_secenekleri else 0
    )
    gd_isim = st.selectbox(
        "Gönderen",
        _gonderen_secenekleri,
        index=_gonderen_idx,
        key=f"{key_prefix}_gonderen",
        help="Varsayılan kaydın sahibi — bu ilanı/talebi başka bir danışman adına paylaşmak istersen listeden seçebilirsin.",
    )

    if _intro_verilmedi:
        intro_metin = (
            f"Merhaba,\nBen {gd_isim}.\n{unvan} olarak, müşterileriniz için uygun olabileceğini "
            f"düşündüğüm güncel bir {icerik_kelime} paylaşmak isterim."
        )

    mod = st.radio(
        "Gönderim Kapsamı",
        ["🌐 Herkese Gönder", "📍 Bölge/Aks Seç", "👤 Ofis + Danışman"],
        key=f"{key_prefix}_mod", horizontal=True,
    )

    alicilar = []
    if mod == "🌐 Herkese Gönder":
        alicilar = [EVERYBODY_MAIL]
        st.caption(f"Gönderilecek adres: `{EVERYBODY_MAIL}`")

    elif mod == "📍 Bölge/Aks Seç":
        bolgeler = _bolge_secenekleri()
        if bolgeler:
            secilen_bolge = st.selectbox("Bölge/Aks", bolgeler, key=f"{key_prefix}_bolge")
            ofisler_bu_bolgede = _ofisler_bolgede(secilen_bolge)
            st.caption(f"Bu bölgede {len(ofisler_bu_bolgede)} ofis var — istemediğini listeden çıkarabilirsin.")
            secilen_ofisler = st.multiselect(
                "Ofisler", ofisler_bu_bolgede, default=ofisler_bu_bolgede,
                key=f"{key_prefix}_bolge_ofis",
            )
            alicilar = _mailleri_ofislerden(secilen_ofisler)
            st.caption(f"{len(alicilar)} danışmana gönderilecek." if alicilar
                       else "⚠️ Seçili ofis(ler)de kayıtlı danışman maili bulunamadı.")
            if secilen_ofisler and not alicilar:
                benzer = _benzer_ofis_uyarisi(secilen_ofisler)
                if benzer:
                    st.warning(
                        "Rehberde bu ofis adına eşleşen danışman kaydı yok — "
                        f"danışman tablosunda geçen benzer ofis adları: **{', '.join(benzer[:6])}**"
                    )
        else:
            st.caption("⚠️ Rehberde bölge/aks bilgisi bulunamadı.")

    else:
        tum_ofisler = _tum_ofis_listesi()
        secilen_ofisler2 = st.multiselect("1) Ofis(ler) Seç", tum_ofisler, key=f"{key_prefix}_ofis2")
        if secilen_ofisler2:
            dan_opts = _danismanlar_ofislerde(secilen_ofisler2)
            secilenler = st.multiselect("2) Danışman(lar)", dan_opts, key=f"{key_prefix}_dan2")
            alicilar = _mailleri_secim_etiketlerinden(secilenler)
            st.caption(f"{len(alicilar)} adrese gönderilecek." if alicilar else "Danışman seçin.")
            if len(dan_opts) <= 1:
                benzer = _benzer_ofis_uyarisi(secilen_ofisler2)
                if benzer:
                    st.warning(
                        "⚠️ Seçtiğin ofis adıyla danışman rehberinde eşleşen kayıt yok/çok az. "
                        "Rehberde bu ofisin danışmanları FARKLI bir ofis adıyla kayıtlı olabilir — "
                        f"benzer isimler: **{', '.join(benzer[:6])}**. Doğru olanı yukarıdan seçmeyi dene."
                    )
                else:
                    st.warning("⚠️ Bu ofisle eşleşen danışman kaydı (aktif + mail alanı dolu) bulunamadı.")
        else:
            st.caption("Önce en az bir ofis seçin — o ofisteki danışmanlar listelenecek.")

    konu_default = f"{gd_isim} — {konu_ozet}"
    konu = st.text_input("Mail Konusu", value=konu_default, key=f"{key_prefix}_konu")

    gc1, gc2 = st.columns(2)
    with gc1:
        intro_kutusu = st.text_area("Giriş Metni", value=intro_metin, key=f"{key_prefix}_intro", height=90)
    with gc2:
        kapanis_kutusu = st.text_area("Kapanış Metni", value=kapanis_metni, key=f"{key_prefix}_kapanis", height=90)

    _onizle_ac_key = f"{key_prefix}_onizle_acik"
    if st.button("👁 Mail Önizleme (alıcının göreceği görünüm)", key=f"{key_prefix}_onizle_btn",
                  use_container_width=True):
        st.session_state[_onizle_ac_key] = not st.session_state.get(_onizle_ac_key, True)

    if st.session_state.get(_onizle_ac_key, True):
        _onizle_html = _html_govde(
            gd_isim=gd_isim, baslik=baslik, ara_metin=ara_metin, rozetler=rozetler,
            bilgi_satirlari=bilgi_satirlari, ilan_linki=ilan_linki, gorsel_urls=gorsel_urls,
            intro_metin=intro_kutusu, kapanis_metni=kapanis_kutusu, unvan=unvan,
        )
        components.html(
            f'<div style="font-family:Arial,Helvetica,sans-serif;padding:4px 2px;'
            f'background:#ffffff;box-sizing:border-box;">{_onizle_html}</div>',
            height=560, scrolling=True,
        )
        st.caption(
            "ℹ️ Bazı mail istemcileri (özellikle Outlook masaüstü) görselleri/stilleri "
            "burada gördüğünden biraz sade gösterebilir — ama tablo, link ve fotoğraflar hep ulaşır."
        )

    c1, c2 = st.columns(2)
    gonderildi = False
    with c1:
        if st.button("✅ Gönder", key=f"{key_prefix}_gonder_btn", type="primary",
                      use_container_width=True, disabled=not alicilar):
            try:
                govde_html_tam = _html_govde(
                    gd_isim=gd_isim, baslik=baslik, ara_metin=ara_metin, rozetler=rozetler,
                    bilgi_satirlari=bilgi_satirlari, ilan_linki=ilan_linki, gorsel_urls=gorsel_urls,
                    intro_metin=intro_kutusu, kapanis_metni=kapanis_kutusu, unvan=unvan,
                )
                govde_text_tam = _text_govde(
                    gd_isim=gd_isim, baslik=baslik, ara_metin=ara_metin, bilgi_satirlari=bilgi_satirlari,
                    ilan_linki=ilan_linki, intro_metin=intro_kutusu,
                    kapanis_metni=kapanis_kutusu, unvan=unvan,
                )
                _mail_gonder(konu, govde_text_tam, govde_html_tam, alicilar)
                st.success(f"✅ {len(alicilar)} adrese gönderildi!")
                st.session_state[acik_key] = False
                if on_success:
                    on_success()
                gonderildi = True
            except Exception as e:
                st.error(f"Mail gönderilemedi: {e}")
    with c2:
        if st.button("İptal", key=f"{key_prefix}_iptal_btn", use_container_width=True):
            st.session_state[acik_key] = False
            st.rerun()

    return gonderildi
