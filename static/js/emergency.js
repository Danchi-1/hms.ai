/**
 * HMS-AI Emergency Engine
 * ════════════════════════════════════════════════════════════
 * Five modules:
 *   EmergencyEngine    — orchestrates all escalation layers
 *   EmergencyUI        — full-screen modal + countdown ring
 *   CountdownManager   — 15-second countdown, auto-escalates
 *   LocationFetcher    — GPS via navigator.geolocation
 *   AlertDispatcher    — POSTs to /api/emergency/*
 * ════════════════════════════════════════════════════════════
 */

const EMERGENCY_NUMBER = '767';    // Nigeria EMS; overridden by backend config
const COUNTDOWN_SECS   = 15;       // overridden by backend config

// ─── IndexedDB offline queue ────────────────────────────────────────────────
const EmergencyDB = {
    _db: null,
    async open() {
        return new Promise((res, rej) => {
            const req = indexedDB.open('hms_emergency_queue', 1);
            req.onupgradeneeded = e => {
                e.target.result.createObjectStore('queue', { keyPath: 'id', autoIncrement: true });
            };
            req.onsuccess = e => { this._db = e.target.result; res(); };
            req.onerror   = e => rej(e);
        });
    },
    async enqueue(payload) {
        if (!this._db) await this.open();
        const tx = this._db.transaction('queue', 'readwrite');
        tx.objectStore('queue').add({ payload, ts: Date.now() });
    },
    async flush() {
        if (!this._db) await this.open();
        const tx    = this._db.transaction('queue', 'readwrite');
        const store = tx.objectStore('queue');
        const all   = await new Promise(r => { const req = store.getAll(); req.onsuccess = e => r(e.target.result); });
        for (const item of all) {
            const ok = await AlertDispatcher._post('/api/emergency/alert', item.payload);
            if (ok) store.delete(item.id);
        }
    }
};

// ─── LocationFetcher ────────────────────────────────────────────────────────
const LocationFetcher = {
    async get() {
        return new Promise(resolve => {
            if (!navigator.geolocation) { resolve(null); return; }
            navigator.geolocation.getCurrentPosition(
                pos => resolve({
                    latitude:  pos.coords.latitude,
                    longitude: pos.coords.longitude,
                    accuracy:  pos.coords.accuracy,
                    timestamp: new Date().toISOString(),
                    maps_link: `https://maps.google.com/?q=${pos.coords.latitude},${pos.coords.longitude}`
                }),
                () => resolve(null),
                { timeout: 6000, maximumAge: 30000 }
            );
        });
    }
};

// ─── AlertDispatcher ────────────────────────────────────────────────────────
const AlertDispatcher = {
    async _post(url, body) {
        try {
            const res = await fetch(url, {
                method:      'POST',
                credentials: 'include',
                headers:     { 'Content-Type': 'application/json' },
                body:        JSON.stringify(body)
            });
            return res.ok;
        } catch (_) {
            return false;
        }
    },

    async triggerBackend(vitals, location, triggerSource) {
        return this._post('/api/emergency/trigger', { vitals, location, trigger_source: triggerSource });
    },

    async sendAlerts(vitals, location, anomalyType) {
        const payload = { vitals, location, anomaly_type: anomalyType };
        if (!navigator.onLine) {
            await EmergencyDB.enqueue(payload);
            console.warn('[Emergency] Offline — alert queued for retry.');
            return false;
        }
        const ok = await this._post('/api/emergency/alert', payload);
        if (!ok) await EmergencyDB.enqueue(payload);
        return ok;
    }
};

// ─── CountdownManager ───────────────────────────────────────────────────────
class CountdownManager {
    constructor(seconds, onTick, onComplete) {
        this.total      = seconds;
        this.remaining  = seconds;
        this.onTick     = onTick;
        this.onComplete = onComplete;
        this._timer     = null;
    }

    start() {
        this.onTick(this.remaining);
        this._timer = setInterval(() => {
            this.remaining--;
            this.onTick(this.remaining);
            if (this.remaining <= 0) {
                clearInterval(this._timer);
                this.onComplete();
            }
        }, 1000);
    }

    cancel() {
        clearInterval(this._timer);
    }
}

// ─── Audio Alert ────────────────────────────────────────────────────────────
const EmergencyAudio = {
    _ctx: null,
    _running: false,

    async canPlayOnSpeaker() {
        // Avoid playing through earphones/earbuds
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            const audioOut = devices.filter(d => d.kind === 'audiooutput');
            // If the only audio output looks like a headphone, skip
            const headphoneLabels = /head|ear|pod|bud|airpod/i;
            const allHeadphones   = audioOut.every(d => headphoneLabels.test(d.label));
            return !allHeadphones;
        } catch (_) {
            return true;   // can't detect → assume speaker
        }
    },

    async start() {
        if (this._running) return;
        const ok = await this.canPlayOnSpeaker();
        if (!ok) { console.info('[EmergencyAudio] Headphones detected — audio suppressed.'); return; }

        this._ctx    = new (window.AudioContext || window.webkitAudioContext)();
        this._running = true;
        this._beep();
    },

    _beep() {
        if (!this._running || !this._ctx) return;
        const o = this._ctx.createOscillator();
        const g = this._ctx.createGain();
        o.connect(g); g.connect(this._ctx.destination);
        o.type      = 'square';
        o.frequency.setValueAtTime(880, this._ctx.currentTime);
        g.gain.setValueAtTime(0.6, this._ctx.currentTime);
        g.gain.exponentialRampToValueAtTime(0.001, this._ctx.currentTime + 0.4);
        o.start(this._ctx.currentTime);
        o.stop(this._ctx.currentTime + 0.4);
        if (this._running) setTimeout(() => this._beep(), 900);
    },

    stop() {
        this._running = false;
        if (this._ctx) { this._ctx.close(); this._ctx = null; }
    }
};

// ─── EmergencyUI ────────────────────────────────────────────────────────────
const EmergencyUI = {
    modal: null,

    show(vitals, countdownEl, onCancel, onCallNow, onAlertContacts, onShareLocation) {
        this.modal = document.getElementById('emergencyModal');
        if (!this.modal) return;

        const hr    = vitals.heart_rate   ?? window._latestHR   ?? 'N/A';
        const spo2  = vitals.spo2         ?? window._latestSpO2 ?? 'N/A';
        const label = vitals.trigger_detail ?? 'ANOMALOUS VITALS DETECTED';

        this.modal.innerHTML = `
            <div class="emergency-glow"></div>
            <div class="emergency-card">
                <div class="emergency-icon">🚨</div>
                <h2 class="emergency-title">Medical Emergency</h2>
                <p class="emergency-subtitle">${label}</p>

                <div class="emergency-vitals">
                    <span class="emergency-vital-badge">❤️ HR: ${hr} BPM</span>
                    <span class="emergency-vital-badge">🩸 SpO₂: ${spo2}%</span>
                </div>

                <div class="emergency-countdown-wrap">
                    <div class="emergency-countdown-label">Calling emergency services in</div>
                    <div class="emergency-countdown-ring" id="emergencyRing">
                        <div class="emergency-countdown-inner">
                            <span class="emergency-countdown-number" id="emergencyCountdownNum">${COUNTDOWN_SECS}</span>
                        </div>
                    </div>
                </div>

                <div class="emergency-actions">
                    <button class="emergency-btn btn-cancel" id="emergencyCancelBtn">✋ Cancel Emergency</button>
                    <a class="emergency-btn btn-call" href="tel:${EMERGENCY_NUMBER}" id="emergencyCallBtn">📞 Call Ambulance Now</a>
                    <button class="emergency-btn btn-contacts" id="emergencyAlertBtn">📲 Alert Contacts</button>
                    <button class="emergency-btn btn-location" id="emergencyLocationBtn">📍 Share Location</button>
                </div>
            </div>`;

        document.getElementById('emergencyCancelBtn').addEventListener('click', onCancel);
        document.getElementById('emergencyCallBtn').addEventListener('click', onCallNow);
        document.getElementById('emergencyAlertBtn').addEventListener('click', onAlertContacts);
        document.getElementById('emergencyLocationBtn').addEventListener('click', onShareLocation);

        this.modal.classList.add('active');
    },

    updateCountdown(n) {
        const el = document.getElementById('emergencyCountdownNum');
        if (el) el.textContent = n;

        const ring = document.getElementById('emergencyRing');
        if (ring) {
            const deg = ((COUNTDOWN_SECS - n) / COUNTDOWN_SECS) * 360;
            ring.style.background = `conic-gradient(#ef4444 ${deg}deg, rgba(239,68,68,0.12) ${deg}deg)`;
        }
    },

    hide() {
        if (this.modal) this.modal.classList.remove('active');
    }
};

// ─── EmergencyEngine (main orchestrator) ────────────────────────────────────
const EmergencyEngine = {
    _active: false,
    _countdown: null,
    _inactivityTimer: null,
    _location: null,
    _vitals: {},
    _alertSent: false,

    async start(triggerSource = 'manual', extraVitals = {}) {
        if (this._active) return;   // prevent double trigger
        this._active    = true;
        this._alertSent = false;

        const hr   = window._latestHR   ?? extraVitals.heart_rate ?? 'N/A';
        const spo2 = window._latestSpO2 ?? extraVitals.spo2       ?? 'N/A';

        this._vitals = {
            heart_rate:     hr,
            spo2:           spo2,
            trigger_detail: extraVitals.trigger_detail ?? this._describeAnomaly(hr, spo2, triggerSource),
            steps:          window._sessionSteps    ?? 'N/A',
            health_score:   window._lastHealthScore ?? 'N/A',
            device_id:      localStorage.getItem('hms_last_ble_device') ?? 'N/A',
        };

        // Get GPS in parallel while modal opens
        this._location = null;
        LocationFetcher.get().then(loc => { this._location = loc; });

        // Notify backend
        await AlertDispatcher.triggerBackend(this._vitals, {}, triggerSource);

        // Start audio
        EmergencyAudio.start();

        // Show UI
        EmergencyUI.show(
            this._vitals,
            COUNTDOWN_SECS,
            () => this.cancel(),
            () => this._onCallNow(),
            () => this._onAlertContacts(),
            () => this._onShareLocation()
        );

        // Inactivity auto-escalate (if user is unconscious and can't cancel)
        this._inactivityTimer = setTimeout(() => this._autoEscalate(), (COUNTDOWN_SECS + 2) * 1000);

        // Countdown
        this._countdown = new CountdownManager(
            COUNTDOWN_SECS,
            (n) => EmergencyUI.updateCountdown(n),
            () => this._autoEscalate()
        );
        this._countdown.start();

        // Flush any offline queued alerts
        if (navigator.onLine) EmergencyDB.flush();
    },

    cancel() {
        if (!this._active) return;
        this._cleanup();
        console.info('[EmergencyEngine] Emergency cancelled by user.');
    },

    _autoEscalate() {
        console.warn('[EmergencyEngine] Auto-escalating — no user response.');
        this._sendAlerts();
        // Open system dialer
        window.location.href = `tel:${EMERGENCY_NUMBER}`;
    },

    async _sendAlerts() {
        if (this._alertSent) return;
        this._alertSent = true;

        // Merge in GPS if available
        const loc  = this._location || await LocationFetcher.get();
        const type = this._vitals.trigger_detail ?? 'Emergency';

        await AlertDispatcher.sendAlerts(this._vitals, loc ?? {}, type);
    },

    _onCallNow() {
        // href already opened by <a> tag — just track intent
        this._sendAlerts();
    },

    async _onAlertContacts() {
        const btn = document.getElementById('emergencyAlertBtn');
        if (btn) { btn.disabled = true; btn.textContent = '⏳ Sending...'; }
        await this._sendAlerts();
        if (btn) btn.textContent = '✅ Sent';
    },

    async _onShareLocation() {
        const loc = await LocationFetcher.get();
        if (loc) {
            // Copy or open Maps link
            try { await navigator.clipboard.writeText(loc.maps_link); } catch (_) {}
            window.open(loc.maps_link, '_blank');
        }
    },

    _describeAnomaly(hr, spo2, source) {
        if (source === 'fall') return 'Fall detected with possible loss of consciousness';
        if (source === 'ml')   return 'ML model flagged HIGH health risk';
        if (hr !== 'N/A') {
            if (hr > 130) return `Dangerously high heart rate (${hr} BPM)`;
            if (hr < 40)  return `Dangerously low heart rate (${hr} BPM)`;
        }
        if (spo2 !== 'N/A' && spo2 < 90) return `Critically low blood oxygen (${spo2}%)`;
        return 'Critical health anomaly detected';
    },

    _cleanup() {
        this._active = false;
        if (this._countdown) { this._countdown.cancel(); this._countdown = null; }
        clearTimeout(this._inactivityTimer);
        EmergencyAudio.stop();
        EmergencyUI.hide();
    }
};

// ── Expose globally ──────────────────────────────────────────────────────────
window.EmergencyEngine = EmergencyEngine;

// ── Flush offline queue when coming back online ──────────────────────────────
window.addEventListener('online', () => EmergencyDB.flush());

// ── apiFetch interceptor (JWT auto-refresh) ──────────────────────────────────
// Wraps fetch: on 401 → silently calls /api/auth/refresh → retries once.
(function patchFetch() {
    const _originalFetch = window.fetch.bind(window);
    let _refreshing = false;
    let _refreshQueue = [];

    async function _doRefresh() {
        const res = await _originalFetch('/api/auth/refresh', {
            method: 'POST', credentials: 'include'
        });
        return res.ok;
    }

    window.fetch = async function(url, options = {}) {
        options.credentials = options.credentials ?? 'include';
        let response = await _originalFetch(url, options);

        if (response.status === 401 && !String(url).includes('/api/auth/')) {
            if (_refreshing) {
                // Queue concurrent 401s until refresh completes
                await new Promise((res, rej) => _refreshQueue.push({ res, rej }));
                return _originalFetch(url, options);
            }
            _refreshing = true;
            try {
                const ok = await _doRefresh();
                _refreshQueue.forEach(p => ok ? p.res() : p.rej());
                _refreshQueue = [];
                _refreshing   = false;
                if (ok) return _originalFetch(url, options);
                // Refresh failed — redirect to login
                window.location.href = '/login';
                return response;
            } catch (err) {
                _refreshQueue.forEach(p => p.rej(err));
                _refreshQueue = [];
                _refreshing   = false;
                window.location.href = '/login';
                return response;
            }
        }
        return response;
    };
})();

console.info('[HMS-AI] Emergency Engine + JWT interceptor loaded.');
