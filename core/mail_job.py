"""
Mail çekme ve AI kategorize etme işlerini orkestre eden ortak katman.

Hem pages/5_Mail_Islem.py (manuel buton) hem de scripts/mail_auto_job.py
(GitHub Actions üzerinden otomatik çalışan zamanlanmış iş) bu modüldeki
fonksiyonları çağırır — mantık tek yerde, iki farklı tetikleyici var.

Faz 1 (veri bütünlüğü) ve Faz 2.5 (otomasyon) revizeleri burada toplandı:
- "İşlendi mi?" artık bolge_mahalle değil, parse_status alanı ile anlaşılıyor.
- Portföye taşımada satır SİLİNMİYOR; parse_status="moved_to_portfoy" +
  linked_portfoy_id yazılıyor. Geçmiş kaybolmuyor, hata olursa iz sürülebiliyor.
- Sabit 5 gün yerine mail_fetch_state tablosundaki son başarılı çekim
  zamanına göre since_date hesaplanıyor.
- Her çalıştırma mail_fetch_log tablosuna özet olarak yazılıyor
  (UI'da ve otomasyonda aynı rapor kullanılabiliyor).
"""

from datetime import datetime, timezone
import time

from core.supabase_client import get_client
from core.mail_fetcher import mailleri_cek, DEFAULT_LOOKBACK_DAYS
from core.mail_parser import mailleri_isle

FETCH_KLASORLERI = ["INBOX", "1_Alici_Depo"]


def _mevcut_kimlikleri_cek(supabase):
    """alici_talepleri + portfoyler tablolarındaki mevcut message_id ve
    fallback_hash değerlerini çeker (dedupe için).

    ÖNEMLİ: Supabase/PostgREST varsayılan olarak tek sorguda en fazla 1000
    satır döndürür. Tablo 1000 satırı geçtiğinde .range() ile sayfalama
    yapılmazsa bazı eski kayıtlar "yokmuş" gibi görünür ve tekrar tekrar
    çekilmeye çalışılır (portfoyler tablosunda unique constraint'e takılıp
    'failed' olarak işaretlenmesine yol açan sorun buydu). Bu yüzden burada
    tüm satırlar bitene kadar sayfa sayfa okunuyor.
    """
    message_idler = set()
    fallback_hashler = set()

    for tablo in ("alici_talepleri", "portfoyler"):
        try:
            sayfa_boyutu = 1000
            baslangic = 0
            while True:
                resp = (
                    supabase.table(tablo)
                    .select("message_id, fallback_hash")
                    .range(baslangic, baslangic + sayfa_boyutu - 1)
                    .execute()
                )
                satirlar = resp.data or []
                for row in satirlar:
                    if row.get("message_id"):
                        message_idler.add(row["message_id"])
                    if row.get("fallback_hash"):
                        fallback_hashler.add(row["fallback_hash"])
                if len(satirlar) < sayfa_boyutu:
                    break
                baslangic += sayfa_boyutu
        except Exception as e:
            # fallback_hash kolonu migration uygulanmadan önce yoksa da
            # sistem çökmesin — sadece message_id ile devam eder.
            print(f"{tablo} kimlik listesi çekilirken uyarı: {e}")

    return message_idler, fallback_hashler


def _since_date_hesapla(supabase, lookback_days_override=None):
    """
    mail_fetch_state tablosundaki en eski 'last_successful_fetch_at' baz
    alınarak IMAP SINCE formatında tarih üretir. Hiç kayıt yoksa (ilk
    çalıştırma) DEFAULT_LOOKBACK_DAYS / override kullanılır.
    """
    if lookback_days_override:
        from datetime import timedelta
        return (datetime.now() - timedelta(days=lookback_days_override)).strftime("%d-%b-%Y"), None

    try:
        resp = supabase.table("mail_fetch_state").select("klasor, last_successful_fetch_at").execute()
        zamanlar = [r["last_successful_fetch_at"] for r in (resp.data or []) if r.get("last_successful_fetch_at")]
    except Exception as e:
        print(f"mail_fetch_state okunamadı, varsayılan pencere kullanılacak: {e}")
        zamanlar = []

    if not zamanlar:
        from datetime import timedelta
        since = datetime.now() - timedelta(days=DEFAULT_LOOKBACK_DAYS)
        return since.strftime("%d-%b-%Y"), None

    en_eski = min(zamanlar)
    try:
        en_eski_dt = datetime.fromisoformat(en_eski.replace("Z", "+00:00"))
    except Exception:
        from datetime import timedelta
        en_eski_dt = datetime.now(timezone.utc) - timedelta(days=DEFAULT_LOOKBACK_DAYS)

    # Küçük bir güvenlik payı: son çekimden 1 saat öncesinden itibaren tara
    # (saat dilimi/IMAP gecikme farklarına karşı).
    from datetime import timedelta
    guvenli_since = en_eski_dt - timedelta(hours=1)
    return guvenli_since.strftime("%d-%b-%Y"), en_eski_dt


def _fetch_state_guncelle(supabase, klasor, zaman):
    try:
        supabase.table("mail_fetch_state").upsert({
            "klasor": klasor,
            "last_successful_fetch_at": zaman.isoformat(),
        }).execute()
    except Exception as e:
        print(f"mail_fetch_state güncellenemedi ({klasor}): {e}")


def _log_yaz(supabase, is_tipi, klasor=None, bulunan=0, yeni_kayit=0,
             zaten_var=0, filtrelenen=0, hata_sayisi=0, hata_detay=None, sure_saniye=None):
    try:
        supabase.table("mail_fetch_log").insert({
            "is_tipi": is_tipi,
            "klasor": klasor,
            "bulunan": bulunan,
            "yeni_kayit": yeni_kayit,
            "zaten_var": zaten_var,
            "filtrelenen": filtrelenen,
            "hata_sayisi": hata_sayisi,
            "hata_detay": hata_detay,
            "sure_saniye": sure_saniye,
        }).execute()
    except Exception as e:
        print(f"mail_fetch_log yazılamadı: {e}")


def run_mail_fetch_job(durum_callback=None, lookback_days=None):
    """
    Mailleri çeker, dedupe eder, Supabase'e parse_status='raw' olarak
    kaydeder. UI'daki "Mailleri Çek" butonu ve otomasyon script'i bu
    fonksiyonu çağırır.

    Döner: özet dict (bulunan, yeni_kayit, zaten_var, hata_sayisi, ...)
    """
    baslangic = time.time()
    supabase = get_client()

    message_idler, fallback_hashler = _mevcut_kimlikleri_cek(supabase)
    since_date, referans_zaman = _since_date_hesapla(supabase, lookback_days)

    sonuc = mailleri_cek(
        durum_callback=durum_callback,
        since_date=since_date,
        mevcut_message_idler=message_idler,
        mevcut_fallback_hashler=fallback_hashler,
    )
    veriler = sonuc["veriler"]
    hata_log = sonuc["hata_log"]

    kayit_sayisi = 0
    for kayit in veriler:
        try:
            supabase.table("alici_talepleri").insert(kayit).execute()
            kayit_sayisi += 1
        except Exception as e:
            hata_log.append({"klasor": kayit.get("kaynak_klasor"), "uid": None,
                              "hata": f"Insert hatası: {e}"})

    simdi = datetime.now(timezone.utc)
    for klasor in FETCH_KLASORLERI:
        _fetch_state_guncelle(supabase, klasor, simdi)

    sure = round(time.time() - baslangic, 1)
    _log_yaz(
        supabase, is_tipi="fetch",
        bulunan=len(veriler), yeni_kayit=kayit_sayisi,
        hata_sayisi=len(hata_log), hata_detay=hata_log or None,
        sure_saniye=sure,
    )

    if durum_callback:
        durum_callback(f"✅ Çekim tamamlandı: {kayit_sayisi} yeni kayıt, {len(hata_log)} hata ({sure}sn)")

    return {
        "bulunan": len(veriler),
        "yeni_kayit": kayit_sayisi,
        "hata_sayisi": len(hata_log),
        "hata_log": hata_log,
        "sure_saniye": sure,
        "ozet_klasor": sonuc["ozet"],
    }


def run_pending_ai_parse_job(limit=50, durum_callback=None, max_workers=3):
    """
    parse_status='raw' olan kayıtları AI ile işler.
    - alici_talebi / diger -> aynı satır güncellenir, parse_status='parsed'/'ignored'
    - portfoy_paylasimi -> portfoyler tablosuna yeni satır eklenir; ham satır
      SİLİNMEZ, parse_status='moved_to_portfoy' + linked_portfoy_id yazılır.
    - hata alan kayıtlar -> parse_status='failed' + parse_error

    UI'daki "AI ile Kategorize Et" butonu ve otomasyon script'i bu
    fonksiyonu çağırır.
    """
    baslangic = time.time()
    supabase = get_client()

    resp = supabase.table("alici_talepleri").select("*").eq("parse_status", "raw").limit(limit).execute()
    kayitlar = resp.data or []

    if not kayitlar:
        if durum_callback:
            durum_callback("İşlenecek yeni kayıt yok.")
        return {"islenen": 0, "alici": 0, "portfoy": 0, "hatali": 0, "sure_saniye": 0}

    if durum_callback:
        durum_callback(f"{len(kayitlar)} kayıt AI ile işlenecek...")

    alici_sonuclar, portfoy_sonuclar, hatali_kayitlar = mailleri_isle(
        kayitlar, durum_callback=durum_callback, max_workers=max_workers
    )

    simdi_iso = datetime.now(timezone.utc).isoformat()

    # alici_talebi / diger sonuçları güncelle
    for kayit in alici_sonuclar:
        guncelleme = {
            "kategori": kayit.get("kategori", "diger"),
            "ozet": kayit.get("ozet", ""),
            "islem_tipi": kayit.get("islem_tipi", ""),
            "mulk_tipi": kayit.get("mulk_tipi", ""),
            "il": kayit.get("il", ""),
            "ilce": kayit.get("ilce", ""),
            "ilceler": kayit.get("ilceler", []),
            "bolge_mahalle": kayit.get("bolge_mahalle", ""),
            "oda_sayisi_m2": kayit.get("oda_sayisi_m2", ""),
            "max_butce": kayit.get("max_butce", ""),
            "ozel_kriterler": kayit.get("ozel_kriterler", ""),
            "iletisim_not": kayit.get("iletisim_not", ""),
            "parse_status": kayit.get("parse_status", "parsed"),
            "ai_processed_at": simdi_iso,
        }
        try:
            supabase.table("alici_talepleri").update(guncelleme).eq("id", kayit["id"]).execute()
        except Exception as e:
            hatali_kayitlar.append({"kayit": kayit, "hata": f"Update hatası: {e}"})

    # portfoy_paylasimi sonuçları: insert + kaynak satırı GÜVENLİ şekilde işaretle
    portfoy_basarili = 0
    for portfoy in portfoy_sonuclar:
        source_id = portfoy.pop("_source_alici_id", None)
        try:
            insert_resp = supabase.table("portfoyler").insert(portfoy).execute()
            yeni_portfoy_id = (insert_resp.data or [{}])[0].get("id")

            if source_id is not None:
                supabase.table("alici_talepleri").update({
                    "parse_status": "moved_to_portfoy",
                    "linked_portfoy_id": yeni_portfoy_id,
                    "ai_processed_at": simdi_iso,
                }).eq("id", source_id).execute()

            portfoy_basarili += 1
        except Exception as e:
            hata_metni = str(e)
            # Bu mail (message_id) daha önce zaten portfoyler tablosuna
            # eklenmiş demektir (unique constraint tetiklendi). Bu gerçek
            # bir hata değil — dedupe'un kaçırdığı bir kayıt. 'failed'
            # yazmak yerine mevcut portföy kaydını bulup doğru şekilde
            # bağlıyoruz.
            if "portfoyler_message_id_key" in hata_metni and portfoy.get("message_id"):
                try:
                    mevcut = (
                        supabase.table("portfoyler")
                        .select("id")
                        .eq("message_id", portfoy["message_id"])
                        .limit(1)
                        .execute()
                    )
                    mevcut_id = (mevcut.data or [{}])[0].get("id")
                    if source_id is not None:
                        supabase.table("alici_talepleri").update({
                            "parse_status": "moved_to_portfoy",
                            "linked_portfoy_id": mevcut_id,
                            "ai_processed_at": simdi_iso,
                            "parse_error": None,
                        }).eq("id", source_id).execute()
                    portfoy_basarili += 1
                    continue
                except Exception as e2:
                    hatali_kayitlar.append({"kayit": portfoy, "hata": f"Duplicate çözümleme hatası: {e2}"})
                    continue

            hatali_kayitlar.append({"kayit": portfoy, "hata": f"Portföy insert/link hatası: {e}"})
            if source_id is not None:
                try:
                    supabase.table("alici_talepleri").update({
                        "parse_status": "failed",
                        "parse_error": f"Portföy taşıma hatası: {e}",
                    }).eq("id", source_id).execute()
                except Exception:
                    pass

    # AI çağrısı veya sonrasında hata alan kayıtları işaretle
    for hata_kayit in hatali_kayitlar:
        kayit = hata_kayit.get("kayit") or {}
        kayit_id = kayit.get("id")
        if kayit_id is None:
            continue
        try:
            supabase.table("alici_talepleri").update({
                "parse_status": "failed",
                "parse_error": str(hata_kayit.get("hata"))[:500],
            }).eq("id", kayit_id).execute()
        except Exception as e:
            print(f"Hatalı kayıt işaretlenemedi (id={kayit_id}): {e}")

    sure = round(time.time() - baslangic, 1)
    _log_yaz(
        supabase, is_tipi="ai_parse",
        bulunan=len(kayitlar),
        yeni_kayit=len(alici_sonuclar) + portfoy_basarili,
        hata_sayisi=len(hatali_kayitlar),
        hata_detay=[{"hata": h["hata"]} for h in hatali_kayitlar] or None,
        sure_saniye=sure,
    )

    if durum_callback:
        durum_callback(
            f"✅ AI işleme bitti: {len(alici_sonuclar)} alıcı/diğer, "
            f"{portfoy_basarili} portföy, {len(hatali_kayitlar)} hatalı ({sure}sn)"
        )

    return {
        "islenen": len(kayitlar),
        "alici": len(alici_sonuclar),
        "portfoy": portfoy_basarili,
        "hatali": len(hatali_kayitlar),
        "sure_saniye": sure,
    }


def run_full_mail_job(ai_enabled=True, ai_limit=20, durum_callback=None):
    """
    Otomasyon (GitHub Actions) tarafından çağrılan tam iş: önce çekim,
    sonra (istenirse) AI kategorize etme.

    Faz 2.5 kararı gereği: otomatik çekim ilk etapta AI'sız (ai_enabled=False)
    çalıştırılmalı; bir süre sorunsuz işledikten sonra ai_enabled=True yapılır.
    """
    fetch_sonuc = run_mail_fetch_job(durum_callback=durum_callback)

    parse_sonuc = None
    if ai_enabled:
        parse_sonuc = run_pending_ai_parse_job(limit=ai_limit, durum_callback=durum_callback)

    return {"fetch": fetch_sonuc, "ai_parse": parse_sonuc}
