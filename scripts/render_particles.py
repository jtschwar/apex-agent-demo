"""Render a few single particle images from one 2D class, for the "why average?" explainer.

Usage: python scripts/render_particles.py <project dir> <Class2D/jobNNN> <iteration> <class> [n]

Reads <job>/run_itNNN_data.star to find particles assigned to <class>, then reads those
images from the extracted stacks. Writes assets/particles/class_NN_p<i>.png. Each image is
rotated by its in-plane angle so it lines up with the class average, then gently low-passed
so the slide shows what the eye sees: still mostly noise.
"""
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


def read_star(path):
    lines = path.read_text().splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith("data_particles"))
    cols, rows = [], []
    for l in lines[i + 1:]:
        s = l.strip()
        if s.startswith("_rln"):
            cols.append(s.split()[0][4:])
        elif cols and s and not s.startswith(("loop_", "#")):
            rows.append(dict(zip(cols, s.split())))
    return rows


def read_slice(path, index):
    with open(path, "rb") as fh:
        h = fh.read(1024)
        nx, ny, nz, mode = struct.unpack("4i", h[:16])
        dtype = {2: "<f4", 12: "<f2"}[mode]            # float32, or RELION 5's float16 stacks
        size = np.dtype(dtype).itemsize
        ext = struct.unpack("i", h[92:96])[0]
        fh.seek(1024 + ext + (index - 1) * nx * ny * size)
        return np.frombuffer(fh.read(nx * ny * size), dtype=dtype).reshape(ny, nx).astype(np.float64)


def lowpass(img, frac=0.12):
    f = np.fft.fft2(img - img.mean())
    ky = np.fft.fftfreq(img.shape[0])[:, None]
    kx = np.fft.fftfreq(img.shape[1])[None, :]
    return np.real(np.fft.ifft2(f * np.exp(-(kx ** 2 + ky ** 2) / (2 * frac ** 2))))


def to_u8(img):
    lo, hi = np.percentile(img, [1, 99])
    return (np.clip((img - lo) / (hi - lo), 0, 1) * 255).astype(np.uint8)


def main(project, job, it, cls, n=5):
    project = Path(project)
    rows = [r for r in read_star(project / job / ("run_it%03d_data.star" % it)) if r["ClassNumber"] == str(cls)]
    rng = np.random.default_rng(cls)
    picks = rng.choice(len(rows), size=n, replace=False)
    out = ROOT / "assets" / "particles"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("class_%02d_p*.png" % cls):
        old.unlink()
    for i, k in enumerate(sorted(picks), start=1):
        r = rows[k]
        idx, stack = r["ImageName"].split("@")
        img = lowpass(read_slice(project / stack, int(idx)))
        im = Image.fromarray(to_u8(img)).rotate(float(r.get("AnglePsi", 0)), resample=Image.BILINEAR)
        a = np.asarray(im.resize((180, 180), Image.LANCZOS)).copy()
        yy, xx = np.indices(a.shape) - 89.5
        a[np.hypot(yy, xx) > 80] = 46                  # same circle and surround as the class tiles
        Image.fromarray(a).save(out / ("class_%02d_p%d.png" % (cls, i)))
    print("wrote %d of the %d particles in class %d" % (n, len(rows), cls))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), *(int(a) for a in sys.argv[5:6]))
