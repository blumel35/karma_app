"""
startkey_ofis_job.py
---------------------
Startkey ofisleri analizi için Revy ilan verisini (aktif + yayından kalkan,
ilan tarihi >= 2025-01-01, İzmir'in 30 ilçesi) çekip startkey_ofis_ilanlar
tablosuna yazan başsız (headless) iş. ELLE tetiklenir (GitHub Actions >
"Startkey Ofis Verisi Çekimi" > Run workflow).

Motor: core/startkey_ofis_cek.py (neden ayrı olduğu orada açıklanıyor).

DAVRANIŞ
  * Önce kendi kendini sınar; sınama başarısızsa veri çekilmez, iş KIRMIZI biter.
  * Sıra: önce TÜM aktif kombinasyonlar, sonra TÜM pasif (yayından kalkan)
    kombinasyonlar — bir ilan her iki listede de görünürse PASİF kazanır
    (arşiv durumu kesindir; pasif sonradan yazıldığı için aktifi ezer).
  * Kombinasyon başına (ilçe x mülk x işlem x durum) bir kez yazar ve
    startkey_ofis_cekim_log'a sonuç satırı bırakır.
  * DEVAM EDEBİLİR: son 24 saatte "tamam" biten kombinasyonlar (aynı ilan
    başlangıç tarihiyle) atlanır; YENIDEN=true ile hepsi baştan çekilir.
  * Süre sınırına (MAX_DAKIKA) yaklaşınca düzgünce durur — aynı işi tekrar
    çalıştırınca kalan yerden devam eder.
  * Herhangi bir kombinasyon "eksik" kalırsa ya da sınama başarısızsa
    çıkış kodu 1 (sessizce yeşil tik almaz).

ORTAM DEĞİŞKENLERİ (workflow girdileri): ILAN_BASLANGIC (varsayılan
2025-01-01), ILCELER ("hepsi" veya virgüllü ilçe adları), YENIDEN
(true/false), MAX_DAKIKA (varsayılan 330), SADECE_SINAMA (true/false).
Kimlik bilgileri revy_sync.py ile aynı GitHub Secrets (yeni secret gerekmez).
"""

import os
import sys
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
CORE_DIR = ROOT_DIR / "core"
for p in (ROOT_DIR, CORE_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

TABLO = "startkey_ofis_ilanlar"
LOG_TABLO = "startkey_ofis_cekim_log"
MULKLER = ["konut", "ticari", "arsa"]
ISLEMLER = ["satilik", "kiralik"]
DURUMLAR = ["aktif", "pasif"]          # SIRA ÖNEMLİ: pasif sonra → aktifi ezer
SINAMA_ILCESI = "Balçova"


def _log(msg):
    print(msg, flush=True)


def _bool(ad, varsayilan=False):
    v = os.environ.get(ad)
    if v is None or v == "":
        return varsayilan
    return v.strip().lower() in ("1", "true", "evet", "yes")


def _norm(s):
    return str(s).strip().lower().replace("i̇", "i").replace("ı", "i")


def ilce_secimi(ilce_sozlugu, istek):
    """ilce_sozlugu: {ad: id}. istek: 'hepsi' | 'A, B'. Bilinmeyen ad → hata."""
    istek = (istek or "hepsi").strip()
    if istek.lower() == "hepsi":
        return dict(ilce_sozlugu)
    harita = {_norm(a): a for a in ilce_sozlugu}
    secilen, bilinmeyen = {}, []
    for parca in istek.split(","):
        ad = _norm(parca)
        if not ad:
            continue
        if ad in harita:
            secilen[harita[ad]] = ilce_sozlugu[harita[ad]]
        else:
            bilinmeyen.append(parca.strip())
    if bilinmeyen:
        raise ValueError(f"Bilinmeyen ilçe adı: {', '.join(bilinmeyen)}")
    return secilen


def kombinasyon_listesi(ilceler):
    return [
        (durum, ilce_ad, ilce_id, mulk, islem)
        for durum in DURUMLAR
        for ilce_ad, ilce_id in ilceler.items()
        for mulk in MULKLER
        for islem in ISLEMLER
    ]


def biten_kombinasyonlar(supa, ilan_baslangic, simdi):
    """Son 24 saatte 'tamam' biten (ilce, mulk, islem, durum) kümesi."""
    esik = (simdi - timedelta(hours=24)).isoformat()
    resp = (
        supa.table(LOG_TABLO)
        .select("ilce,mulk,islem,durum,ilan_baslangic,sonuc,created_at")
        .eq("sonuc", "tamam")
        .eq("ilan_baslangic", str(ilan_baslangic))
        .gte("created_at", esik)
        .execute()
    )
    return {
        (r["ilce"], r["mulk"], r["islem"], r["durum"])
        for r in (resp.data or [])
        if r.get("mulk") and r.get("durum") in DURUMLAR
    }


def toplu_yaz(supa, kayitlar, parca=300, deneme=3, uyku=time.sleep):
    """Kayıtları upsert eder. Döner: (yazilan, hata_mesaji|None)."""
    yazilan = 0
    for i in range(0, len(kayitlar), parca):
        dilim = kayitlar[i:i + parca]
        for d in range(deneme):
            try:
                supa.table(TABLO).upsert(dilim, on_conflict="ilan_url").execute()
                yazilan += len(dilim)
                break
            except Exception as e:  # noqa: BLE001
                if d == deneme - 1:
                    return yazilan, f"yazma hatası ({type(e).__name__}): {str(e)[:200]}"
                uyku(2 * (d + 1))
    return yazilan, None


def log_yaz(supa, calisma_id, ozet):
    satir = {k: v for k, v in ozet.items()}
    satir["calisma_id"] = calisma_id
    try:
        supa.table(LOG_TABLO).insert(satir).execute()
    except Exception as e:  # noqa: BLE001
        _log(f"⚠️ Log satırı yazılamadı ({type(e).__name__}): {str(e)[:150]}")


def ozet_markdown(calisma_id, bas, bit, sonuclar, sinama_msg, durdu, sure_dk):
    toplam = len(sonuclar)
    tamam = [s for s in sonuclar if s["sonuc"] == "tamam"]
    eksik = [s for s in sonuclar if s["sonuc"] == "eksik"]
    sk = sum(s["startkey_satir"] for s in sonuclar)
    gevsek = sum(s["gevsek_satir"] for s in sonuclar)
    ham = sum(s["ham_satir"] for s in sonuclar)
    satirlar = [
        f"## Startkey Ofis Verisi Çekimi ({calisma_id})",
        f"- İlan tarihi aralığı: **{bas} → {bit}**",
        f"- {sinama_msg}",
        f"- Bu çalışmada işlenen kombinasyon: **{toplam}** (tamam {len(tamam)}, eksik {len(eksik)})",
        f"- İndirilen ham satır (tüm markalar): **{ham:,}**; Startkey satırı: **{sk:,}**; gevşek eşleşen: **{gevsek:,}**",
        f"- Süre: {sure_dk:.1f} dk" + (" — **süre sınırında durdu, işi tekrar çalıştır**" if durdu else ""),
    ]
    if eksik:
        satirlar.append("\n### Eksik kalan kombinasyonlar")
        for s in eksik:
            satirlar.append(f"- {s['durum']} / {s['ilce']} / {s['mulk']} / {s['islem']}: {s['detay']['hatalar'][:2]}")
    belirsiz = [s for s in sonuclar if s["belirsiz_bos"]]
    if belirsiz:
        satirlar.append(f"\n### Belirsiz-boş yanıt alan kombinasyon: {len(belirsiz)} (örnek yanıt log tablosunda)")
    tek = [s for s in sonuclar if s["tek_gun_limit"]]
    if tek:
        satirlar.append(f"\n### ⚠️ Tek günde 1000 satıra çarpan kombinasyon: {len(tek)}")
    return "\n".join(satirlar)


def main(oturum_fabrikasi=None, supa=None, ayarlar=None, cevre=None,
         uyku=time.sleep, bekleme=None, simdi_fn=None):
    """Test edilebilirlik için bağımlılıklar parametre olarak verilebilir."""
    cevre = cevre if cevre is not None else os.environ
    simdi_fn = simdi_fn or (lambda: datetime.now(timezone.utc))
    import revy_pazar_cek as rpc
    from core import startkey_ofis_cek as motor

    if bekleme is None:
        bekleme = motor.BEKLEME_SN

    ilan_baslangic = date.fromisoformat((cevre.get("ILAN_BASLANGIC") or "2025-01-01").strip())
    ilan_bitis = date.today()
    yeniden = (cevre.get("YENIDEN") or "").strip().lower() in ("1", "true", "evet", "yes")
    sadece_sinama = (cevre.get("SADECE_SINAMA") or "").strip().lower() in ("1", "true", "evet", "yes")
    max_dk = float(cevre.get("MAX_DAKIKA") or 330)

    ilceler = ilce_secimi(rpc.IZMIR_ILCELER, cevre.get("ILCELER"))

    if supa is None or ayarlar is None:
        from revy_sync import ayarlari_oku, get_supabase
        ayarlar = ayarlar or ayarlari_oku()
        supa = supa or get_supabase()

    if oturum_fabrikasi is None:
        def oturum_fabrikasi():
            return motor.RevyOturum(
                lambda: rpc.selenium_cookie_al(
                    kullanici=ayarlar.get("revy1_kullanici"),
                    sifre=ayarlar.get("revy1_sifre"),
                    giris_url=ayarlar.get("revy_giris_url", "https://revy.com.tr"),
                    headless=True,
                    progress_cb=None,
                ),
                log=_log, uyku=uyku,
            )

    calisma_id = uuid.uuid4().hex[:8]
    baslangic_zamani = simdi_fn()
    t0 = time.time()
    _log(f"▶️ Çalışma {calisma_id}: ilan tarihi {ilan_baslangic} → {ilan_bitis}, "
         f"{len(ilceler)} ilçe, yeniden={yeniden}, sadece_sinama={sadece_sinama}")

    oturum = oturum_fabrikasi()

    # ── 1) Kendi kendini sınama ───────────────────────────────────────
    sinama_ilce_id = rpc.IZMIR_ILCELER[SINAMA_ILCESI]
    ok, mesajlar = True, []
    for sinama_durumu in ("aktif", "pasif"):       # pasif = arşiv sekmesi (farklı parametre)
        ok_i, msg_i = motor.kendi_kendini_sinama(
            oturum, sinama_ilce_id, log=_log, uyku=uyku, bekleme=bekleme, durum=sinama_durumu)
        ok = ok and ok_i
        mesajlar.append(msg_i)
        if not ok_i:
            break
    sinama_msg = " | ".join(mesajlar)
    _log(("✅ " if ok else "❌ ") + sinama_msg)
    log_yaz(supa, calisma_id, {
        "ilce": SINAMA_ILCESI, "mulk": "konut", "islem": "satilik", "durum": "sinama",
        "ilan_baslangic": str(ilan_baslangic), "ilan_bitis": str(ilan_bitis),
        "sonuc": "tamam" if ok else "eksik",
        "detay": {"mesaj": sinama_msg},
    })
    if not ok:
        _ozet_yaz(ozet_markdown(calisma_id, ilan_baslangic, ilan_bitis, [], "❌ " + sinama_msg, False, (time.time() - t0) / 60))
        return 1
    if sadece_sinama:
        _log("ℹ️ SADECE_SINAMA: veri çekilmedi.")
        _ozet_yaz(ozet_markdown(calisma_id, ilan_baslangic, ilan_bitis, [], "✅ " + sinama_msg, False, (time.time() - t0) / 60))
        return 0

    # ── 2) Veri çekimi ───────────────────────────────────────────────
    atla = set() if yeniden else biten_kombinasyonlar(supa, ilan_baslangic, baslangic_zamani)
    kombler = kombinasyon_listesi(ilceler)
    _log(f"📋 {len(kombler)} kombinasyon, {len(atla)} tanesi son 24 saatte tamamlanmış (atlanacak).")

    cekim_zamani = baslangic_zamani.isoformat()
    sonuclar, durdu = [], False
    for sira, (durum, ilce_ad, ilce_id, mulk, islem) in enumerate(kombler, 1):
        if (ilce_ad, mulk, islem, durum) in atla:
            continue
        if (time.time() - t0) / 60 > max_dk:
            durdu = True
            _log(f"⏱️ Süre sınırına ({max_dk:.0f} dk) ulaşıldı; durduruluyor.")
            break

        try:
            sonuc = motor.kombinasyon_cek(
                oturum, ilce_ad, ilce_id, mulk, islem, durum,
                ilan_baslangic, ilan_bitis, cekim_zamani, uyku=uyku, bekleme=bekleme)
        except motor.OturumHatasi as e:
            _log(f"❌ Oturum hatası, iş durduruluyor: {e}")
            sonuc = None
        if sonuc is None:
            sonuclar.append({
                "ilce": ilce_ad, "mulk": mulk, "islem": islem, "durum": durum,
                "ilan_baslangic": str(ilan_baslangic), "ilan_bitis": str(ilan_bitis),
                "istek_sayisi": 0, "ham_satir": 0, "tekil_satir": 0, "startkey_satir": 0,
                "gevsek_satir": 0, "url_yok": 0, "en_derin_bolme": 0, "hata_sayisi": 1,
                "belirsiz_bos": 0, "tek_gun_limit": 0, "sonuc": "eksik",
                "detay": {"hatalar": [("-", "-", "oturum hatası")]},
            })
            log_yaz(supa, calisma_id, sonuclar[-1])
            break

        ozet = sonuc["ozet"]
        if sonuc["kayitlar"]:
            yazilan, hata = toplu_yaz(supa, sonuc["kayitlar"], uyku=uyku)
            if hata:
                ozet["sonuc"] = "eksik"
                ozet["hata_sayisi"] += 1
                ozet["detay"]["hatalar"].append(("-", "-", hata))
        log_yaz(supa, calisma_id, ozet)
        sonuclar.append(ozet)
        _log(f"[{sira}/{len(kombler)}] {durum:5s} {ilce_ad:12s} {mulk:6s} {islem:7s} "
             f"ham={ozet['ham_satir']:5d} startkey={ozet['startkey_satir']:4d} "
             f"istek={ozet['istek_sayisi']:3d} → {ozet['sonuc']}")

    sure_dk = (time.time() - t0) / 60
    md = ozet_markdown(calisma_id, ilan_baslangic, ilan_bitis, sonuclar, "✅ " + sinama_msg, durdu, sure_dk)
    _log("\n" + md)
    _ozet_yaz(md)

    eksik = [s for s in sonuclar if s["sonuc"] == "eksik"]
    if eksik:
        _log(f"❌ {len(eksik)} kombinasyon EKSİK kaldı — işi tekrar çalıştır (tamamlananlar atlanır).")
        return 1
    return 0


def _ozet_yaz(md):
    yol = os.environ.get("GITHUB_STEP_SUMMARY")
    if yol:
        try:
            with open(yol, "a", encoding="utf-8") as f:
                f.write(md + "\n")
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
