# tools/portfoy_gorunurluk_backfill.py
# -*- coding: utf-8 -*-
"""
Portföy Görünürlük Backfill Scripti

Amaç:
- Mevcut portfoyler tablosundaki kayıtları geriye dönük sınıflandırmak.
- core/portfoy_gorunurluk.py içindeki sınıflandırma motorunu kullanır.
- Mail içeriği / özet / özel kriter / ilan_linki alanlarından linkleri çıkarır.
- izmir_pazar_ilanlar tablosu varsa merkezi ilan eşleşmesi yapar.
- Sonucu portfoyler tablosundaki yeni alanlara yazar.

Kullanım:

1) Önce test:
python tools\\portfoy_gorunurluk_backfill.py --dry-run --limit 20

2) Sonra gerçek güncelleme:
python tools\\portfoy_gorunurluk_backfill.py --apply

3) Sadece eksik / teyit gerekli kayıtları güncellemek için:
python tools\\portfoy_gorunurluk_backfill.py --apply --only-missing
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────
# Proje kökünü path'e ekle
# ─────────────────────────────────────────────

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from core.supabase_client import get_client
from core.portfoy_gorunurluk import (
    siniflandir_portfoy,
    supabase_update_payload,
    gorunurluk_label,
)


# ─────────────────────────────────────────────
# Supabase yardımcıları
# ─────────────────────────────────────────────

def fetch_all(
    table_name: str,
    select: str = "*",
    page_size: int = 1000,
    max_rows: Optional[int] = None,
    order_col: Optional[str] = None,
    desc: bool = True,
) -> List[Dict[str, Any]]:
    """
    Supabase tablosunu sayfa sayfa çeker.
    Limit takılmasını önlemek için .range kullanır.
    """
    client = get_client()
    rows: List[Dict[str, Any]] = []
    start = 0

    while True:
        end = start + page_size - 1

        q = client.table(table_name).select(select)

        if order_col:
            q = q.order(order_col, desc=desc)

        q = q.range(start, end)

        try:
            resp = q.execute()
        except Exception as e:
            print(f"⚠️ {table_name} okunamadı: {e}")
            return rows

        batch = resp.data or []
        if not batch:
            break

        rows.extend(batch)

        if max_rows and len(rows) >= max_rows:
            rows = rows[:max_rows]
            break

        if len(batch) < page_size:
            break

        start += page_size

    return rows


def fetch_portfoyler(
    page_size: int = 1000,
    max_rows: Optional[int] = None,
    only_missing: bool = False,
) -> List[Dict[str, Any]]:
    """
    Portföy kayıtlarını çeker.
    only_missing True ise daha önce sınıflandırılmamış veya teyit_gerekli kalanları hedefler.
    """
    rows = fetch_all(
        table_name="portfoyler",
        select="*",
        page_size=page_size,
        max_rows=max_rows,
        order_col="olusturma_tarihi",
        desc=True,
    )

    if not only_missing:
        return rows

    filtered = []
    for r in rows:
        gor = (r.get("portfoy_gorunurluk") or "").strip()
        link_sayisi = r.get("link_sayisi")

        if not gor or gor == "teyit_gerekli" or link_sayisi is None:
            filtered.append(r)

    return filtered


def fetch_merkezi_ilanlar(page_size: int = 1000) -> List[Dict[str, Any]]:
    """
    Merkezi ilan tablosunu çeker.
    Tablo yoksa veya hata olursa boş liste döner.
    """
    rows = fetch_all(
        table_name="izmir_pazar_ilanlar",
        select="*",
        page_size=page_size,
        max_rows=None,
        order_col=None,
    )

    if rows:
        print(f"✅ Merkezi ilan tablosu yüklendi: {len(rows)} kayıt")
    else:
        print("ℹ️ Merkezi ilan tablosu boş veya okunamadı. Sınıflandırma linksiz/fuzzy eşleşmesiz yapılacak.")

    return rows


def update_portfoy(row_id: Any, payload: Dict[str, Any]) -> bool:
    """
    Tek portföy kaydını günceller.
    """
    if not row_id:
        return False

    try:
        get_client().table("portfoyler").update(payload).eq("id", row_id).execute()
        return True
    except Exception as e:
        print(f"❌ Güncelleme hatası id={row_id}: {e}")
        return False


# ─────────────────────────────────────────────
# Görsel / rapor yardımcıları
# ─────────────────────────────────────────────

def short(v: Any, n: int = 80) -> str:
    s = "" if v is None else str(v)
    s = s.replace("\n", " ").replace("\r", " ").strip()
    return s[:n] + ("..." if len(s) > n else "")


def print_sample_result(row: Dict[str, Any], sonuc: Dict[str, Any], idx: int) -> None:
    """
    Dry-run için örnek çıktı.
    """
    print("-" * 90)
    print(f"{idx}. ID: {row.get('id')}")
    print(f"Danışman : {short(row.get('talep_eden_danisan'))}")
    print(f"Özet     : {short(row.get('ozet') or row.get('mail_konusu'))}")
    print(f"İlçe     : {row.get('ilce') or row.get('ilceler')}")
    print(f"Fiyat    : {row.get('fiyat')}")
    print(f"Link     : {short(row.get('ilan_linki'), 120)}")
    print()
    print(f"Sonuç    : {sonuc.get('portfoy_gorunurluk')} | {gorunurluk_label(sonuc.get('portfoy_gorunurluk'))}")
    print(f"Güven    : {sonuc.get('siniflandirma_guveni')}")
    print(f"Link Sayısı: {sonuc.get('link_sayisi')}")
    print(f"Kapalı Öncelik: {sonuc.get('kapali_oncelik')}")
    print(f"Paylaşım Onayı: {sonuc.get('paylasim_onayi_var')}")
    print(f"Merkezi Eşleşme: {sonuc.get('merkezi_ilan_eslesme')}")
    print(f"Merkezi İlan ID: {sonuc.get('merkezi_ilan_id')}")
    print(f"Debug: {sonuc.get('_debug')}")


# ─────────────────────────────────────────────
# Ana çalışma
# ─────────────────────────────────────────────

def run_backfill(
    apply: bool = False,
    dry_run: bool = True,
    limit: Optional[int] = None,
    page_size: int = 1000,
    only_missing: bool = False,
    sample_count: int = 20,
) -> None:
    """
    Backfill ana akışı.
    """
    print("=" * 90)
    print("PORTFÖY GÖRÜNÜRLÜK BACKFILL")
    print("=" * 90)

    if apply:
        dry_run = False

    print(f"Mod              : {'GERÇEK GÜNCELLEME' if apply else 'DRY-RUN / TEST'}")
    print(f"Limit            : {limit or 'Yok'}")
    print(f"Page size        : {page_size}")
    print(f"Only missing     : {only_missing}")
    print()

    print("1) Merkezi ilanlar yükleniyor...")
    merkezi_ilanlar = fetch_merkezi_ilanlar(page_size=page_size)

    print()
    print("2) Portföyler yükleniyor...")
    portfoyler = fetch_portfoyler(
        page_size=page_size,
        max_rows=limit,
        only_missing=only_missing,
    )
    print(f"✅ İşlenecek portföy sayısı: {len(portfoyler)}")
    print()

    if not portfoyler:
        print("İşlenecek kayıt yok.")
        return

    counter = Counter()
    guven_counter = Counter()
    updated = 0
    failed = 0

    print("3) Sınıflandırma başlıyor...")
    print()

    for idx, row in enumerate(portfoyler, start=1):
        sonuc = siniflandir_portfoy(row, merkezi_ilanlar=merkezi_ilanlar)
        payload = supabase_update_payload(sonuc)

        gor = sonuc.get("portfoy_gorunurluk") or "bilinmiyor"
        guven = sonuc.get("siniflandirma_guveni") or "bilinmiyor"

        counter[gor] += 1
        guven_counter[guven] += 1

        if dry_run and idx <= sample_count:
            print_sample_result(row, sonuc, idx)

        if apply:
            ok = update_portfoy(row.get("id"), payload)
            if ok:
                updated += 1
            else:
                failed += 1

        if idx % 100 == 0:
            print(f"İşlenen: {idx}/{len(portfoyler)}")

    print()
    print("=" * 90)
    print("ÖZET")
    print("=" * 90)

    print("Görünürlük dağılımı:")
    for k, v in counter.most_common():
        print(f"  {k:28} {v:5}  {gorunurluk_label(k)}")

    print()
    print("Güven dağılımı:")
    for k, v in guven_counter.most_common():
        print(f"  {k:10} {v:5}")

    if apply:
        print()
        print(f"✅ Güncellenen kayıt: {updated}")
        print(f"❌ Hatalı kayıt     : {failed}")
    else:
        print()
        print("ℹ️ Bu bir dry-run idi. Veritabanına yazılmadı.")
        print("Gerçek güncelleme için:")
        print("python tools\\portfoy_gorunurluk_backfill.py --apply")

    print("=" * 90)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Portföy görünürlük backfill scripti")

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Gerçek güncelleme yapar. Bu parametre yoksa dry-run çalışır.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test modu. Veritabanına yazmaz.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="İşlenecek maksimum portföy sayısı. Örn: --limit 20",
    )

    parser.add_argument(
        "--page-size",
        type=int,
        default=1000,
        help="Supabase sayfa boyutu. Varsayılan 1000.",
    )

    parser.add_argument(
        "--only-missing",
        action="store_true",
        help="Sadece sınıflandırması eksik / teyit gerekli kayıtları işler.",
    )

    parser.add_argument(
        "--sample-count",
        type=int,
        default=20,
        help="Dry-run modunda detaylı gösterilecek örnek kayıt sayısı.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    run_backfill(
        apply=args.apply,
        dry_run=not args.apply,
        limit=args.limit,
        page_size=args.page_size,
        only_missing=args.only_missing,
        sample_count=args.sample_count,
    )