"""
Otomatik mail çekim scripti — GitHub Actions tarafından zamanlanmış olarak
çalıştırılır (bkz. .github/workflows/mail_auto_fetch.yml).

Streamlit sunucusu ÇALIŞTIRMAZ; sadece core/mail_job.py içindeki iş
mantığını çağırır. st.secrets'ın çalışabilmesi için GitHub Actions
workflow'u, repo secret'larından bir .streamlit/secrets.toml dosyası
üretip bu script'i onun yanında çalıştırır (workflow dosyasına bakınız).

Faz 2.5 kararı:
- Otomatik çalıştırmada AI kategorizasyon başlangıçta KAPALI olmalı
  (AI_KATEGORIZASYON_AKTIF=false). Sadece ham mail çekimi otomatik yapılır.
- Bir süre (örn. 1 hafta) hatasız çalıştıktan sonra ortam değişkeni
  "true" yapılarak AI adımı da otomasyona dahil edilebilir.

Ortam değişkenleri (GitHub Actions workflow'unda ayarlanır):
  AI_KATEGORIZASYON_AKTIF = "true" / "false"  (varsayılan: false)
  AI_ISLEME_LIMITI        = "20"              (her çalıştırmada en fazla kaç kayıt)
"""

import os
import sys

# Bu script repo kökünden çalıştırılacağı için core/ modülleri doğrudan
# import edilebilir olmalı. Farklı bir konumdan çalıştırılırsa aşağıdaki
# satır repo kökünü path'e ekler.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.mail_job import run_full_mail_job  # noqa: E402


def _env_bool(name, default=False):
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "evet")


def main():
    ai_enabled = _env_bool("AI_KATEGORIZASYON_AKTIF", default=False)
    ai_limit = int(os.environ.get("AI_ISLEME_LIMITI", "20"))

    print(f"[mail_auto_job] Başladı. AI kategorizasyon: {'AÇIK' if ai_enabled else 'KAPALI'}, "
          f"limit={ai_limit}")

    def durum_callback(mesaj):
        print(f"[mail_auto_job] {mesaj}")

    try:
        sonuc = run_full_mail_job(
            ai_enabled=ai_enabled,
            ai_limit=ai_limit,
            durum_callback=durum_callback,
        )
    except Exception as e:
        print(f"[mail_auto_job] KRİTİK HATA: {type(e).__name__}: {e}")
        sys.exit(1)

    fetch = sonuc["fetch"]
    print(
        f"[mail_auto_job] Çekim tamamlandı: {fetch['yeni_kayit']} yeni kayıt, "
        f"{fetch['hata_sayisi']} hata."
    )

    if sonuc["ai_parse"]:
        parse = sonuc["ai_parse"]
        print(
            f"[mail_auto_job] AI işleme tamamlandı: {parse['alici']} alıcı/diğer, "
            f"{parse['portfoy']} portföy, {parse['hatali']} hatalı."
        )

    # Hata varsa GitHub Actions'ta koşuyu görünür şekilde "başarısız" işaretle
    # ki bildirim alasın, ama script tamamen çökmesin.
    if fetch["hata_sayisi"] > 0 or (sonuc["ai_parse"] and sonuc["ai_parse"]["hatali"] > 0):
        print("[mail_auto_job] Uyarı: bu çalıştırmada hatalar oluştu, detaylar için "
              "Supabase mail_fetch_log tablosuna bakınız.")
        sys.exit(2)

    print("[mail_auto_job] Bitti, sorun yok.")


if __name__ == "__main__":
    main()
