"""
pazar_bildirim_job.py
-----------------------
FAZ 2 (27.09.2026): FSBO İlanları ve Startkey İlanları için günlük toplu
"bölgede bugün yeni ilan çıktı" push bildirimlerini gönderen, GitHub
Actions üzerinden GÜNDE BİR KERE otomatik çalışan başsız (headless) iş.

izmir_pazar_sync_job.py'nin GÜNLÜK SENKRONİZASYONU BİTTİKTEN HEMEN SONRA,
AYNI GitHub Actions job'ında (aynı runner'da, aynı .streamlit/secrets.toml
ile) çalıştırılır — izmir_pazar_ilanlar tablosu o günün taze verisiyle
dolu olsun diye (asıl mantık core/bildirim_tetikleyici.py'deki
pazar_yeni_ilan_bildirimleri_gonder()'de; bkz. o dosyanın modül üstü notu).

Meltem'in AskUserQuestion ile onayladığı kapsam: SADECE "yeni ilan"
bildirimi — fiyat düşüşü tespiti Faz 3'e bırakıldı; FSBO ve Startkey için
AYRI bildirimler (birleşik tek özet YOK).

Kimlik bilgileri: bu iş Revy'ye HİÇ giriş yapmıyor (sadece
izmir_pazar_ilanlar tablosunu okuyup push gönderiyor) — sadece mevcut
SUPABASE_URL / SUPABASE_SECRET_KEY secret'ları (izmir_pazar_sync.yml'de
zaten yazılan .streamlit/secrets.toml üzerinden) ve push imzası için YENİ
bir secret: VAPID_PRIVATE_KEY (core/push_bildirim.py'nin headless
fallback'i — Streamlit Cloud'daki [vapid] private_key ile AYNI değer).

Elle test etmek için: python pazar_bildirim_job.py
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
CORE_DIR = ROOT_DIR / "core"
for p in (ROOT_DIR, CORE_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from core.bildirim_tetikleyici import pazar_yeni_ilan_bildirimleri_gonder  # noqa: E402


def _progress_cb(msg):
    print(msg, flush=True)


def main():
    sonuc = pazar_yeni_ilan_bildirimleri_gonder(progress_cb=_progress_cb)
    print(f"🏁 Özet: {sonuc}")


if __name__ == "__main__":
    main()
