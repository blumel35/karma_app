import re
import html
from typing import Any, Dict, List, Optional

SUNUM_KAYDI_ALANLARI = [
    "sunum_tipi",
    "kaynak",
    "kaynak_id",
    "baslik",
    "ozet",
    "fiyat",
    "butce",
    "islem_tipi",
    "mulk_tipi",
    "il",
    "ilce",
    "mahalle",
    "bolge",
    "lokasyon",
    "m2",
    "oda",
    "kat",
    "bina_yasi",
    "isitma",
    "kullanim_durumu",
    "esyali",
    "site_icerisinde",
    "ilan_durumu",
    "ilan_linki",
    "ilan_no",
    "ilan_tarihi",
    "ilan_suresi",
    "zorunlu_kriterler",
    "esnek_notlar",
    "one_cikanlar",
    "hedef_kitle",
    "danisman_ad",
    "danisman_tel",
    "danisman_email",
    "danisman_ofis",
    "foto_listesi",
    "raw",
]

_EMPTY_TEXT_VALUES = {"", "none", "nan", "null"}


def safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default

    if isinstance(value, bool):
        return default if value is None else str(value).strip()

    try:
        text = str(value)
    except Exception:
        return default

    if text.strip() == "":
        return default

    lowered = text.strip().lower()
    if lowered in _EMPTY_TEXT_VALUES:
        return default

    return html.escape(text.strip(), quote=True)


def get_first(row: Any, keys: List[str], default: str = "") -> str:
    if not isinstance(row, dict):
        return default

    for key in keys:
        if key in row:
            value = safe_text(row.get(key))
            if value:
                return value
    return default


def normalize_price(value: Any) -> str:
    if value is None:
        return ""

    raw_text = str(value)
    digits = "".join(re.findall(r"\d+", raw_text))
    if not digits:
        return ""

    try:
        formatted = f"₺ {int(digits):,}".replace(",", ".")
        return formatted
    except ValueError:
        return ""


def normalize_budget(value: Any) -> str:
    return normalize_price(value)


def normalize_bool_label(value: Any) -> str:
    text = safe_text(value).lower()
    if not text:
        return ""

    if text in {"evet", "var", "true", "1", "yes"}:
        return "Var"
    if text in {"hayır", "hayir", "yok", "false", "0", "no"}:
        return "Yok"
    return safe_text(value)


def split_list(value: Any) -> List[str]:
    if isinstance(value, list):
        items = [safe_text(item) for item in value]
        return [item for item in items if item]

    if isinstance(value, str):
        parts = re.split(r"[\n;,|]+", value)
        items = [safe_text(item) for item in parts]
        return [item for item in items if item]

    return []


def build_location(row: Any) -> str:
    if not isinstance(row, dict):
        return ""

    mahalle = safe_text(row.get("mahalle"))
    ilce = safe_text(row.get("ilce"))
    il = safe_text(row.get("il"))
    parts = [part for part in (mahalle, ilce, il) if part]
    return " / ".join(parts)


def build_portfoy_title(row: Any) -> str:
    if not isinstance(row, dict):
        return ""

    title = get_first(row, ["ozet", "ilan_basligi", "baslik", "mail_konusu"])
    if title:
        return title

    ilce = safe_text(row.get("ilce"))
    islem_tipi = safe_text(row.get("islem_tipi"))
    mulk_tipi = safe_text(row.get("mulk_tipi"))
    oda = safe_text(row.get("oda"))
    m2 = safe_text(row.get("m2"))

    parts = [part for part in (ilce, islem_tipi, mulk_tipi) if part]
    if oda:
        parts.append(oda)
    if m2:
        parts.append(f"{m2} m²")

    return " ".join(parts)


def build_talep_title(row: Any) -> str:
    if not isinstance(row, dict):
        return ""

    ilce = safe_text(row.get("ilce"))
    islem_tipi = safe_text(row.get("islem_tipi"))
    mulk_tipi = safe_text(row.get("mulk_tipi"))
    oda = safe_text(row.get("oda"))
    budget = normalize_budget(get_first(row, ["butce", "fiyat", "maksimum_butce", "max_butce", "bütçe"]))

    parts = [part for part in (ilce, islem_tipi, mulk_tipi) if part]
    if parts:
        title = " ".join(parts) + " Arayışı"
    else:
        title = "Talep Arayışı"

    extras = []
    if oda:
        extras.append(oda)
    if budget:
        extras.append(budget)

    if extras:
        title = f"{title} {' '.join(extras)}"

    return title


def extract_highlights(row: Any) -> List[str]:
    if not isinstance(row, dict):
        return []

    highlights: List[str] = []
    m2 = safe_text(row.get("m2"))
    oda = safe_text(row.get("oda"))
    kat = safe_text(row.get("kat"))
    bina_yasi = safe_text(row.get("bina_yasi"))
    isitma = normalize_bool_label(row.get("isitma"))
    site_icerisinde = normalize_bool_label(row.get("site_icerisinde"))
    kullanim_durumu = safe_text(row.get("kullanim_durumu"))
    esyali = normalize_bool_label(row.get("esyali"))

    if m2:
        highlights.append(f"{m2} m²")
    if oda:
        highlights.append(oda)
    if kat:
        highlights.append(f"Kat {kat}" if any(char.isdigit() for char in kat) else kat)
    if bina_yasi:
        highlights.append(f"{bina_yasi} Yaşında" if any(char.isdigit() for char in bina_yasi) else bina_yasi)
    if isitma and isitma != "Yok":
        highlights.append(isitma)
    if site_icerisinde == "Var":
        highlights.append("Site İçerisinde")
    if kullanim_durumu and kullanim_durumu.lower() not in {"yok", "farketmez", "fark etmez"}:
        highlights.append(kullanim_durumu)
    if esyali == "Var":
        highlights.append("Eşyalı")

    return highlights[:6]


def extract_required_criteria(row: Any) -> List[str]:
    if not isinstance(row, dict):
        return []

    criteria: List[str] = []
    normalized_keys = {key.lower(): safe_text(value) for key, value in row.items() if safe_text(value)}

    for key, value in normalized_keys.items():
        if any(term in key for term in ["zorunlu", "olmalı", "olmali", "şart", "sart", "must"]):
            criteria.append(value)

    if "asansor" in " ".join(normalized_keys):
        if "asansor" in normalized_keys:
            item = normalize_bool_label(normalized_keys.get("asansor"))
            if item == "Var":
                criteria.append("Asansör")
            elif item:
                criteria.append(f"Asansör: {item}")
    if "tapu" in " ".join(normalized_keys):
        candidate = normalized_keys.get("tapu") or normalized_keys.get("tapu_durumu")
        if candidate:
            criteria.append(f"Tapu: {candidate}")
    if "kat" in normalized_keys:
        kat_value = normalized_keys.get("kat")
        if kat_value:
            criteria.append(f"Kat: {kat_value}")
    budget_key = get_first(row, ["butce", "fiyat", "maksimum_butce", "max_butce", "bütçe"])
    if budget_key:
        criteria.append(f"Bütçe: {normalize_budget(budget_key)}")
    if get_first(row, ["bolge", "ilce", "il"]):
        location = build_location(row)
        if location:
            criteria.append(f"Bölge: {location}")

    result = []
    for item in criteria:
        if item and item not in result:
            normalized = safe_text(item)
            if normalized:
                result.append(normalized)
        if len(result) >= 6:
            break

    return result


def make_empty_sunum_kaydi() -> Dict[str, Any]:
    return {
        "sunum_tipi": "",
        "kaynak": "",
        "kaynak_id": "",
        "baslik": "",
        "ozet": "",
        "fiyat": "",
        "butce": "",
        "islem_tipi": "",
        "mulk_tipi": "",
        "il": "",
        "ilce": "",
        "mahalle": "",
        "bolge": "",
        "lokasyon": "",
        "m2": "",
        "oda": "",
        "kat": "",
        "bina_yasi": "",
        "isitma": "",
        "kullanim_durumu": "",
        "esyali": "",
        "site_icerisinde": "",
        "ilan_durumu": "",
        "ilan_linki": "",
        "ilan_no": "",
        "ilan_tarihi": "",
        "ilan_suresi": "",
        "zorunlu_kriterler": [],
        "esnek_notlar": "",
        "one_cikanlar": [],
        "hedef_kitle": "",
        "danisman_ad": "",
        "danisman_tel": "",
        "danisman_email": "",
        "danisman_ofis": "",
        "foto_listesi": [],
        "raw": {},
    }


def _extract_photo_list(row: Any) -> List[str]:
    if not isinstance(row, dict):
        return []

    candidates = []
    for key in [
        "foto_listesi",
        "foto_url",
        "fotograf_url",
        "gorsel_url",
        "image_url",
        "images",
        "foto_urls",
    ]:
        if key in row:
            value = row.get(key)
            if isinstance(value, list):
                candidates.extend(split_list(value))
            elif isinstance(value, str):
                candidates.extend(split_list(value))

    return [item for item in candidates if item]


def _build_portfoy_base(row: Any, kaynak: str, hedef_kitle: str) -> Dict[str, Any]:
    kayit = make_empty_sunum_kaydi()
    kayit["sunum_tipi"] = "portfoy"
    kayit["kaynak"] = kaynak
    kayit["kaynak_id"] = get_first(row, ["id", "ilan_id", "kaynak_id", "source_id"])
    kayit["baslik"] = build_portfoy_title(row)
    kayit["ozet"] = get_first(row, ["ozet", "aciklama", "description", "ilan_aciklamasi"])
    kayit["fiyat"] = normalize_price(get_first(row, ["fiyat", "price", "sale_price", "ilan_fiyati", "fiyat_tl"]))
    kayit["butce"] = get_first(row, ["butce", "budget"])
    kayit["islem_tipi"] = get_first(row, ["islem_tipi", "islem", "transaction_type"])
    kayit["mulk_tipi"] = get_first(row, ["mulk_tipi", "emlak_tipi", "ilan_turu"])
    kayit["il"] = get_first(row, ["il", "city"])
    kayit["ilce"] = get_first(row, ["ilce", "district"])
    kayit["mahalle"] = get_first(row, ["mahalle", "neighbourhood"])
    kayit["bolge"] = get_first(row, ["bolge", "region", "semt"])
    kayit["lokasyon"] = build_location(row)
    kayit["m2"] = get_first(row, ["m2", "metrekare", "alan", "area"])
    kayit["oda"] = get_first(row, ["oda", "oda_sayisi", "room", "rooms"])
    kayit["kat"] = get_first(row, ["kat", "floor"])
    kayit["bina_yasi"] = get_first(row, ["bina_yasi", "yapim_yili", "building_age"])
    kayit["isitma"] = normalize_bool_label(get_first(row, ["isitma", "heating"]))
    kayit["kullanim_durumu"] = get_first(row, ["kullanim_durumu", "durum", "usage_status"])
    kayit["esyali"] = normalize_bool_label(get_first(row, ["esyali", "furnished"]))
    kayit["site_icerisinde"] = normalize_bool_label(get_first(row, ["site_icerisinde", "site_icinde", "site"]))
    kayit["ilan_durumu"] = get_first(row, ["ilan_durumu", "status"])
    kayit["ilan_linki"] = get_first(row, ["ilan_linki", "link", "url"])
    kayit["ilan_no"] = get_first(row, ["ilan_no", "ilan_id", "reference_no"])
    kayit["ilan_tarihi"] = get_first(row, ["ilan_tarihi", "tarih", "date"])
    kayit["ilan_suresi"] = get_first(row, ["ilan_suresi", "sure", "duration"])
    kayit["one_cikanlar"] = extract_highlights(row)
    kayit["esnek_notlar"] = get_first(row, ["iletisim_not", "ozellikler", "mail_icerigi", "aciklama", "description"])
    kayit["hedef_kitle"] = hedef_kitle
    kayit["danisman_ad"] = get_first(row, ["talep_eden_danisan", "danisman", "ilan_sahibi", "sahip_ad", "agent_name"])
    kayit["danisman_tel"] = get_first(row, ["danisman_tel", "tel", "telefon", "agent_phone"])
    kayit["danisman_email"] = get_first(row, ["danisman_email", "email", "agent_email"])
    kayit["danisman_ofis"] = get_first(row, ["danisman_ofis", "ofis", "ofis_label", "kaynak"])
    kayit["foto_listesi"] = _extract_photo_list(row)
    kayit["raw"] = row if isinstance(row, dict) else {}
    return kayit


def map_portfoy_to_sunum(row: Any, kaynak: str = "portfoy_havuzu", hedef_kitle: str = "musteri") -> Dict[str, Any]:
    return _build_portfoy_base(row, kaynak, hedef_kitle)


def map_ofis_portfoy_to_sunum(row: Any, hedef_kitle: str = "musteri") -> Dict[str, Any]:
    kayit = _build_portfoy_base(row, "zeta_ofis", hedef_kitle)
    kayit["kaynak"] = "zeta_ofis"
    kayit["danisman_ofis"] = get_first(row, ["ofis_label", "kaynak", "source", "source_name", "ofis"])
    kayit["ilan_no"] = get_first(row, ["ilan_no", "ilan_id", "reference_no"])
    kayit["ilan_linki"] = get_first(row, ["ilan_linki", "link", "url"])
    kayit["ilan_tarihi"] = get_first(row, ["ilan_tarihi", "tarih", "date"])
    kayit["ilan_suresi"] = get_first(row, ["ilan_suresi", "sure", "duration"])
    return kayit


def _build_talep_base(row: Any, kaynak: str, hedef_kitle: str) -> Dict[str, Any]:
    kayit = make_empty_sunum_kaydi()
    kayit["sunum_tipi"] = "talep"
    kayit["kaynak"] = kaynak
    kayit["kaynak_id"] = get_first(row, ["id", "talep_id", "kaynak_id", "source_id"])
    kayit["baslik"] = build_talep_title(row)
    kayit["ozet"] = get_first(row, ["ozet", "aciklama", "note", "description"])
    kayit["butce"] = normalize_budget(get_first(row, ["butce", "fiyat", "maksimum_butce", "max_butce", "bütçe"]))
    kayit["islem_tipi"] = get_first(row, ["islem_tipi", "islem", "transaction_type"])
    kayit["mulk_tipi"] = get_first(row, ["mulk_tipi", "emlak_tipi", "ilan_turu"])
    kayit["il"] = get_first(row, ["il", "city"])
    kayit["ilce"] = get_first(row, ["ilce", "district"])
    kayit["mahalle"] = get_first(row, ["mahalle", "neighbourhood"])
    kayit["bolge"] = get_first(row, ["bolge", "region", "semt"])
    kayit["lokasyon"] = build_location(row)
    kayit["m2"] = get_first(row, ["m2", "metrekare", "alan", "area"])
    kayit["oda"] = get_first(row, ["oda", "oda_sayisi", "room", "rooms"])
    kayit["kat"] = get_first(row, ["kat", "floor"])
    kayit["bina_yasi"] = get_first(row, ["bina_yasi", "yapim_yili", "building_age"])
    kayit["isitma"] = normalize_bool_label(get_first(row, ["isitma", "heating"]))
    kayit["kullanim_durumu"] = get_first(row, ["kullanim_durumu", "durum", "usage_status"])
    kayit["esyali"] = normalize_bool_label(get_first(row, ["esyali", "furnished"]))
    kayit["site_icerisinde"] = normalize_bool_label(get_first(row, ["site_icerisinde", "site_icinde", "site"]))
    kayit["zorunlu_kriterler"] = extract_required_criteria(row)
    kayit["one_cikanlar"] = [item for item in (
        f"Bütçe: {kayit['butce']}" if kayit["butce"] else "",
        f"{kayit['m2']} m²" if kayit["m2"] else "",
        kayit["oda"],
        build_location(row),
    ) if item][:6]
    kayit["esnek_notlar"] = get_first(row, ["ozel_kriterler", "not", "mail_icerigi", "iletisim_not", "aciklama"])
    kayit["hedef_kitle"] = hedef_kitle
    kayit["danisman_ad"] = get_first(row, ["talep_eden_danisan", "danisman", "gonderen", "agent_name"])
    kayit["danisman_tel"] = get_first(row, ["danisman_tel", "tel", "telefon", "agent_phone"])
    kayit["danisman_email"] = get_first(row, ["danisman_email", "email", "agent_email"])
    kayit["danisman_ofis"] = get_first(row, ["danisman_ofis", "ofis", "ofis_label", "kaynak"])
    kayit["raw"] = row if isinstance(row, dict) else {}
    return kayit


def map_talep_to_sunum(row: Any, kaynak: str = "talep_merkezi", hedef_kitle: str = "meslektas") -> Dict[str, Any]:
    return _build_talep_base(row, kaynak, hedef_kitle)


def map_manual_to_sunum(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return make_empty_sunum_kaydi()

    tip = safe_text(data.get("sunum_tipi")).lower()
    hedef_kitle = get_first(data, ["hedef_kitle", "target", "hedef"], "musteri")

    if tip in {"portfoy", "portföy"}:
        kayit = map_portfoy_to_sunum(data, kaynak="manuel", hedef_kitle=hedef_kitle)
        kayit["kaynak"] = "manuel"
        return kayit

    if tip == "talep":
        kayit = map_talep_to_sunum(data, kaynak="manuel", hedef_kitle=hedef_kitle)
        kayit["kaynak"] = "manuel"
        return kayit

    kayit = make_empty_sunum_kaydi()
    kayit["kaynak"] = "manuel"
    kayit["raw"] = data
    kayit["baslik"] = safe_text(data.get("baslik", data.get("title", "")))
    kayit["ozet"] = safe_text(data.get("ozet", data.get("aciklama", "")))
    kayit["fiyat"] = normalize_price(data.get("fiyat"))
    kayit["butce"] = normalize_budget(data.get("butce"))
    return kayit


def validate_sunum_kaydi(kayit: Any) -> Dict[str, Any]:
    if not isinstance(kayit, dict):
        return make_empty_sunum_kaydi()

    valid = make_empty_sunum_kaydi()
    for key in SUNUM_KAYDI_ALANLARI:
        value = kayit.get(key, valid[key])
        if key in {"zorunlu_kriterler", "one_cikanlar", "foto_listesi"}:
            if isinstance(value, list):
                valid[key] = [safe_text(item) for item in value if safe_text(item)]
            else:
                valid[key] = split_list(value)
        elif key == "raw":
            valid[key] = value if isinstance(value, dict) else {}
        else:
            valid[key] = safe_text(value)

    return valid


def to_render_payload(kayit: Any) -> Dict[str, Any]:
    if not isinstance(kayit, dict):
        kayit = make_empty_sunum_kaydi()

    fiyat = kayit.get("fiyat") or kayit.get("butce") or ""
    aciklama = safe_text(kayit.get("esnek_notlar", kayit.get("ozet", "")))
    ozellikler: List[str] = []

    if safe_text(kayit.get("sunum_tipi")).lower() == "portfoy":
        ozellikler = validate_sunum_kaydi(kayit).get("one_cikanlar", [])
    else:
        validated = validate_sunum_kaydi(kayit)
        ozellikler = validated.get("zorunlu_kriterler", []) + validated.get("one_cikanlar", [])

    return {
        "baslik": safe_text(kayit.get("baslik")),
        "islem_tipi": safe_text(kayit.get("islem_tipi")),
        "mulk_tipi": safe_text(kayit.get("mulk_tipi")),
        "il": safe_text(kayit.get("il")),
        "ilce": safe_text(kayit.get("ilce")),
        "m2": safe_text(kayit.get("m2")),
        "oda": safe_text(kayit.get("oda")),
        "kat": safe_text(kayit.get("kat")),
        "bina_yasi": safe_text(kayit.get("bina_yasi")),
        "fiyat": fiyat,
        "aciklama": aciklama,
        "ozellikler": ozellikler,
        "fotolar": validate_sunum_kaydi(kayit).get("foto_listesi", []),
        "dan_ad": safe_text(kayit.get("danisman_ad")),
        "dan_telefon": safe_text(kayit.get("danisman_tel")),
    }


# Bu dosya Sunum Merkezi V2 için veri standardizasyon katmanıdır.
# UI, Supabase ve render işlemleri bu dosyada yapılmaz.
