# Mail Sistemi Revizyonu — Kurulum Rehberi

Bu paket, üzerinde mutabık kalınan yol haritasının (Faz 1 → Faz 4) tamamını
kodluyor. Aşağıdaki sırayla uygula — sıra önemli, çünkü Faz 2.5 ve Faz 3,
Faz 1'deki şema değişikliklerine bağımlı.

## 1) Supabase şema migration (önce bu)

`supabase_migration_001.sql` dosyasını Supabase Dashboard → SQL Editor'a
yapıştırıp çalıştır. Var olan veriyi silmez, sadece yeni kolon/tablo ekler.

Dosyanın sonundaki NOT kısmına dikkat: `linked_portfoy_id` ve
`source_alici_id` kolonlarını `bigint` varsaydım (Supabase'in varsayılan
otomatik-artan id tipi). Eğer senin `id` kolonların `uuid` ise, migration'ı
çalıştırmadan önce o iki satırı `uuid` olarak değiştir.

## 2) Dosyaları projene kopyala

```
core/mail_fetcher.py          → core/mail_fetcher.py (üzerine yaz)
core/mail_parser.py           → core/mail_parser.py (üzerine yaz)
core/mail_job.py              → core/mail_job.py (YENİ dosya)
core/data/izmir_mahalleler.json → core/data/izmir_mahalleler.json (YENİ)
pages/5_Mail_Islem.py         → pages/5_Mail_Islem.py (üzerine yaz)
scripts/mail_auto_job.py      → scripts/mail_auto_job.py (YENİ)
.github/workflows/mail_auto_fetch.yml → .github/workflows/mail_auto_fetch.yml (YENİ)
```

`app.py`'de değişiklik gerekmiyor — `5_Mail_Islem.py`'nin arayüzü/importları
aynı `render_navbar` yapısını kullanıyor.

## 3) GitHub Secrets tanımla (Faz 2.5 için)

Repo → Settings → Secrets and variables → Actions içine ekle:

- `MAIL_USER`, `MAIL_PASSWORD`, `MAIL_IMAP`
- `ANTHROPIC_API_KEY`
- `SUPABASE_URL`, `SUPABASE_SECRET_KEY`

**Doğrulandı:** `core/supabase_client.py` içeriği kontrol edildi —
`get_client()` fonksiyonu `st.secrets["supabase"]["url"]` ve
`st.secrets["supabase"]["secret_key"]` okuyor (önceki taslakta `"key"`
yazılmıştı, bu yanlıştı — workflow dosyası `secret_key` olarak düzeltildi).

## 4) İlk çalıştırma — AI otomasyonu KAPALI başlat

Workflow dosyasında `AI_KATEGORIZASYON_AKTIF: "false"` olarak bırakıldı.
Yani GitHub Actions ilk etapta **sadece ham mail çekimini** otomatik yapacak;
AI kategorize etme adımı hâlâ manuel buton ile (`pages/5_Mail_Islem.py`)
sende kalıyor. Bir hafta sorunsuz geçtikten sonra bu değeri `"true"` yap.

## 5) requirements.txt kontrolü

Script'in çalışması için `requirements.txt` içinde şunlar olmalı (muhtemelen
zaten var, kontrol amaçlı):

```
streamlit
anthropic
supabase
```

## Bilinçli olarak YAPILMAYAN şey

Diğer AI'ın önerdiği ayrı `mail_raw` tablosunu bilerek eklemedim —
`parse_status` alanı aynı ayrımı (ham/işlenmiş) mevcut tabloyu bozmadan
sağlıyor. Sistem ileride çok kullanıcılı/yüksek hacimli hale gelirse o
ayrım yeniden değerlendirilebilir.

## Değişen davranışlar — özet

| Konu | Eskiden | Şimdi |
|---|---|---|
| İşlenme durumu | `bolge_mahalle==""` | `parse_status` kolonu |
| Portföye taşıma | insert + delete (atomik değil) | insert + `parse_status="moved_to_portfoy"` (satır silinmiyor) |
| message_id boş | dedupe yok | `fallback_hash` ile dedupe |
| Tarih penceresi | sabit 5 gün | `mail_fetch_state`'e göre dinamik |
| RE: mailleri | tamamen atılıyor | `is_reply=true` ile dahil ediliyor |
| fırsat/kampanya/davet | filtreleniyor | filtre kaldırıldı |
| Sessiz hatalar | `except: continue` | `hata_log` listesi + ekranda özet |
| İlçe tahmini | sadece AI | AI + `izmir_mahalleler.json` sözlük doğrulaması |
| İçerik kırpma | ilk 3000 karakter | ilk 2000 + son 1500 karakter |
| AI çağrıları | sıralı, tek tek | `ThreadPoolExecutor`, max_workers=3, retry+timeout |
| Anthropic client | her çağrıda yeniden | `st.cache_resource` ile tekil |
| Otomasyon | yok | GitHub Actions, 30 dakikada bir |
