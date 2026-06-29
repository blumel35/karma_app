import re
import json
import anthropic
import streamlit as st


SISTEM_MESAJI_TEMPLATE = """
Sen bir gayrimenkul şirketinin (Startkey) mail analiz asistanısın.
Bu mailler Startkey gayrimenkul danışmanları arasındaki iletişimdir.
Danışmanlar birbirlerine iki amaçla mail atar:
1. Ellerindeki alıcı müşteri için uygun portföy ararlar (Alıcı Talebi)
2. Ellerindeki portföyü paylaşarak alıcısı olan danışmanı ararlar (Portföy Paylaşımı)

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


@st.cache_data(ttl=3600)
def ilce_listesini_cek():
    """Supabase'deki ilceler tablosundan tüm ilçeleri çeker. 1 saat cache'lenir."""
    try:
        from core.supabase_client import get_client
        supabase = get_client()
        response = supabase.table("ilceler").select("il, ilce").execute()
        if not response.data:
            return None, []
        
        # İl bazında grupla
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
        
        # Prompt için formatla
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
        # Fallback: sabit liste
        ilce_listesi_str = """İzmir: Aliağa, Balçova, Bayındır, Bayraklı, Bergama, Beydağ, Bornova, Buca, Çeşme, Çiğli, Dikili, Foça, Gaziemir, Güzelbahçe, Karabağlar, Karaburun, Karşıyaka, Kemalpaşa, Kınık, Kiraz, Konak, Menderes, Menemen, Narlıdere, Ödemiş, Seferihisar, Selçuk, Tire, Torbalı, Urla
Aydın: Bozdoğan, Buharkent, Çine, Didim, Efeler, Germencik, İncirliova, Karacasu, Karpuzlu, Koçarlı, Köşk, Kuşadası, Kuyucak, Nazilli, Söke, Sultanhisar, Yenipazar
Manisa: Ahmetli, Akhisar, Alaşehir, Demirci, Gölmarmara, Gördes, Kırkağaç, Köprübaşı, Kula, Salihli, Sarıgöl, Saruhanlı, Selendi, Soma, Şehzadeler, Turgutlu, Yunusemre
Balıkesir: Altıeylül, Ayvalık, Balya, Bandırma, Bigadiç, Burhaniye, Dursunbey, Edremit, Erdek, Gömeç, Gönen, Havran, İvrindi, Karesi, Kepsut, Manyas, Marmara, Savaştepe, Sındırgı, Susurluk
Muğla: Bodrum, Dalaman, Datça, Fethiye, Kavaklıdere, Köyceğiz, Marmaris, Menteşe, Milas, Ortaca, Seydikemer, Ula, Yatağan"""
    
    return SISTEM_MESAJI_TEMPLATE.format(ilce_listesi=ilce_listesi_str)


def ilce_dogrula(ilce_adi, gecerli_ilceler):
    """Gelen ilçe adının listede olup olmadığını kontrol eder."""
    if not ilce_adi or not gecerli_ilceler:
        return ilce_adi
    if ilce_adi in gecerli_ilceler:
        return ilce_adi
    return ""  # Listede yoksa boş döndür


def parse_mail(konu, icerik):
    client = anthropic.Anthropic(api_key=st.secrets["anthropic"]["api_key"].strip())
    icerik_kisalt = icerik[:3000] if len(icerik) > 3000 else icerik
    prompt = f"Konu: {konu}\n\nİçerik:\n{icerik_kisalt}"

    sistem_mesaji = sistem_mesaji_olustur()

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=600,
        system=sistem_mesaji,
        messages=[{"role": "user", "content": prompt}]
    )

    if not message.content or len(message.content) == 0:
        return {"kategori": "diger", "ozet": ""}
    raw = message.content[0].text.strip()
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)
    try:
        sonuc = json.loads(raw)
        
        # İkinci güvenlik katmanı: ilçe doğrulama
        _, gecerli_ilceler = ilce_listesini_cek()
        if gecerli_ilceler:
            ilce = sonuc.get("ilce", "")
            ilceler = sonuc.get("ilceler", [])
            bolge_mahalle = sonuc.get("bolge_mahalle", "")
            
            # ilce doğrula
            if ilce and ilce not in gecerli_ilceler:
                # Geçersiz ilçeyi bolge_mahalle'ye ekle
                if bolge_mahalle:
                    bolge_mahalle = f"{ilce}, {bolge_mahalle}"
                else:
                    bolge_mahalle = ilce
                sonuc["ilce"] = ""
                sonuc["bolge_mahalle"] = bolge_mahalle
            
            # ilceler listesini doğrula
            if ilceler:
                gecerli = []
                gecersiz = []
                for i in ilceler:
                    if i in gecerli_ilceler:
                        gecerli.append(i)
                    else:
                        gecersiz.append(i)
                
                sonuc["ilceler"] = gecerli
                if gecersiz:
                    ek = ", ".join(gecersiz)
                    mevcut_bolge = sonuc.get("bolge_mahalle", "")
                    sonuc["bolge_mahalle"] = f"{mevcut_bolge}, {ek}".strip(", ") if mevcut_bolge else ek
        
        return sonuc
    except Exception as e:
        print("Parse hatası:", e, "| Ham:", raw)
        return {"kategori": "diger", "ozet": ""}


def mailleri_isle(kayitlar, durum_callback=None):
    alici_sonuclar = []
    portfoy_sonuclar = []
    toplam = len(kayitlar)

    for i, kayit in enumerate(kayitlar):
        if durum_callback:
            durum_callback(f"İşleniyor: {i+1}/{toplam}")

        konu = kayit.get("mail_konusu", "")
        icerik = kayit.get("mail_icerigi", "")

        if not konu and not icerik:
            continue

        sonuc = parse_mail(konu, icerik)
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
                "kaynak_klasor": kayit.get("kaynak_klasor", "")
            }
            portfoy_sonuclar.append(portfoy)

        else:
            kayit["kategori"] = "diger"
            kayit["ozet"] = ""
            kayit["bolge_mahalle"] = "diger"
            alici_sonuclar.append(kayit)

    return alici_sonuclar, portfoy_sonuclar