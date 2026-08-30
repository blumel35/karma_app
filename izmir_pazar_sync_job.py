"""
izmir_pazar_sync_job.py
------------------------
Danışmanların Uzmanlık Bölgelerim'de seçtiği ilçeler için Revy pazar
verisini (Startkey + FSBO/mülk sahibinden + diğer markalar) çekip
izmir_pazar_ilanlar merkezi tablosuna yazan, GitHub Actions üzerinden
GÜNDE BİR KERE otomatik çalışan başsız (headless) iş.

Bu, "Danışman Startkey İlanları" ve "Danışman FSBO İlanları" ekranlarının
canlı olarak okuduğu tabloyu, kimse Startkey İlanları (admin) sayfasını
elle açmasa bile taze tutar.

Taranacak ilçe kapsamı SABİT DEĞİL — core.danisman_ortak.aktif_uzmanlik_bolgeleri()
ile hangi ilçelerin en az bir danışman tarafından Uzmanlık Bölgesi olarak
seçildiği canlı okunur, sadece o ilçeler taranır (kaynak israfı yok).

Kimlik bilgileri (Revy + Supabase) revy_sync.py'nin GitHub Actions'ta zaten
kanıtlanmış ortam değişkeni desenini KULLANIR — yeni bir GitHub Secret
eklemeye gerek YOK (aynı REVY1_KULLANICI, REVY1_SIFRE, REVY_GIRIS_URL,
SUPABASE_URL, SUPABASE_SECRET_KEY secret'ları paylaşılıyor).

Elle test etmek için: python izmir_pazar_sync_job.py
"""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
CORE_DIR = ROOT_DIR / "core"
for p in (ROOT_DIR, CORE_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# revy_sync.py'nin ayarlari_oku()/get_supabase()'i: önce st.secrets, yoksa
# (GitHub Actions dahil) ortam değişkenleri — kanıtlanmış, tek kaynak.
from revy_sync import ayarlari_oku, get_supabase  # noqa: E402
from core.danisman_ortak import aktif_uzmanlik_bolgeleri  # noqa: E402
from core.izmir_pazar_sync import senkronize  # noqa: E402


def _progress_cb(msg):
    print(msg, flush=True)


def main():
    ayarlar = ayarlari_oku()
    supa = get_supabase()

    hedef_ilceler = aktif_uzmanlik_bolgeleri()
    if not hedef_ilceler:
        print(
            "ℹ️ Hiçbir danışmanın seçili Uzmanlık Bölgesi yok — "
            "taranacak ilçe bulunamadı, iş sonlandırılıyor."
        )
        return

    print(f"📋 {len(hedef_ilceler)} ilçe taranacak: {', '.join(hedef_ilceler)}")

    sonuc = senkronize(
        hedef_ilceler=hedef_ilceler,
        kullanici=ayarlar.get("revy1_kullanici"),
        sifre=ayarlar.get("revy1_sifre"),
        giris_url=ayarlar.get("revy_giris_url", "https://revy.com.tr"),
        supabase_client=supa,
        progress_cb=_progress_cb,
    )

    print(f"🏁 Bitti: {sonuc}")
    if not sonuc.get("basarili", False):
        # GitHub Actions'ta işi "başarısız" olarak işaretle — sessizce
        # yeşil tik almasın, birisi fark etsin.
        sys.exit(1)


if __name__ == "__main__":
    main()
