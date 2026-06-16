/**
 * max-bridge.js — Promise-based wrapper for Max WebApp Bridge SDK
 *
 * Wraps window.WebApp.* with clean async API and graceful fallback
 * when not running inside the Max client (browser/dev mode).
 *
 * Usage:
 *   const bridge = new MaxBridge();
 *   if (!bridge.isAvailable) console.warn("Not in Max client");
 *
 *   const user = bridge.user;
 *   const contact = await bridge.requestContact();
 *   await bridge.haptic.impact("light");
 *
 * All async methods reject with { error: { code: string } }
 * when the Bridge returns an error or is unavailable.
 */

class MaxBridge {
    constructor() {
        this._wb = (typeof window !== "undefined" && window.WebApp) || null;
    }

    // ── Meta ────────────────────────────────────────────────────────────────

    /** True when running inside the Max client WebView. */
    get isAvailable() { return !!this._wb; }

    /** Platform string: 'ios' | 'android' | 'desktop' | 'web' | null */
    get platform() { return this._wb?.platform ?? null; }

    /** Max version string, e.g. "25.9.16" */
    get version() { return this._wb?.version ?? null; }

    // ── initData ────────────────────────────────────────────────────────────

    /**
     * Raw initData string for server-side HMAC validation.
     * Send this to your backend — never trust initDataUnsafe directly.
     */
    get initData() { return this._wb?.initData ?? ""; }

    /** Parsed initData WITHOUT signature — do NOT use for auth decisions. */
    get initDataUnsafe() { return this._wb?.initDataUnsafe ?? {}; }

    /** Shortcut: current user from initDataUnsafe. */
    get user() { return this._wb?.initDataUnsafe?.user ?? null; }

    /** start_param from OpenAppButton payload or deeplink. */
    get startParam() { return this._wb?.initDataUnsafe?.start_param ?? null; }

    // ── Contact ─────────────────────────────────────────────────────────────

    /**
     * Request user's phone number.
     * Validate the returned hash server-side via validate_contact().
     *
     * @returns {Promise<{phone: string, authDate: string, hash: string}>}
     */
    async requestContact() {
        this._require("requestContact");
        return this._wb.requestContact();
    }

    // ── Links & Files ────────────────────────────────────────────────────────

    /**
     * Open a URL in the external browser.
     * Must be called from a user click handler.
     * @param {string} url
     */
    openLink(url) {
        this._require("openLink");
        this._wb.openLink(url);
    }

    /**
     * Open a Max deeplink (https://max.ru/...) or fall back to browser.
     * @param {string} url
     */
    openMaxLink(url) {
        this._require("openMaxLink");
        this._wb.openMaxLink(url);
    }

    /**
     * Download a file. Must be HTTPS and called from a user click handler.
     * @param {string} url
     * @param {string} fileName
     * @returns {Promise<{status: 'downloading'|'cancelled'}>}
     */
    async downloadFile(url, fileName) {
        this._require("downloadFile");
        return this._wb.downloadFile(url, fileName);
    }

    // ── Sharing ──────────────────────────────────────────────────────────────

    /**
     * Native OS share sheet (iOS/Android only).
     * @param {{text?: string, link?: string}} params  At least one required.
     * @returns {Promise<{status: 'shared'|'cancelled'}>}
     */
    async shareContent(params) {
        this._require("shareContent");
        return this._wb.shareContent(params);
    }

    /**
     * Share inside Max (text/link OR forward a message by mid).
     * @param {{text?: string, link?: string}|{mid: string, chatType: 'DIALOG'|'CHAT'}} params
     * @returns {Promise<{status: 'shared'|'cancelled'}>}
     */
    async shareMaxContent(params) {
        this._require("shareMaxContent");
        return this._wb.shareMaxContent(params);
    }

    // ── QR Code ─────────────────────────────────────────────────────────────

    /**
     * Open QR / barcode scanner.
     * @param {boolean} [fileSelect=true]  Allow gallery selection in addition to camera.
     * @returns {Promise<{value: string}>}
     */
    async openCodeReader(fileSelect = true) {
        this._require("openCodeReader");
        return this._wb.openCodeReader(fileSelect);
    }

    // ── Closing Confirmation ─────────────────────────────────────────────────

    /** Show "are you sure?" dialog when user tries to close the mini-app. */
    enableClosingConfirmation() {
        this._wb?.enableClosingConfirmation();
    }

    disableClosingConfirmation() {
        this._wb?.disableClosingConfirmation();
    }

    // ── Screen ───────────────────────────────────────────────────────────────

    /**
     * Set screen to maximum brightness for 30 seconds (iOS/Android).
     * @returns {Promise<{maxBrightness: boolean}>}
     */
    async requestMaxBrightness() {
        this._require("requestScreenMaxBrightness");
        return this._wb.requestScreenMaxBrightness();
    }

    /**
     * Restore screen brightness to user setting.
     * @returns {Promise<{maxBrightness: boolean}>}
     */
    async restoreBrightness() {
        this._require("restoreScreenBrightness");
        return this._wb.restoreScreenBrightness();
    }

    // ── Back Button ──────────────────────────────────────────────────────────

    /**
     * Back button controller.
     *
     * @example
     * bridge.backButton.show();
     * bridge.backButton.onClick(() => history.back());
     */
    get backButton() {
        const wb = this._wb;
        return {
            get isVisible() { return wb?.BackButton?.isVisible ?? false; },
            show: () => wb?.BackButton?.show(),
            hide: () => wb?.BackButton?.hide(),
            onClick: (cb) => wb?.BackButton?.onClick(cb),
            offClick: (cb) => wb?.BackButton?.offClick(cb),
        };
    }

    // ── Haptic Feedback ──────────────────────────────────────────────────────

    /**
     * Haptic feedback controller (iOS/Android only).
     *
     * @example
     * await bridge.haptic.impact("medium");
     * await bridge.haptic.notification("success");
     * await bridge.haptic.selectionChanged();
     */
    get haptic() {
        const wb = this._wb;
        return {
            /**
             * @param {'light'|'medium'|'heavy'|'rigid'|'soft'} style
             * @param {boolean} [disableVibrationFallback=false]
             */
            impact: (style, disableVibrationFallback = false) =>
                wb?.HapticFeedback?.impactOccurred(style, disableVibrationFallback)
                    ?? Promise.resolve({ status: "unavailable" }),

            /**
             * @param {'error'|'success'|'warning'} type
             * @param {boolean} [disableVibrationFallback=false]
             */
            notification: (type, disableVibrationFallback = false) =>
                wb?.HapticFeedback?.notificationOccurred(type, disableVibrationFallback)
                    ?? Promise.resolve({ status: "unavailable" }),

            /** Use on selection change, not on confirmation. */
            selectionChanged: (disableVibrationFallback = false) =>
                wb?.HapticFeedback?.selectionChanged(disableVibrationFallback)
                    ?? Promise.resolve({ status: "unavailable" }),
        };
    }

    // ── Device Storage ───────────────────────────────────────────────────────

    /**
     * Unencrypted per-bot local storage (iOS/Android).
     * Do NOT store secrets here — use secureStorage instead.
     *
     * @example
     * await bridge.deviceStorage.set("theme", "dark");
     * const { value } = await bridge.deviceStorage.get("theme");
     */
    get deviceStorage() {
        const wb = this._wb;
        return {
            set: (key, value) => wb?.DeviceStorage?.setItem(key, value),
            get: (key) => wb?.DeviceStorage?.getItem(key),
            remove: (key) => wb?.DeviceStorage?.removeItem(key),
            clear: () => wb?.DeviceStorage?.clear(),
        };
    }

    // ── Secure Storage ───────────────────────────────────────────────────────

    /**
     * Encrypted per-bot secure storage (iOS/Android, max 10 keys).
     * Use for auth tokens and user preferences that need protection.
     *
     * @example
     * await bridge.secureStorage.set("session", token);
     * const { value } = await bridge.secureStorage.get("session");
     */
    get secureStorage() {
        const wb = this._wb;
        return {
            set: (key, value) => wb?.SecureStorage?.setItem(key, value),
            get: (key) => wb?.SecureStorage?.getItem(key),
            remove: (key) => wb?.SecureStorage?.removeItem(key),
            clear: () => wb?.SecureStorage?.clear(),
        };
    }

    // ── Biometric ────────────────────────────────────────────────────────────

    /**
     * Biometric authentication manager (iOS/Android).
     *
     * @example
     * const info = await bridge.biometric.init();
     * if (info.available) {
     *   const { token } = await bridge.biometric.authenticate("Confirm payment");
     * }
     */
    get biometric() {
        const wb = this._wb;
        return {
            /**
             * @returns {Promise<{available, type, accessRequested, accessGranted, tokenSaved, deviceId}>}
             */
            init: () => wb?.BiometricManager?.init(),

            get isInited() { return wb?.BiometricManager?.isInited ?? false; },
            get isAvailable() { return wb?.BiometricManager?.isBiometricAvailable ?? false; },
            get isAccessGranted() { return wb?.BiometricManager?.isAccessGranted ?? false; },
            get type() { return wb?.BiometricManager?.biometricType ?? []; },
            get deviceId() { return wb?.BiometricManager?.deviceId ?? null; },

            /** @param {string} [reason]  Shown to user. Max 128 chars. */
            requestAccess: (reason) => wb?.BiometricManager?.requestAccess(reason),

            /** @param {string} [reason]  @returns {Promise<{status:'authorized', token:string}>} */
            authenticate: (reason) => wb?.BiometricManager?.authenticate(reason),

            /** @param {string} [token]  Omit to delete saved token. */
            updateToken: (token, reason) => wb?.BiometricManager?.updateBiometricToken(token, reason),

            /** Opens privacy settings; closes the mini-app. */
            openSettings: () => wb?.BiometricManager?.openSettings(),
        };
    }

    // ── NFC ──────────────────────────────────────────────────────────────────

    /**
     * NFC tag emulation (Android only).
     *
     * @example
     * const info = await bridge.nfc.init();
     * if (info.available && info.enabled) {
     *   const result = await bridge.nfc.emulate("payload");
     * }
     */
    get nfc() {
        const wb = this._wb;
        return {
            /** @returns {Promise<{available, enabled, accessRevoked?}>} */
            init: () => wb?.NfcManager?.init(),

            get isInited() { return wb?.NfcManager?.isInited ?? false; },

            /** Opens NFC system settings; closes the mini-app. */
            openSettings: () => wb?.NfcManager?.openSystemSettings(),

            /**
             * Emulate NFC tag. Call without argument to stop broadcasting.
             * @param {string} [payload]
             * @returns {Promise<{status:'scanned'|'stopped'}>}
             */
            emulate: (payload) => wb?.NfcManager?.emulateNfcTag(payload),
        };
    }

    // ── Screen Capture ───────────────────────────────────────────────────────

    /**
     * Screen capture control (iOS/Android).
     *
     * @example
     * await bridge.screenCapture.disable();  // block screenshots
     */
    get screenCapture() {
        const wb = this._wb;
        return {
            enable: () => wb?.ScreenCapture?.enableScreenCapture(),
            disable: () => wb?.ScreenCapture?.disableScreenCapture(),
        };
    }

    // ── Auth helper ──────────────────────────────────────────────────────────

    /**
     * Send initData to the bot API for server-side validation.
     * The server responds with the validated user object.
     *
     * @param {string} apiUrl  Your bot's /api/auth endpoint URL
     * @returns {Promise<Object>}  Parsed JSON response
     */
    async authenticate(apiUrl) {
        const resp = await fetch(apiUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `MaxWebApp ${this.initData}`,
            },
            body: JSON.stringify({}),
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.error || `HTTP ${resp.status}`);
        }
        return resp.json();
    }

    // ── Internal ─────────────────────────────────────────────────────────────

    _require(method) {
        if (!this._wb) {
            throw new Error(`MaxBridge.${method}: not running inside Max client`);
        }
    }
}

// Export as ES module and global variable
if (typeof module !== "undefined" && module.exports) {
    module.exports = { MaxBridge };
} else if (typeof window !== "undefined") {
    window.MaxBridge = MaxBridge;
}
