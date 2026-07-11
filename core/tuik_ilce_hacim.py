"""
core/tuik_ilce_hacim.py
────────────────────────
İzmir ilçelerinin gayrimenkul pazarındaki "hacim sınıfı" — TÜİK'in resmi
2025 yıllık konut satış istatistiklerine (biruni.tuik.gov.tr/medas, "İlçe
Konut Satış Sayıları" göstergesi) dayanır. Doğal kırılım noktalarına göre
4 kademeye ayrılmıştır (eşit sayıda ilçe değil — verideki gerçek boşluklara
göre bölünmüştür):

    Yüksek Hacim     : 2025'te ≥ 4.619 konut satışı
    Orta-Üst Hacim   : 1.541 – 2.907 arası
    Orta-Alt Hacim   : 743 – 1.010 arası
    Düşük Hacim      : ≤ 208 (çoğunlukla küçük/kırsal ilçeler)

NOT: Bu tablo YILLIK bir güncelleme gerektirir — TÜİK her yıl Ocak/Şubat'ta
bir önceki yılın kesin verisini yayınlar. 2026 sonunda 2026 verisiyle
güncellenmesi önerilir. Güncelleme adımları için dosya sonundaki
`_KAYNAK_NOTU`na bakın.
"""

# İlçe → 2025 TÜİK konut satış sayısı (kaynak: biruni.tuik.gov.tr/medas,
# "Konut Satış İstatistikleri" → "İlçe Konut Satış Sayıları", Ocak-Aralık 2025)
IZMIR_ILCE_2025_SATIS = {
    "Menemen": 12069, "Buca": 11910, "Torbalı": 8610, "Karşıyaka": 8513,
    "Karabağlar": 5939, "Konak": 5902, "Çiğli": 5746, "Bornova": 5344,
    "Bayraklı": 4619, "Seferihisar": 2907, "Dikili": 2720, "Aliağa": 2571,
    "Kemalpaşa": 2449, "Menderes": 2281, "Gaziemir": 2278, "Bergama": 2097,
    "Ödemiş": 1970, "Çeşme": 1811, "Balçova": 1689, "Foça": 1658,
    "Urla": 1556, "Tire": 1541, "Narlıdere": 1010, "Selçuk": 774,
    "Güzelbahçe": 756, "Karaburun": 743, "Bayındır": 208, "Kiraz": 203,
    "Kınık": 142, "Beydağ": 68,
}

# İlçe → 2026 Ocak-Mayıs TÜİK konut satış sayısı (henüz yıl tamamlanmadığı
# için sadece referans/karşılaştırma amaçlı — hacim sınıfı hesabında
# kullanılmıyor)
IZMIR_ILCE_2026_OCAK_MAYIS_SATIS = {
    "Aliağa": 935, "Balçova": 515, "Bayraklı": 1858, "Bayındır": 70,
    "Bergama": 821, "Beydağ": 23, "Bornova": 1717, "Buca": 4040,
    "Dikili": 773, "Foça": 506, "Gaziemir": 681, "Güzelbahçe": 273,
    "Karabağlar": 1913, "Karaburun": 199, "Karşıyaka": 2761,
    "Kemalpaşa": 1055, "Kiraz": 50, "Konak": 1968, "Kınık": 107,
    "Menderes": 783, "Menemen": 4186, "Narlıdere": 318, "Seferihisar": 924,
    "Selçuk": 247, "Tire": 512, "Torbalı": 3070, "Urla": 493,
    "Çeşme": 610, "Çiğli": 1807, "Ödemiş": 770,
}

_YUKSEK_ESIK    = 4619
_ORTA_UST_ESIK  = 1541
_ORTA_ALT_ESIK  = 743

def hacim_sinifi(ilce: str) -> str:
    """İlçe adını alır, 4 kademeli hacim sınıfını döner.
    Bilinmeyen/eşleşmeyen ilçe adı için 'Bilinmiyor' döner."""
    satis = IZMIR_ILCE_2025_SATIS.get(str(ilce).strip())
    if satis is None:
        return "Bilinmiyor"
    if satis >= _YUKSEK_ESIK:
        return "Yüksek Hacim"
    elif satis >= _ORTA_UST_ESIK:
        return "Orta-Üst Hacim"
    elif satis >= _ORTA_ALT_ESIK:
        return "Orta-Alt Hacim"
    else:
        return "Düşük Hacim"

def hacim_rozet_rengi(sinif: str) -> str:
    """UI'da rozet/etiket rengi için — kademeye göre bir renk kodu döner."""
    return {
        "Yüksek Hacim":   "#059669",  # yeşil
        "Orta-Üst Hacim": "#2563eb",  # mavi
        "Orta-Alt Hacim": "#d97706",  # turuncu
        "Düşük Hacim":    "#dc2626",  # kırmızı
        "Bilinmiyor":     "#94a3b8",  # gri
    }.get(sinif, "#94a3b8")

def ilce_satis_2025(ilce: str):
    """İlçenin 2025 TÜİK satış sayısını döner (bulunamazsa None)."""
    return IZMIR_ILCE_2025_SATIS.get(str(ilce).strip())


# ── _KAYNAK_NOTU ──────────────────────────────────────────────────────────
# Güncelleme adımları (yılda bir, örn. 2027 başında 2026 verisiyle):
#   1) https://biruni.tuik.gov.tr/medas/?kn=73 adresine git
#   2) Konu: "Konut Satış İstatistikleri" → Ölçüm: "İlçe Konut Satış Sayıları"
#   3) Zaman: ilgili yılın 12 ayını seç (Periyot: Aylık)
#   4) Düzey: İzmir ili altındaki tüm ilçeleri seç
#   5) Rapor sekmesinden CSV indir (XLS değil — 255 sütun sınırına takılır)
#   6) IZMIR_ILCE_2025_SATIS sözlüğünü yeni yılın toplamlarıyla güncelle,
#      eşik değerlerini (_YUKSEK_ESIK vb.) doğal kırılım noktalarına göre
#      yeniden gözden geçir.
