"""
Claude ile mail sınıflandırma ve alan çıkarma katmanı.

Faz 3 revizeleri:
- izmir_mahalleler.json'dan mahalle -> ilçe ters-indeksi kuruldu.
  AI'ın ilçe tahminine ek olarak, kod seviyesinde deterministik bir
  doğrulama/tamamlama katmanı eklendi (normalize_ilce_sonucu).
- Eski ilce_dogrula() fonksiyonu (tanımlı ama hiç çağrılmıyordu)
  kaldırıldı; tüm doğrulama mantığı tek bir fonksiyonda birleşti.
- İçerik kırpma stratejisi değişti: "ilk 3000 karakter" yerine
  "ilk 2000 + son 1500" — fiyat/telefon/ilan linki gibi bilgiler
  genelde mailin sonunda oluyor.

Faz 4 revizeleri:
- Anthropic client artık her çağrıda değil, bir kere oluşturulup
  yeniden kullanılıyor (st.cache_resource).
- mailleri_isle() artık kayıtları tek tek sırayla değil, kontrollü
  paralel (ThreadPoolExecutor, sınırlı eşzamanlılık + retry + timeout)
  şekilde işliyor.
"""

import json
import os
import re
import time
import json as _json
from concurrent.futures import ThreadPoolExecutor, as_completed

import anthropic
import streamlit as st


SISTEM_MESAJI_TEMPLATE = """
Sen bir gayrimenkul şirketinin (Startkey) mail analiz asistanısın.
Bu mailler Startkey gayrimenkul danışmanları arasındaki iletişimdir.
Danışmanlar birbirlerine iki amaçla mail atar:
1. Ellerindeki alıcı müşteri için uygun portföy ararlar (Alıcı Talebi)
2. Ellerindeki portföyü paylaşarak alıcısı olan danışmanı ararlar (Portföy Paylaşımı)

Bazı mailler "RE:" ile başlayan yanıtlardır — bu bir önceki yazışmaya
cevaptır ama yine de yeni bir alıcı talebi veya portföy paylaşımı
bilgisi içerebilir. Yanıt olması onu otomatik olarak "diger" yapmaz;
içeriğe göre normal şekilde sınıflandır.

Mailin kategorisini belirle:
- "alici_talebi": Danışmanın elinde alıcı müşteri var, bu müşteri için uygun gayrimenkul arıyor
- "portfoy_paylasimi": Danışmanın elinde satılık veya kiralık gayrimenkul var, alıcısı olan danışmanı arıyor
- "diger": Sistem bildirimi, reklam, sosyal medya, alakasız içerik

Türkiye'nin Ege bölgesi illeri: İzmir, Aydın, Manisa, Balıkesir, Muğla
Bu illerin dışındaki yerler için il="Diğer", ilce="Diğer Bölge" yaz.

=== KESİN İLÇE LİSTESİ ===
Aşağıdaki liste, sistemdeki TÜM geçerli ilçe adlarıdır.
"ilce" ve "ilceler" alanlarına YALNIZCA bu listeden ilçe adı yaz.
Listede olmayan bir yer adı (mahalle, semt, sokak vb.) ilçe değildir — o zaman bolge_mahalle alanına yaz.

{ilce_listesi}

=== ÖRNEK HATALAR VE DOĞRULARI ===
❌ YANLIŞ: ilce: "Bahçelievler" → Bahçelievler bir mahalledir, Buca ilçesindedir
✅ DOĞRU: ilce: "Buca", bolge_mahalle: "Bahçelievler"

❌ YANLIŞ: ilce: "Mavişehir" → Mavişehir bir semttir, Karşıyaka ilçesindedir  
✅ DOĞRU: ilce: "Karşıyaka", bolge_mahalle: "Mavişehir"

❌ YANLIŞ: ilce: "Alsancak" → Alsancak bir semttir, Konak ilçesindedir
✅ DOĞRU: ilce: "Konak", bolge_mahalle: "Alsancak"

❌ YANLIŞ: ilce: "Çiğli" → Listede varsa doğru, yoksa bolge_mahalle'ye yaz
===========================

Sonra kategoriye göre bilgileri çıkar ve SADECE JSON formatında ver:

Eğer "alici_talebi" ise:
{{
  "kategori": "alici_talebi",
  "ozet": "kısa talep özeti, örn: Bornova 2+1 kiralık arayışı",
  "islem_tipi": "Satılık veya Kiralık veya Belirsiz",
  "mulk_tipi": "Konut veya İşyeri veya Arsa veya Belirsiz",
  "il": "İzmir veya Aydın veya Manisa veya Balıkesir veya Muğla veya Diğer",
  "ilce": "birincil ilçe adı (SADECE yukarıdaki listeden)",
  "ilceler": ["ilçe1", "ilçe2"],
  "bolge_mahalle": "aranan mahalle, semt veya sokak detayı",
  "oda_sayisi_m2": "istenen oda sayısı veya metrekare",
  "max_butce": "maksimum bütçe",
  "ozel_kriterler": "özel istekler, önemli kriterler",
  "iletisim_not": "iletişim bilgisi veya not"
}}

Eğer "portfoy_paylasimi" ise:
{{
  "kategori": "portfoy_paylasimi",
  "ozet": "kısa portföy özeti, örn: Foça satılık villa 8 milyon",
  "islem_tipi": "Satılık veya Kiralık veya Belirsiz",
  "mulk_tipi": "Konut veya İşyeri veya Arsa veya Belirsiz",
  "il": "İzmir veya Aydın veya Manisa veya Balıkesir veya Muğla veya Diğer",
  "ilce": "birincil ilçe adı (SADECE yukarıdaki listeden)",
  "ilceler": ["ilçe1"],
  "bolge_mahalle": "gayrimenkulün bulunduğu mahalle veya semt detayı",
  "fiyat": "satış veya kira fiyatı",
  "oda_sayisi_m2": "oda sayısı veya metrekare",
  "ozellikler": "öne çıkan özellikler",
  "ilan_linki": "varsa ilan linki",
  "kapali_portfoy": false,
  "iletisim_not": "iletişim bilgisi"
}}

Eğer "diger" ise:
{{
  "kategori": "diger",
  "ozet": ""
}}

Önemli kurallar:
- ilceler alanına tüm talep edilen ilçeleri yaz. Örn "Bornova veya Karşıyaka" ise ["Bornova", "Karşıyaka"]
- ilce alanına sadece birincil/ilk ilçeyi yaz
- ilce ve ilceler alanlarına YALNIZCA yukarıdaki listede yer alan ilçe adları yazılabilir
- Listede olmayan yer adları (mahalle, semt, sokak) bolge_mahalle alanına yaz
- Eğer bir bilgi yoksa ilgili alanı boş bırak ("") veya boş array ([])
- SADECE JSON döndür, başka hiçbir şey yazma.
"""

MAHALLE_JSON_YOLU = os.path.join(os.path.dirname(__file__), "data", "izmir_mahalleler.json")

# Mahalle adlarının sonundaki bu ekler normalize edilirken temizlenir
_MAHALLE_EK_DESENI = re.compile(r"\s*(mahallesi|mah\.?|mh\.?)\s*$", re.IGNORECASE)


def _mahalle_normalize(ad):
    if not ad:
        return ""
    ad = _MAHALLE_EK_DESENI.sub("", ad).strip().lower()
    # Türkçe karakter/case normalize (İ/I sorunlarını azaltmak için)
    ad = ad.replace("İ", "i").replace("I", "ı")
    return ad


@st.cache_data(ttl=86400)
def mahalle_indeksi_yukle():
    """
    izmir_mahalleler.json dosyasından mahalle -> ilçe ters-indeksi kurar.
    Dosya bulunamazsa boş dict döner (sistem AI'ın kendi tahminine geri düşer).
    """
    try:
        with open(MAHALLE_JSON_YOLU, encoding="utf-8") as f:
            veri = json.load(f)
    except Exception as e:
        print(f"izmir_mahalleler.json yüklenemedi: {e}")
        return {}

    indeks = {}
    for ilce, mahalleler in veri.items():
        for mahalle in mahalleler:
            anahtar = _mahalle_normalize(mahalle)
            if anahtar:
                indeks[anahtar] = ilce
    return indeks


def _mahalle_sozlugunden_ilce_bul(bolge_mahalle, mahalle_indeksi):
    """
    bolge_mahalle metni içinde bilinen bir mahalle adı geçiyorsa ilçesini döner.
    Önce tam eşleşme, sonra metin içinde geçme (substring) denenir.
    """
    if not bolge_mahalle or not mahalle_indeksi:
        return None

    temiz = _mahalle_normalize(bolge_mahalle)
    if temiz in mahalle_indeksi:
        return mahalle_indeksi[temiz]

    # "Kazımdirik civarı" gibi cümle içinde geçen mahalle adlarını da yakala
    for mahalle_anahtari, ilce in mahalle_indeksi.items():
        if len(mahalle_anahtari) > 3 and mahalle_anahtari in temiz:
            return ilce

    return None


def normalize_ilce_sonucu(sonuc, gecerli_ilceler, mahalle_indeksi):
    """
    AI çıktısındaki ilce/ilceler/bolge_mahalle alanlarını doğrular ve
    mümkünse mahalle sözlüğüyle tamamlar.

    Eski `ilce_dogrula()` fonksiyonu ve inline doğrulama mantığı bu tek
    fonksiyonda birleştirildi.

    Adımlar:
    1. ilce geçerli listede değilse bolge_mahalle'ye taşı, ilce'yi boşalt.
    2. ilceler listesindeki geçersizleri bolge_mahalle'ye taşı.
    3. ilce hâlâ boşsa, bolge_mahalle içindeki mahalle adından ilçeyi
       mahalle sözlüğü ile tamamlamayı dene (AI tahmin etmek zorunda
       kalmadan, deterministik eşleşme).
    """
    ilce = sonuc.get("ilce", "") or ""
    ilceler = sonuc.get("ilceler", []) or []
    bolge_mahalle = sonuc.get("bolge_mahalle", "") or ""

    # 1) ilce doğrulama
    if ilce and gecerli_ilceler and ilce not in gecerli_ilceler:
        bolge_mahalle = f"{ilce}, {bolge_mahalle}".strip(", ") if bolge_mahalle else ilce
        ilce = ""

    # 2) ilceler listesi doğrulama
    if ilceler and gecerli_ilceler:
        gecerli = [i for i in ilceler if i in gecerli_ilceler]
        gecersiz = [i for i in ilceler if i not in gecerli_ilceler]
        ilceler = gecerli
        if gecersiz:
            ek = ", ".join(gecersiz)
            bolge_mahalle = f"{bolge_mahalle}, {ek}".strip(", ") if bolge_mahalle else ek

    # 3) ilce boşsa mahalle sözlüğünden tamamlamayı dene
    ilce_kaynagi = "ai" if ilce else "yok"
    if not ilce and bolge_mahalle:
        bulunan_ilce = _mahalle_sozlugunden_ilce_bul(bolge_mahalle, mahalle_indeksi)
        if bulunan_ilce and (not gecerli_ilceler or bulunan_ilce in gecerli_ilceler):
            ilce = bulunan_ilce
            ilce_kaynagi = "mahalle_sozlugu"
            if not ilceler:
                ilceler = [ilce]

    sonuc["ilce"] = ilce
    sonuc["ilceler"] = ilceler
    sonuc["bolge_mahalle"] = bolge_mahalle
    sonuc["_ilce_kaynagi"] = ilce_kaynagi  # DB'ye yazılmaz, sadece debug/log amaçlı
    return sonuc


@st.cache_data(ttl=3600)
def ilce_listesini_cek():
    """Supabase'deki ilceler tablosundan tüm ilçeleri çeker. 1 saat cache'lenir."""
    try:
        from core.supabase_client import get_client
        supabase = get_client()
        response = supabase.table("ilceler").select("il, ilce").execute()
        if not response.data:
            return None, []

        il_ilce_dict = {}
        tum_ilceler = []
        for row in response.data:
            il = row.get("il", "")
            ilce = row.get("ilce", "")
            if il and ilce:
                if il not in il_ilce_dict:
                    il_ilce_dict[il] = []
                il_ilce_dict[il].append(ilce)
                tum_ilceler.append(ilce)

        satirlar = []
        for il, ilceler in sorted(il_ilce_dict.items()):
            satirlar.append(f"{il}: {', '.join(sorted(ilceler))}")

        ilce_listesi_str = "\n".join(satirlar)
        return ilce_listesi_str, tum_ilceler
    except Exception as e:
        print(f"İlçe listesi çekilemedi: {e}")
        return None, []


def sistem_mesaji_olustur():
    """Veritabanından ilçe listesi çekip sistem mesajına enjekte eder."""
    ilce_listesi_str, _ = ilce_listesini_cek()

    if not ilce_listesi_str:
        ilce_listesi_str = """İzmir: Aliağa, Balçova, Bayındır, Bayraklı, Bergama, Beydağ, Bornova, Buca, Çeşme, Çiğli, Dikili, Foça, Gaziemir, Güzelbahçe, Karabağlar, Karaburun, Karşıyaka, Kemalpaşa, Kınık, Kiraz, Konak, Menderes, Menemen, Narlıdere, Ödemiş, Seferihisar, Selçuk, Tire, Torbalı, Urla
Aydın: Bozdoğan, Buharkent, Çine, Didim, Efeler, Germencik, İncirliova, Karacasu, Karpuzlu, Koçarlı, Köşk, Kuşadası, Kuyucak, Nazilli, Söke, Sultanhisar, Yenipazar
Manisa: Ahmetli, Akhisar, Alaşehir, Demirci, Gölmarmara, Gördes, Kırkağaç, Köprübaşı, Kula, Salihli, Sarıgöl, Saruhanlı, Selendi, Soma, Şehzadeler, Turgutlu, Yunusemre
Balıkesir: Altıeylül, Ayvalık, Balya, Bandırma, Bigadiç, Burhaniye, Dursunbey, Edremit, Erdek, Gömeç, Gönen, Havran, İvrindi, Karesi, Kepsut, Manyas, Marmara, Savaştepe, Sındırgı, Susurluk
Muğla: Bodrum, Dalaman, Datça, Fethiye, Kavaklıdere, Köyceğiz, Marmaris, Menteşe, Milas, Ortaca, Seydikemer, Ula, Yatağan"""

    return SISTEM_MESAJI_TEMPLATE.format(ilce_listesi=ilce_listesi_str)


@st.cache_resource
def get_anthropic_client():
    """Anthropic client bir kere oluşturulur, sonraki çağrılarda tekrar kullanılır."""
    return anthropic.Anthropic(api_key=st.secrets["anthropic"]["api_key"].strip())


def _icerik_kirp(icerik, ilk=2000, son=1500):
    """
    Eski strateji sadece ilk 3000 karakteri alıyordu; fiyat, telefon,
    ilan linki gibi bilgiler genelde mailin sonunda olduğu için kayboluyordu.
    Yeni strateji: ilk `ilk` + son `son` karakteri birleştirir.
    """
    if not icerik:
        return ""
    if len(icerik) <= ilk + son:
        return icerik
    return icerik[:ilk] + " [...] " + icerik[-son:]


def parse_mail(konu, icerik, sistem_mesaji=None, gecerli_ilceler=None,
               mahalle_indeksi=None, max_tokens=600):
    """
    Tek bir maili Claude'a gönderip yapılandırılmış sonuç döner.
    sistem_mesaji / gecerli_ilceler / mahalle_indeksi dışarıdan verilirse
    (toplu işlemede olduğu gibi) tekrar tekrar hesaplanmaz.
    """
    client = get_anthropic_client()
    icerik_kisalt = _icerik_kirp(icerik)
    prompt = f"Konu: {konu}\n\nİçerik:\n{icerik_kisalt}"

    if sistem_mesaji is None:
        sistem_mesaji = sistem_mesaji_olustur()

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=[
            {
                "type": "text",
                "text": sistem_mesaji,
                "cache_control": {"type": "ephemeral"}
            }
        ],
        messages=[{"role": "user", "content": prompt}],
        extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
    )

    if not message.content or len(message.content) == 0:
        return {"kategori": "diger", "ozet": ""}
    raw = message.content[0].text.strip()
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)

    sonuc = _json.loads(raw)  # burada hata olursa çağıran taraf yakalar (retry için)

    if gecerli_ilceler is None:
        _, gecerli_ilceler = ilce_listesini_cek()
    if mahalle_indeksi is None:
        mahalle_indeksi = mahalle_indeksi_yukle()

    sonuc = normalize_ilce_sonucu(sonuc, gecerli_ilceler or [], mahalle_indeksi or {})
    return sonuc


def _kayit_isle_worker(kayit, sistem_mesaji, gecerli_ilceler, mahalle_indeksi, max_retry=2):
    """
    Tek bir kaydı işler; hata olursa max_retry kadar tekrar dener.
    Thread havuzunda çalıştırılmak üzere tasarlandı.
    Döner: (kayit, sonuc_dict_or_None, hata_mesaji_or_None)
    """
    konu = kayit.get("mail_konusu", "")
    icerik = kayit.get("mail_icerigi", "")

    if not konu and not icerik:
        return kayit, {"kategori": "diger", "ozet": ""}, None

    son_hata = None
    for deneme in range(max_retry + 1):
        try:
            sonuc = parse_mail(
                konu, icerik,
                sistem_mesaji=sistem_mesaji,
                gecerli_ilceler=gecerli_ilceler,
                mahalle_indeksi=mahalle_indeksi,
            )
            return kayit, sonuc, None
        except Exception as e:
            son_hata = f"{type(e).__name__}: {e}"
            if deneme < max_retry:
                time.sleep(1.5 * (deneme + 1))
                continue
    return kayit, None, son_hata


def mailleri_isle(kayitlar, durum_callback=None, max_workers=3, timeout_saniye=30):
    """
    Kayıtları kontrollü paralel şekilde işler (eski sürüm tek tek, sırayla
    işliyordu — 100 kayıt = 100 sıralı API çağrısı demekti).

    max_workers: aynı anda kaç mail işlensin (API'yi boğmamak için düşük
                 tutuldu, agresif "hepsini birden" değil).
    timeout_saniye: her worker için üst zaman sınırı.

    Döner: (alici_sonuclar, portfoy_sonuclar, hatali_kayitlar)
    hatali_kayitlar: [{"kayit": ..., "hata": "..."}]  — bu kayıtlar
    çağıran tarafta parse_status="failed" + parse_error olarak işaretlenmeli.
    """
    alici_sonuclar = []
    portfoy_sonuclar = []
    hatali_kayitlar = []

    if not kayitlar:
        return alici_sonuclar, portfoy_sonuclar, hatali_kayitlar

    sistem_mesaji = sistem_mesaji_olustur()
    _, gecerli_ilceler = ilce_listesini_cek()
    mahalle_indeksi = mahalle_indeksi_yukle()

    toplam = len(kayitlar)
    islenen = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_kayit = {
            executor.submit(
                _kayit_isle_worker, kayit, sistem_mesaji, gecerli_ilceler, mahalle_indeksi
            ): kayit
            for kayit in kayitlar
        }

        for future in as_completed(future_to_kayit):
            islenen += 1
            if durum_callback:
                durum_callback(f"İşleniyor: {islenen}/{toplam}")

            try:
                kayit, sonuc, hata = future.result(timeout=timeout_saniye)
            except Exception as e:
                kayit = future_to_kayit[future]
                sonuc, hata = None, f"Timeout/hata: {e}"

            if hata is not None:
                hatali_kayitlar.append({"kayit": kayit, "hata": hata})
                continue

            kategori = sonuc.get("kategori", "diger")

            if kategori == "alici_talebi":
                kayit["kategori"] = "alici_talebi"
                kayit["ozet"] = sonuc.get("ozet", "")
                kayit["islem_tipi"] = sonuc.get("islem_tipi", "")
                kayit["mulk_tipi"] = sonuc.get("mulk_tipi", "")
                kayit["il"] = sonuc.get("il", "")
                kayit["ilce"] = sonuc.get("ilce", "")
                kayit["ilceler"] = sonuc.get("ilceler", [])
                kayit["bolge_mahalle"] = sonuc.get("bolge_mahalle", "")
                kayit["oda_sayisi_m2"] = sonuc.get("oda_sayisi_m2", "")
                kayit["max_butce"] = sonuc.get("max_butce", "")
                kayit["ozel_kriterler"] = sonuc.get("ozel_kriterler", "")
                kayit["iletisim_not"] = sonuc.get("iletisim_not", "")
                kayit["parse_status"] = "parsed"
                alici_sonuclar.append(kayit)

            elif kategori == "portfoy_paylasimi":
                portfoy = {
                    "kayit_tarihi": kayit.get("kayit_tarihi", ""),
                    "talep_eden_danisan": kayit.get("talep_eden_danisan", ""),
                    "ozet": sonuc.get("ozet", ""),
                    "islem_tipi": sonuc.get("islem_tipi", ""),
                    "mulk_tipi": sonuc.get("mulk_tipi", ""),
                    "il": sonuc.get("il", ""),
                    "ilce": sonuc.get("ilce", ""),
                    "ilceler": sonuc.get("ilceler", []),
                    "bolge_mahalle": sonuc.get("bolge_mahalle", ""),
                    "fiyat": sonuc.get("fiyat", ""),
                    "oda_sayisi_m2": sonuc.get("oda_sayisi_m2", ""),
                    "ozellikler": sonuc.get("ozellikler", ""),
                    "ilan_linki": sonuc.get("ilan_linki", ""),
                    "kapali_portfoy": sonuc.get("kapali_portfoy", False),
                    "iletisim_not": sonuc.get("iletisim_not", ""),
                    "mail_konusu": kayit.get("mail_konusu", ""),
                    "mail_icerigi": kayit.get("mail_icerigi", ""),
                    "message_id": kayit.get("message_id", ""),
                    "fallback_hash": kayit.get("fallback_hash", ""),
                    "kaynak_klasor": kayit.get("kaynak_klasor", ""),
                    # asıl ham kaydın id'si — mail_job.py bunu kullanarak
                    # kaynak satırı silmeden "moved_to_portfoy" işaretleyecek
                    "_source_alici_id": kayit.get("id"),
                }
                portfoy_sonuclar.append(portfoy)

            else:
                kayit["kategori"] = "diger"
                kayit["ozet"] = ""
                kayit["bolge_mahalle"] = kayit.get("bolge_mahalle") or "diger"
                kayit["parse_status"] = "ignored"
                alici_sonuclar.append(kayit)

    return alici_sonuclar, portfoy_sonuclar, hatali_kayitlar
