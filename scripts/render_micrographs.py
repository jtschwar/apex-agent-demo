"""Render real micrographs and their power spectra (Thon rings) as web images.

Usage: python scripts/render_micrographs.py <MotionCorr/jobNNN/Movies dir> <name> [<name> ...]

For each name (e.g. 20170629_00021_frameImage) writes, relative to the repo root:
  assets/micrographs/<name>.jpg      the photo, binned 4x and gently low-passed so the
                                     particles are visible at slide size
  assets/micrographs/<name>_ps.png   its power spectrum, averaged over tiles (Welch), so
                                     the rings the CTF fit reads are visible
"""
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "micrographs"


def read_mrc(path):
    raw = path.read_bytes()
    nx, ny, nz, mode = struct.unpack("4i", raw[:16])
    assert mode == 2 and nz == 1, "expected one float32 image"
    ext = struct.unpack("i", raw[92:96])[0]
    expected = 1024 + ext + nx * ny * 4
    assert len(raw) == expected, "%s is incomplete (%d of %d bytes)" % (path.name, len(raw), expected)
    return np.frombuffer(raw, dtype="<f4", offset=1024 + ext, count=nx * ny).reshape(ny, nx).astype(np.float64)


def stretch(img, lo_pct=1, hi_pct=99):
    lo, hi = np.percentile(img, [lo_pct, hi_pct])
    return (np.clip((img - lo) / (hi - lo), 0, 1) * 255).astype(np.uint8)


def photo(img, binning=4):
    ny, nx = (s // binning * binning for s in img.shape)
    small = img[:ny, :nx].reshape(ny // binning, binning, nx // binning, binning).mean(axis=(1, 3))
    f = np.fft.rfft2(small - small.mean())                         # Gaussian low-pass
    ky = np.fft.fftfreq(small.shape[0])[:, None]
    kx = np.fft.rfftfreq(small.shape[1])[None, :]
    f *= np.exp(-(kx ** 2 + ky ** 2) / (2 * 0.08 ** 2))
    return stretch(np.fft.irfft2(f, s=small.shape), 0.5, 99.5)


def blur(a, sigma):
    k = np.exp(-0.5 * (np.arange(-3 * sigma, 3 * sigma + 1) / sigma) ** 2)
    k /= k.sum()
    a = np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 0, a)
    return np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 1, a)


def spectrum(img, box=512, binning=2):
    """Tile-averaged power spectrum of the 2x-binned photo (edge of the disc = 2 x 2 x pixel size)."""
    ny, nx = (s // binning * binning for s in img.shape)
    img = img[:ny, :nx].reshape(ny // binning, binning, nx // binning, binning).mean(axis=(1, 3))
    ny, nx = img.shape
    win = np.outer(np.hanning(box), np.hanning(box))
    acc, n = np.zeros((box, box)), 0
    for y in range(0, ny - box + 1, box // 4):
        for x in range(0, nx - box + 1, box // 4):
            t = img[y:y + box, x:x + box]
            acc += np.abs(np.fft.fft2((t - t.mean()) * win)) ** 2
            n += 1
    ps = blur(np.log(np.fft.fftshift(acc / n) + 1e-12), 1.2)
    yy, xx = np.indices(ps.shape) - box // 2
    r = np.hypot(yy, xx).astype(int)
    cnt = np.maximum(np.bincount(r.ravel()), 1)
    mean = np.bincount(r.ravel(), ps.ravel()) / cnt
    # background: the radial profile smoothed along the radius only (wider than a ring),
    # then each radius scaled by its own spread so faint outer rings show as clearly as inner ones
    k = np.exp(-0.5 * (np.arange(-24, 25) / 8.0) ** 2); k /= k.sum()
    pad = np.pad(mean, 24, mode="edge")
    bg = np.convolve(pad, k, mode="same")[24:-24]
    flat = ps - bg[r]
    spread = np.sqrt(np.bincount(r.ravel(), (flat ** 2).ravel()) / cnt)
    flat = flat / np.convolve(np.pad(spread, 24, mode="edge"), k, mode="same")[24:-24][r]
    keep = (r < box // 2 - 10) & (r > 10)
    out = (np.clip((flat + 2.2) / 4.4, 0, 1) * 255).astype(np.uint8)
    out[~keep] = 0
    return out


def main(movies_dir, names):
    OUT.mkdir(parents=True, exist_ok=True)
    for name in names:
        img = read_mrc(Path(movies_dir) / (name + ".mrc"))
        Image.fromarray(photo(img)).save(OUT / (name + ".jpg"), quality=86)
        Image.fromarray(spectrum(img)).save(OUT / (name + "_ps.png"))
        print("wrote", name)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
