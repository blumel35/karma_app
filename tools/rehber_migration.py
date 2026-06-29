"""
rehber_migration.py
Excel → Supabase ilk yükleme (bir kere çalıştırılır).
"""

import os
import sys
from datetime import datetime

import pandas as pd
from supabase import create_client

# ── Ayarlar — buraya yapıştır ─────────────────────────────────────────────────
SUPABASE_URL = "https://lfpnkuldlirnljsrkkyf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxmcG5rdWxkbGlybmxqc3Jra3lmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Nzg5NzYzNSwiZXhwIjoyMDkzNDczNjM1fQ.A6KvAD3-22K5OgRPqHWuZlntZ0s_iYw9sSqDieYtTiA"

OFIS_EXCEL     = r"C:\Users\melte\Startkey_Talep_Sistemi\Startkey_Rehber\output\startkey_ofis_detaylari_bolgeli_logolu.xlsx"
DANISMAN_EXCEL = r"C:\Users\melte\Startkey_Talep_Sistemi\Startkey_Rehber\output\startkey_danismanlar_detayli.xlsx"

# ── Yardımcı ──────────────────────────────────────────────────────────────────

def kontrol():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("HATA: SUPABASE_URL ve SUPABASE_KEY boş.")
        sys.exit(1)
    if not os.path.exists(OFIS_EXCEL):
        print(f"HATA: Dosya bulunamadı: {OFIS_EXCEL}")
        print("      karma_app/ ana dizininden çalıştır: python tools/rehber_migration.py")
        sys.exit(1)
    if not os.path.exists(DANISMAN_EXCEL):
        print(f"HATA: Dosya bulunamadı: {DANISMAN_EXCEL}")
        sys.exit(1)


def temizle(deger):
    if deger is None:
        return ""
    s = str(deger).strip()
    return "" if s in ("nan", "None", "NaT") else s


def ofisleri_yukle(supa):
    print("\n── Ofisler yükleniyor... ──────────────────────────")
    df = pd.read_excel(OFIS_EXCEL).fillna("")

    kayitlar = []
    for _, row in df.iterrows():
        kayitlar.append({
            "ofis_adi":       temizle(row["ofis"]),
            "telefon":        temizle(row["telefon"]),
            "mail":           temizle(row["mail"]),
            "il":             temizle(row["il"]),
            "ilce":           temizle(row["ilce"]),
            "mahalle":        temizle(row["mahalle"]),
            "adres":          temizle(row["adres"]),
            "ofis_link":      temizle(row["ofis_link"]),
            "bolge_tipi":     temizle(row["bolge_tipi"]),
            "bolge_aksi":     temizle(row["bolge_aksi"]),
            "logo_url":       temizle(row["logo_url"]),
            "logo_dosya":     temizle(row["logo_dosya"]),
            "aktif":          True,
            "guncelleme_tar": datetime.utcnow().isoformat(),
        })

    supa.table("rehber_ofisler").upsert(kayitlar, on_conflict="ofis_adi").execute()
    print(f"  ✓ {len(kayitlar)} ofis kaydedildi.")
    return set(df["ofis"].str.strip())


def danismanlari_yukle(supa, gecerli_ofisler):
    print("\n── Danışmanlar yükleniyor... ──────────────────────")
    df = pd.read_excel(DANISMAN_EXCEL).fillna("")

    kayitlar = []
    atlanan  = []

    for _, row in df.iterrows():
        ofis = temizle(row["ofis"])
        isim = temizle(row["isim"])
        if not ofis or not isim:
            atlanan.append(f"Boş ofis/isim: {ofis} / {isim}")
            continue
        if ofis not in gecerli_ofisler:
            atlanan.append(f"Ofis tablosunda yok: {ofis}")
            continue
        kayitlar.append({
            "ofis_adi":       ofis,
            "isim":           isim,
            "unvan":          temizle(row["unvan"]),
            "telefon":        temizle(row["telefon"]),
            "mail":           temizle(row["mail"]),
            "foto_url":       temizle(row["foto_url"]),
            "profil_link":    temizle(row["profil_link"]),
            "aktif":          True,
            "guncelleme_tar": datetime.utcnow().isoformat(),
        })

    BATCH = 500
    toplam = 0
    for i in range(0, len(kayitlar), BATCH):
        batch = kayitlar[i:i+BATCH]
        supa.table("rehber_danismanlar").upsert(batch, on_conflict="ofis_adi,isim").execute()
        toplam += len(batch)
        print(f"  {toplam}/{len(kayitlar)} danışman yüklendi...")

    print(f"  ✓ {toplam} danışman kaydedildi.")
    if atlanan:
        print(f"  ⚠ Atlanan {len(atlanan)} kayıt (ilk 10):")
        for a in atlanan[:10]:
            print(f"    - {a}")


# ── Ana akış ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    kontrol()
    print("Supabase bağlanılıyor...")
    supa = create_client(SUPABASE_URL, SUPABASE_KEY)
    print(f"  ✓ Bağlandı: {SUPABASE_URL}")

    gecerli_ofisler = ofisleri_yukle(supa)
    danismanlari_yukle(supa, gecerli_ofisler)

    print("\n✅ Migration tamamlandı.")
