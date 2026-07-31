"""
pages/Pano_Goruntule.py

Paylaşılan ilan panolarını (Talep/Portföy) görüntülemek için kullanılan
sayfa. Supabase Storage'daki public bucket'lar, güvenlik amaçlı olarak
HTML dosyalarını "text/plain" (ham metin) olarak sunuyor — tarayıcı
Storage linkine doğrudan gidince sayfa render olmuyor, kaynak kod olarak
görünüyor.

Bu sayfa o sorunu şöyle çözüyor: dosyayı Storage'dan BACKEND'de (Python
requests ile) çekip, içeriğini Streamlit'in kendi component'i üzerinden
gömülü olarak render ediyor. Tarayıcı hiç Storage URL'ine gitmiyor,
Supabase'in içerik türü kısıtlaması hiç devreye girmiyor.

Link formatı: https://<uygulama-adresi>/Pano_Goruntule?p=<klasor>/<dosya>.html

NOT: Bu sayfa bilerek oturum_kontrol() ÇAĞIRMIYOR — link'i bilen herkes
(ofis personeli dahil, giriş yapmadan) açabilsin diye. Link'in kendisi
tahmin edilmesi güç (rastgele token'lı) olduğu için bu kabul edilebilir
bir paylaşım modeli — İlan Vitrini'ndeki share_token mantığıyla aynı.
"""

import streamlit as st
import requests
import streamlit.components.v1 as components

st.set_page_config(page_title="İlan Panosu", layout="wide")

PANO_BUCKET = "pano-paylasim"

params = st.query_params
dosya_yolu = params.get("p", "")

if not dosya_yolu:
    st.error("Geçersiz veya eksik pano linki. Lütfen size gönderilen linki kontrol edin.")
    st.stop()

# Basit bir güvenlik kontrolü: yol sadece bucket içindeki beklenen
# formatta olmalı (klasor/dosya.html) — path traversal denemelerini
# (örn. "../../secrets.toml") engellemek için.
if ".." in dosya_yolu or not dosya_yolu.endswith(".html"):
    st.error("Geçersiz pano linki.")
    st.stop()

try:
    supabase_url = st.secrets["supabase"]["url"].rstrip("/")
except Exception:
    st.error("Uygulama yapılandırması eksik — yönetici ile iletişime geçin.")
    st.stop()

kaynak_url = f"{supabase_url}/storage/v1/object/public/{PANO_BUCKET}/{dosya_yolu}"

try:
    with st.spinner("Pano yükleniyor..."):
        yanit = requests.get(kaynak_url, timeout=15)
        yanit.raise_for_status()
    html_icerik = yanit.text
except requests.exceptions.HTTPError:
    st.error("Bu pano bulunamadı — link geçersiz olabilir veya süresi dolmuş olabilir.")
    st.stop()
except Exception as e:
    st.error(f"Pano yüklenirken bir hata oluştu: {e}")
    st.stop()

components.html(html_icerik, height=2400, scrolling=True)
