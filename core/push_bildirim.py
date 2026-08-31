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

Parçalar:
- push_abonelikleri tablosu (Supabase, elle oluşturulmalı — SQL için
  Meltem'e ayrıca verildi): bir kullanıcının HER cihazı/tarayıcısı için
  ayrı bir satır (endpoint benzersiz).
- render_bildirim_izni_butonu(): tarayıcıdan bildirim izni isteyip
  aboneliği doğrudan Supabase'e (anon key ile, favoriToggle'daki AYNI
  desen — core/pano_export.py) yazan küçük bir HTML/JS bileşeni.
  Service worker'ın kendisi (static/sw.js) app.py'de HER sayfada zaten
  sessizce kaydediliyor — burada sadece İZİN + ABONELİK var.
- bildirim_gonder(kullanici, baslik, govde, url=None): kullanıcının
  KAYITLI TÜM cihazlarına pywebpush ile push gönderir. Süresi
  dolmuş/iptal edilmiş abonelikler (410/404) otomatik silinir.

VAPID: Bir kez üretilip SABİTLENMİŞ bir anahtar çifti kullanılıyor —
public key aşağıda (gizli değil, tarayıcıya gönderilmesi gerekiyor zaten),
private key SIR — Streamlit secrets'ta st.secrets["vapid"]["private_key"]
olarak (yerelde .streamlit/secrets.toml, canlıda Streamlit Cloud'un Secrets
panelinde) saklanmalı. ASLA repoya committed edilmemeli.
"""

import json

import streamlit as st
import streamlit.components.v1 as components

from core.supabase_client import get_client
from core.danisman_ortak import supabase_anon_secrets

supabase = get_client()

# Tarayıcıya gönderilen taraf — GİZLİ DEĞİL, hardcode edilebilir.
VAPID_PUBLIC_KEY = "BHoooveN3H3ONOIqV2TYfGGKgRKf-Br-IFyAjb4A6XvX_sCn-r72F5YbkZ9Jzg6GhASXnFiKox5EENqhzKzFjT8"


def abonelikleri_cek(kullanici):
    resp = supabase.table("push_abonelikleri").select("*").eq("kullanici", kullanici).execute()
    return resp.data or []


def render_bildirim_izni_butonu(kullanici, key_prefix="pb"):
    """'🔔 Bildirimleri Aç' butonu + durum yazısı. Tıklanınca:
    1) Notification.requestPermission() (kullanıcı gerçekten tıkladığı
       için tarayıcılar bunu güvenilir şekilde kabul ediyor),
    2) service worker kaydını bekler (app.py'de zaten sessizce
       kaydedilmiş olmalı — burada sadece hazır olmasını bekliyoruz),
    3) pushManager.subscribe(),
    4) aboneliği DOĞRUDAN Supabase'e yazar (anon/publishable key ile,
       core/pano_export.py'deki favoriToggle JS'iyle AYNI desen —
       Streamlit'e hiç uğramadan, çünkü bu HTML bir iframe içinde
       render ediliyor).

    Tüm DOM/Notification/serviceWorker erişimi window.parent üzerinden
    yapılıyor — app.py'deki PWA manifest injection'ıyla AYNI, KANITLANMIŞ
    aynı-origin iframe tekniği."""
    supabase_url, supabase_anon = supabase_anon_secrets()
    if not supabase_url or not supabase_anon:
        st.caption("⚠️ Bildirim altyapısı için Supabase anon anahtarı bulunamadı.")
        return

    kullanici_js = json.dumps(kullanici or "")

    components.html(
        f"""
        <div style="font-family:sans-serif;">
          <button id="{key_prefix}_btn" style="
              padding:8px 16px; border-radius:8px; border:1px solid #d8cdb4;
              background:#ffffff; color:#1c2b47; font-weight:600; font-size:13px;
              cursor:pointer;">🔔 Bildirimleri Aç</button>
          <div id="{key_prefix}_durum" style="margin-top:6px; font-size:12px; color:#8a8271;"></div>
        </div>
        <script>
        (function () {{
            var win = window.parent;
            var durumEl = document.getElementById('{key_prefix}_durum');
            var btn = document.getElementById('{key_prefix}_btn');

            function durumYaz(metin) {{
                if (durumEl) durumEl.textContent = metin;
            }}

            function urlB64ToUint8Array(base64String) {{
                var padding = '='.repeat((4 - base64String.length % 4) % 4);
                var base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
                var rawData = win.atob(base64);
                var arr = new Uint8Array(rawData.length);
                for (var i = 0; i < rawData.length; ++i) arr[i] = rawData.charCodeAt(i);
                return arr;
            }}

            if (!win.navigator.serviceWorker || !win.PushManager) {{
                durumYaz('Bu tarayıcı telefon bildirimlerini desteklemiyor.');
                btn.disabled = true;
                return;
            }}

            // Zaten abone mi? (sayfa her yenilendiğinde butonu tekrar
            // basmaya zorlamamak için) — sessizce kontrol et.
            win.navigator.serviceWorker.ready.then(function (reg) {{
                return reg.pushManager.getSubscription();
            }}).then(function (mevcut) {{
                if (mevcut) durumYaz('Bildirimler açık ✅');
            }}).catch(function () {{}});

            btn.addEventListener('click', function () {{
                durumYaz('İzin isteniyor...');
                win.Notification.requestPermission().then(function (izin) {{
                    if (izin !== 'granted') {{
                        durumYaz('İzin verilmedi — tarayıcı/telefon ayarlarından bildirim iznini açabilirsin.');
                        return;
                    }}
                    return win.navigator.serviceWorker.ready.then(function (reg) {{
                        return reg.pushManager.subscribe({{
                            userVisibleOnly: true,
                            applicationServerKey: urlB64ToUint8Array('{VAPID_PUBLIC_KEY}')
                        }});
                    }}).then(function (sub) {{
                        var ham = sub.toJSON();
                        return fetch('{supabase_url}/rest/v1/push_abonelikleri?on_conflict=endpoint', {{
                            method: 'POST',
                            headers: {{
                                'apikey': '{supabase_anon}',
                                'Authorization': 'Bearer {supabase_anon}',
                                'Content-Type': 'application/json',
                                'Prefer': 'resolution=merge-duplicates'
                            }},
                            body: JSON.stringify({{
                                kullanici: {kullanici_js},
                                endpoint: ham.endpoint,
                                p256dh: ham.keys.p256dh,
                                auth: ham.keys.auth
                            }})
                        }});
                    }}).then(function (r) {{
                        if (r && r.ok) {{
                            durumYaz('Bildirimler açık ✅');
                        }} else {{
                            durumYaz('Abonelik kaydedilemedi (sunucu hatası).');
                        }}
                    }});
                }}).catch(function (e) {{
                    durumYaz('Bir hata oluştu: ' + (e && e.message ? e.message : e));
                }});
            }});
        }})();
        </script>
        """,
        height=70,
    )


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

    payload = json.dumps({"title": baslik, "body": govde, "url": url or "/Danisman_Secim"})

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
