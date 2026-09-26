# core/bildirim_tetikleyici.py
# -*- coding: utf-8 -*-
"""
Talep/Portföy eklendiğinde iki bildirim türünü tetikleyen ortak katman
(23.09.2026 — Meltem: "uzmanlık bölgelerim ilçe bazlı bildirim olsa
yeterli fikrini sevdim... zeta etkileşimleri olsun istiyorum (bölgeden
bağımsız) örneğin ömer çiğli de yeni bir portföy ilanı paylaştı. sinan
buda için bir alıcı talebi girdi gibi.").

Planlanan 4 bildirim kaynağından (A: Uzmanlık Bölgem, B: Startkey
İlanları, C: FSBO İlanları, D: Zeta Etkileşimleri) bu dosya SADECE A ve
D'yi kapsıyor — Meltem'in onayladığı sıralama gereği ("A+D önce, sonra
B+C"). B ve C (günlük toplu FSBO/Startkey bildirimi + fiyat düşüşü)
ayrı bir turda core/izmir_pazar_sync.py'ye bağlanacak.

FAZ 1 kararı (Meltem onayı — "tek anahtar, hepsi birlikte"): 4 kaynak
için AYRI AÇMA/KAPAMA tercihi YOK — mevcut tek "Telefon Bildirimlerini
Aç" anahtarını (core/push_bildirim.py) açmış olan HERKES, ilgili
olay gerçekleştiğinde otomatik olarak bildirim alır. İleride ihtiyaç
çıkarsa (Meltem'in "sırayla başlayalım" tercihiyle tutarlı) kaynak
bazlı açma/kapama ayrı bir adımda eklenebilir.

talep_portfoy_bildirim_gonder(), core/danisman_ortak.py'deki
ekle_dialog() içinde, bir kayıt Supabase'e BAŞARIYLA eklendikten HEMEN
SONRA çağrılır. BİLEREK sadece MANUEL ekleme akışını kapsıyor (temiz/
güvenilir "kim ekledi" ve "hangi ilçe" bilgisi burada var) — mail
otomasyonuyla (core/mail_job.py) otomatik ayrıştırılan kayıtlar için
aynı bildirim AYRI, sonraki bir adımda eklenebilir (oradaki "kim"
bilgisi mail başlığından geliyor, buradaki kadar güvenilir/normalize
değil — küçük adımlarla ilerleme kararına uygun, bilerek şimdi
kapsanmadı).

Bildirim gönderimi BEST-EFFORT'tur — herhangi bir hata (Supabase
sorgusu, push gönderimi) SESSİZCE yutulur; asıl kayıt ekleme akışını
ASLA bozmamalı veya kullanıcıya hata göstermemeli (kayıt zaten
başarıyla eklenmiş oluyor, bildirim ikincil bir katman).
"""

from core.supabase_client import get_client
from core.push_bildirim import bildirim_gonder

supabase = get_client()


def _ilce_normalize(ilce):
    return (ilce or "").strip().casefold()


def _uzmanlik_bolgesi_eslesenler(ilceler):
    """Verilen ilçe listesinden EN AZ biriyle Uzmanlık Bölgesi'nde
    eşleşen danışmanların {kullanici: eşleşen_ilce} sözlüğünü döner.
    Bir danışmanın birden fazla ilçesi eşleşse bile tek bir bildirim
    gitsin diye sadece İLK eşleşen ilçe tutulur."""
    hedef = {_ilce_normalize(i) for i in (ilceler or []) if i}
    if not hedef:
        return {}
    try:
        resp = supabase.table("uzmanlik_bolgeleri").select("kullanici, ilce").execute()
    except Exception:
        return {}
    eslesenler = {}
    for row in (resp.data or []):
        kullanici = (row.get("kullanici") or "").strip()
        ilce = row.get("ilce") or ""
        if not kullanici or _ilce_normalize(ilce) not in hedef:
            continue
        if kullanici not in eslesenler:
            eslesenler[kullanici] = ilce
    return eslesenler


def _push_abone_kullanicilar():
    """Telefon bildirimini açmış (en az bir cihazda kayıtlı aboneliği
    olan) TÜM danışmanların kullanıcı adlarının tekrarsız kümesini
    döner — Zeta Etkileşimleri'nin (D) hedef kitlesi budur."""
    try:
        resp = supabase.table("push_abonelikleri").select("kullanici").execute()
    except Exception:
        return set()
    return {(r.get("kullanici") or "").strip() for r in (resp.data or []) if r.get("kullanici")}


def talep_portfoy_bildirim_gonder(kayit_tipi, ilceler, olusturan, islem_tipi=None):
    """Yeni bir talep/portföy kaydı BAŞARIYLA eklendikten sonra çağrılır.

    kayit_tipi: "Talep" | "Portföy"
    ilceler:    o kayıtta seçilen ilçe(ler) — liste, birden fazla olabilir
    olusturan:  kaydı ekleyen danışmanın kullanıcı adı (su_anki_danisman())
                — kendi eklediği kayıt için KENDİSİNE bildirim gitmez.
    islem_tipi: "Satılık" | "Kiralık" (opsiyonel, A mesajına eklenir)

    Hiçbir şey döndürmez, hiçbir hatayı dışarı sızdırmaz (best-effort)."""
    try:
        _gonder_ic(kayit_tipi, ilceler, olusturan, islem_tipi)
    except Exception:
        pass


def _gonder_ic(kayit_tipi, ilceler, olusturan, islem_tipi):
    ilceler = [i for i in (ilceler or []) if i]
    if not ilceler:
        return
    olusturan_norm = (olusturan or "").strip().casefold()
    portfoy_mu = (kayit_tipi == "Portföy")
    tur_adi = "portföy" if portfoy_mu else "talep"
    ilk_ilce = ilceler[0]
    islem_ek = f"{islem_tipi} " if islem_tipi else ""

    # ── A) Uzmanlık Bölgesi eşleşenler — bölge bazlı, isimsiz/nesnel metin.
    # DEĞİŞTİ (26.09.2026, Meltem: "yazı karakteri renk değişse vs dikkat
    # çekici olsun istiyorum"): sistem bildirimlerinin yazı tipi/rengi
    # Android tarafından sabitlendiği için (platform sınırı — bkz.
    # sw.js'teki not), tek kontrol edebildiğimiz "renk" başlıktaki emoji —
    # bölge eşleşmesi 📍 ile işaretlendi, bildirim listesinde bir bakışta
    # ayırt edilsin diye.
    eslesenler = _uzmanlik_bolgesi_eslesenler(ilceler)
    bildirilenler = set()
    for kullanici, ilce in eslesenler.items():
        if kullanici.strip().casefold() == olusturan_norm:
            continue
        bildirim_gonder(
            kullanici,
            "📍 Uzmanlık Bölgeniz",
            f"Uzmanlık bölgeniz olan {ilce} bölgesinde 1 adet {islem_ek}{tur_adi} yayınlandı.",
        )
        bildirilenler.add(kullanici.strip().casefold())

    # ── D) Zeta Etkileşimleri — bölgeden BAĞIMSIZ, telefon bildirimini
    # açmış TÜM danışmanlara (A'da zaten bildirim alanlar HARİÇ — aynı
    # olay için aynı kişiye 2. bildirim gitmesin diye).
    if portfoy_mu:
        govde = f"{olusturan} {ilk_ilce} bölgesinde yeni bir portföy ilanı paylaştı."
    else:
        govde = f"{olusturan} {ilk_ilce} bölgesi için bir alıcı talebi girdi."

    for kullanici in _push_abone_kullanicilar():
        kullanici_norm = kullanici.strip().casefold()
        if kullanici_norm == olusturan_norm or kullanici_norm in bildirilenler:
            continue
        bildirim_gonder(kullanici, "🔔 Zeta Etkileşimleri", govde)
