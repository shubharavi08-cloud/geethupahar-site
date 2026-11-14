"""Audio-reactive envelopes: per-frame energy (0..1) and beat pulse (0..1) from a real audio file (numpy only)."""
import subprocess, numpy as np
def envelopes(path, fps=24, start=0.0, dur=None):
    cmd = ["ffmpeg", "-loglevel", "error", "-ss", str(start)] + (["-t", str(dur)] if dur else []) + ["-i", path, "-ac", "1", "-ar", "22050", "-f", "f32le", "-"]
    x = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, dtype=np.float32)
    hop = 22050 // fps; n = len(x) // hop
    fr = x[:n*hop].reshape(n, hop); rms = np.sqrt((fr**2).mean(1))
    # low-band emphasis for beat: crude spectral flux on first FFT bins
    sp = np.abs(np.fft.rfft(fr * np.hanning(hop), axis=1))[:, :24]; flux = np.maximum(0, np.diff(sp.sum(1), prepend=sp[0].sum()))
    en = rms / (np.percentile(rms, 98) + 1e-9); en = np.clip(en, 0, 1)
    k = np.ones(3)/3; en = np.convolve(en, k, "same")
    b = flux / (np.percentile(flux, 95) + 1e-9); b = np.clip(b, 0, 1); out = np.zeros_like(b)
    for i in range(len(b)): out[i] = max(b[i], out[i-1]*0.82 if i else 0)
    return [round(float(v), 3) for v in en], [round(float(v), 3) for v in out]
