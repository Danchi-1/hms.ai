/**
 * HMS-AI Fall Detection Module
 * ─────────────────────────────
 * Listens to DeviceMotionEvent and detects the classic three-phase fall pattern:
 *   1. Free-fall  → |a| < 0.5g
 *   2. Impact     → |a| > 2.5g
 *   3. Inactivity → variance ≈ 0 for 15+ seconds
 *
 * Uses a confidence score combining motion + HR + inactivity signals.
 * Only triggers EmergencyEngine when confidence ≥ 1.0.
 */

class FallDetector {
    constructor() {
        this.freeFall       = false;
        this.lastImpactTime = null;
        this.motionBuffer   = [];   // { magnitude, t } rolling 20s window
        this.active         = false;
        this._handler       = this._handleMotion.bind(this);
        this._inactivityTimer = null;
        this._postImpactActive = false;
    }

    // ── Public API ──────────────────────────────────────────────────────────

    async start() {
        if (this.active) return;

        // Request permission on iOS 13+
        if (typeof DeviceMotionEvent !== 'undefined' &&
            typeof DeviceMotionEvent.requestPermission === 'function') {
            try {
                const perm = await DeviceMotionEvent.requestPermission();
                if (perm !== 'granted') {
                    console.warn('[FallDetector] Motion permission denied.');
                    return;
                }
            } catch (err) {
                console.warn('[FallDetector] Permission request failed:', err);
                return;
            }
        }

        if (typeof DeviceMotionEvent === 'undefined') {
            console.info('[FallDetector] DeviceMotionEvent not supported on this platform.');
            return;
        }

        window.addEventListener('devicemotion', this._handler);
        this.active = true;
        console.info('[FallDetector] Listening for motion events.');
    }

    stop() {
        window.removeEventListener('devicemotion', this._handler);
        clearTimeout(this._inactivityTimer);
        this.active            = false;
        this.freeFall          = false;
        this.lastImpactTime    = null;
        this.motionBuffer      = [];
        this._postImpactActive = false;
        console.info('[FallDetector] Stopped.');
    }

    // ── Motion handler ──────────────────────────────────────────────────────

    _handleMotion(event) {
        const accel = event.accelerationIncludingGravity;
        if (!accel) return;

        const { x = 0, y = 0, z = 0 } = accel;
        const magnitude = Math.sqrt(x * x + y * y + z * z);
        const now = Date.now();

        // Maintain a 20-second rolling buffer
        this.motionBuffer.push({ magnitude, t: now });
        this.motionBuffer = this.motionBuffer.filter(e => now - e.t < 20000);

        // ── Phase 1: Free-Fall ──
        if (magnitude < 0.5) {
            this.freeFall = true;
        }

        // ── Phase 2: Impact ──
        if (this.freeFall && magnitude > 2.5) {
            this.freeFall          = false;
            this.lastImpactTime    = now;
            this._postImpactActive = true;
            console.info(`[FallDetector] Impact detected (|a|=${magnitude.toFixed(2)}g)`);

            // Start inactivity watch after impact
            clearTimeout(this._inactivityTimer);
            this._inactivityTimer = setTimeout(() => this._checkPostImpact(), 15000);
        }
    }

    // ── Phase 3: Inactivity + multi-signal confirmation ─────────────────────

    _checkPostImpact() {
        if (!this._postImpactActive) return;

        const variance = this._calcVariance(this.motionBuffer.map(e => e.magnitude));
        const confidence = this._computeConfidence(variance);

        console.info(
            `[FallDetector] Post-impact check | variance=${variance.toFixed(3)} | confidence=${confidence.toFixed(2)}`
        );

        if (confidence >= 1.0) {
            this._triggerEmergency(confidence);
        } else {
            this._postImpactActive = false;
        }
    }

    _computeConfidence(motionVariance) {
        let score = 0;

        // Fall + inactivity signal: low variance means no movement after impact
        if (motionVariance < 0.15) score += 0.6;
        else if (motionVariance < 0.5) score += 0.3;

        // HR anomaly signal (reads from window._latestHR set by dashboard.js)
        const hr = window._latestHR;
        if (hr !== null && hr !== undefined) {
            if (hr < 40 || hr > 150) {
                score += 0.3;  // strongly abnormal
            } else if (hr < 50 || hr > 130) {
                score += 0.15;
            }
        }

        // HR flatline signal (reads last 10 HR readings)
        const recentHR = window._hrHistory || [];
        if (recentHR.length >= 5) {
            const hrVariance = this._calcVariance(recentHR);
            if (hrVariance < 1) score += 0.3;  // flatline
        }

        return score;
    }

    _calcVariance(arr) {
        if (arr.length < 2) return 0;
        const mean = arr.reduce((a, b) => a + b, 0) / arr.length;
        const sq   = arr.map(v => Math.pow(v - mean, 2));
        return sq.reduce((a, b) => a + b, 0) / sq.length;
    }

    _triggerEmergency(confidence) {
        this._postImpactActive = false;
        console.warn(`[FallDetector] FALL CONFIRMED | confidence=${confidence.toFixed(2)}`);

        // Delegate to EmergencyEngine (loaded separately)
        if (window.EmergencyEngine) {
            window.EmergencyEngine.start('fall', {
                trigger_detail: `Fall detected (confidence: ${(confidence * 100).toFixed(0)}%)`,
                heart_rate: window._latestHR ?? 'N/A',
                spo2: window._latestSpO2 ?? 'N/A'
            });
        }
    }
}

// Expose as singleton
window.FallDetector = new FallDetector();
