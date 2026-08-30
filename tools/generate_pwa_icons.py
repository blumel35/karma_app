# tools/generate_pwa_icons.py
# -*- coding: utf-8 -*-
"""
Danışman Panosu'nu telefonda "ana ekrana eklenen uygulama" gibi açmak için
gereken PWA ikonlarını üretir (2026-08-30). Giriş ekranlarında (Danisman_
Giris.py, giris.py, Hesap_Aktivasyon.py) zaten kullanılan marka renkleri
kullanılıyor: lacivert kare (#1C2B47) zemin + beyaz "Z" harfi.

Tek seferlik bir üretim scripti — normal uygulama çalışması sırasında
çağrılmaz. Çıktılar static/icons/ altına yazılır (Streamlit'in
enableStaticServing özelliğiyle sunulacak).

Kullanım: python tools/generate_pwa_icons.py
"""

import os
from PIL import Image, ImageDraw, ImageFont

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
OUT_DIR = os.path.join(PROJECT_ROOT, "static", "icons")

BG_COLOR = "#1C2B47"
FG_COLOR = "#FFFFFF"
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

SIZES = {
    "icon-192.png": 192,
    "icon-512.png": 512,
    "apple-touch-icon.png": 180,
}


def _font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _tek_ikon_uret(boyut):
    img = Image.new("RGB", (boyut, boyut), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_boyutu = int(boyut * 0.56)
    font = _font(font_boyutu)

    harf = "Z"
    bbox = draw.textbbox((0, 0), harf, font=font)
    metin_w = bbox[2] - bbox[0]
    metin_h = bbox[3] - bbox[1]
    x = (boyut - metin_w) / 2 - bbox[0]
    y = (boyut - metin_h) / 2 - bbox[1]

    draw.text((x, y), harf, fill=FG_COLOR, font=font)
    return img


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for dosya_adi, boyut in SIZES.items():
        img = _tek_ikon_uret(boyut)
        yol = os.path.join(OUT_DIR, dosya_adi)
        img.save(yol, "PNG")
        print(f"✅ {yol} ({boyut}x{boyut})")


if __name__ == "__main__":
    main()
