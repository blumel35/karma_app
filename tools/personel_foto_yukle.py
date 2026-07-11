"""
tools/personel_foto_yukle.py
─────────────────────────────────────────────────────────────────────────
TEK SEFERLİK migration script'i. Yerel `zeta_personel_fotolar/` klasöründeki
fotoğrafları Supabase Storage'daki "danismanlar" bucket'ına yükler ve
`personel_foto_url` tablosuna (user_key -> public URL) yazar.

Çalıştırma:
    cd karma_app
    python tools/personel_foto_yukle.py

Önkoşul:
  - `personel_foto_url_sema.sql`'i Supabase SQL Editor'de çalıştırmış olman gerekiyor.
  - .streamlit/secrets.toml içinde SUPABASE_URL ve service/secret key tanımlı olmalı
    (auth.py'nin foto_yukle() fonksiyonundaki aynı service key mantığı kullanılıyor,
    çünkü RLS politikaları normal anon key ile storage yazımını engelleyebilir).

Bu script'i istediğin kadar tekrar çalıştırabilirsin — upsert=True olduğu için
var olan dosyaların üzerine güvenle yazar, hata vermez.
"""

import sys
import os

# karma_app kökünü path'e ekle (core/ modüllerine erişim için)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

import toml
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────
# SECRETS OKU (streamlit çalıştırmadan, doğrudan dosyadan)
# ─────────────────────────────────────────────────────────────────────────
def _secrets_yukle():
    _root = Path(__file__).parent.parent
    secrets_path = _root / ".streamlit" / "secrets.toml"
    if not secrets_path.exists():
        raise FileNotFoundError(f"secrets.toml bulunamadı: {secrets_path}")
    return toml.load(secrets_path)


def _get_supa_service():
    from supabase import create_client
    secrets = _secrets_yukle()

    url = (
        os.environ.get("SUPABASE_URL")
        or secrets.get("SUPABASE_URL", "")
        or secrets.get("supabase", {}).get("url", "")
    )
    key = (
        os.environ.get("SUPABASE_SERVICE_KEY")
        or secrets.get("supabase", {}).get("secret_key", "")
        or secrets.get("supabase", {}).get("service_key", "")
    )
    if not url or not key:
        raise ValueError(
            "SUPABASE_URL / service_key secrets.toml'de bulunamadı. "
            "auth.py'deki _get_supa(use_service_key=True) ile aynı alanları kontrol et."
        )
    return create_client(url, key)


# ─────────────────────────────────────────────────────────────────────────
# ANA İŞLEM
# ─────────────────────────────────────────────────────────────────────────
def main():
    from core.personel_manager import load_personel_listesi, resolve_personel_photo

    BUCKET = "danismanlar"
    STORAGE_KLASOR = "personel"  # bucket içinde personel/ altında tutulacak

    print("Personel listesi yükleniyor...")
    df = load_personel_listesi(force_reload=True)
    if df.empty:
        print("⚠️  Personel listesi boş — zeta_personel_listesi.xlsx bulunamadı veya boş.")
        return

    print(f"{len(df)} aktif personel bulundu. Supabase'e bağlanılıyor...")
    supa = _get_supa_service()

    basarili, atlanan, hatali = 0, 0, 0

    for _, row in df.iterrows():
        row_dict = row.to_dict()
        user_key = str(row_dict.get("user_key", "") or "").strip()
        ad_soyad = str(row_dict.get("ad_soyad", "") or "").strip()
        telefon = str(row_dict.get("telefon", "") or "").strip()
        mail = str(row_dict.get("email", "") or row_dict.get("mail", "") or "").strip()

        if not user_key:
            print(f"  ⏭  Atlandı (user_key yok): {ad_soyad}")
            atlanan += 1
            continue

        foto_yolu = resolve_personel_photo(row_dict)
        if not foto_yolu or not os.path.exists(foto_yolu):
            print(f"  ⏭  Atlandı (fotoğraf bulunamadı): {ad_soyad} ({user_key})")
            atlanan += 1
            continue

        try:
            ext = Path(foto_yolu).suffix.lower().lstrip(".") or "jpg"
            mime = {
                "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "png": "image/png", "webp": "image/webp",
            }.get(ext, "image/jpeg")

            storage_path = f"{STORAGE_KLASOR}/{user_key}.{ext}"

            with open(foto_yolu, "rb") as f:
                raw = f.read()

            supa.storage.from_(BUCKET).upload(
                path=storage_path,
                file=raw,
                file_options={"content-type": mime, "upsert": "true"},
            )
            public_url = supa.storage.from_(BUCKET).get_public_url(storage_path)

            supa.table("personel_foto_url").upsert({
                "user_key": user_key,
                "ad_soyad": ad_soyad,
                "foto_url": public_url,
                "telefon": telefon,
                "mail": mail,
            }).execute()

            print(f"  ✅ {ad_soyad} ({user_key}) → {public_url}")
            basarili += 1

        except Exception as e:
            print(f"  ❌ Hata — {ad_soyad} ({user_key}): {e}")
            hatali += 1

    print()
    print(f"Tamamlandı: {basarili} yüklendi, {atlanan} atlandı, {hatali} hata.")


if __name__ == "__main__":
    main()
