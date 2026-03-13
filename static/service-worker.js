/**
 * HMS-AI Service Worker
 * ─────────────────────
 * Strategy:
 *   - Cache-first for static assets (CSS, JS, fonts, icons)
 *   - Network-first for API calls (with cache fallback)
 *   - Background sync for failed emergency alerts
 *   - Push notification handler
 */

const CACHE_NAME    = 'hms-ai-v1';
const OFFLINE_PAGE  = '/login';

const PRECACHE_ASSETS = [
    '/',
    '/login',
    '/dashboard',
    '/static/css/main.css',
    '/static/css/dashboard.css',
    '/static/css/emergency.css',
    '/static/js/emergency.js',
    '/static/js/fall_detection.js',
    '/static/js/dashboard.js',
    '/static/manifest.json',
    'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
];

// ── Install: pre-cache static shell ────────────────────────────────────────
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE_ASSETS))
    );
    self.skipWaiting();
});

// ── Activate: clean old caches ───────────────────────────────────────────
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        )
    );
    clients.claim();
});

// ── Fetch: cache-first for static, network-first for API ────────────────
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // Always network-first for API and auth routes
    if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/login')) {
        event.respondWith(
            fetch(event.request).catch(() => caches.match(event.request))
        );
        return;
    }

    // Cache-first for everything else
    event.respondWith(
        caches.match(event.request).then(cached => {
            if (cached) return cached;
            return fetch(event.request).then(networkRes => {
                if (networkRes && networkRes.status === 200) {
                    const clone = networkRes.clone();
                    caches.open(CACHE_NAME).then(c => c.put(event.request, clone));
                }
                return networkRes;
            }).catch(() => caches.match(OFFLINE_PAGE));
        })
    );
});

// ── Background Sync: retry emergency alerts ──────────────────────────────
self.addEventListener('sync', event => {
    if (event.tag === 'emergency-alert') {
        event.waitUntil(
            // The page-side IndexedDB flush logic handles the actual retry
            self.clients.matchAll().then(clients =>
                clients.forEach(c => c.postMessage({ type: 'FLUSH_EMERGENCY_QUEUE' }))
            )
        );
    }
});

// ── Push Notifications ───────────────────────────────────────────────────
self.addEventListener('push', event => {
    let data = {};
    try { data = event.data.json(); } catch (_) { data = { title: 'HMS-AI Alert', body: event.data?.text() ?? '' }; }

    event.waitUntil(
        self.registration.showNotification(data.title ?? 'HMS-AI Health Alert', {
            body:    data.body   ?? 'Check your dashboard for updates.',
            icon:    '/static/icons/icon-192.png',
            badge:   '/static/icons/icon-192.png',
            vibrate: [200, 100, 200, 100, 400],
            tag:     'hms-alert',
            data:    { url: data.url ?? '/dashboard' }
        })
    );
});

// Notification click → open dashboard
self.addEventListener('notificationclick', event => {
    event.notification.close();
    event.waitUntil(
        clients.openWindow(event.notification.data?.url ?? '/dashboard')
    );
});
