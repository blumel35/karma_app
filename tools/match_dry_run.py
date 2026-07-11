# tools/match_dry_run.py
# -*- coding: utf-8 -*-
"""
Alıcı → Portföy Eşleşme Motoru Dry-Run Scripti
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from core.supabase_client import get_client
from core.match_engine import eslesen_portfoyleri_bul


def safe(v: Any) -> str:
    if v is None:
        return ""
    return str(v).replace("\n", " ").replace("\r", " ").strip()


def short(v: Any, n: int = 90) -> str:
    s = safe(v)
    return s[:n] + ("..." if len(s) > n else "")


def fetch_all(
    table_name: str,
    select: str = "*",
    page_size: int = 1000,
    max_rows: Optional[int] = None,
    order_col: Optional[str] = None,
    desc: bool = True,
    eq_filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    client = get_client()
    rows: List[Dict[str, Any]] = []
    start = 0

    while True:
        end = start + page_size - 1
        q = client.table(table_name).select(select)
        if eq_filters:
            for col, val in eq_filters.items():
                q = q.eq(col, val)
        if order_col:
            q = q.order(order_col, desc=desc)
        q = q.range(start, end)

        try:
            resp = q.execute()
        except Exception as e:
            print(f"❌ {table_name} okunamadı: {e}")
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


def fetch_talepler(limit_talep: int = 10, talep_id: Optional[str] = None) -> List[Dict[str, Any]]:
    if talep_id:
        return fetch_all(
            table_name="alici_talepleri", select="*", page_size=1000,
            max_rows=1, order_col=None, eq_filters={"id": talep_id},
        )
    return fetch_all(
        table_name="alici_talepleri", select="*", page_size=1000,
        max_rows=limit_talep, order_col="id", desc=True,
        eq_filters={"kategori": "alici_talebi"},
    )


def fetch_portfoyler() -> List[Dict[str, Any]]:
    return fetch_all(
        table_name="portfoyler", select="*", page_size=1000,
        max_rows=None, order_col="id", desc=True, eq_filters=None,
    )


def sonuc_to_csv_row(talep: Dict[str, Any], sonuc: Dict[str, Any], sira: int) -> Dict[str, Any]:
    p = sonuc.get("portfoy", {}) or {}
    return {
        "talep_id": talep.get("id"), "talep_ozet": safe(talep.get("ozet")),
        "talep_il": safe(talep.get("il")), "talep_ilce": safe(talep.get("ilce")),
        "talep_ilceler": safe(talep.get("ilceler")),
        "talep_islem_tipi": safe(talep.get("islem_tipi")),
        "talep_mulk_tipi": safe(talep.get("mulk_tipi")),
        "talep_oda_m2": safe(talep.get("oda_sayisi_m2")),
        "talep_max_butce": safe(talep.get("max_butce")),
        "sonuc_sira": sira, "skor": sonuc.get("skor"), "seviye": sonuc.get("seviye"),
        "grup": sonuc.get("grup"), "gerekce": safe(sonuc.get("gerekce")),
        "portfoy_id": p.get("id"), "portfoy_ozet": safe(p.get("ozet")),
        "portfoy_il": safe(p.get("il")), "portfoy_ilce": safe(p.get("ilce")),
        "portfoy_islem_tipi": safe(p.get("islem_tipi")),
        "portfoy_mulk_tipi": safe(p.get("mulk_tipi")),
        "portfoy_oda_m2": safe(p.get("oda_sayisi_m2")),
        "portfoy_fiyat": safe(p.get("fiyat")),
        "portfoy_gorunurluk": safe(p.get("portfoy_gorunurluk")),
        "link_sayisi": p.get("link_sayisi"), "aktif": p.get("aktif"),
        "talep_eden_danisan": safe(p.get("talep_eden_danisan")),
    }


def csv_yaz(rows: List[Dict[str, Any]], path: str) -> None:
    if not rows:
        print("ℹ️ CSV yazılacak sonuç yok.")
        return
    full_path = path
    if not os.path.isabs(full_path):
        full_path = os.path.join(PROJECT_ROOT, full_path)
    fieldnames = list(rows[0].keys())
    with open(full_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"✅ CSV çıktı yazıldı: {full_path}")


def run_dry_run(
    limit_talep: int = 10, talep_id: Optional[str] = None,
    max_sonuc: int = 10, csv_path: Optional[str] = None,
) -> None:
    print("=" * 100)
    print("ALICI → PORTFÖY EŞLEŞME MOTORU DRY-RUN")
    print("=" * 100)

    print("1) Talepler çekiliyor...")
    talepler = fetch_talepler(limit_talep=limit_talep, talep_id=talep_id)
    print(f"✅ Talep sayısı: {len(talepler)}")

    print()
    print("2) Portföyler çekiliyor...")
    portfoyler = fetch_portfoyler()
    print(f"✅ Portföy sayısı: {len(portfoyler)}")

    if not talepler:
        print("❌ Test edilecek talep bulunamadı.")
        return
    if not portfoyler:
        print("❌ Test edilecek portföy bulunamadı.")
        return

    print()
    print("3) Eşleşme testleri başlıyor...")
    print()

    tum_csv_rows: List[Dict[str, Any]] = []

    for t_idx, talep in enumerate(talepler, start=1):
        print("-" * 100)
        print(f"TALEP {t_idx}/{len(talepler)} | ID: {talep.get('id')}")
        print(f"Özet       : {short(talep.get('ozet'), 120)}")
        print(f"Lokasyon   : {safe(talep.get('il'))} / {safe(talep.get('ilce'))} / {safe(talep.get('ilceler'))}")
        print(f"Tip        : {safe(talep.get('islem_tipi'))} / {safe(talep.get('mulk_tipi'))}")
        print(f"Oda-M2     : {safe(talep.get('oda_sayisi_m2'))}")
        print(f"Bütçe      : {safe(talep.get('max_butce'))}")
        print()

        sonuclar = eslesen_portfoyleri_bul(talep=talep, portfoyler=portfoyler, max_sonuc=max_sonuc)

        if not sonuclar:
            print("  Eşleşme bulunamadı.")
            continue

        kapali_count = sum(1 for s in sonuclar if s.get("grup") == "kapali_linksiz")
        aktif_count = sum(1 for s in sonuclar if s.get("grup") == "aktif_portfoy")
        print(f"  Bulunan sonuç: {len(sonuclar)} | Kapalı/Linksiz: {kapali_count} | Diğer aktif: {aktif_count}")
        print()

        for sira, sonuc in enumerate(sonuclar, start=1):
            p = sonuc.get("portfoy", {}) or {}
            grup_label = "🔒 Kapalı/Linksiz" if sonuc.get("grup") == "kapali_linksiz" else "🏠 Aktif Portföy"
            print(f"  {sira:02d}. {sonuc.get('skor')}/100 · {sonuc.get('seviye')} · {grup_label}")
            print(f"      Portföy ID : {p.get('id')}")
            print(f"      Özet       : {short(p.get('ozet'), 120)}")
            print(f"      Lokasyon   : {safe(p.get('il'))} / {safe(p.get('ilce'))}")
            print(f"      Tip        : {safe(p.get('islem_tipi'))} / {safe(p.get('mulk_tipi'))}")
            print(f"      Fiyat      : {safe(p.get('fiyat'))}")
            print(f"      Görünürlük : {safe(p.get('portfoy_gorunurluk'))} | link_sayisi={p.get('link_sayisi')} | aktif={p.get('aktif')}")
            print(f"      Gerekçe    : {safe(sonuc.get('gerekce'))}")
            print()

            tum_csv_rows.append(sonuc_to_csv_row(talep, sonuc, sira))

    print("=" * 100)
    print("ÖZET")
    print("=" * 100)
    print(f"Test edilen talep sayısı : {len(talepler)}")
    print(f"Toplam CSV sonuç satırı  : {len(tum_csv_rows)}")

    if csv_path:
        csv_yaz(tum_csv_rows, csv_path)
    else:
        print("ℹ️ CSV oluşturulmadı.")
    print("=" * 100)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Alıcı → Portföy eşleşme dry-run scripti")
    parser.add_argument("--limit-talep", type=int, default=10)
    parser.add_argument("--talep-id", type=str, default=None)
    parser.add_argument("--max-sonuc", type=int, default=10)
    parser.add_argument("--csv", type=str, default=None)
    parser.add_argument("--no-csv", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.no_csv:
        csv_path = None
    elif args.csv:
        csv_path = args.csv
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = f"match_dry_run_sonuclar_{ts}.csv"

    run_dry_run(
        limit_talep=args.limit_talep, talep_id=args.talep_id,
        max_sonuc=args.max_sonuc, csv_path=csv_path,
    )
