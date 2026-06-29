import imaplib
import email
from email.header import decode_header
import re
import streamlit as st


def decode_mime_text(text):
    if not text:
        return ""
    parts = decode_header(text)
    result = ""
    for part, encoding in parts:
        if isinstance(part, bytes):
            try:
                result += part.decode(encoding if encoding else "utf-8", errors="replace")
            except:
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
            except:
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
    except:
        return ""


def konu_filtrele(konu):
    """RE: ve alakasız mailleri filtrele"""
    if not konu:
        return False
    konu_lower = konu.lower().strip()
    
    # RE: ile başlayanları atla
    if konu_lower.startswith("re:"):
        return False
    
    # Alakasız mail başlıkları
    alakasiz = [
        "facebook", "instagram", "linkedin", "twitter",
        "newsletter", "bülten", "kampanya", "fırsat",
        "doğrulama", "verification", "password", "şifre",
        "yandex", "google", "apple", "microsoft",
        "unsubscribe", "abonelik", "bildirim",
        "davet", "invitation"
    ]
    
    for kelime in alakasiz:
        if kelime in konu_lower:
            return False
    
    return True


def klasorden_mailleri_cek(mail, klasor, mevcut_message_idler):
    status, _ = mail.select(f'"{klasor}"')
    if status != "OK":
        return []

    from datetime import datetime, timedelta
    bes_gun_once = (datetime.now() - timedelta(days=5)).strftime("%d-%b-%Y")

    status_uid, data_uid = mail.uid("search", None, f'(SINCE "{bes_gun_once}")')
    uid_listesi = data_uid[0].split() if status_uid == "OK" and data_uid[0] else []

    tum_uidler = sorted(set(uid_listesi), key=lambda x: int(x))

    veriler = []
    for uid_bytes in tum_uidler:
        try:
            uid_str = uid_bytes.decode() if isinstance(uid_bytes, bytes) else str(uid_bytes)
            status, msg_data = mail.uid("fetch", uid_str, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            raw_email = msg_data[0][1]
            if not raw_email:
                continue
            msg = email.message_from_bytes(raw_email)

            message_id = decode_mime_text(msg.get("Message-ID")).strip()

            if message_id and message_id in mevcut_message_idler:
                continue

            konu = decode_mime_text(msg.get("Subject"))

            # Konu filtresi
            if not konu_filtrele(konu):
                continue

            gonderen = decode_mime_text(msg.get("From"))
            tarih = decode_mime_text(msg.get("Date"))
            icerik = get_mail_body(msg)

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
                "kaynak_klasor": klasor
            })

            if message_id:
                mevcut_message_idler.add(message_id)

        except Exception as e:
            continue

    return veriler


def mailleri_cek(durum_callback=None):
    user = st.secrets["email"]["user"]
    password = st.secrets["email"]["password"]
    imap_url = st.secrets["email"]["imap"]

    klasorler = ["INBOX", "1_Alici_Depo"]

    if durum_callback:
        durum_callback("Mail sunucusuna bağlanılıyor...")

    mail = imaplib.IMAP4_SSL(imap_url)
    mail.login(user, password)

    mevcut_message_idler = set()
    tum_veriler = []

    for klasor in klasorler:
        if durum_callback:
            durum_callback(f"'{klasor}' klasörü okunuyor...")

        veriler = klasorden_mailleri_cek(mail, klasor, mevcut_message_idler)
        tum_veriler.extend(veriler)

        if durum_callback:
            durum_callback(f"'{klasor}': {len(veriler)} mail bulundu")

    mail.logout()

    if durum_callback:
        durum_callback(f"Toplam {len(tum_veriler)} yeni mail bulundu")

    return tum_veriler