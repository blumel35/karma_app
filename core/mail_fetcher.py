"""
IMAP/Yandex mail çekme katmanı.

Faz 2 revizeleri:
- Sabit 5 gün yerine dışarıdan verilen since_date / lookback_days parametresi
  (gerçek "son başarılı çekim" mantığı core/mail_job.py içinde kurulur;
  bu modül sadece IMAP tarafını bilir, Supabase'e dokunmaz).
- "RE:" ile başlayan mailler artık tamamen atılmıyor; is_reply=True
  olarak işaretlenip AI'a gönderiliyor.
- "fırsat", "kampanya", "davet" gibi gerçek emlak içeriğinde de geçebilecek
  kelimeler alakasız listesinden çıkarıldı.
- Sessiz `except: continue` yerine her hata bir hata_listesi içine
  kaydediliyor, çağıran taraf bunu görebiliyor.
- message_id boşsa fallback_hash üretiliyor (gonderen+tarih+konu+içerik
  özetinden) — dedupe artık sadece message_id'ye bağımlı değil.
"""

import hashlib
import imaplib
import email
from email.header import decode_header
import re
from datetime import datetime, timedelta

import streamlit as st


DEFAULT_LOOKBACK_DAYS = 5

# Sadece kesin alakasız olanlar. "fırsat", "kampanya", "davet" gibi
# emlak mailinde de geçebilecek kelimeler bilerek burada YOK.
ALAKASIZ_KELIMELER = [
    "facebook", "instagram", "linkedin", "twitter",
    "newsletter", "bülten",
    "doğrulama", "verification", "password", "şifre",
    "yandex", "google", "apple", "microsoft",
    "unsubscribe", "abonelik", "bildirim",
]


def decode_mime_text(text):
    if not text:
        return ""
    parts = decode_header(text)
    result = ""
    for part, encoding in parts:
        if isinstance(part, bytes):
            try:
                result += part.decode(encoding if encoding else "utf-8", errors="replace")
            except Exception:
                result += part.decode("utf-8", errors="replace")
        else:
            result += part
    return result.replace("\u200b", "").replace("\ufeff", "").strip()


def clean_text(text):
    if not text:
        return ""
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def strip_html_tags(html_text):
    html_text = re.sub(r"<style.*?>.*?</style>", " ", html_text, flags=re.DOTALL | re.IGNORECASE)
    html_text = re.sub(r"<script.*?>.*?</script>", " ", html_text, flags=re.DOTALL | re.IGNORECASE)
    html_text = re.sub(r"<[^>]+>", " ", html_text)
    return clean_text(html_text)


def get_mail_body(msg):
    if msg.is_multipart():
        plain_text = ""
        html_text = ""
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition") or "").lower()
            if "attachment" in content_disposition:
                continue
            try:
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                charset = part.get_content_charset() or "utf-8"
                decoded = payload.decode(charset, errors="replace")
                if content_type == "text/plain" and not plain_text:
                    plain_text = clean_text(decoded)
                elif content_type == "text/html" and not html_text:
                    html_text = strip_html_tags(decoded)
            except Exception:
                continue
        return plain_text or html_text or ""
    try:
        payload = msg.get_payload(decode=True)
        if not payload:
            return ""
        charset = msg.get_content_charset() or "utf-8"
        text = payload.decode(charset, errors="replace")
        if "<html" in text.lower():
            return strip_html_tags(text)
        return clean_text(text)
    except Exception:
        return ""


def konu_analiz(konu):
    """
    Konuyu inceler.
    Döner: (dahil_et: bool, is_reply: bool)

    - Kesin alakasız kelimeler geçiyorsa dahil_et=False.
    - "RE:" ile başlıyorsa artık ATILMIYOR; is_reply=True olarak
      işaretlenip dahil ediliyor (AI, yanıt içinde yeni bilgi olup
      olmadığına karar verecek).
    """
    if not konu:
        return False, False

    konu_lower = konu.lower().strip()
    is_reply = konu_lower.startswith("re:")

    for kelime in ALAKASIZ_KELIMELER:
        if kelime in konu_lower:
            return False, is_reply

    return True, is_reply


def fallback_hash_uret(gonderen, tarih, konu, icerik):
    """
    message_id boş geldiğinde dedupe için kullanılacak deterministik hash.
    Gönderen + tarih + konu + içeriğin ilk 1000 karakteri üzerinden üretilir.
    """
    temel = f"{gonderen}|{tarih}|{konu}|{(icerik or '')[:1000]}"
    return hashlib.sha256(temel.encode("utf-8", errors="ignore")).hexdigest()


def klasorden_mailleri_cek(mail, klasor, mevcut_message_idler, mevcut_fallback_hashler,
                            since_date_str, hata_listesi):
    """
    Tek bir klasörden mailleri çeker.

    hata_listesi: dışarıdan verilen liste; okunamayan/işlenemeyen her mail
    için {"klasor":..., "uid":..., "hata": "..."} dict'i eklenir. Böylece
    sessiz `except: continue` yerine çağıran taraf neyin kaçtığını görebilir.
    """
    veriler = []

    status, _ = mail.select(f'"{klasor}"')
    if status != "OK":
        hata_listesi.append({"klasor": klasor, "uid": None, "hata": "Klasör seçilemedi"})
        return veriler

    status_uid, data_uid = mail.uid("search", None, f'(SINCE "{since_date_str}")')
    uid_listesi = data_uid[0].split() if status_uid == "OK" and data_uid[0] else []
    tum_uidler = sorted(set(uid_listesi), key=lambda x: int(x))

    for uid_bytes in tum_uidler:
        uid_str = uid_bytes.decode() if isinstance(uid_bytes, bytes) else str(uid_bytes)
        try:
            status, msg_data = mail.uid("fetch", uid_str, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                hata_listesi.append({"klasor": klasor, "uid": uid_str, "hata": "Fetch başarısız"})
                continue
            raw_email = msg_data[0][1]
            if not raw_email:
                hata_listesi.append({"klasor": klasor, "uid": uid_str, "hata": "Boş içerik"})
                continue
            msg = email.message_from_bytes(raw_email)

            message_id = decode_mime_text(msg.get("Message-ID")).strip()

            if message_id and message_id in mevcut_message_idler:
                continue

            konu = decode_mime_text(msg.get("Subject"))
            dahil_et, is_reply = konu_analiz(konu)
            if not dahil_et:
                continue

            gonderen = decode_mime_text(msg.get("From"))
            tarih = decode_mime_text(msg.get("Date"))
            icerik = get_mail_body(msg)

            fb_hash = None
            if not message_id:
                fb_hash = fallback_hash_uret(gonderen, tarih, konu, icerik)
                if fb_hash in mevcut_fallback_hashler:
                    continue

            veriler.append({
                "kayit_tarihi": tarih,
                "talep_eden_danisan": gonderen,
                "bolge_mahalle": "",
                "oda_sayisi_m2": "",
                "max_butce": "",
                "ozel_kriterler": "",
                "iletisim_not": "",
                "mail_konusu": konu,
                "mail_icerigi": icerik,
                "message_id": message_id,
                "fallback_hash": fb_hash,
                "is_reply": is_reply,
                "kaynak_klasor": klasor,
                "parse_status": "raw",
            })

            if message_id:
                mevcut_message_idler.add(message_id)
            if fb_hash:
                mevcut_fallback_hashler.add(fb_hash)

        except Exception as e:
            hata_listesi.append({"klasor": klasor, "uid": uid_str, "hata": f"{type(e).__name__}: {e}"})
            continue

    return veriler


def mailleri_cek(durum_callback=None, since_date=None, lookback_days=None,
                  mevcut_message_idler=None, mevcut_fallback_hashler=None):
    """
    Ana giriş noktası.

    since_date: "DD-Mon-YYYY" formatında IMAP tarih string'i verilirse
                doğrudan kullanılır (core/mail_job.py, son başarılı çekim
                zamanına göre bunu hesaplayıp gönderir).
    lookback_days: since_date verilmezse kaç gün geriye gidileceği.
                   Verilmezse DEFAULT_LOOKBACK_DAYS (5) kullanılır.
    mevcut_message_idler / mevcut_fallback_hashler: dışarıdan (Supabase'ten
                   okunmuş) mevcut kimlik setleri verilirse, klasörler arası
                   ve DB'deki mevcut kayıtlarla çakışma da bu fonksiyon
                   içinde engellenir. Verilmezse sadece bu çalıştırma
                   içindeki tekrarlar engellenir (eski davranış).

    Döner:
    {
        "veriler": [...],
        "hata_log": [...],
        "ozet": {klasor: {"bulunan": N, "hata": M}, ...}
    }
    """
    user = st.secrets["email"]["user"]
    password = st.secrets["email"]["password"]
    imap_url = st.secrets["email"]["imap"]

    if since_date is None:
        gun = lookback_days if lookback_days is not None else DEFAULT_LOOKBACK_DAYS
        since_date = (datetime.now() - timedelta(days=gun)).strftime("%d-%b-%Y")

    klasorler = ["INBOX", "1_Alici_Depo"]

    if durum_callback:
        durum_callback("Mail sunucusuna bağlanılıyor...")

    mail = imaplib.IMAP4_SSL(imap_url)
    mail.login(user, password)

    mevcut_message_idler = set(mevcut_message_idler) if mevcut_message_idler else set()
    mevcut_fallback_hashler = set(mevcut_fallback_hashler) if mevcut_fallback_hashler else set()

    tum_veriler = []
    hata_log = []
    ozet = {}

    for klasor in klasorler:
        if durum_callback:
            durum_callback(f"'{klasor}' klasörü okunuyor (since {since_date})...")

        onceki_hata_sayisi = len(hata_log)
        veriler = klasorden_mailleri_cek(
            mail, klasor, mevcut_message_idler, mevcut_fallback_hashler,
            since_date, hata_log
        )
        tum_veriler.extend(veriler)
        ozet[klasor] = {
            "bulunan": len(veriler),
            "hata": len(hata_log) - onceki_hata_sayisi,
        }

        if durum_callback:
            durum_callback(f"'{klasor}': {len(veriler)} yeni mail, {ozet[klasor]['hata']} hata")

    mail.logout()

    if durum_callback:
        durum_callback(f"Toplam {len(tum_veriler)} yeni mail bulundu, {len(hata_log)} hata")

    return {"veriler": tum_veriler, "hata_log": hata_log, "ozet": ozet}
