"""
scripts/rehber_alarm_job.py

Rehberim "yeniden ara" alarmlarını gönderen başsız iş (09.10.2026).
GitHub Actions'ta, mail_auto_fetch.yml içinde 30 dakikada bir çalışır
(ayrı bir workflow açmamak için — Actions dakika kotasını artırmamak üzere).

Zamanı gelmiş (alarm_zamani <= şimdi) ve henüz bildirilmemiş
(alarm_bildirildi boş) kayıtlar için kaydın sahibi danışmana push gönderir,
sonra alarm_bildirildi'yi doldurur. Push gönderimi hata verirse kayıt
işaretlenmez, 30 dakika sonra yeniden denenir. Danışmanın kayıtlı cihazı
yoksa bildirim yine 'Bildirimlerim' geçmişine düşer ve Rehberim'de
"⏰ Zamanı geldi" olarak görünür.

Bildirim metni TELEFON NUMARASI İÇERMEZ (kilit ekranında görünür); sadece
ad, alarm notu ve ilan özetinin ilk satırı. Bildirime dokununca giriş
istenir ve Rehberim açılır.

Ayrıca Ajandam olay hatırlatmaları (ajanda_olaylari.hatirlat_zamani) aynı
çalıştırmada gönderilir; bildirim metni kişinin telefonunu içermez.

Elle test: python scripts/rehber_alarm_job.py
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.supabase_client import get_client  # noqa: E402
from core.push_bildirim import bildirim_gonder, KARMA_APP_URL  # noqa: E402


def rehber_alarmlari(supa):
    simdi = datetime.now(timezone.utc).isoformat()
    try:
        satirlar = (
            supa.table("danisman_kisiler")
            .select("id, danisman, ad, alarm_zamani, alarm_notu, ilan_ozeti")
            .lte("alarm_zamani", simdi)
            .is_("alarm_bildirildi", "null")
            .limit(500)
            .execute()
            .data or []
        )
    except Exception as e:
        # Sütunlar henüz yoksa (SQL çalıştırılmadıysa) iş sessizce geçsin.
        print(f"ℹ️ Alarm sorgusu yapılamadı (SQL çalıştırıldı mı?): {e}")
        return

    print(f"⏰ Zamanı gelen alarm: {len(satirlar)}")
    gonderilen = hata = 0
    for k in satirlar:
        sahibi = (k.get("danisman") or "").strip()
        if not sahibi:
            continue
        ad = (k.get("ad") or "Kişi").strip()
        parcalar = []
        if (k.get("alarm_notu") or "").strip():
            parcalar.append(k["alarm_notu"].strip())
        ozet = (k.get("ilan_ozeti") or "").strip().split("\n")[0].strip()
        if ozet and not ozet.startswith("http"):
            parcalar.append(ozet)
        govde = " · ".join(parcalar) or "Rehberim'de kurduğun alarmın zamanı geldi."
        try:
            bildirim_gonder(
                sahibi, f"⏰ Yeniden ara: {ad}", govde,
                url=f"{KARMA_APP_URL}/Danisman_Rehberim",
            )
            supa.table("danisman_kisiler").update(
                {"alarm_bildirildi": datetime.now(timezone.utc).isoformat()}
            ).eq("id", k["id"]).execute()
            gonderilen += 1
        except Exception as e:
            hata += 1
            print(f"⚠️ {sahibi} / {ad}: {e}")
    print(f"🏁 Alarm özeti: bildirilen={gonderilen}, hata={hata}")


def ajanda_hatirlatmalari(supa):
    """Zamanı gelen Ajandam olay hatırlatmaları (sql/ajanda_olaylari.sql)."""
    simdi = datetime.now(timezone.utc).isoformat()
    try:
        satirlar = (
            supa.table("ajanda_olaylari")
            .select("id, danisman, baslik, tur, saat, kisi_ad, yer")
            .lte("hatirlat_zamani", simdi)
            .is_("hatirlat_bildirildi", "null")
            .eq("tamamlandi", False)
            .limit(500)
            .execute()
            .data or []
        )
    except Exception as e:
        print(f"ℹ️ Ajanda sorgusu yapılamadı (SQL çalıştırıldı mı?): {e}")
        return

    print(f"📅 Zamanı gelen ajanda hatırlatması: {len(satirlar)}")
    gonderilen = hata = 0
    for o in satirlar:
        sahibi = (o.get("danisman") or "").strip()
        if not sahibi:
            continue
        parcalar = [str(o.get("saat") or "")[:5]]
        for alan in ("kisi_ad", "yer"):
            if (o.get(alan) or "").strip():
                parcalar.append(o[alan].strip())
        try:
            bildirim_gonder(
                sahibi, f"📅 {(o.get('baslik') or 'Ajanda').strip()}",
                " · ".join(p for p in parcalar if p),
                url=f"{KARMA_APP_URL}/Danisman_Rehberim",
            )
            supa.table("ajanda_olaylari").update(
                {"hatirlat_bildirildi": datetime.now(timezone.utc).isoformat()}
            ).eq("id", o["id"]).execute()
            gonderilen += 1
        except Exception as e:
            hata += 1
            print(f"⚠️ {sahibi} / {o.get('baslik')}: {e}")
    print(f"🏁 Ajanda özeti: bildirilen={gonderilen}, hata={hata}")


def main():
    supa = get_client()
    rehber_alarmlari(supa)
    ajanda_hatirlatmalari(supa)


if __name__ == "__main__":
    main()
