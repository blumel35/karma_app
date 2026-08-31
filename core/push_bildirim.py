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
    """Sağ altta yüzen bir '🔔' düğmesi. Tıklanınca:
    1) Notification.requestPermission(),
    2) service worker kaydını bekler (app.py'de zaten sessizce
       kaydedilmiş olmalı — burada sadece hazır olmasını bekliyoruz),
    3) pushManager.subscribe(),
    4) aboneliği DOĞRUDAN Supabase'e yazar (anon/publishable key ile,
       core/pano_export.py'deki favoriToggle JS'iyle AYNI desen).

    DÜZELTME (31.08.2026 — Meltem'in "izin verilmedi" hatası): düğme
    ÖNCEDEN bu bileşenin kendi <iframe>'i İÇİNDE render ediliyordu.
    Android Chrome'da o iç-çerçeveden gelen tıklama, üst sayfanın
    Notification.requestPermission() çağrısı için istediği "gerçek
    kullanıcı tıklaması" (transient activation) olarak sayılmıyor —
    tarayıcı hiçbir izin penceresi GÖSTERMEDEN sessizce 'denied'
    döndürüyor. Çözüm: düğmeyi artık üst sayfanın (window.parent)
    GERÇEK DOM'una — body'nin sonuna, sabit/yüzen küçük bir daire
    olarak — ekliyoruz. Böylece tıklama gerçekten üst sayfada
    gerçekleşiyor. Streamlit'in kendi React ağacına dokunmuyoruz
    (body'ye ayrı bir kardeş eleman olarak ekleniyor), bu yüzden
    sayfa yeniden render olduğunda React'in "beklenmeyen DOM
    elemanı" hatası vermesi riski de yok. Sayfa her rerun olduğunda
    bileşen tekrar çalışır ama id kontrolüyle ikinci kez eklemiyor."""
    supabase_url, supabase_anon = supabase_anon_secrets()
    if not supabase_url or not supabase_anon:
        st.caption("⚠️ Bildirim altyapısı için Supabase anon anahtarı bulunamadı.")
        return

    kullanici_js = json.dumps(kullanici or "")
    fab_id = f"{key_prefix}_fab"

    components.html(
        f"""
        <script>
        (function () {{
            var win = window.parent;
            var pdoc = win.document;

            // Zaten eklenmişse (Streamlit bu bileşeni yeniden render
            // ettiği için) ikinci kez ekleme.
            if (pdoc.getElementById('{fab_id}')) {{ return; }}

            if (!win.navigator.serviceWorker || !win.PushManager || !win.Notification) {{
                return; // desteklenmiyor — sessizce hiçbir şey gösterme
            }}

            function urlB64ToUint8Array(base64String) {{
                var padding = '='.repeat((4 - base64String.length % 4) % 4);
                var base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
                var rawData = win.atob(base64);
                var arr = new Uint8Array(rawData.length);
                for (var i = 0; i < rawData.length; ++i) arr[i] = rawData.charCodeAt(i);
                return arr;
            }}

            var wrap = pdoc.createElement('div');
            wrap.id = '{fab_id}';
            wrap.style.cssText = 'position:fixed; right:16px; bottom:16px; z-index:999999; font-family:sans-serif; display:flex; flex-direction:column; align-items:flex-end;';

            var durumEl = pdoc.createElement('div');
            durumEl.style.cssText = 'max-width:230px; margin-bottom:6px; padding:7px 10px; border-radius:8px; background:#1c2b47; color:#ffffff; font-size:11px; line-height:1.4; display:none; box-shadow:0 2px 8px rgba(0,0,0,.25);';

            var btn = pdoc.createElement('button');
            btn.type = 'button';
            btn.textContent = '🔔';
            btn.title = 'Telefon bildirimlerini aç';
            btn.style.cssText = 'width:48px; height:48px; border-radius:50%; border:none; background:#c0392b; color:#fff; font-size:20px; cursor:pointer; box-shadow:0 2px 10px rgba(0,0,0,.25);';

            wrap.appendChild(durumEl);
            wrap.appendChild(btn);
            pdoc.body.appendChild(wrap);

            function durumYaz(metin) {{
                durumEl.textContent = metin;
                durumEl.style.display = metin ? 'block' : 'none';
            }}

            if (win.Notification.permission === 'denied') {{
                btn.style.background = '#8a8271';
                durumYaz('Bildirimler bu tarayıcıda engellenmiş. Chrome ⋮ > Ayarlar > Site ayarları > Bildirimler\\'den bu siteyi bulup izin vermen gerekiyor (site listede yoksa: yukarıdaki genel anahtarın açık olduğundan emin ol).');
            }}

            // Zaten abone mi? — buysa düğmeyi tamamen gizle.
            win.navigator.serviceWorker.ready.then(function (reg) {{
                return reg.pushManager.getSubscription();
            }}).then(function (mevcut) {{
                if (mevcut && win.Notification.permission === 'granted') {{
                    wrap.style.display = 'none';
                }}
            }}).catch(function () {{}});

            function zamanAsimliCalistir(sozVerme, ms, etiket) {{
                return new Promise(function (resolve, reject) {{
                    var zamanlayici = setTimeout(function () {{
                        reject(new Error(etiket + ' 15 saniyede yanıt vermedi (ağ/firewall engeli olabilir).'));
                    }}, ms);
                    sozVerme.then(function (v) {{ clearTimeout(zamanlayici); resolve(v); }},
                                   function (e) {{ clearTimeout(zamanlayici); reject(e); }});
                }});
            }}

            btn.addEventListener('click', function () {{
                durumYaz('İzin isteniyor... (telefonunda bir izin penceresi çıkmalı — çıkmazsa engellenmiş demektir)');
                win.Notification.requestPermission().then(function (izin) {{
                    if (izin !== 'granted') {{
                        durumYaz('İzin verilmedi (durum: ' + izin + '). Chrome ⋮ > Ayarlar > Site ayarları > Bildirimler\\'den bu siteyi bul, izin ver.');
                        return;
                    }}
                    durumYaz('İzin verildi ✅ — cihaz kaydı hazırlanıyor (service worker)...');
                    return zamanAsimliCalistir(win.navigator.serviceWorker.ready, 15000, 'Service worker')
                        .then(function (reg) {{
                            durumYaz('Service worker hazır — push servisine kaydediliyor...');
                            return zamanAsimliCalistir(
                                reg.pushManager.subscribe({{
                                    userVisibleOnly: true,
                                    applicationServerKey: urlB64ToUint8Array('{VAPID_PUBLIC_KEY}')
                                }}),
                                15000,
                                'Push servisi kaydı'
                            );
                        }})
                        .then(function (sub) {{
                            durumYaz('Push kaydı alındı — sunucuya yazılıyor...');
                            var ham = sub.toJSON();
                            return zamanAsimliCalistir(
                                fetch('{supabase_url}/rest/v1/push_abonelikleri?on_conflict=endpoint', {{
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
                                }}),
                                15000,
                                'Sunucuya kayıt'
                            );
                        }})
                        .then(function (r) {{
                            if (r && r.ok) {{
                                durumYaz('Bildirimler açık ✅');
                                setTimeout(function () {{ wrap.style.display = 'none'; }}, 2500);
                            }} else {{
                                r.text().then(function (t) {{
                                    durumYaz('Sunucu reddetti (HTTP ' + (r ? r.status : '?') + '): ' + t);
                                }}).catch(function () {{
                                    durumYaz('Abonelik kaydedilemedi (sunucu hatası, HTTP ' + (r ? r.status : '?') + ').');
                                }});
                            }}
                        }});
                }}).catch(function (e) {{
                    durumYaz('Hata: ' + (e && e.message ? e.message : e));
                }});
            }});
        }})();
        </script>
        """,
        height=0,
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
