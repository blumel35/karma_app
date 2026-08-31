// static/sw.js
// ---------------------------------------------------------------------
// Startkey Zeta Danışman Panosu — telefon bildirimleri (web push) için
// service worker (2026-08-31).
//
// Streamlit'in kendi static dosya sunumu üzerinden /app/static/sw.js
// yolunda servis edilir (bkz. app.py'deki head-injection script'i,
// .streamlit/config.toml: enableStaticServing = true). Varsayılan kayıt
// kapsamı (scope) bu yüzden /app/static/ ile sınırlı — bu ÖNEMLİ DEĞİL,
// çünkü push bildirimleri sayfa "kontrolü"ne değil, doğrudan bu worker'ın
// kayıtlı olmasına bağlı: bir push mesajı geldiğinde, hangi sayfa açık
// olursa olsun (veya hiç sayfa açık değilken bile) aşağıdaki 'push' olayı
// tetiklenir.
//
// Bu dosya BİLEREK basit tutuldu (Faz 1 — temel altyapı doğrulaması):
// offline/cache desteği YOK, sadece push + bildirime tıklama var.

self.addEventListener('install', function (event) {
  // Yeni sürüm yayınlandığında eski bekleyen worker'ı beklemeden hemen
  // devreye gir — kullanıcı sayfayı kapatıp açana kadar beklemek yerine.
  self.skipWaiting();
});

self.addEventListener('activate', function (event) {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('push', function (event) {
  var veri = {};
  try {
    veri = event.data ? event.data.json() : {};
  } catch (e) {
    veri = { title: 'Startkey Zeta', body: event.data ? event.data.text() : '' };
  }

  var baslik = veri.title || 'Startkey Zeta';
  var secenekler = {
    body: veri.body || '',
    icon: '/app/static/icons/icon-192.png',
    badge: '/app/static/icons/icon-192.png',
    data: { url: veri.url || '/Danisman_Secim' },
  };

  event.waitUntil(self.registration.showNotification(baslik, secenekler));
});

self.addEventListener('notificationclick', function (event) {
  event.notification.close();
  var hedefUrl = (event.notification.data && event.notification.data.url) || '/';

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (istemciler) {
      for (var i = 0; i < istemciler.length; i++) {
        var istemci = istemciler[i];
        if (istemci.url.indexOf(hedefUrl) !== -1 && 'focus' in istemci) {
          return istemci.focus();
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow(hedefUrl);
      }
    })
  );
});
