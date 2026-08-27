# pages/Hesap_Aktivasyon.py
# Startkey Zeta — yalnızca davet edilen kullanıcının ilk şifresini belirlemesi için.
# Karma App'e veya Danışman Panosu'na giriş/yönlendirme yapmaz.
#
# NOT (2026-08-27): Render mantığı core/auth_ui.py:render_hesap_aktivasyon()
# içine taşındı. app.py artık Supabase davet linkini KÖK URL'de yakaladığı
# anda st.switch_page() ile buraya GEÇİŞ yapmıyor — bunun yerine bu
# fonksiyonu doğrudan, sayfa geçişi olmadan çağırıyor (switch_page üç ayrı
# denemede güvenilmez çıktı: sayfa bulunamadı hatası / ekranı, query param
# kaybı). Bu dosya yalnızca biri doğrudan bu sayfanın kendi URL'sine
# giderse diye st.Page olarak duruyor.

from core.auth_ui import render_hesap_aktivasyon

render_hesap_aktivasyon()
