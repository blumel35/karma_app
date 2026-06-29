# render_sablonlar.py
# Sunum Merkezi V2 — Startkey Zeta şablon motoru
# Tasarım Sprint v2 — Mayıs 2026
#
# Public API (dokunulmaz):
#   SABLON_LISTESI
#   KartVeri
#   render_bytes(sablon_key, veri) -> tuple[bytes, bytes]
#   thumbnail(sablon_key, veri, size=200) -> PIL.Image
#   render_mail_html(v, sablon_id) -> str
#   render_landing_html(v, sablon_id) -> str

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any
import html as _html_module
import io
import re
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont, ImageFilter


SABLON_LISTESI = [
    ("portfoy_premium",   "Portföy Premium",   "Büyük fotoğraf · fiyat odaklı · danışman güven alanı"),
    ("portfoy_gallery",   "Portföy Galeri",    "Dominant görsel · destek fotoğraflar · +N overlay"),
    ("portfoy_editorial", "Portföy Editorial", "Luxury magazine estetik · minimal bilgi · ultra premium"),
    ("talep_b2b",         "Talep B2B",         "Meslektaşlar arası talep sunumu · kriter odaklı"),
]


@dataclass
class KartVeri:
    baslik:      str = ""
    islem_tipi:  str = "Satılık"
    mulk_tipi:   str = "Konut"
    il:          str = "İzmir"
    ilce:        str = ""
    m2:          str = ""
    oda:         str = ""
    kat:         str = ""
    bina_yasi:   str = ""
    fiyat:       str = ""
    aciklama:    str = ""
    ozellikler:  list = field(default_factory=list)
    fotolar:     list = field(default_factory=list)

    dan_ad:      str = ""
    dan_telefon: str = ""
    dan_email:   str = ""
    dan_unvan:   str = "Gayrimenkul Danışmanı"
    dan_foto:    Optional[bytes] = None
    dan_logo:    Optional[bytes] = None

    # Talep B2B
    talep_no:          str  = ""
    talep_tarihi:      str  = ""
    hedef_bolge:       str  = ""
    butce:             str  = ""
    metraj_araligi:    str  = ""
    oda_araligi:       str  = ""
    kat_araligi:       str  = ""
    zorunlu_kriterler: list = field(default_factory=list)
    negatif_kriterler: list = field(default_factory=list)
    danisman_notu:     str  = ""
    qr_data:           Any  = None


# ─────────────────────────────────────────────────────────────────────────────
# MARKA PALETİ
# ─────────────────────────────────────────────────────────────────────────────
NAVY       = (10, 35, 78)
NAVY2      = (18, 47, 96)
NAVY_LIGHT = (235, 240, 250)   # açık lacivert alan
RED        = (190, 24, 35)
RED_SOFT   = (253, 238, 238)   # kırmızı vurgu zemini
TEXT       = (13, 27, 54)
MUTED      = (90, 104, 130)
MUTED2     = (140, 152, 172)
BORDER     = (218, 226, 238)
BORDER2    = (232, 236, 244)   # çok ince çizgi
SOFT       = (247, 250, 253)
CREAM      = (252, 251, 248)   # kırık beyaz editorial zemin
WHITE      = (255, 255, 255)
GREEN      = (22, 145, 55)
BLUE       = (37, 99, 235)
ORANGE     = (234, 126, 37)
PURPLE     = (126, 72, 210)

_AVATAR_CROP_USED = False


# ─────────────────────────────────────────────────────────────────────────────
# TEMEL YARDIMCILAR
# ─────────────────────────────────────────────────────────────────────────────

def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    paths = (
        [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
            "C:/Windows/Fonts/georgiab.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        if bold else
        [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "C:/Windows/Fonts/georgia.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    )
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def _read_image(raw: Any) -> Optional[Image.Image]:
    if raw is None:
        return None
    try:
        if isinstance(raw, Image.Image):
            return raw.convert("RGB")
        if isinstance(raw, (bytes, bytearray)):
            return Image.open(io.BytesIO(raw)).convert("RGB")
        if hasattr(raw, "read"):
            raw.seek(0)
            return Image.open(raw).convert("RGB")
        return None
    except Exception:
        return None


def _cover(raw: Any, size: tuple[int, int]) -> Image.Image:
    W, H = size
    img = _read_image(raw)
    if img is None:
        ph = Image.new("RGB", size, (228, 234, 244))
        d = ImageDraw.Draw(ph)
        d.rounded_rectangle([20, 20, W - 20, H - 20], radius=20, outline=(200, 210, 224), width=2)
        d.text((W // 2, H // 2 - 16), "STARTKEY", font=_font(28, True), fill=(160, 175, 200), anchor="mm")
        d.text((W // 2, H // 2 + 18), "Fotograf Yok", font=_font(20), fill=(180, 192, 212), anchor="mm")
        return ph
    w, h = img.size
    r = max(W / w, H / h)
    nw, nh = int(w * r), int(h * r)
    img = img.resize((nw, nh), Image.LANCZOS)
    l, t = (nw - W) // 2, (nh - H) // 2
    return img.crop((l, t, l + W, t + H))


def _cover_face(raw: Any, size: tuple[int, int]) -> Image.Image:
    """
    Danışman fotoğrafını yüz merkezli kırp.
    Portrait: yüz genellikle üst %15-40 arasında — oradan kare kırp.
    Landscape: üst yarıdan kare kırp.
    Kare: merkez kırp.
    """
    W, H = size
    img = _read_image(raw)
    if img is None:
        return _cover(raw, size)
    w, h = img.size

    if h > w * 1.2:
        # Portrait (dikey) — tam boy fotoğraf
        # Yüz üstten %10-40 arasında, kare crop w×w boyutunda başlatsak
        # yüzü kaçırıyoruz çünkü w küçük kalıyor
        # Çözüm: kare boyutunu w olarak al, başlangıcı %12'den başlat
        crop_size = w
        crop_x    = 0
        # Yüz genellikle h'nin %10-35'inde — %12'den başlamak orta nokta
        crop_y    = int(h * 0.12)
        crop_y    = max(0, min(crop_y, h - crop_size))
    elif w > h * 1.3:
        # Geniş landscape
        crop_size = h
        crop_x    = (w - crop_size) // 2
        crop_y    = int(h * 0.04)
        crop_y    = max(0, min(crop_y, h - crop_size))
    else:
        # Yakın kare
        crop_size = min(w, h)
        crop_x    = (w - crop_size) // 2
        crop_y    = (h - crop_size) // 3   # üst 1/3 — yüz genellikle orada
        crop_y    = max(0, min(crop_y, h - crop_size))

    img = img.crop((crop_x, crop_y, crop_x + crop_size, crop_y + crop_size))
    return img.resize((W, H), Image.LANCZOS)


def _circle(raw: Any, size: int, initials: str = "SK") -> Image.Image:
    global _AVATAR_CROP_USED
    _AVATAR_CROP_USED = False
    img = _read_image(raw)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size, size], fill=255)
    if img is not None:
        img = _cover_face(img, (size, size)).convert("RGBA")
        _AVATAR_CROP_USED = True
        img.putalpha(mask)
        return img
    d = ImageDraw.Draw(out)
    d.ellipse([0, 0, size, size], fill=(*NAVY, 255))
    d.text((size // 2, size // 2), initials[:2], font=_font(max(16, size // 3), True), fill=WHITE, anchor="mm")
    return out


def _wrap(text: str, font, max_w: int, draw: ImageDraw.ImageDraw, max_lines: int = 99) -> list[str]:
    text = str(text or "").strip()
    if not text:
        return [""]
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
            if len(lines) >= max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    return lines[:max_lines]


def _money(value: str) -> str:
    if value is None or str(value).strip() == "":
        return "Fiyat Belirlenmedi"
    s = str(value).replace("₺", "").replace("TL", "").replace("tl", "").strip()
    digits = "".join(c for c in s if c.isdigit())
    if not digits:
        return str(value)
    n = int(digits)
    return "₺ " + f"{n:,}".replace(",", ".")


def _short_money(value: str) -> str:
    if value is None or str(value).strip() == "":
        return "Fiyat Belirlenmedi"
    s = str(value).replace("₺", "").replace("TL", "").replace("tl", "").strip()
    digits = "".join(c for c in s if c.isdigit())
    if not digits:
        return str(value)
    n = int(digits)
    if n >= 1_000_000:
        m = n / 1_000_000
        return f"₺ {m:.1f}M".replace(".0M", "M")
    return "₺ " + f"{n:,}".replace(",", ".")


def _logo(canvas: Image.Image, logo_bytes: Optional[bytes], box, fallback_size=28):
    d = ImageDraw.Draw(canvas)
    x, y, w, h = box
    if logo_bytes:
        try:
            logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
            logo.thumbnail((w, h), Image.LANCZOS)
            lx = x + (w - logo.width) // 2
            ly = y + (h - logo.height) // 2
            canvas.paste(logo, (lx, ly), logo)
            return
        except Exception:
            pass
    d.text((x + w // 2, y + h // 2 - 8), "STARTKEY", font=_font(fallback_size, True), fill=RED, anchor="mm")
    d.text((x + w // 2, y + h // 2 + fallback_size - 10), "ZETA GAYRIMENKUL", font=_font(max(13, fallback_size // 2), True), fill=NAVY, anchor="mm")


def _rounded_card(draw, box, radius=22, fill=WHITE, outline=BORDER, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _chip(draw, xy, text, icon="", fill=WHITE, outline=BORDER, color=TEXT, font_size=24, w=None, h=62):
    x, y = xy
    f = _font(font_size, False)
    label = f"{icon}  {text}".strip() if icon else text
    tw = int(draw.textlength(label, font=f))
    width = w or max(150, tw + 48)
    draw.rounded_rectangle([x, y, x + width, y + h], radius=12, fill=fill, outline=outline, width=1)
    draw.text((x + width // 2, y + h // 2), label, font=f, fill=color, anchor="mm")
    return width


def _decode_entities(text: str) -> str:
    """HTML entity'leri kaç kez encode edilmiş olursa olsun temizle.
    &amp;amp;#x27; → ' gibi çok katmanlı encode'ları da çözer."""
    if not text:
        return text
    for _ in range(6):
        decoded = _html_module.unescape(text)
        if decoded == text:
            break
        text = decoded
    # Kalan &#x27; / &#39; gibi numeric entity'leri çöz
    text = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), text)
    text = re.sub(r'&#([0-9]+);',        lambda m: chr(int(m.group(1))),      text)
    return text


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    if not text:
        return True
    return text.lower() in {
        "nan", "none", "null", "nat", "farketmez", "fark etmez",
        "belirtilmedi", "belirtilmemiş", "-", "—"
    }


def _clean(value: Any, default: str = "") -> str:
    if _is_blank(value):
        return default
    return _decode_entities(str(value).strip())


def _join_clean(parts: list[Any], sep: str = " / ") -> str:
    return sep.join([_clean(p) for p in parts if not _is_blank(p)])


def _specs(v: KartVeri, include_heating: bool = True) -> list[tuple[str, str]]:
    """Spec (chip etiket, değer) listesi. Değerler label tekrarı içermez."""
    specs: list[tuple[str, str]] = []
    if not _is_blank(v.m2):
        m2_val = _clean(v.m2)
        # "150 m2" veya "150" → "150 m²" 
        m2_display = m2_val if "m" in m2_val.lower() else f"{m2_val} m²"
        specs.append(("M²", m2_display))
    if not _is_blank(v.oda):
        specs.append(("Oda", _clean(v.oda)))
    if not _is_blank(v.kat):
        specs.append(("Kat", _clean(v.kat)))
    heating = ""
    for item in v.ozellikler or []:
        t = _clean(item)
        if t and any(k in t.lower() for k in ["ısıt", "isit", "kombi", "merkezi"]):
            heating = t
            break
    if include_heating and heating:
        specs.append(("Isıtma", heating))
    return specs


def _draw_gradient(canvas: Image.Image, box, top_alpha=0, bottom_alpha=150, color=(0, 0, 0)):
    x1, y1, x2, y2 = box
    h = max(1, y2 - y1)
    layer = Image.new("RGBA", (x2 - x1, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(layer)
    for i in range(h):
        a = int(top_alpha + (bottom_alpha - top_alpha) * (i / max(1, h - 1)))
        gd.line([0, i, x2 - x1, i], fill=(*color, a))
    canvas.paste(layer, (x1, y1), layer)


def _rounded_paste(canvas: Image.Image, img: Image.Image, box, radius: int = 24):
    """
    box = (x, y, w, h)  — x/y: sol-üst köşe, w/h: genişlik/yükseklik
    """
    x, y, w, h = box
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w, h], radius=radius, fill=255)
    canvas.paste(img.resize((w, h), Image.LANCZOS), (x, y), mask)


def _initials(name: str) -> str:
    return "".join(w[0].upper() for w in str(name or "").split()[:2]) or "SK"


def _thin_line(draw, x1, y1, x2, y2, color=BORDER2):
    """1px ince ayraç çizgisi — editorial tasarım için."""
    draw.line([x1, y1, x2, y2], fill=color, width=1)


def _title_case(text: str) -> str:
    """ALL CAPS Türkçe başlığı Title Case'e çevir."""
    if not text:
        return text
    TR_LOWER = str.maketrans("IİŞĞÜÖÇ", "ıişğüöç")
    KUCUK    = {"ve", "veya", "ile", "de", "da", "den", "dan", "için", "bir", "ya", "ki"}
    words    = text.split()
    result   = []
    for i, w in enumerate(words):
        low = w.translate(TR_LOWER).lower()
        if i > 0 and low in KUCUK:
            result.append(low)
        else:
            result.append(w[0] + w[1:].translate(TR_LOWER).lower())
    return " ".join(result)


def _spec_value(label: str, txt: str) -> str:
    """Spec chip için temiz metin — 'M2: 150 m2' değil '150 m²'."""
    val = _clean(txt)
    # label tekrarını kaldır: "M2: 150 m2" → "150 m²"
    # "KAT: Müstakil" → "Müstakil"  "ODA: 3+1" → "3+1"
    if not val:
        return ""
    # Değer zaten birimi içeriyorsa label'ı gösterme, sadece değer
    return val


# ─────────────────────────────────────────────────────────────────────────────
# PORTFÖY PREMIUM  —  dikey kart, fiyat + foto ağırlıklı
# Sprint v2: hero hizası, CTA metni, advisor bloğu rafine
# ─────────────────────────────────────────────────────────────────────────────

def _render_portfoy_premium(v: KartVeri, W=1080, H=1500) -> Image.Image:
    canvas = Image.new("RGB", (W, H), (240, 244, 250))
    draw   = ImageDraw.Draw(canvas)
    margin = 30
    card_x1, card_y1 = margin, 24
    card_x2, card_y2 = W - margin, H - 24
    card_w = card_x2 - card_x1   # 1020
    card_h = card_y2 - card_y1

    # ── Kart zemini
    draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=32, fill=WHITE)

    # ── Hero fotoğraf (tam genişlik, köşeler üstte rounded)
    hero_h = 680
    hero_img = _cover(v.fotolar[0] if v.fotolar else None, (card_w, hero_h))
    _rounded_paste(canvas, hero_img, (card_x1, card_y1, card_w, hero_h), radius=32)
    # Alt hero kenarında kart boşluğunu kapat (alt köşeler düz)
    canvas.paste(
        hero_img.crop((0, hero_h - 32, card_w, hero_h)).resize((card_w, 32), Image.LANCZOS),
        (card_x1, card_y1 + hero_h - 32)
    )

    # ── Hero üst gradyanı (üstten aşağı, logo/badge için okunabilirlik)
    _draw_gradient(canvas, (card_x1, card_y1, card_x2, card_y1 + 180), top_alpha=110, bottom_alpha=0)
    # ── Hero alt gradyanı (fiyat alanına geçiş yumuşatma — olmayacak, temiz kesmek daha iyi)

    # ── "ÖZEL PORTFÖY" badge — sol üst
    badge_x1 = card_x1 + 28
    badge_y1 = card_y1 + 28
    badge_x2 = badge_x1 + 220
    badge_y2 = badge_y1 + 46
    draw.rounded_rectangle([badge_x1, badge_y1, badge_x2, badge_y2], radius=16, fill=RED)
    draw.text(
        ((badge_x1 + badge_x2) // 2, (badge_y1 + badge_y2) // 2),
        "ÖZEL PORTFÖY",
        font=_font(19, True), fill=WHITE, anchor="mm"
    )

    # ── Logo — sağ üst
    _logo(canvas, v.dan_logo, (card_x2 - 220, card_y1 + 26, 188, 68), fallback_size=26)

    # ── İçerik alanı
    cx = card_x1 + 48
    cy = card_y1 + hero_h + 36

    # Fiyat
    price_str = _money(v.fiyat)
    draw.text((cx, cy), price_str, font=_font(74, True), fill=TEXT)
    cy += 88

    # İnce ayraç
    _thin_line(draw, cx, cy, card_x2 - 48, cy)
    cy += 22

    # Başlık
    title = _title_case(_clean(v.baslik) or _join_clean([v.ilce, v.islem_tipi, v.mulk_tipi], " ") or "Portföy Sunumu")
    for line in _wrap(title, _font(40, True), card_w - 96, draw, 2):
        draw.text((cx, cy), line, font=_font(40, True), fill=TEXT)
        cy += 50
    cy += 4

    # Lokasyon
    loc = _join_clean([v.ilce, v.il], " / ")
    if loc:
        draw.text((cx, cy), loc, font=_font(22), fill=MUTED)
        cy += 38

    cy += 8

    # Spec chip'leri — değer büyük üstte, label küçük altta
    specs = _specs(v, include_heating=True)[:4]
    chip_x, chip_y = cx, cy
    for label, txt in specs:
        val = _clean(txt)
        if not val:
            continue
        val_w  = int(draw.textlength(val,   font=_font(20, True)))
        lbl_w  = int(draw.textlength(label, font=_font(13)))
        chip_w = min(280, max(120, max(val_w, lbl_w) + 40))
        draw.rounded_rectangle(
            [chip_x, chip_y, chip_x + chip_w, chip_y + 56],
            radius=24, fill=NAVY_LIGHT, outline=BORDER, width=1
        )
        draw.text((chip_x + chip_w // 2, chip_y + 18), val,   font=_font(20, True), fill=NAVY,  anchor="mm")
        draw.text((chip_x + chip_w // 2, chip_y + 40), label, font=_font(13),        fill=MUTED2, anchor="mm")
        chip_x += chip_w + 12
        if chip_x > card_x2 - 48 - 120:
            chip_x = cx
            chip_y += 66
    cy = chip_y + (66 if specs else 16)

    # Açıklama (max 2 satır)
    desc = _clean(v.aciklama)
    if desc:
        cy += 4
        for line in _wrap(desc, _font(22), card_w - 96, draw, 2):
            draw.text((cx, cy), line, font=_font(22), fill=(78, 91, 116))
            cy += 32
        cy += 16

    # ── Advisor bloğu (kartın alt kısmına sabitlenmiş)
    advisor_y = cy + 24

    # İnce ayraç
    _thin_line(draw, cx, advisor_y, card_x2 - 48, advisor_y)
    advisor_y += 24

    # Avatar + bilgi
    avatar = _circle(v.dan_foto, 84, _initials(v.dan_ad))
    canvas.paste(avatar, (cx, advisor_y), avatar)

    tx = cx + 102
    draw.text((tx, advisor_y + 8),  _clean(v.dan_ad, "Danişman"),      font=_font(23, True), fill=TEXT)
    draw.text((tx, advisor_y + 36), _clean(v.dan_unvan, "Gayrimenkul Danismani"), font=_font(16), fill=MUTED)
    contact = _join_clean([v.dan_telefon, v.dan_email], "  |  ")
    if contact:
        draw.text((tx, advisor_y + 58), contact[:68], font=_font(16), fill=TEXT)

    _logo(canvas, v.dan_logo, (card_x2 - 230, advisor_y + 8, 180, 62), fallback_size=22)

    # ── CTA butonu
    cta_y1 = advisor_y + 108
    cta_y2 = cta_y1 + 56
    draw.rounded_rectangle([cx, cta_y1, card_x2 - 48, cta_y2], radius=16, fill=NAVY)
    draw.text(
        ((cx + card_x2 - 48) // 2, (cta_y1 + cta_y2) // 2),
        "Portföyü İncele",
        font=_font(21, True), fill=WHITE, anchor="mm"
    )

    # ── Marka değer şeridi — CTA altında, kartın en sonunda
    SERIT_ITEMS = [
        ("Güvenilir",      "Profesyonel Hizmet"),
        ("Özel Portföy",   "İlana Çıkmayan Portföyler"),
        ("ZETA Ofisleri",  "Türkiye Genelinde"),
        ("Kalite Odaklı",  "Fark Yaratan Hizmet"),
    ]
    serit_y1   = cta_y2 + 24
    serit_y2   = serit_y1 + 72
    serit_col  = card_w // 4

    # Şerit arka plan
    draw.rounded_rectangle(
        [card_x1, serit_y1, card_x2, serit_y2],
        radius=0, fill=(240, 244, 250)
    )
    # Üst ince çizgi
    _thin_line(draw, card_x1, serit_y1, card_x2, serit_y1, color=BORDER)

    for i, (bas, alt) in enumerate(SERIT_ITEMS):
        col_cx = card_x1 + i * serit_col + serit_col // 2
        # Dikey ayraç
        if i > 0:
            _thin_line(draw, card_x1 + i * serit_col, serit_y1 + 12,
                       card_x1 + i * serit_col, serit_y2 - 12, color=BORDER)
        draw.text((col_cx, serit_y1 + 24), bas, font=_font(16, True),
                  fill=NAVY, anchor="mm")
        draw.text((col_cx, serit_y1 + 50), alt, font=_font(13),
                  fill=MUTED2, anchor="mm")

    return canvas


def _portfoy_story(v: KartVeri) -> Image.Image:
    """Premium story — 1080x1920, hero üst, metin alt kartta."""
    W, H = 1080, 1920
    canvas = Image.new("RGB", (W, H), (240, 244, 250))
    d = ImageDraw.Draw(canvas)

    # ── Hero fotoğraf — tam genişlik, üst %60
    hero_h = 1140
    hero = _cover(v.fotolar[0] if v.fotolar else None, (W, hero_h))
    canvas.paste(hero, (0, 0))

    # Hero alt güçlü gradient
    _draw_gradient(canvas, (0, hero_h - 360, W, hero_h), top_alpha=0, bottom_alpha=210)

    # Hero üst gradient (logo için okunabilirlik)
    _draw_gradient(canvas, (0, 0, W, 140), top_alpha=120, bottom_alpha=0)

    # Badge + logo
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle([40, 42, 260, 88], radius=16, fill=RED)
    draw.text((150, 65), "ÖZEL PORTFÖY", font=_font(19, True), fill=WHITE, anchor="mm")
    _logo(canvas, v.dan_logo, (W - 212, 32, 172, 62), fallback_size=22)

    # Fiyat + başlık — hero alt kısmında, gradient üzerinde
    cx = 52
    text_w = W - cx * 2   # 976px — story genişliği için doğru wrap

    fiyat_y = hero_h - 280
    draw.text((cx, fiyat_y), _money(v.fiyat), font=_font(64, True), fill=WHITE)

    title_y = fiyat_y + 80
    title = _title_case(_clean(v.baslik) or _join_clean([v.islem_tipi, v.mulk_tipi, v.ilce], " "))
    lines = _wrap(title, _font(42, True), text_w, draw, 2)
    for i, line in enumerate(lines):
        draw.text((cx, title_y + i * 52), line, font=_font(42, True), fill=WHITE)

    # ── Alt kart — beyaz, bilgi + CTA
    card_y = hero_h
    draw.rectangle([0, card_y, W, H], fill=WHITE)

    cy = card_y + 40

    # Lokasyon
    loc = _join_clean([v.ilce, v.il], " / ")
    if loc:
        draw.text((cx, cy), loc, font=_font(22), fill=MUTED)
        cy += 38

    # Spec chip'leri
    specs = _specs(v)[:3]
    if specs:
        cy += 8
        chip_x = cx
        for label, txt in specs:
            label_txt = f"{label}: {_clean(txt)}"
            chip_w = min(260, max(140, int(draw.textlength(label_txt, font=_font(18, True))) + 36))
            draw.rounded_rectangle([chip_x, cy, chip_x + chip_w, cy + 46], radius=23, fill=NAVY_LIGHT, outline=BORDER, width=1)
            draw.text((chip_x + chip_w // 2, cy + 23), label_txt, font=_font(18, True), fill=NAVY, anchor="mm")
            chip_x += chip_w + 10
        cy += 58

    cy += 12

    # CTA butonu
    cta_x2 = W - cx
    draw.rounded_rectangle([cx, cy, cta_x2, cy + 72], radius=20, fill=NAVY)
    draw.text(((cx + cta_x2) // 2, cy + 36), "Portföyü İncele", font=_font(24, True), fill=WHITE, anchor="mm")
    cy += 96

    # Danışman
    _thin_line(draw, cx, cy, W - cx, cy)
    cy += 20
    avatar = _circle(v.dan_foto, 78, _initials(v.dan_ad))
    canvas.paste(avatar, (cx, cy), avatar)
    draw.text((cx + 96, cy + 12), _clean(v.dan_ad, "Danışman"),    font=_font(22, True), fill=TEXT)
    draw.text((cx + 96, cy + 40), _clean(v.dan_unvan, "Gayrimenkul Danışmanı"), font=_font(16), fill=MUTED)
    _logo(canvas, v.dan_logo, (W - cx - 180, cy + 8, 170, 60), fallback_size=20)

    return canvas


# ─────────────────────────────────────────────────────────────────────────────
# PORTFÖY GALERİ  —  çoklu fotoğraf grid
# Sprint v2: grid oranları ve koordinatlar düzeltildi
# ─────────────────────────────────────────────────────────────────────────────

def _render_portfoy_gallery(v: KartVeri, W=1080, H=1500) -> Image.Image:
    canvas = Image.new("RGB", (W, H), (240, 244, 250))
    draw   = ImageDraw.Draw(canvas)
    margin = 30
    card_x1, card_y1 = margin, 24
    card_x2, card_y2 = W - margin, H - 24
    card_w = card_x2 - card_x1   # 1020

    draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=32, fill=WHITE)

    # ── Fotoğraf grid: sol büyük + sağda 3 küçük
    gap       = 10
    grid_h    = 620
    main_w    = int(card_w * 0.62)   # ~632px
    side_w    = card_w - main_w - gap  # ~378px
    side_h    = (grid_h - gap * 2) // 3  # ~200px

    # Ana fotoğraf (sol, tam yükseklik)
    main_img = _cover(v.fotolar[0] if v.fotolar else None, (main_w, grid_h))
    _rounded_paste(canvas, main_img, (card_x1, card_y1, main_w, grid_h), radius=28)

    # Sağdaki 3 küçük fotoğraf
    side_x = card_x1 + main_w + gap
    for idx in range(3):
        y0 = card_y1 + idx * (side_h + gap)
        photo_idx = idx + 1
        frame = _cover(v.fotolar[photo_idx] if photo_idx < len(v.fotolar) else None, (side_w, side_h))
        _rounded_paste(canvas, frame, (side_x, y0, side_w, side_h), radius=18)
        # Son küçük karede +N overlay
        if idx == 2 and len(v.fotolar) > 4:
            overlay = Image.new("RGBA", (side_w, side_h), (0, 0, 0, 148))
            od = ImageDraw.Draw(overlay)
            od.text((side_w // 2, side_h // 2 - 10), f"+{len(v.fotolar) - 4}", font=_font(44, True), fill=WHITE, anchor="mm")
            od.text((side_w // 2, side_h // 2 + 34), "FOTO",                   font=_font(20, True), fill=WHITE, anchor="mm")
            canvas.paste(overlay, (side_x, y0), overlay)

    # ── "GALERİ" badge
    badge_x1 = card_x1 + 26
    badge_y1 = card_y1 + 26
    draw.rounded_rectangle([badge_x1, badge_y1, badge_x1 + 190, badge_y1 + 44], radius=16, fill=NAVY)
    draw.text(((badge_x1 + badge_x1 + 190) // 2, badge_y1 + 22), "GALERİ", font=_font(19, True), fill=WHITE, anchor="mm")

    # Sağ üst: logo
    _logo(canvas, v.dan_logo, (card_x2 - 216, card_y1 + 24, 184, 64), fallback_size=24)

    # ── İçerik alanı
    cx = card_x1 + 48
    cy = card_y1 + grid_h + 36

    if not _is_blank(v.fiyat):
        draw.text((cx, cy), _money(v.fiyat), font=_font(68, True), fill=TEXT)
        cy += 82

    _thin_line(draw, cx, cy, card_x2 - 48, cy)
    cy += 20

    title = _title_case(_clean(v.baslik) or _join_clean([v.ilce, v.islem_tipi, v.mulk_tipi], " ") or "Portföy Galerisi")
    for line in _wrap(title, _font(38, True), card_w - 96, draw, 2):
        draw.text((cx, cy), line, font=_font(38, True), fill=TEXT)
        cy += 48
    cy += 6

    loc = _join_clean([v.ilce, v.il], " / ")
    if loc:
        draw.text((cx, cy), loc, font=_font(22), fill=MUTED)
        cy += 38
    cy += 8

    specs = _specs(v, include_heating=True)[:4]
    chip_x, chip_y = cx, cy
    for label, txt in specs:
        val = _clean(txt)
        if not val:
            continue
        val_w  = int(draw.textlength(val,   font=_font(20, True)))
        lbl_w  = int(draw.textlength(label, font=_font(13)))
        chip_w = min(280, max(120, max(val_w, lbl_w) + 40))
        draw.rounded_rectangle([chip_x, chip_y, chip_x + chip_w, chip_y + 56], radius=24, fill=NAVY_LIGHT, outline=BORDER, width=1)
        draw.text((chip_x + chip_w // 2, chip_y + 18), val,   font=_font(20, True), fill=NAVY,  anchor="mm")
        draw.text((chip_x + chip_w // 2, chip_y + 40), label, font=_font(13),        fill=MUTED2, anchor="mm")
        chip_x += chip_w + 12
        if chip_x > card_x2 - 48 - 120:
            chip_x = cx
            chip_y += 66
    cy = chip_y + (66 if specs else 16)

    desc = _clean(v.aciklama)
    if desc:
        for line in _wrap(desc, _font(22), card_w - 96, draw, 2):
            draw.text((cx, cy), line, font=_font(22), fill=(78, 91, 116))
            cy += 32
        cy += 16

    # Footer danışman — içerik akışının hemen altında, minimum 32px boşluk
    footer_y = cy + 32
    _thin_line(draw, cx, footer_y, card_x2 - 48, footer_y)
    footer_y += 20
    avatar = _circle(v.dan_foto, 80, _initials(v.dan_ad))
    canvas.paste(avatar, (cx, footer_y), avatar)
    draw.text((cx + 98,  footer_y + 10), _clean(v.dan_ad, "Danişman"),                font=_font(22, True), fill=TEXT)
    draw.text((cx + 98,  footer_y + 38), _clean(v.dan_unvan, "Gayrimenkul Danismani"), font=_font(16), fill=MUTED)
    if not _is_blank(v.dan_telefon):
        draw.text((cx + 98, footer_y + 60), _clean(v.dan_telefon), font=_font(16), fill=TEXT)
    _logo(canvas, v.dan_logo, (card_x2 - 224, footer_y + 8, 176, 60), fallback_size=22)

    # ── Marka değer şeridi — kartın en altında
    _SERIT_ITEMS = [
        ("Güvenilir",      "Profesyonel Hizmet"),
        ("Özel Portföy",   "İlana Çıkmayan Portföyler"),
        ("ZETA Ofisleri",  "Türkiye Genelinde"),
        ("Kalite Odaklı",  "Fark Yaratan Hizmet"),
    ]
    serit_y1  = card_y2 - 76
    serit_y2  = card_y2
    serit_col = card_w // 4
    draw.rectangle([card_x1, serit_y1, card_x2, serit_y2], fill=(240, 244, 250))
    _thin_line(draw, card_x1, serit_y1, card_x2, serit_y1, color=BORDER)
    for i, (bas, alt) in enumerate(_SERIT_ITEMS):
        col_cx = card_x1 + i * serit_col + serit_col // 2
        if i > 0:
            _thin_line(draw, card_x1 + i * serit_col, serit_y1 + 10,
                       card_x1 + i * serit_col, serit_y2 - 10, color=BORDER)
        draw.text((col_cx, serit_y1 + 22), bas, font=_font(15, True),
                  fill=NAVY, anchor="mm")
        draw.text((col_cx, serit_y1 + 48), alt, font=_font(12),
                  fill=MUTED2, anchor="mm")

    return canvas


def _portfoy_gallery_story(v: KartVeri) -> Image.Image:
    """Galeri story — hero üst grid, alt kart bilgi."""
    W, H = 1080, 1920
    canvas = Image.new("RGB", (W, H), (240, 244, 250))
    draw = ImageDraw.Draw(canvas)

    # ── Hero grid — kare ile aynı oranlar, story'e uyarlanmış
    gap    = 8
    grid_h = 900
    main_w = int(W * 0.62)
    side_w = W - main_w - gap
    side_h = (grid_h - gap * 2) // 3

    main_img = _cover(v.fotolar[0] if v.fotolar else None, (main_w, grid_h))
    _rounded_paste(canvas, main_img, (0, 0, main_w, grid_h), radius=0)

    side_x = main_w + gap
    for idx in range(3):
        y0 = idx * (side_h + gap)
        photo_idx = idx + 1
        frame = _cover(v.fotolar[photo_idx] if photo_idx < len(v.fotolar) else None, (side_w, side_h))
        _rounded_paste(canvas, frame, (side_x, y0, side_w, side_h), radius=0)
        if idx == 2 and len(v.fotolar) > 4:
            ov = Image.new("RGBA", (side_w, side_h), (0, 0, 0, 145))
            od = ImageDraw.Draw(ov)
            od.text((side_w // 2, side_h // 2 - 8), f"+{len(v.fotolar) - 4}", font=_font(40, True), fill=WHITE, anchor="mm")
            od.text((side_w // 2, side_h // 2 + 34), "FOTO", font=_font(18, True), fill=WHITE, anchor="mm")
            canvas.paste(ov, (side_x, y0), ov)

    # Badge + logo
    draw.rounded_rectangle([28, 28, 200, 72], radius=15, fill=NAVY)
    draw.text((114, 50), "GALERİ", font=_font(18, True), fill=WHITE, anchor="mm")
    _logo(canvas, v.dan_logo, (W - 208, 22, 178, 60), fallback_size=20)

    # Üst gradient (badge okunabilirliği)
    _draw_gradient(canvas, (0, 0, W, 100), top_alpha=80, bottom_alpha=0)

    # ── Alt kart
    card_y = grid_h
    draw.rectangle([0, card_y, W, H], fill=WHITE)

    cx = 52
    text_w = W - cx * 2
    cy = card_y + 44

    draw.text((cx, cy), _money(v.fiyat), font=_font(62, True), fill=TEXT)
    cy += 76

    _thin_line(draw, cx, cy, W - cx, cy)
    cy += 20

    title = _title_case(_clean(v.baslik) or _join_clean([v.ilce, v.islem_tipi, v.mulk_tipi], " "))
    for line in _wrap(title, _font(38, True), text_w, draw, 2):
        draw.text((cx, cy), line, font=_font(38, True), fill=TEXT)
        cy += 48
    cy += 6

    loc = _join_clean([v.ilce, v.il], " / ")
    if loc:
        draw.text((cx, cy), loc, font=_font(21), fill=MUTED)
        cy += 36

    specs = _specs(v)[:3]
    if specs:
        cy += 10
        chip_x = cx
        for label, txt in specs:
            label_txt = f"{label}: {_clean(txt)}"
            chip_w = min(270, max(140, int(draw.textlength(label_txt, font=_font(18, True))) + 36))
            draw.rounded_rectangle([chip_x, cy, chip_x + chip_w, cy + 46], radius=23, fill=NAVY_LIGHT, outline=BORDER, width=1)
            draw.text((chip_x + chip_w // 2, cy + 23), label_txt, font=_font(18, True), fill=NAVY, anchor="mm")
            chip_x += chip_w + 10
        cy += 60

    cy += 12
    cta_x2 = W - cx
    draw.rounded_rectangle([cx, cy, cta_x2, cy + 70], radius=20, fill=NAVY)
    draw.text(((cx + cta_x2) // 2, cy + 35), "Galeriyi Gör", font=_font(23, True), fill=WHITE, anchor="mm")
    cy += 94

    _thin_line(draw, cx, cy, W - cx, cy)
    cy += 18
    avatar = _circle(v.dan_foto, 76, _initials(v.dan_ad))
    canvas.paste(avatar, (cx, cy), avatar)
    draw.text((cx + 94, cy + 10), _clean(v.dan_ad, "Danışman"),    font=_font(21, True), fill=TEXT)
    draw.text((cx + 94, cy + 38), _clean(v.dan_unvan, "Gayrimenkul Danışmanı"), font=_font(15), fill=MUTED)
    _logo(canvas, v.dan_logo, (W - cx - 178, cy + 8, 168, 58), fallback_size=19)

    return canvas


# ─────────────────────────────────────────────────────────────────────────────
# PORTFÖY EDİTORİAL  —  Startkey Luxury Magazine
# Sprint v2: beyaz/kırık beyaz zemin · lacivert tipografi · ince kırmızı vurgu
# ─────────────────────────────────────────────────────────────────────────────

def _render_portfoy_editorial(v: KartVeri, W=1080, H=1620) -> Image.Image:
    canvas = Image.new("RGB", (W, H), CREAM)
    draw   = ImageDraw.Draw(canvas)

    # İçerik sol marjin
    cx = 52
    rw = W - cx * 2   # 976px

    # ── BÖLÜM 1: Hero fotoğraf — tam bleed, köşesiz
    hero_h  = 720
    hero_img = _cover(v.fotolar[0] if v.fotolar else None, (W, hero_h))
    canvas.paste(hero_img, (0, 0))

    # Hero alt gradient — krem renge yumuşak geçiş
    _draw_gradient(canvas, (0, hero_h - 160, W, hero_h), top_alpha=0, bottom_alpha=80, color=(252, 251, 248))

    # ── Sol kırmızı accent şerit — sadece içerik alanında (hero'da değil)
    draw.rectangle([0, hero_h, 6, H], fill=RED)

    # ── Logo — sağ üst, kart içinde (taşmayacak şekilde)
    # FIX 8: logo_bg W-margin içinde kalacak şekilde boyutlandı
    logo_bg_w, logo_bg_h = 196, 56
    logo_bg_x = W - logo_bg_w - 16   # 1080 - 196 - 16 = 868, yani 868+196=1064 < 1080 ✓
    logo_bg = Image.new("RGBA", (logo_bg_w, logo_bg_h), (255, 255, 255, 210))
    canvas.paste(logo_bg, (logo_bg_x, 18), logo_bg)
    _logo(canvas, v.dan_logo, (logo_bg_x + 2, 20, logo_bg_w - 4, logo_bg_h - 4), fallback_size=22)

    # ── "EDITORIAL PORTFÖY" badge — sol alt hero üzerinde
    # FIX 7: RGBA fill yerine RGB (ImageDraw.Draw'da RGBA tuple reliability)
    lbl_x1, lbl_y1 = 28, hero_h - 54
    lbl_x2, lbl_y2 = 240, hero_h - 16
    # Önce opak lacivert arka plan çiz
    draw.rounded_rectangle([lbl_x1, lbl_y1, lbl_x2, lbl_y2], radius=8, fill=NAVY)
    draw.text(
        ((lbl_x1 + lbl_x2) // 2, (lbl_y1 + lbl_y2) // 2),
        "EDITORIAL PORTFÖY", font=_font(15, True), fill=WHITE, anchor="mm"
    )

    # ── BÖLÜM 2: İçerik alanı
    cy = hero_h + 44

    # Fiyat
    fiyat_str = _money(v.fiyat)
    draw.text((cx, cy), fiyat_str, font=_font(84, True), fill=NAVY)
    cy += 100

    # Kırmızı vurgu çizgisi
    draw.rectangle([cx, cy, cx + 60, cy + 4], fill=RED)
    cy += 22

    # Başlık
    title = _title_case(_clean(v.baslik) or _join_clean([v.islem_tipi, v.mulk_tipi, v.ilce], " "))
    for line in _wrap(title, _font(46, True), rw, draw, 2):
        draw.text((cx, cy), line, font=_font(46, True), fill=NAVY)
        cy += 58
    cy += 6

    # Lokasyon
    loc = _join_clean([v.ilce, v.il], "  ·  ")
    if loc:
        draw.text((cx, cy), loc.upper(), font=_font(18), fill=MUTED2)
        cy += 38

    # ── Spec grid: minimal metin çiftleri, eşit kolonlar
    # FIX 6: col_w sabit 220px — her spec kendi kolonunda, sola dayalı
    cy += 20
    specs = _specs(v, include_heating=False)[:4]
    if specs:
        SPEC_COL_W = 220   # sabit kolon genişliği, spec sayısından bağımsız
        for i, (label, txt) in enumerate(specs):
            sx = cx + i * SPEC_COL_W
            if sx + SPEC_COL_W > W - cx:   # sığmıyorsa alt satıra geç
                sy_offset = 80 * ((sx - cx) // (rw + 1))
                sx = cx + (i % (rw // SPEC_COL_W)) * SPEC_COL_W
            draw.text((sx, cy),      _clean(txt),   font=_font(28, True), fill=NAVY)
            draw.text((sx, cy + 34), label.lower(), font=_font(14),        fill=MUTED2)
        cy += 80
    else:
        cy += 20

    # İnce tam genişlik ayraç
    _thin_line(draw, cx, cy, W - cx, cy)
    cy += 28

    # Açıklama
    acik = _clean(v.aciklama)
    if acik:
        for line in _wrap(acik, _font(23), rw, draw, 3):
            draw.text((cx, cy), line, font=_font(23), fill=(60, 75, 100))
            cy += 34
        cy += 20

    # ── Destek fotoğraflar — kaç foto varsa o kadar tile, kart içinde
    # FIX 5: sx hesabı cx'ten başlıyor, taşmıyor
    side_fotos = [raw for raw in v.fotolar[1:4] if raw]
    if side_fotos:
        cy += 4
        n_side    = len(side_fotos)
        side_gap  = 12
        # Toplam genişlik = rw, her tile = (rw - gap*(n-1)) / n
        side_w_px = (rw - side_gap * (n_side - 1)) // n_side
        side_h_px = 240
        for j, raw in enumerate(side_fotos):
            sx = cx + j * (side_w_px + side_gap)   # cx'ten başla, W'yi aşmaz
            simg = _cover(raw, (side_w_px, side_h_px))
            _rounded_paste(canvas, simg, (sx, cy, side_w_px, side_h_px), radius=14)
        cy += side_h_px + 28

    # ── Danışman satırı
    adv_y = cy + 20
    _thin_line(draw, cx, adv_y, W - cx, adv_y)
    adv_y += 22

    avatar = _circle(v.dan_foto, 72, _initials(v.dan_ad))
    canvas.paste(avatar, (cx, adv_y), avatar)

    draw.text((cx + 88, adv_y + 6),  _clean(v.dan_ad, "Danişman"),                font=_font(21, True), fill=NAVY)
    draw.text((cx + 88, adv_y + 32), _clean(v.dan_unvan, "Gayrimenkul Danismani"), font=_font(15),        fill=MUTED2)
    contact = _join_clean([v.dan_telefon, v.dan_email], "  ·  ")
    if contact:
        draw.text((cx + 88, adv_y + 54), contact[:66], font=_font(15), fill=MUTED)

    # ── CTA butonu — FIX 9: daha geniş, danışman bloğunun sağında
    # Danışman avatar+metin toplam ~88+180 = ~268px → CTA sağ tarafta 280px
    cta_w   = 280
    cta_h   = 52
    cta_x1  = W - cx - cta_w
    cta_y1  = adv_y + (72 - cta_h) // 2   # dikey ortalı avatar bloğuna göre
    cta_x2  = W - cx
    cta_y2  = cta_y1 + cta_h
    draw.rounded_rectangle([cta_x1, cta_y1, cta_x2, cta_y2], radius=14, fill=NAVY)
    draw.text(
        ((cta_x1 + cta_x2) // 2, (cta_y1 + cta_y2) // 2),
        "Portföyü İncele", font=_font(19, True), fill=WHITE, anchor="mm"
    )


    # ── Marka değer şeridi — editorial alt bant
    _SERIT_E = [
        ("Güvenilir",      "Profesyonel Hizmet"),
        ("Özel Portföy",   "İlana Çıkmayan Portföyler"),
        ("ZETA Ofisleri",  "Türkiye Genelinde"),
        ("Kalite Odaklı",  "Fark Yaratan Hizmet"),
    ]
    serit_y1_e  = H - 72
    serit_col_e = W // 4
    draw.rectangle([0, serit_y1_e, W, H], fill=(240, 244, 250))
    _thin_line(draw, 8, serit_y1_e, W - 8, serit_y1_e, color=BORDER)
    for i, (bas, alt) in enumerate(_SERIT_E):
        col_cx_e = i * serit_col_e + serit_col_e // 2
        if i > 0:
            _thin_line(draw, i * serit_col_e, serit_y1_e + 10,
                       i * serit_col_e, H - 10, color=BORDER)
        draw.text((col_cx_e, serit_y1_e + 22), bas, font=_font(15, True),
                  fill=NAVY, anchor="mm")
        draw.text((col_cx_e, serit_y1_e + 48), alt, font=_font(12),
                  fill=MUTED2, anchor="mm")

    return canvas


def _portfoy_editorial_story(v: KartVeri) -> Image.Image:
    """Editorial story — tam bleed hero üst %55, içerik alt kart."""
    W, H = 1080, 1920
    canvas = Image.new("RGB", (W, H), CREAM)
    draw = ImageDraw.Draw(canvas)

    # ── Hero — güçlü, tam bleed
    hero_h = 1060
    hero = _cover(v.fotolar[0] if v.fotolar else None, (W, hero_h))
    canvas.paste(hero, (0, 0))

    # Güçlü alt gradient (içerik geçişi için)
    _draw_gradient(canvas, (0, hero_h - 300, W, hero_h), top_alpha=0, bottom_alpha=180)
    # Üst gradient (logo okunabilirliği)
    _draw_gradient(canvas, (0, 0, W, 120), top_alpha=100, bottom_alpha=0)

    # Sol kırmızı şerit — tüm yükseklik
    draw.rectangle([0, 0, 8, H], fill=RED)

    # Logo — sağ üst
    logo_bg_w, logo_bg_h = 192, 54
    logo_bg = Image.new("RGBA", (logo_bg_w, logo_bg_h), (255, 255, 255, 210))
    canvas.paste(logo_bg, (W - logo_bg_w - 16, 18), logo_bg)
    _logo(canvas, v.dan_logo, (W - logo_bg_w - 14, 20, logo_bg_w - 4, logo_bg_h - 4), fallback_size=21)

    # Fiyat + başlık üst hero alt kısmında
    cx = 52
    text_w = W - cx - 40   # sol margin 52, sağ 40 — taşmaz

    fiyat_y = hero_h - 240
    draw.text((cx, fiyat_y), _money(v.fiyat), font=_font(62, True), fill=WHITE)

    # Kırmızı vurgu çizgisi
    draw.rectangle([cx, fiyat_y + 72, cx + 50, fiyat_y + 76], fill=RED)

    title_y = fiyat_y + 88
    title = _clean(v.baslik) or _join_clean([v.islem_tipi, v.mulk_tipi, v.ilce], " ")
    for i, line in enumerate(_wrap(title, _font(40, True), text_w, draw, 2)):
        draw.text((cx, title_y + i * 50), line, font=_font(40, True), fill=WHITE)

    # "EDITORIAL PORTFÖY" badge — sol alt hero
    lbl_x1, lbl_y1 = cx, hero_h - 52
    lbl_x2, lbl_y2 = cx + 240, hero_h - 16
    draw.rounded_rectangle([lbl_x1, lbl_y1, lbl_x2, lbl_y2], radius=8, fill=NAVY)
    draw.text(((lbl_x1 + lbl_x2) // 2, (lbl_y1 + lbl_y2) // 2),
              "EDITORIAL PORTFÖY", font=_font(14, True), fill=WHITE, anchor="mm")

    # ── Alt kart — krem zemin
    card_y = hero_h
    draw.rectangle([0, card_y, W, H], fill=CREAM)

    cy = card_y + 36

    # Lokasyon
    loc = _join_clean([v.ilce, v.il], "  ·  ")
    if loc:
        draw.text((cx, cy), loc.upper(), font=_font(17), fill=MUTED2)
        cy += 36

    # Spec grid — minimal, 3 kolon
    specs = _specs(v, include_heating=False)[:3]
    if specs:
        cy += 10
        SPEC_COL_W = 210
        for i, (label, txt) in enumerate(specs):
            sx = cx + i * SPEC_COL_W
            draw.text((sx, cy),      _clean(txt),   font=_font(26, True), fill=NAVY)
            draw.text((sx, cy + 32), label.lower(), font=_font(13),        fill=MUTED2)
        cy += 72

    # İnce ayraç
    _thin_line(draw, cx, cy, W - cx, cy)
    cy += 20

    # Destek fotoğraflar (2. ve 3. — ikili)
    side_fotos = [raw for raw in v.fotolar[1:3] if raw]
    if side_fotos:
        n = len(side_fotos)
        gap_s = 10
        sw = (W - cx * 2 - gap_s * (n - 1)) // n
        sh = 200
        for j, raw in enumerate(side_fotos):
            sx = cx + j * (sw + gap_s)
            simg = _cover(raw, (sw, sh))
            _rounded_paste(canvas, simg, (sx, cy, sw, sh), radius=12)
        cy += sh + 22
        _thin_line(draw, cx, cy, W - cx, cy)
        cy += 20

    # CTA
    cta_x2 = W - cx
    draw.rounded_rectangle([cx, cy, cta_x2, cy + 68], radius=18, fill=NAVY)
    draw.text(((cx + cta_x2) // 2, cy + 34), "Portföyü İncele", font=_font(22, True), fill=WHITE, anchor="mm")
    cy += 88

    # Danışman
    avatar = _circle(v.dan_foto, 72, _initials(v.dan_ad))
    canvas.paste(avatar, (cx, cy), avatar)
    draw.text((cx + 88, cy + 8),  _clean(v.dan_ad, "Danışman"),    font=_font(20, True), fill=NAVY)
    draw.text((cx + 88, cy + 34), _clean(v.dan_unvan, "Gayrimenkul Danışmanı"), font=_font(14), fill=MUTED2)
    if not _is_blank(v.dan_telefon):
        draw.text((cx + 88, cy + 54), _clean(v.dan_telefon), font=_font(14), fill=MUTED)

    return canvas


# ─────────────────────────────────────────────────────────────────────────────
# TALEP B2B — yatay operasyon kartı (değişmedi)
# ─────────────────────────────────────────────────────────────────────────────

def _metric(draw, x, y, w, h, icon, label, value, sub="", color=BLUE):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=0, fill=WHITE)
    draw.ellipse([x + 28, y + 28, x + 92, y + 92], fill=tuple(list(color) + [60]) if len(color) == 4 else (color[0], color[1], color[2], 42))
    draw.text((x + 60, y + 60), icon, font=_font(30, True), fill=color, anchor="mm")
    draw.text((x + 120, y + 32), label.upper(), font=_font(21, True), fill=NAVY)
    draw.text((x + 120, y + 70), value or "—",  font=_font(28, True), fill=NAVY)
    if sub:
        draw.text((x + 120, y + 112), sub, font=_font(16), fill=NAVY)
    draw.line([x + w - 1, y + 18, x + w - 1, y + h - 18], fill=BORDER, width=1)


def _pill(draw, x, y, text, ok=True, max_w=245):
    color   = GREEN if ok else (220, 38, 38)
    bg      = (240, 253, 244) if ok else (255, 241, 242)
    outline = (168, 224, 178) if ok else (252, 180, 180)
    f   = _font(19, True)
    txt = ("OK: " if ok else "NO: ") + str(text)
    tw  = min(max_w, int(draw.textlength(txt, font=f)) + 38)
    draw.rounded_rectangle([x, y, x + tw, y + 44], radius=14, fill=bg, outline=outline, width=1)
    draw.text((x + 19, y + 22), txt, font=f, fill=(13, 35, 76), anchor="lm")
    return tw


def _render_talep_b2b(v: KartVeri, W=1200, H=950) -> Image.Image:
    canvas = Image.new("RGB", (W, H), (245, 247, 250))
    draw   = ImageDraw.Draw(canvas)
    margin = 34
    draw.rounded_rectangle([margin, 26, W-margin, H-26], radius=28, fill=WHITE, outline=(224,231,242), width=2)

    _logo(canvas, v.dan_logo, (margin + 28, 44, 210, 76), fallback_size=30)
    badge = [W - margin - 178, 52, W - margin - 34, 94]
    draw.rounded_rectangle(badge, radius=18, fill=(240, 253, 244), outline=GREEN, width=1)
    draw.text(((badge[0]+badge[2])//2, (badge[1]+badge[3])//2), "AKTIF TALEP", font=_font(17, True), fill=GREEN, anchor="mm")
    talep_no = _clean(v.talep_no, "T-0001")
    tarih    = _clean(v.talep_tarihi, datetime.now().strftime("%d.%m.%Y"))
    draw.text((W - margin - 205, 58), f"Talep No: {talep_no}", font=_font(17, True), fill=MUTED, anchor="ra")
    draw.text((W - margin - 205, 84), tarih,                   font=_font(16),        fill=MUTED, anchor="ra")

    y = 132
    x = margin + 42
    title = _clean(v.baslik) or _join_clean([v.islem_tipi, v.mulk_tipi, "Arayisi"], " ")
    for line in _wrap(title, _font(38, True), W - 2*margin - 84, draw, 2):
        draw.text((x, y), line, font=_font(38, True), fill=NAVY)
        y += 46
    loc = _join_clean([v.hedef_bolge or v.ilce, v.il], " / ")
    if loc:
        draw.text((x, y + 4), loc, font=_font(21), fill=MUTED)
    y += 58

    metric_y  = y
    gap       = 12
    metric_w  = (W - 2*margin - 84 - gap*4) // 5
    metrics   = [
        ("BUTCE",  _clean(v.butce) or (_money(v.fiyat) if not _is_blank(v.fiyat) else "")),
        ("METRAJ", _clean(v.metraj_araligi) or (f"{_clean(v.m2)} m2" if not _is_blank(v.m2) else "")),
        ("ODA",    _clean(v.oda_araligi) or _clean(v.oda)),
        ("KAT",    _clean(v.kat_araligi) or _clean(v.kat)),
        ("ISLEM",  _join_clean([v.islem_tipi, v.mulk_tipi], " / ")),
    ]
    for i, (label, value) in enumerate(metrics):
        mx = x + i * (metric_w + gap)
        draw.rounded_rectangle([mx, metric_y, mx + metric_w, metric_y + 108], radius=18, fill=(248,250,252), outline=(224,231,242), width=1)
        draw.text((mx + 18, metric_y + 24), label, font=_font(14, True), fill=MUTED)
        display = _clean(value, "-")
        for line in _wrap(display, _font(21, True), metric_w - 36, draw, 2)[:2]:
            draw.text((mx + 18, metric_y + 56), line, font=_font(21, True), fill=NAVY)
            break
    y = metric_y + 138

    draw.text((x, y), "KRITERLER", font=_font(17, True), fill=MUTED)
    y += 30
    kriterler = [_clean(k) for k in (v.zorunlu_kriterler or v.ozellikler or []) if not _is_blank(k)]
    negatif   = [_clean(k) for k in (v.negatif_kriterler or []) if not _is_blank(k)]
    if not kriterler and not negatif:
        kriterler = [t for t in [_clean(v.ilce), _clean(v.oda), _clean(v.m2)] if t]
    cx, cy = x, y
    for k in kriterler[:7]:
        text = k[:34]
        tw   = min(300, max(110, int(draw.textlength(text, font=_font(17, True))) + 34))
        if cx + tw > W - margin - 42:
            cx = x; cy += 50
        draw.rounded_rectangle([cx, cy, cx + tw, cy + 38], radius=16, fill=(239,246,255), outline=(191,219,254), width=1)
        draw.text((cx + 17, cy + 19), text, font=_font(17, True), fill=NAVY, anchor="lm")
        cx += tw + 10
    for k in negatif[:3]:
        text = "Degil: " + k[:28]
        tw   = min(310, max(130, int(draw.textlength(text, font=_font(17, True))) + 34))
        if cx + tw > W - margin - 42:
            cx = x; cy += 50
        draw.rounded_rectangle([cx, cy, cx + tw, cy + 38], radius=16, fill=(255,241,242), outline=(252,180,180), width=1)
        draw.text((cx + 17, cy + 19), text, font=_font(17, True), fill=(127,29,29), anchor="lm")
        cx += tw + 10
    y = cy + 70

    note = _clean(v.danisman_notu) or _clean(v.aciklama)
    draw.rounded_rectangle([x, y, W - margin - 42, y + 150], radius=22, fill=(250,252,255), outline=(224,231,242), width=1)
    draw.text((x + 28, y + 30), "DANISMAN NOTU", font=_font(16, True), fill=MUTED)
    if note:
        ty = y + 62
        for line in _wrap(note, _font(20), W - 2*margin - 150, draw, 3):
            draw.text((x + 28, ty), line, font=_font(20), fill=TEXT)
            ty += 29
    else:
        draw.text((x + 28, y + 70), "Uygun portfoylerinizi paylasmanizi rica ederiz.", font=_font(20), fill=TEXT)
    y += 176

    footer_y = H - 170
    draw.rounded_rectangle([x, footer_y, W - margin - 42, H - 58], radius=24, fill=NAVY)
    avatar = _circle(v.dan_foto, 78, _initials(v.dan_ad))
    canvas.paste(avatar, (x + 26, footer_y + 24), avatar)
    draw.text((x + 126, footer_y + 34), _clean(v.dan_ad, "Gayrimenkul Danismani"),     font=_font(22, True), fill=WHITE)
    draw.text((x + 126, footer_y + 64), _clean(v.dan_unvan, "Startkey Zeta Gayrimenkul"), font=_font(16),        fill=(216,226,241))
    contact = _join_clean([v.dan_telefon, v.dan_email], "  |  ")
    if contact:
        draw.text((x + 126, footer_y + 92), contact[:78], font=_font(16), fill=(238,242,248))

    qx, qy, qs = W - margin - 170, footer_y + 22, 86
    draw.rounded_rectangle([qx, qy, qx + qs, qy + qs], radius=10, fill=WHITE)
    draw.rectangle([qx+16, qy+16, qx+32, qy+32], outline=NAVY, width=4)
    draw.rectangle([qx+54, qy+16, qx+70, qy+32], outline=NAVY, width=4)
    draw.rectangle([qx+16, qy+54, qx+32, qy+70], outline=NAVY, width=4)
    for i in range(7):
        xx = qx + 40 + (i % 3) * 10
        yy = qy + 42 + (i // 3) * 10
        draw.rectangle([xx, yy, xx+6, yy+6], fill=NAVY)
    draw.text((qx + qs//2, qy + qs + 22), "QR", font=_font(13, True), fill=(216,226,241), anchor="mm")
    return canvas


def _talep_story(v: KartVeri) -> Image.Image:
    base = _render_talep_b2b(v, 1600, 1067)
    base.thumbnail((1040, 700), Image.LANCZOS)
    canvas = Image.new("RGB", (1080, 1920), (245, 247, 250))
    d = ImageDraw.Draw(canvas)
    d.text((540, 110), "STARTKEY ZETA · TALEP SUNUMU", font=_font(28, True), fill=NAVY, anchor="mm")
    canvas.paste(base, ((1080 - base.width)//2, 180))
    d.text((540, 960),  v.baslik or f"{v.islem_tipi} {v.mulk_tipi} Arayisi", font=_font(42, True), fill=NAVY,  anchor="mm")
    d.text((540, 1030), v.hedef_bolge or v.ilce or "Hedef bolge",             font=_font(28),        fill=MUTED, anchor="mm")
    return canvas


# ─────────────────────────────────────────────────────────────────────────────
# RENDERER TABLOSU
# ─────────────────────────────────────────────────────────────────────────────

_RENDERERS = {
    "portfoy_premium":   (_render_portfoy_premium,   _portfoy_story),
    "portfoy_gallery":   (_render_portfoy_gallery,   _portfoy_gallery_story),
    "portfoy_editorial": (_render_portfoy_editorial, _portfoy_editorial_story),
    "talep_b2b":         (_render_talep_b2b,         _talep_story),
    # Eski anahtarlar — kırılmasın
    "startkey_klasik":   (_render_portfoy_premium,   _portfoy_story),
    "story_split":       (_render_portfoy_premium,   _portfoy_story),
    "koyu_premium":      (_render_portfoy_premium,   _portfoy_story),
}


def render_bytes(sablon_key: str, veri: KartVeri) -> tuple[bytes, bytes]:
    kare_fn, story_fn = _RENDERERS.get(sablon_key, _RENDERERS["portfoy_premium"])
    return _to_bytes(kare_fn(veri)), _to_bytes(story_fn(veri))


def thumbnail(sablon_key: str, veri: KartVeri, size: int = 200) -> Image.Image:
    kare_fn, _ = _RENDERERS.get(sablon_key, _RENDERERS["portfoy_premium"])
    img = kare_fn(veri)
    if img is None:
        return Image.new("RGB", (size, size), WHITE)
    out = img.copy()
    if max(out.width, out.height) > size:
        out.thumbnail((size, size), Image.LANCZOS)
    return out


def avatar_crop_was_used() -> bool:
    return _AVATAR_CROP_USED


# ─────────────────────────────────────────────────────────────────────────────
# HTML ÇIKTI YARDIMCILARI
# ─────────────────────────────────────────────────────────────────────────────

def _veri_to_b64_cover(v: KartVeri) -> str:
    if not v.fotolar:
        return ""
    raw = v.fotolar[0]
    if isinstance(raw, (bytes, bytearray)):
        img = _read_image(raw)
        if img is None:
            return ""
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=85)
        b64 = __import__("base64").b64encode(buf.getvalue()).decode()
        return f"data:image/jpeg;base64,{b64}"
    if isinstance(raw, str) and raw.startswith("http"):
        return raw
    return ""


def _avatar_b64(raw: Optional[bytes]) -> str:
    if not raw:
        return ""
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        img.thumbnail((80, 80), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=85)
        return "data:image/jpeg;base64," + __import__("base64").b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


def _gallery_b64_items(fotolar: list, max_count: int = 6, thumb_w: int = 320, thumb_h: int = 220) -> list[str]:
    """Galeri için base64 src listesi üret (2. foto'dan başlar)."""
    srcs = []
    for raw in fotolar[1:max_count + 1]:
        src = ""
        if isinstance(raw, (bytes, bytearray)):
            try:
                img = Image.open(io.BytesIO(raw)).convert("RGB")
                img.thumbnail((thumb_w, thumb_h), Image.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, "JPEG", quality=76)
                src = "data:image/jpeg;base64," + __import__("base64").b64encode(buf.getvalue()).decode()
            except Exception:
                pass
        elif isinstance(raw, str) and raw.startswith("http"):
            src = raw
        if src:
            srcs.append(src)
    return srcs


# ─────────────────────────────────────────────────────────────────────────────
# HTML ÇIKTI: MAIL BROŞÜRÜ
# Sprint v2: marka dili PNG şablonlarıyla hizalandı
# ─────────────────────────────────────────────────────────────────────────────

def render_mail_html(v: KartVeri, sablon_id: str = "portfoy_premium") -> str:
    title    = _clean(v.baslik) or _join_clean([v.islem_tipi, v.mulk_tipi, v.ilce], " | ")
    fiyat    = _money(v.fiyat)
    loc      = _join_clean([v.ilce, v.il], " / ")
    m2       = _clean(v.m2)
    oda      = _clean(v.oda)
    kat      = _clean(v.kat)
    dan      = _clean(v.dan_ad, "Gayrimenkul Danışmanı")
    unvan    = _clean(v.dan_unvan, "Gayrimenkul Danışmanı")
    tel      = _clean(v.dan_telefon)
    tel_clean = "".join(c for c in tel if c.isdigit() or c == "+")
    acik     = _clean(v.aciklama)

    # Kapak
    cover_src   = _veri_to_b64_cover(v)
    cover_block = (
        f'<div style="line-height:0;">'
        f'<img src="{cover_src}" style="width:100%;max-height:480px;object-fit:cover;display:block;"></div>'
        if cover_src else
        '<div style="height:220px;background:#0a2348;display:flex;align-items:center;justify-content:center;">'
        '<span style="color:#4a6fa5;font-size:14px;font-weight:600;letter-spacing:.08em;">STARTKEY ZETA</span></div>'
    )

    # Galeri
    gallery_srcs = _gallery_b64_items(v.fotolar, max_count=5, thumb_w=300, thumb_h=200)
    gallery_items_html = "".join(
        f'<div style="flex:0 0 calc(33.33% - 6px);min-width:0;">'
        f'<img src="{src}" style="width:100%;height:140px;object-fit:cover;border-radius:6px;display:block;"></div>'
        for src in gallery_srcs
    )
    gallery_block = (
        f'<div style="padding:0 32px 24px;">'
        f'<div style="font-size:9px;font-weight:700;color:#8898aa;letter-spacing:.14em;text-transform:uppercase;margin-bottom:10px;">FOTOĞRAFLAR</div>'
        f'<div style="display:flex;flex-wrap:wrap;gap:8px;">{gallery_items_html}</div></div>'
        if gallery_items_html else ""
    )

    # Özellik rozetleri — NAVY_LIGHT zemin, marka uyumlu
    ozellikler = [_clean(o) for o in (v.ozellikler or []) if not _is_blank(o)]
    badges_html = "".join(
        f'<span style="display:inline-block;background:#eaf0fb;color:#0a234e;border:1px solid #c5d4ee;'
        f'padding:5px 13px;border-radius:999px;font-size:13px;font-weight:600;margin:3px 6px 3px 0;">{o}</span>'
        for o in ozellikler[:8]
    ) or '<span style="color:#8898aa;font-size:13px;">Detay için iletişime geçiniz</span>'

    acik_block = (
        f'<div style="margin-top:18px;padding:14px 16px;background:#f7f9fc;border-left:3px solid #c5122a;'
        f'border-radius:0 8px 8px 0;font-size:14px;color:#334155;line-height:1.65;">{acik}</div>'
        if acik else ""
    )

    # Specs satırı
    specs_parts = []
    if m2:  specs_parts.append(f"{m2} m²")
    if oda: specs_parts.append(oda)
    if kat: specs_parts.append(f"Kat: {kat}")
    if v.mulk_tipi and not _is_blank(v.mulk_tipi): specs_parts.append(_clean(v.mulk_tipi))
    specs_line = "  ·  ".join(specs_parts)

    # Avatar
    avatar_src   = _avatar_b64(v.dan_foto)
    avatar_block = (
        f'<img src="{avatar_src}" style="width:54px;height:54px;border-radius:50%;object-fit:cover;'
        f'border:2px solid #c5d4ee;flex-shrink:0;">'
        if avatar_src else
        f'<div style="width:54px;height:54px;border-radius:50%;background:#0a2348;display:flex;'
        f'align-items:center;justify-content:center;font-size:18px;font-weight:800;color:#fff;flex-shrink:0;">'
        f'{"".join(w[0].upper() for w in dan.split()[:2]) or "SK"}</div>'
    )

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#eef2f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
<div style="max-width:660px;margin:32px auto 48px;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 32px rgba(10,35,78,.10);">

  <!-- HEADER BAR -->
  <div style="background:#0a2348;padding:26px 32px 22px;display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <div style="font-size:9px;letter-spacing:.18em;color:#4a6fa5;text-transform:uppercase;margin-bottom:10px;">
        STARTKEY ZETA · PORTFÖY SUNUMU
      </div>
      <div style="font-size:22px;font-weight:800;color:#fff;line-height:1.25;margin-bottom:6px;">{title}</div>
      <div style="font-size:12px;color:#8eb4e8;">📍 {loc}</div>
    </div>
    <div style="font-size:9px;font-weight:700;color:#c5122a;letter-spacing:.12em;text-align:right;padding-top:4px;">
      STARTKEY<br><span style="color:#4a6fa5;font-weight:600;letter-spacing:.06em;">ZETA GAYRİMENKUL</span>
    </div>
  </div>

  <!-- KAPAK -->
  {cover_block}

  <!-- FİYAT + DETAYLAR -->
  <div style="padding:28px 32px 0;">
    <div style="font-size:38px;font-weight:900;color:#0a2348;letter-spacing:-.02em;line-height:1;">{fiyat}</div>
    {f'<div style="font-size:13px;color:#8898aa;margin-top:8px;letter-spacing:.02em;">{specs_line}</div>' if specs_line else ''}

    <!-- Kırmızı vurgu çizgisi -->
    <div style="width:48px;height:3px;background:#c5122a;border-radius:2px;margin:18px 0 16px;"></div>

    <div>
      <div style="font-size:9px;font-weight:700;color:#8898aa;letter-spacing:.14em;text-transform:uppercase;margin-bottom:10px;">
        ÖNE ÇIKAN ÖZELLİKLER
      </div>
      {badges_html}
    </div>
    {acik_block}
  </div>

  <!-- GALERİ -->
  {gallery_block}

  <!-- İNCE AYRAÇ -->
  <div style="margin:0 32px;height:1px;background:#e8edf5;"></div>

  <!-- DANIŞMAN -->
  <div style="padding:20px 32px 24px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:14px;">
    <div style="display:flex;align-items:center;gap:14px;">
      {avatar_block}
      <div>
        <div style="font-size:15px;font-weight:800;color:#0a2348;">{dan}</div>
        <div style="font-size:12px;color:#8898aa;margin-top:2px;">{unvan}</div>
        {f'<div style="font-size:13px;color:#334155;font-weight:600;margin-top:4px;">{tel}</div>' if tel else ''}
      </div>
    </div>
    {f'<a href="https://wa.me/{tel_clean}" style="display:inline-block;background:#25D366;color:#fff;padding:10px 20px;border-radius:8px;font-weight:700;font-size:13px;text-decoration:none;white-space:nowrap;">💬 WhatsApp</a>' if tel_clean else ''}
  </div>

  <!-- FOOTER -->
  <div style="background:#f3f6fb;border-top:1px solid #e8edf5;padding:14px 32px;text-align:center;">
    <div style="font-size:11px;color:#aab4c4;">Bu sunum Startkey Zeta ile oluşturulmuştur. © 2026</div>
  </div>

</div>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# HTML ÇIKTI: LANDING SAYFASI
# Sprint v2: hero gradient güçlendirildi, CTA büyütüldü, marka dili hizalandı
# ─────────────────────────────────────────────────────────────────────────────

def render_landing_html(v: KartVeri, sablon_id: str = "portfoy_premium") -> str:
    title    = _clean(v.baslik) or _join_clean([v.islem_tipi, v.mulk_tipi, v.ilce], " | ")
    fiyat    = _money(v.fiyat)
    loc      = _join_clean([v.ilce, v.il], " / ")
    m2       = _clean(v.m2)
    oda      = _clean(v.oda)
    kat      = _clean(v.kat)
    dan      = _clean(v.dan_ad, "Gayrimenkul Danışmanı")
    unvan    = _clean(v.dan_unvan, "Gayrimenkul Danışmanı")
    tel      = _clean(v.dan_telefon)
    tel_clean = "".join(c for c in tel if c.isdigit() or c == "+")
    acik     = _clean(v.aciklama)

    cover_src  = _veri_to_b64_cover(v)
    hero_style = (
        f"background-image:linear-gradient(180deg,rgba(10,35,78,.32) 0%,rgba(10,35,78,.72) 60%,rgba(10,35,78,.92) 100%),url({cover_src});"
        f"background-size:cover;background-position:center;"
        if cover_src else "background:linear-gradient(135deg,#0a2348,#163a72);"
    )

    # Hero özellik rozetleri
    ozellikler = [_clean(o) for o in (v.ozellikler or []) if not _is_blank(o)]
    hero_badges = "".join(
        f'<span style="display:inline-block;background:rgba(255,255,255,.15);backdrop-filter:blur(4px);'
        f'color:#fff;border:1px solid rgba(255,255,255,.25);'
        f'padding:5px 14px;border-radius:999px;font-size:13px;font-weight:600;margin:3px 5px 3px 0;">{o}</span>'
        for o in ozellikler[:5]
    )

    # Spec grid
    specs = []
    if m2:          specs.append(("M²",        m2,               "Alan"))
    if oda:         specs.append(("ODA",        oda,              "Oda"))
    if kat:         specs.append(("KAT",        kat,              "Kat"))
    if v.bina_yasi: specs.append(("YAŞ",        _clean(v.bina_yasi), "Bina Yaşı"))
    specs_html = "".join(
        f'<div style="flex:1;min-width:90px;background:#f3f6fb;border-radius:10px;padding:16px 12px;text-align:center;border:1px solid #e2e8f3;">'
        f'<div style="font-size:9px;font-weight:700;color:#8898aa;letter-spacing:.12em;margin-bottom:6px;">{label}</div>'
        f'<div style="font-size:22px;font-weight:900;color:#0a2348;">{val}</div>'
        f'<div style="font-size:11px;color:#aab4c4;margin-top:2px;">{sub}</div>'
        f'</div>'
        for label, val, sub in specs
    ) if specs else ""

    # Galeri
    gallery_srcs = _gallery_b64_items(v.fotolar, max_count=5, thumb_w=380, thumb_h=260)
    gallery_html = "".join(
        f'<div style="flex:0 0 calc(33.33% - 8px);min-width:0;">'
        f'<img src="{src}" style="width:100%;height:168px;object-fit:cover;border-radius:10px;display:block;"></div>'
        for src in gallery_srcs
    )
    gallery_block = (
        f'<div style="margin:28px 0;">'
        f'<div style="font-size:9px;font-weight:700;color:#8898aa;text-transform:uppercase;letter-spacing:.14em;margin-bottom:12px;">FOTOĞRAFLAR</div>'
        f'<div style="display:flex;flex-wrap:wrap;gap:10px;">{gallery_html}</div></div>'
        if gallery_html else ""
    )

    acik_block = (
        f'<div style="background:#f3f6fb;border-left:3px solid #c5122a;border-radius:0 10px 10px 0;'
        f'padding:18px 20px;margin:24px 0;">'
        f'<div style="font-size:9px;font-weight:700;color:#8898aa;text-transform:uppercase;letter-spacing:.12em;margin-bottom:8px;">AÇIKLAMA</div>'
        f'<div style="font-size:15px;color:#334155;line-height:1.7;">{acik}</div></div>'
        if acik else ""
    )

    avatar_src   = _avatar_b64(v.dan_foto)
    avatar_block = (
        f'<img src="{avatar_src}" style="width:64px;height:64px;border-radius:50%;object-fit:cover;border:3px solid #c5d4ee;">'
        if avatar_src else
        f'<div style="width:64px;height:64px;border-radius:50%;background:#0a2348;display:flex;align-items:center;'
        f'justify-content:center;font-size:22px;font-weight:800;color:#fff;">'
        f'{"".join(w[0].upper() for w in dan.split()[:2]) or "SK"}</div>'
    )

    # CTA butonları — f-string dışında hazırla (Python 3.11 backslash uyumu)
    _wa_label  = "\U0001f4ac WhatsApp'tan Bilgi Al"
    _tel_label = "\U0001f4de Hemen Ara"
    wa_btn  = (
        f'<a href="https://wa.me/{tel_clean}" class="cta-btn"'
        f' style="background:#25D366;color:#fff;">{_wa_label}</a>'
        if tel_clean else ""
    )
    tel_btn = (
        f'<a href="tel:{tel}" class="cta-btn"'
        f' style="background:#0a2348;color:#fff;">{_tel_label}</a>'
        if tel else ""
    )

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — Startkey Zeta</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0;}}
    body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;background:#eef2f7;color:#0a2348;}}
    .wrap{{max-width:740px;margin:0 auto;background:#fff;min-height:100vh;}}
    .cta-row{{display:flex;gap:12px;flex-wrap:wrap;}}
    .cta-btn{{flex:1;display:block;padding:16px 20px;border-radius:10px;font-weight:700;font-size:15px;text-decoration:none;text-align:center;min-width:180px;}}
    @media(max-width:580px){{.specs-row{{flex-direction:column!important;}}.cta-row{{flex-direction:column;}}}}
  </style>
</head>
<body>
<div class="wrap">

  <!-- HERO -->
  <div style="min-height:400px;display:flex;flex-direction:column;justify-content:flex-end;padding:36px 36px 32px;{hero_style}">
    <div style="font-size:9px;letter-spacing:.18em;color:rgba(255,255,255,.55);text-transform:uppercase;margin-bottom:10px;">
      STARTKEY ZETA · PORTFÖY
    </div>
    <div style="font-size:30px;font-weight:900;color:#fff;line-height:1.2;margin-bottom:8px;">{title}</div>
    <div style="font-size:13px;color:rgba(255,255,255,.72);margin-bottom:{('14px' if hero_badges else '0')};letter-spacing:.02em;">📍 {loc}</div>
    {f'<div>{hero_badges}</div>' if hero_badges else ''}
  </div>

  <!-- FİYAT -->
  <div style="padding:28px 36px 0;">
    <div style="font-size:44px;font-weight:900;color:#0a2348;letter-spacing:-.02em;line-height:1;">{fiyat}</div>
    <div style="width:48px;height:3px;background:#c5122a;border-radius:2px;margin:14px 0 20px;"></div>

    <!-- SPEC GRID -->
    {f'<div class="specs-row" style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:24px;">{specs_html}</div>' if specs_html else ''}

    <!-- AÇIKLAMA -->
    {acik_block}

    <!-- GALERİ -->
    {gallery_block}

    <!-- İNCE AYRAÇ -->
    <div style="height:1px;background:#e2e8f3;margin:8px 0 24px;"></div>

    <!-- DANIŞMAN -->
    <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:24px;">
      {avatar_block}
      <div style="flex:1;min-width:160px;">
        <div style="font-size:17px;font-weight:800;color:#0a2348;">{dan}</div>
        <div style="font-size:12px;color:#8898aa;margin-top:2px;">{unvan} · Startkey Zeta</div>
        {f'<div style="font-size:14px;color:#1a3a6e;font-weight:700;margin-top:6px;">{tel}</div>' if tel else ''}
      </div>
    </div>

    <!-- CTA BUTONLARI -->
    <div class="cta-row" style="margin-bottom:32px;">
      {wa_btn}
      {tel_btn}
    </div>
  </div>

  <!-- FOOTER -->
  <div style="background:#0a2348;padding:18px 36px;text-align:center;">
    <div style="font-size:11px;color:#4a6fa5;">Bu sayfa Startkey Zeta ile oluşturulmuştur. © 2026</div>
  </div>

</div>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# PDF BROŞÜR  —  A4, tek sayfa, Startkey Zeta marka dili
# reportlab canvas tabanlı; QR kod + URL desteği
# ─────────────────────────────────────────────────────────────────────────────

def _qr_image(url: str, size_px: int = 160) -> Image.Image:
    """URL'den QR kodu PIL Image olarak üret."""
    try:
        import qrcode as _qrcode
        qr = _qrcode.QRCode(
            version=1,
            error_correction=_qrcode.constants.ERROR_CORRECT_M,
            box_size=4,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color=(10, 35, 78), back_color="white").convert("RGB")
        img = img.resize((size_px, size_px), Image.LANCZOS)
        return img
    except Exception:
        return Image.new("RGB", (size_px, size_px), (255, 255, 255))


def _pil_to_rl_image(pil_img: Image.Image) -> str:
    """PIL Image'i geçici JPEG dosyasına yaz, yolunu döndür."""
    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    pil_img.convert("RGB").save(tmp.name, "JPEG", quality=85)
    tmp.close()
    return tmp.name


def _rl_color(rgb: tuple):
    """RGB tuple → ReportLab Color."""
    from reportlab.lib.colors import Color
    return Color(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)


def _rl_font_setup():
    """
    Türkçe karakter desteği için TTF font kaydet.
    Windows/Linux sistem fontlarını dener, bulamazsa Helvetica fallback.
    Döndürür: (bold_name, regular_name) — PDF'de kullanılacak font adları.
    """
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import os

        candidates = [
            # Windows
            ("C:/Windows/Fonts/calibrib.ttf",  "C:/Windows/Fonts/calibri.ttf"),
            ("C:/Windows/Fonts/arialbd.ttf",   "C:/Windows/Fonts/arial.ttf"),
            ("C:/Windows/Fonts/verdanab.ttf",  "C:/Windows/Fonts/verdana.ttf"),
            # Linux
            ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            ("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        ]
        for bold_path, reg_path in candidates:
            if os.path.exists(bold_path) and os.path.exists(reg_path):
                pdfmetrics.registerFont(TTFont("SK-Bold",    bold_path))
                pdfmetrics.registerFont(TTFont("SK-Regular", reg_path))
                return "SK-Bold", "SK-Regular"
    except Exception:
        pass
    # Fallback — Türkçe karakterler bozulabilir ama çökmez
    return "Helvetica-Bold", "Helvetica"


# Marka değer şeridi — GD tarafından config.py'den veya sabit tanımlanabilir
PDF_MARKA_SERIT = [
    ("Guvenilir",        "Profesyonel Hizmet"),
    ("Ozel Portfoy Agi", "Ilana Cikmayan Seckin Portfoyler"),
    ("ZETA Ofisleri",    "Turkiye Genelinde Guclu Ag"),
    ("Kalite Odakli",    "Fark Yaratan Hizmet Anlayisi"),
]


def render_pdf_brosur(
    v: KartVeri,
    landing_url: str = "",
    gd_notu: str = "",
) -> bytes:
    """
    KartVeri + opsiyonel landing URL + GD notu → A4 PDF broşür (bytes).
    Türkçe TTF font desteği, marka değer şeridi, durum bazlı GD notu.
    reportlab kurulu değilse ImportError fırlatır.
    """
    try:
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.utils import ImageReader
    except ImportError:
        raise ImportError(
            "PDF brosur icin 'reportlab' paketi gerekli. "
            "Terminalde: pip install reportlab qrcode"
        )

    import io as _io

    # ── Font kurulumu (Türkçe karakter desteği)
    F_BOLD, F_REG = _rl_font_setup()

    # ── Renkler
    C_NAVY  = _rl_color((10, 35, 78))
    C_RED   = _rl_color((190, 24, 35))
    C_MUTED = _rl_color((90, 104, 130))
    C_WHITE = _rl_color((255, 255, 255))
    C_BORDER= _rl_color((218, 226, 238))
    C_NAVY_L= _rl_color((235, 240, 250))
    C_SOFT  = _rl_color((247, 250, 253))
    C_STRIP = _rl_color((240, 244, 250))   # marka şerit zemin

    # ── Boyutlar
    PW, PH = A4        # 595 × 842 pt
    M  = 28
    CW = PW - 2 * M    # 539 pt

    # ── Yardımcı: ASCII-safe metin (font yoksa bozulmayı önle)
    def _sf(text: str) -> str:
        """Font TTF ise orijinal döndür, Helvetica ise ASCII-safe."""
        if F_BOLD == "Helvetica-Bold":
            # Türkçe karakterleri ASCII karşılıklarıyla değiştir
            TR = str.maketrans(
                "çÇğĞıIİöÖşŞüÜ",
                "cCgGiIiooSsSuU"  # noqa: RUF001
            )
            return text.translate(TR)
        return text

    def _img_reader(raw):
        if not raw:
            return None
        try:
            pil = Image.open(_io.BytesIO(raw)).convert("RGB")
            buf = _io.BytesIO()
            pil.save(buf, "JPEG", quality=82)
            buf.seek(0)
            return ImageReader(buf)
        except Exception:
            return None

    def _cover_reader(raw, w_px, h_px):
        if not raw:
            return None
        try:
            pil = _cover(raw, (int(w_px * 2), int(h_px * 2)))
            buf = _io.BytesIO()
            pil.save(buf, "JPEG", quality=85)
            buf.seek(0)
            return ImageReader(buf)
        except Exception:
            return None

    def _draw_str(cx, cy, text, font, size, color, anchor="left"):
        c.setFillColor(color)
        c.setFont(font, size)
        safe = _sf(str(text or ""))
        if anchor == "center":
            c.drawCentredString(cx, cy, safe)
        elif anchor == "right":
            c.drawRightString(cx, cy, safe)
        else:
            c.drawString(cx, cy, safe)

    # ── PDF buffer
    buf = _io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    c.setTitle(_sf(_title_case(_clean(v.baslik) or "Portfoy Sunumu")))

    # ─── BÖLÜM 1: ÜST BAR ────────────────────────────────────────────────
    BAR_H = 36
    bar_y = PH - BAR_H
    c.setFillColor(C_NAVY)
    c.rect(0, bar_y, PW, BAR_H, fill=1, stroke=0)

    _draw_str(M, bar_y + 14, "STARTKEY", F_BOLD, 9, C_WHITE)
    _draw_str(M, bar_y + 5,  "ZETA GAYRIMENKUL", F_REG, 7, _rl_color((138, 180, 232)))

    islem     = _clean(v.islem_tipi, "SATILIK").upper()
    mulk      = _clean(v.mulk_tipi, "Konut")
    badge_txt = _sf(f"{islem} | {mulk}")
    c.setFont(F_BOLD, 8)
    badge_w = c.stringWidth(badge_txt, F_BOLD, 8) + 20
    c.setFillColor(C_RED)
    c.roundRect(PW - M - badge_w, bar_y + 7, badge_w, 20, 4, fill=1, stroke=0)
    c.setFillColor(C_WHITE)
    c.setFont(F_BOLD, 8)
    c.drawCentredString(PW - M - badge_w / 2, bar_y + 14, badge_txt)

    _draw_str(PW - M - badge_w - 8, bar_y + 14,
              _sf("Yeni Portfoy"), F_REG, 7, _rl_color((138, 180, 232)), anchor="right")

    # ─── BÖLÜM 2: KAPAK FOTOĞRAFI ─────────────────────────────────────────
    COVER_H = 240
    cover_y = bar_y - COVER_H
    cover_ir = _cover_reader(v.fotolar[0] if v.fotolar else None, CW, COVER_H)
    if cover_ir:
        c.drawImage(cover_ir, M, cover_y, width=CW, height=COVER_H,
                    preserveAspectRatio=False, mask="auto")
    else:
        c.setFillColor(C_NAVY_L)
        c.rect(M, cover_y, CW, COVER_H, fill=1, stroke=0)
        _draw_str(PW / 2, cover_y + COVER_H / 2, "Fotograf Yok",
                  F_REG, 10, C_MUTED, anchor="center")

    # Sol kırmızı şerit
    c.setFillColor(C_RED)
    c.rect(0, cover_y, 5, COVER_H, fill=1, stroke=0)

    # ─── BÖLÜM 3: ALT 3 KÜÇÜK FOTOĞRAF ───────────────────────────────────
    MINI_H   = 88
    MINI_GAP = 6
    mini_w   = (CW - MINI_GAP * 2) / 3
    mini_y   = cover_y - MINI_H - 4

    for idx in range(3):
        raw = v.fotolar[idx + 1] if (idx + 1) < len(v.fotolar) else None
        mx  = M + idx * (mini_w + MINI_GAP)
        ir  = _cover_reader(raw, mini_w, MINI_H) if raw else None
        if ir:
            c.drawImage(ir, mx, mini_y, width=mini_w, height=MINI_H,
                        preserveAspectRatio=False, mask="auto")
        else:
            c.setFillColor(C_NAVY_L)
            c.rect(mx, mini_y, mini_w, MINI_H, fill=1, stroke=0)

    # ─── BÖLÜM 4: FİYAT + BAŞLIK + LOKASYON ──────────────────────────────
    cy = mini_y - 12

    fiyat_str = _sf(_money(v.fiyat))
    c.setFillColor(C_NAVY)
    c.setFont(F_BOLD, 26)
    c.drawString(M, cy - 26, fiyat_str)
    cy -= 32

    c.setStrokeColor(C_RED)
    c.setLineWidth(2)
    c.line(M, cy, M + 40, cy)
    cy -= 10

    title = _sf(_title_case(_clean(v.baslik) or _join_clean([v.islem_tipi, v.mulk_tipi, v.ilce], " ")))
    c.setFillColor(C_NAVY)
    c.setFont(F_BOLD, 13)
    words_t, lines_t, cur_t = title.split(), [], ""
    for w in words_t:
        trial = (cur_t + " " + w).strip()
        if c.stringWidth(trial, F_BOLD, 13) <= CW:
            cur_t = trial
        else:
            if cur_t: lines_t.append(cur_t)
            cur_t = w
            if len(lines_t) >= 1: break
    if cur_t: lines_t.append(cur_t)
    for line in lines_t[:2]:
        c.drawString(M, cy - 14, line)
        cy -= 17
    cy -= 4

    loc = _sf(_join_clean([v.ilce, v.il], " / "))
    if loc:
        _draw_str(M, cy - 10, loc, F_REG, 9, C_MUTED)
        cy -= 16

    # ─── BÖLÜM 5: SPEC CHIP'LERİ ──────────────────────────────────────────
    cy -= 6
    specs = _specs(v, include_heating=True)[:4]
    if specs:
        chip_x = M
        CHIP_H = 20
        c.setFont(F_BOLD, 8)
        for label, val in specs:
            # Sadece değer göster — label tekrarı kaldırıldı
            clean_val = _clean(val)
            if not clean_val:
                continue
            txt = _sf(clean_val)
            tw  = c.stringWidth(txt, F_BOLD, 8) + 16
            c.setFillColor(C_NAVY_L)
            c.roundRect(chip_x, cy - CHIP_H, tw, CHIP_H, 4, fill=1, stroke=0)
            c.setFillColor(C_NAVY)
            c.setFont(F_BOLD, 8)
            c.drawString(chip_x + 8, cy - CHIP_H + 6, txt)
            chip_x += tw + 6
            if chip_x > M + CW - 80:
                chip_x = M
                cy -= CHIP_H + 4
        cy -= CHIP_H + 8

    # ─── BÖLÜM 6: ÖZELLİKLER ─────────────────────────────────────────────
    ozellikler = [_clean(o) for o in (v.ozellikler or []) if not _is_blank(o)]
    if ozellikler:
        col_items = ozellikler[:10]
        half = (len(col_items) + 1) // 2
        col1, col2 = col_items[:half], col_items[half:]
        ITEM_H = 11
        cy -= 4
        c.setFont(F_REG, 8)
        for i, item in enumerate(col1):
            _draw_str(M, cy - (i + 1) * ITEM_H, _sf(f"• {item}"), F_REG, 8, C_MUTED)
        for i, item in enumerate(col2):
            _draw_str(M + CW // 2, cy - (i + 1) * ITEM_H, _sf(f"• {item}"), F_REG, 8, C_MUTED)
        cy -= (half + 1) * ITEM_H

    # ─── BÖLÜM 7: AÇIKLAMA ────────────────────────────────────────────────
    acik = _clean(v.aciklama)
    if acik and cy > 180:
        cy -= 6
        c.setStrokeColor(C_BORDER)
        c.setLineWidth(0.5)
        c.line(M, cy, M + CW, cy)
        cy -= 10
        words_a, lines_a, cur_a = acik.split(), [], ""
        for w in words_a:
            trial = (cur_a + " " + w).strip()
            if c.stringWidth(trial, F_REG, 8) <= CW:
                cur_a = trial
            else:
                if cur_a: lines_a.append(cur_a)
                cur_a = w
                if len(lines_a) >= 2: break
        if cur_a and len(lines_a) < 3: lines_a.append(cur_a)
        for line in lines_a[:3]:
            _draw_str(M, cy - 10, _sf(line), F_REG, 8, C_MUTED)
            cy -= 12

    # ─── BÖLÜM 7b: GD NOTU (durum bazlı pazarlama) ────────────────────────
    gd_notu_clean = _clean(gd_notu)
    if gd_notu_clean and cy > 175:
        cy -= 6
        # Soluk kırmızı arka plan
        note_h = 22
        c.setFillColor(_rl_color((253, 238, 238)))
        c.roundRect(M, cy - note_h, CW, note_h, 4, fill=1, stroke=0)
        c.setStrokeColor(_rl_color((220, 180, 180)))
        c.setLineWidth(0.5)
        c.roundRect(M, cy - note_h, CW, note_h, 4, fill=0, stroke=1)
        # Sol kırmızı accent çizgi
        c.setFillColor(C_RED)
        c.rect(M, cy - note_h, 3, note_h, fill=1, stroke=0)
        _draw_str(M + 10, cy - note_h + 7, _sf(gd_notu_clean[:90]),
                  F_BOLD, 8, C_RED)
        cy -= note_h + 6

    # ─── BÖLÜM 8: DANIŞMAN + QR ───────────────────────────────────────────
    # Sıra: danışman bloğu üstte, marka şeridi en altta
    STRIP_H  = 44
    FOOTER_H = 84
    strip_y  = M                          # en altta
    footer_y = strip_y + STRIP_H + 6     # danışman şeridin üstünde
    footer_top = footer_y + FOOTER_H

    # Danışman bloğu
    c.setFillColor(C_SOFT)
    c.roundRect(M, footer_y, CW, FOOTER_H, 6, fill=1, stroke=0)
    c.setStrokeColor(C_BORDER)
    c.setLineWidth(0.5)
    c.roundRect(M, footer_y, CW, FOOTER_H, 6, fill=0, stroke=1)

    # Avatar
    tx = M + 12
    if v.dan_foto:
        try:
            av_pil = _circle(v.dan_foto, 56, _initials(v.dan_ad)).convert("RGBA")
            av_buf = _io.BytesIO()
            av_pil.save(av_buf, "PNG")
            av_buf.seek(0)
            c.drawImage(ImageReader(av_buf),
                        M + 10, footer_y + (FOOTER_H - 56) // 2,
                        width=56, height=56, mask="auto")
            tx = M + 76
        except Exception:
            pass

    dan_ad    = _sf(_clean(v.dan_ad, "Gayrimenkul Danismani"))
    dan_unvan = _sf(_clean(v.dan_unvan, "Gayrimenkul Danismani"))
    dan_tel   = _clean(v.dan_telefon)
    dan_email = _clean(v.dan_email)

    _draw_str(tx, footer_y + 60, dan_ad,    F_BOLD, 10, C_NAVY)
    _draw_str(tx, footer_y + 49, dan_unvan, F_REG,  8,  C_MUTED)
    if dan_tel:
        _draw_str(tx, footer_y + 38, dan_tel, F_BOLD, 8, C_NAVY)
    if dan_email:
        _draw_str(tx, footer_y + 28, _sf(dan_email[:40]), F_REG, 7, C_MUTED)

    # Logo
    logo_x = M + CW - 100
    logo_y_pos = footer_y + FOOTER_H - 44
    if v.dan_logo:
        try:
            logo_pil = Image.open(_io.BytesIO(v.dan_logo)).convert("RGBA")
            logo_pil.thumbnail((90, 36), Image.LANCZOS)
            logo_buf = _io.BytesIO()
            logo_pil.save(logo_buf, "PNG")
            logo_buf.seek(0)
            c.drawImage(ImageReader(logo_buf), logo_x, logo_y_pos,
                        width=90, height=36, mask="auto", preserveAspectRatio=True)
        except Exception:
            _draw_str(logo_x, logo_y_pos + 22, "STARTKEY",        F_BOLD, 9, C_RED)
            _draw_str(logo_x, logo_y_pos + 12, "ZETA GAYRIMENKUL", F_BOLD, 7, C_NAVY)
    else:
        _draw_str(logo_x, logo_y_pos + 22, "STARTKEY",        F_BOLD, 9, C_RED)
        _draw_str(logo_x, logo_y_pos + 12, "ZETA GAYRIMENKUL", F_BOLD, 7, C_NAVY)

    # QR kod
    if landing_url:
        QR_SIZE = 56
        qr_x = M + CW - 100 - QR_SIZE - 8
        qr_y = footer_y + (FOOTER_H - QR_SIZE) // 2
        qr_pil = _qr_image(landing_url, size_px=QR_SIZE * 2)
        qr_buf = _io.BytesIO()
        qr_pil.save(qr_buf, "PNG")
        qr_buf.seek(0)
        c.drawImage(ImageReader(qr_buf), qr_x, qr_y,
                    width=QR_SIZE, height=QR_SIZE, mask="auto")
        _draw_str(qr_x + QR_SIZE / 2, qr_y - 8,
                  _sf("Portfoyü Incele"), F_REG, 6, C_MUTED, anchor="center")

    # ─── BÖLÜM 10: AYRAÇ (içerik → danışman arası) ────────────────────────
    sep_y = max(footer_top + 10, cy - 4)
    c.setStrokeColor(C_BORDER)
    c.setLineWidth(0.5)
    c.line(M, sep_y, M + CW, sep_y)

    # ─── BÖLÜM 11: MARKA DEĞERİ ŞERİDİ — en altta ────────────────────────
    col_w = CW / 4
    c.setFillColor(C_STRIP)
    c.roundRect(M, strip_y, CW, STRIP_H, 4, fill=1, stroke=0)
    c.setStrokeColor(C_BORDER)
    c.setLineWidth(0.3)
    c.roundRect(M, strip_y, CW, STRIP_H, 4, fill=0, stroke=1)

    for i, (bas, alt) in enumerate(PDF_MARKA_SERIT):
        col_cx = M + i * col_w + col_w / 2
        if i > 0:
            c.setStrokeColor(C_BORDER)
            c.setLineWidth(0.5)
            c.line(M + i * col_w, strip_y + 6, M + i * col_w, strip_y + STRIP_H - 6)
        _draw_str(col_cx, strip_y + STRIP_H - 14, _sf(bas),
                  F_BOLD, 7, C_NAVY, anchor="center")
        _draw_str(col_cx, strip_y + STRIP_H - 26, _sf(alt),
                  F_REG,  6, C_MUTED, anchor="center")

    c.save()
    return buf.getvalue()
