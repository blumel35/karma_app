# core/push_bildirim.py
# -*- coding: utf-8 -*-
"""
Telefon bildirimleri (web push) altyapısı — Startkey Zeta Danışman Panosu
(2026-08-31, Meltem: "söyle bir uyarı gelsin örn. bugün 2 fsbo takip araman
var... nolur mümkün olsun").

FAZ 1 (bu dosya): TEMEL ALTYAPI — bir kullanıcının telefonuna GERÇEKTEN
bir bildirim düşürebilme yeteneğinin kendisi. Henüz hiçbir OTOMATİK
tetikleyici (FSBO takip alarmı, "Sinan yeni portföy girdi", eşleşen talep
maili) YOK — onlar FAZ 2/3/4, bu altyapı üzerine ayrı adımlarda inşa
edilecek (Meltem'in "sırayla başlayalım" tercihiyle tutarlı).

REVİZYON (Faz 1 mimari değişikliği, bağımsız incelemenin sonucu):
Streamlit Community Cloud'un statik dosya sunumu, /app/static/ altındaki
.js dosyalarını "text/plain" ile sunuyor (resmi Streamlit davranışı,
güvenlik amaçlı). Service Worker'ın GEÇERLİ JS MIME tipiyle, redirect'siz
sunulması tarayıcı tarafından ZORUNLU olduğu için, service worker artık
Karma App'in kendi origin'inde DEĞİL, ayrı bir mini-PWA'da barındırılıyor:
https://blumel35.github.io/zeta-bildirim/ . Ayrıntılar:
faz1_teknik_karar_ve_mimari.md.

Bu dosyada NE DEĞİŞTİ (önceki sürüme göre):
- render_bildirim_izni_butonu() SADELEŞTİ — tarayıcı tarafı izin/kayıt/
  abonelik mantığının tamamı mini-PWA'nın kendi index.html'ine taşındı.
  Artık burada yalnızca mini-PWA'ya yönlendiren imzalı bir link üretip
  st.link_button ile gösteriyor (eski <iframe>+floating-FAB JS bileşeni
  kaldırıldı).
- bildirim_aktivasyon_linki_uret() EKLENDİ — imzalı, süreli (10 dk) bir
  aktivasyon linki üretir; düğme artık bu linke yönlendiriyor.
- bildirim_gonder()'daki varsayılan url MUTLAK adrese çevrildi (bildirim
  artık mini-PWA'nın FARKLI origin'inden gösteriliyor, göreli yol orada
  anlamsız olurdu).
- abonelikleri_cek(), _vapid_private_key(), VAPID_PUBLIC_KEY DEĞİŞMEDİ.

Parçalar:
- push_abonelikleri tablosu (Supabase): bir kullanıcının HER cihazı/
  tarayıcısı için ayrı bir satır (endpoint benzersiz). Bu tabloya YAZMA
  artık doğrudan browser'dan değil, Supabase'deki
  aktivasyon_token_dogrula_ve_kaydet() RPC fonksiyonu üzerinden oluyor
  (bkz. aktivasyon_token_rpc_ADAY.sql, gerçek projede zaten uygulandı) —
  token'ın imzasını sunucu tarafında (Postgres) doğrulayıp kullanici
  adını TOKEN'DAN alıyor, istemcinin gönderdiği değere güvenmiyor.
- bildirim_aktivasyon_linki_uret(kullanici): Karma App'te "Telefon
  Bildirimlerini Aç" düğmesi tıklanınca çağrılır; ~10 dakika geçerli,
  HMAC-imzalı bir token üretip mini-PWA linkini döner.
- bildirim_gonder(kullanici, baslik, govde, url=None): kullanıcının
  KAYITLI TÜM cihazlarına pywebpush ile push gönderir. Süresi
  dolmuş/iptal edilmiş abonelikler (410/404) otomatik silinir.

VAPID: Bir kez üretilip SABİTLENMİŞ bir anahtar çifti kullanılıyor —
public key aşağıda (gizli değil), private key SIR — Streamlit secrets'ta
st.secrets["vapid"]["private_key"] olarak (yerelde .streamlit/secrets.toml,
canlıda Streamlit Cloud'un Secrets panelinde) saklanmalı. ASLA repoya
committed edilmemeli.

AKTİVASYON İMZA ANAHTARI: VAPID private key'den AYRI, yeni bir secrets
girdisi gerekiyor: st.secrets["vapid"]["aktivasyon_gizli_anahtar"] —
Supabase'deki RPC fonksiyonundaki v_gizli_anahtar (Vault'taki
"bildirim_aktivasyon_gizli_anahtar") ile AYNI değer olmalı.
"""

import base64
import hashlib
import hmac
import json
import time
import urllib.parse

import streamlit as st

from core.supabase_client import get_client

supabase = get_client()

# Tarayıcıya gönderilen taraf — GİZLİ DEĞİL, hardcode edilebilir.
VAPID_PUBLIC_KEY = "BHoooveN3H3ONOIqV2TYfGGKgRKf-Br-IFyAjb4A6XvX_sCn-r72F5YbkZ9Jzg6GhASXnFiKox5EENqhzKzFjT8"

# Bildirim mini-PWA'sının adresi — GitHub Pages'te, kendi origin'inde
# barındırılıyor (bkz. bildirim_pwa/ klasörü, faz1_teknik_karar_ve_mimari.md).
# Alt yol var (repo adı) — sonundaki "/" bilerek yok, link üretimi zaten
# "{BILDIRIM_PWA_URL}/#t=..." şeklinde ekliyor.
BILDIRIM_PWA_URL = "https://blumel35.github.io/zeta-bildirim"

# Ana Karma App'in gerçek adresi — bildirim tıklamalarının yönlendiği yer.
KARMA_APP_URL = "https://startkey-zeta.streamlit.app"


def abonelikleri_cek(kullanici):
    """kullanici'nin KAYITLI TÜM abonelik satırlarını döner.

    DEĞİŞTİ (02.09.2026, Meltem: "bildirim hâlâ gitmiyor" teşhisi):
    Eskiden .eq("kullanici", kullanici) ile TAM (büyük/küçük harf ve
    boşluk DUYARLI) eşleşme aranıyordu. Aktivasyon anında token'a
    gömülen isim (bildirim_aktivasyon_linki_uret çağrıldığı andaki
    su_anki_danisman()) ile gönderim anında tekrar çağrılan
    su_anki_danisman() arasında TEK bir boşluk veya harf büyüklüğü
    farkı bile (örn. profil tablosundaki "ad" alanı iki farkı zaman
    farklı normalize edildiyse) satırı SESSİZCE "0 abonelik" gibi
    gösteriyordu — ne kullanıcıya ne de log'a hiçbir hata düşmüyordu.
    Artık kullanıcı adı normalize edilip (strip + casefold) TÜM
    abonelik satırları üzerinde Python tarafında karşılaştırılıyor —
    böylece büyük/küçük harf ve baştaki/sondaki boşluk farkları artık
    bildirim göndermeyi ENGELLEMİYOR. (Kayıt anında RPC hâlâ token
    içindeki ham ismi aynen yazıyor — burada SADECE okuma/eşleştirme
    tarafı gevşetildi, veri değişmedi.)"""
    hedef = (kullanici or "").strip().casefold()
    if not hedef:
        return []
    resp = supabase.table("push_abonelikleri").select("*").execute()
    tumu = resp.data or []
    return [ab for ab in tumu if (ab.get("kullanici") or "").strip().casefold() == hedef]


def _aktivasyon_gizli_anahtar():
    try:
        return st.secrets["vapid"]["aktivasyon_gizli_anahtar"]
    except Exception:
        import os
        return os.environ.get("BILDIRIM_AKTIVASYON_GIZLI_ANAHTAR")


def bildirim_aktivasyon_linki_uret(kullanici, gecerlilik_saniye=600):
    """Karma App'teki düğme bunu çağırır. Kullanıcı adını ve son geçerlilik
    zamanını HMAC-SHA256 ile imzalayıp mini-PWA'nın aktivasyon linkini
    döner. Mini-PWA bu token'ı DOĞRUDAN doğrulamaz (statik JS bir sırrı
    güvenle saklayamaz) — token'ı olduğu gibi Supabase'deki
    aktivasyon_token_dogrula_ve_kaydet() RPC'sine iletir; asıl imza
    kontrolü ORADA, Postgres tarafında (Vault'taki gizli anahtarla)
    yapılır.

    Token URL FRAGMENT'ında (#t=...) taşınıyor — fragment tarayıcı
    tarafından HTTP isteğinde sunucuya HİÇ gönderilmez, bu yüzden
    barındırma erişim loglarına düşme riski yok. Mini-PWA'nın index.html'i
    token'ı location.hash üzerinden okuyor.

    Payload JSON'a, JSON da base64url'e kodlanıyor — base64url alfabesi
    hiç "." İÇERMEZ, HMAC hex imzası da içermez — token'da "." her zaman
    TAM OLARAK BİR kez, bizim eklediğimiz ayıraç olarak geçer. kullanici
    alanı nokta, boşluk, Türkçe karakter, hatta e-posta olsa da güvenli.

    Döner: (link, hata) — hata None ise link kullanılabilir."""
    gizli_anahtar = _aktivasyon_gizli_anahtar()
    if not gizli_anahtar:
        return None, "Aktivasyon gizli anahtarı bulunamadı (st.secrets['vapid']['aktivasyon_gizli_anahtar'])."

    son_gecerlilik = int(time.time()) + gecerlilik_saniye
    payload_json = json.dumps({"k": kullanici, "e": son_gecerlilik}, separators=(",", ":"), ensure_ascii=True)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("ascii").rstrip("=")
    imza = hmac.new(gizli_anahtar.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
    token = f"{payload_b64}.{imza}"

    link = f"{BILDIRIM_PWA_URL}/#t={urllib.parse.quote(token)}"
    return link, None


def render_bildirim_izni_butonu(kullanici, key_prefix="pb"):
    """Mini-PWA'nın aktivasyon linkine yönlendiren sade bir buton.
    Tarayıcıdan izin isteme/abone olma mantığının tamamı artık mini-PWA'nın
    kendi düz sayfasında (Streamlit'in components.html iframe'i içinde
    DEĞİL) çalışıyor — "transient activation" (iframe içinden gelen
    tıklamanın tarayıcı tarafından gerçek kullanıcı eylemi sayılmaması)
    sorunu yapısal olarak bir daha oluşmuyor."""
    link, hata = bildirim_aktivasyon_linki_uret(kullanici)
    if hata:
        st.caption(f"⚠️ {hata}")
        return

    # streamlit==1.45.0'da st.link_button()'ın key parametresi YOK (imza:
    # label, url, *, help, type, icon, disabled, use_container_width) —
    # key_prefix bu yüzden widget'a geçirilmiyor, sadece dışarıdan olası
    # çoklu-çağrı senaryosunda iz sürülebilsin diye tutuluyor.
    st.link_button("📱 Telefon Bildirimlerini Aç", link, use_container_width=True)
    st.caption("Yeni bir sekme açılır, orada izin verip tarayıcına dönebilirsin.")


def _vapid_private_key():
    try:
        return st.secrets["vapid"]["private_key"]
    except Exception:
        import os
        return os.environ.get("VAPID_PRIVATE_KEY")


def bildirim_gonder(kullanici, baslik, govde, url=None):
    """kullanici'nin KAYITLI TÜM cihazlarına push bildirimi gönderir.
    Süresi dolmuş/iptal edilmiş abonelikler (push servisi 404/410
    döndürürse) otomatik silinir — bir dahaki gönderimde tekrar
    denenmesin diye.

    DEĞİŞTİ: varsayılan url artık MUTLAK Karma App adresi — bildirim artık
    FARKLI bir origin'deki (blumel35.github.io/zeta-bildirim) service
    worker tarafından gösteriliyor, göreli yol orada anlamsız olurdu.

    Döner: {"gonderildi": int, "silinen": int, "hata": int}"""
    from pywebpush import webpush, WebPushException

    private_key = _vapid_private_key()
    if not private_key:
        raise RuntimeError(
            "VAPID_PRIVATE_KEY bulunamadı — st.secrets['vapid']['private_key'] "
            "(Streamlit) veya VAPID_PRIVATE_KEY ortam değişkeni (GitHub Actions) "
            "ayarlanmalı."
        )

    abonelikler = abonelikleri_cek(kullanici)
    sonuc = {"gonderildi": 0, "silinen": 0, "hata": 0}
    if not abonelikler:
        return sonuc

    hedef_url = url or f"{KARMA_APP_URL}/Danisman_Secim"
    payload = json.dumps({"title": baslik, "body": govde, "url": hedef_url})

    for ab in abonelikler:
        subscription_info = {
            "endpoint": ab["endpoint"],
            "keys": {"p256dh": ab["p256dh"], "auth": ab["auth"]},
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=private_key,
                vapid_claims={"sub": "mailto:destek@startkeyzeta.com"},
            )
            sonuc["gonderildi"] += 1
        except WebPushException as e:
            durum_kodu = getattr(e.response, "status_code", None)
            if durum_kodu in (404, 410):
                supabase.table("push_abonelikleri").delete().eq("id", ab["id"]).execute()
                sonuc["silinen"] += 1
            else:
                sonuc["hata"] += 1
        except Exception:
            sonuc["hata"] += 1

    return sonuc
