"""Render a RELION Class2D iteration into the demo's gallery and class table.

Usage: python scripts/render_class2d.py <Class2D/jobNNN dir> <iteration>

Writes, relative to the repo root:
  materials/class2d_gallery.png   numbered grid of every class (what Claude reads)
  materials/class2d_classes.csv   per-class metadata from run_itNNN_model.star
  assets/classes/class_NN.png     one upscaled image per class (for the web page)
"""
import csv
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent


def read_mrcs(path):
    raw = path.read_bytes()
    nx, ny, nz, mode = struct.unpack("4i", raw[:16])
    assert mode == 2, "expected float32 MRC"
    ext = struct.unpack("i", raw[92:96])[0]
    data = np.frombuffer(raw, dtype="<f4", offset=1024 + ext, count=nx * ny * nz)
    return data.reshape(nz, ny, nx)


def read_model_classes(path):
    lines = path.read_text().splitlines()
    i = lines.index("data_model_classes")
    cols, rows = [], []
    for line in lines[i + 1:]:
        s = line.strip()
        if s.startswith("_rln"):
            cols.append(s.split()[0][4:])
        elif cols and s and not s.startswith(("loop_", "data_")):
            rows.append(dict(zip(cols, s.split())))
        elif rows and (not s or s.startswith("data_")):
            break
    return rows


def to_u8(img, outside=46):
    """Contrast-stretch using only the pixels inside the circular mask.

    RELION's zero mask leaves a constant value outside the circle; including it in the
    percentiles makes the surround a different grey in every class. Paint it one shade.
    """
    inside = np.abs(img - img[0, 0]) > 1e-6
    if not inside.any():
        return np.full(img.shape, outside, np.uint8)
    lo, hi = np.percentile(img[inside], [1, 99])
    if hi <= lo:
        return np.full(img.shape, 128, np.uint8)
    out = (np.clip((img - lo) / (hi - lo), 0, 1) * 255).astype(np.uint8)
    out[~inside] = outside
    return out


def font(size):
    for name in ("/System/Library/Fonts/Helvetica.ttc",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def main(job_dir, it):
    job = Path(job_dir)
    for old in (ROOT / "assets/classes").glob("class_*.png"):   # drop images from a previous, larger run
        old.unlink()
    stack = read_mrcs(job / ("run_it%03d_classes.mrcs" % it))
    meta = read_model_classes(job / ("run_it%03d_model.star" % it))
    n_particles = sum(1 for l in (job / ("run_it%03d_data.star" % it)).read_text().splitlines()
                      if "@" in l)

    rows = []
    for k, m in enumerate(meta, start=1):
        frac = float(m["ClassDistribution"])
        res = float(m["EstimatedResolution"])
        rows.append({
            "class": k,
            "particle_fraction": round(frac, 4),
            "particles": round(frac * n_particles),
            "estimated_resolution_A": "" if res == float("inf") or res != res else round(res, 1),
            "empty": "yes" if frac == 0 else "no",
        })
    with open(ROOT / "materials/class2d_classes.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    tile, pad, label_h = 180, 8, 40
    ncol = 8 if len(stack) <= 24 else 10
    nrow = -(-len(stack) // ncol)
    sheet = Image.new("RGB", (ncol * (tile + pad) + pad, nrow * (tile + label_h + pad) + pad), "white")
    draw = ImageDraw.Draw(sheet)
    f_big, f_small = font(22), font(16)
    for k, (img, r) in enumerate(zip(stack, rows), start=1):
        im = Image.fromarray(to_u8(img)).resize((tile, tile), Image.LANCZOS)
        im.save(ROOT / ("assets/classes/class_%02d.png" % k))
        x = pad + ((k - 1) % ncol) * (tile + pad)
        y = pad + ((k - 1) // ncol) * (tile + label_h + pad)
        sheet.paste(im, (x, y + label_h))
        draw.text((x + 2, y + 2), "#%d" % k, fill="black", font=f_big)
        draw.text((x + 60, y + 8), "%.1f%%" % (100 * r["particle_fraction"]), fill="#52514e", font=f_small)
    sheet.save(ROOT / "materials/class2d_gallery.png")
    print("wrote %d classes from %d particles" % (len(rows), n_particles))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
