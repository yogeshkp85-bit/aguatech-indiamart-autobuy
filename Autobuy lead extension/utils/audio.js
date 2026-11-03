/**
 * IndiaMart Lead Autoclick Pro - Safe Audio Notification Chime
 * Compliant with Chrome Autoplay Policy. Completely avoids uncaught AudioContext errors.
 */

class SoundNotifier {
  static sharedCtx = null;
  static chimeBlobUrl = null;

  /**
   * Pre-generate a 16-bit PCM WAV chime blob URL once
   */
  static getChimeUrl() {
    if (this.chimeBlobUrl) return this.chimeBlobUrl;

    try {
      const sampleRate = 22050;
      const duration = 0.35;
      const numSamples = Math.floor(sampleRate * duration);
      const buffer = new ArrayBuffer(44 + numSamples * 2);
      const view = new DataView(buffer);

      const writeString = (offset, str) => {
        for (let i = 0; i < str.length; i++) {
          view.setUint8(offset + i, str.charCodeAt(i));
        }
      };

      // RIFF header
      writeString(0, 'RIFF');
      view.setUint32(4, 36 + numSamples * 2, true);
      writeString(8, 'WAVE');
      writeString(12, 'fmt ');
      view.setUint32(16, 16, true);
      view.setUint16(20, 1, true); // PCM
      view.setUint16(22, 1, true); // Mono
      view.setUint32(24, sampleRate, true);
      view.setUint32(28, sampleRate * 2, true);
      view.setUint16(32, 2, true);
      view.setUint16(34, 16, true);
      writeString(36, 'data');
      view.setUint32(40, numSamples * 2, true);

      // Synthesize bell chime with harmonics (880Hz + 1318Hz) and exponential decay
      for (let i = 0; i < numSamples; i++) {
        const t = i / sampleRate;
        const env = Math.exp(-8.0 * t);
        const s = (0.6 * Math.sin(2 * Math.PI * 880 * t) + 0.4 * Math.sin(2 * Math.PI * 1318.5 * t)) * env;
        const sample = Math.max(-1, Math.min(1, s)) * 28000;
        view.setInt16(44 + i * 2, sample, true);
      }

      const blob = new Blob([buffer], { type: 'audio/wav' });
      this.chimeBlobUrl = URL.createObjectURL(blob);
      return this.chimeBlobUrl;
    } catch (e) {
      return null;
    }
  }

  /**
   * Unlock AudioContext on first user interaction
   */
  static unlockContext() {
    try {
      if (!this.sharedCtx) {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (AudioCtx) this.sharedCtx = new AudioCtx();
      }
      if (this.sharedCtx && this.sharedCtx.state === 'suspended') {
        this.sharedCtx.resume().catch(() => {});
      }
    } catch (e) {}
  }

  /**
   * Safe chime playback without any unhandled autoplay errors
   */
  static playSuccessChime() {
    try {
      // Strategy 1: If AudioContext is active and running, use high-precision synthesis
      if (this.sharedCtx && this.sharedCtx.state === 'running') {
        try {
          const ctx = this.sharedCtx;
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.type = 'sine';
          osc.frequency.setValueAtTime(880, ctx.currentTime);
          gain.gain.setValueAtTime(0.3, ctx.currentTime);
          gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.start(ctx.currentTime);
          osc.stop(ctx.currentTime + 0.35);
          return;
        } catch (ctxErr) {
          // Fall through to HTMLAudioElement
        }
      }

      // Strategy 2: HTMLAudioElement with caught promise
      // This guarantees Chrome will NEVER flag an unhandled Autoplay error in chrome://extensions
      const url = this.getChimeUrl();
      if (url) {
        const audio = new Audio(url);
        audio.volume = 0.5;
        const playPromise = audio.play();
        if (playPromise !== undefined) {
          playPromise.catch(() => {
            // Autoplay prevented before user interaction; safely ignored with zero console/extension error
          });
        }
      }
    } catch (err) {
      // Quietly ignore all audio errors
    }
  }
}

// Auto-register passive interaction listeners to unlock audio seamlessly
if (typeof window !== 'undefined') {
  window.SoundNotifier = SoundNotifier;

  ['click', 'keydown', 'mousedown', 'touchstart'].forEach(evt => {
    window.addEventListener(evt, () => {
      SoundNotifier.unlockContext();
    }, { passive: true, capture: true });
  });
}
