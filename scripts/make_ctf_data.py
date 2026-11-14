"""Write materials/ctf_results.csv: a synthetic CTFFIND summary for 40 micrographs.

Synthetic, hand-shaped so each rule in the Skill has something to act on:
  * most micrographs fit at 3.5-5.8 A, a middle band at 6-7.5 A and a tail of 4 bad
    ones, so the 90th percentile (7.64 A) is above the 6 A floor and the cutoff relaxes;
  * two micrographs report a good fit limit with a near-zero figure of merit (a fit
    into noise), which the Skill must flag rather than silently keep;
  * two micrographs are strongly astigmatic, which the Skill reports but does not filter.
Value ranges follow the RELION 5 single-particle tutorial. No real data is used.
"""
import csv
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "materials" / "ctf_results.csv"
rng = random.Random(16)

good = [3.6, 3.7, 3.8, 3.9, 3.9, 4.0, 4.1, 4.1, 4.2, 4.2, 4.3, 4.4, 4.4, 4.5, 4.6,
        4.6, 4.7, 4.8, 4.9, 4.9, 5.0, 5.1, 5.2, 5.3, 5.4, 5.5, 5.5, 5.6, 5.7, 5.8]
middle = [6.1, 6.4, 6.8, 7.0, 7.3, 7.5]
bad = [8.9, 11.2, 14.5, 19.8]
fits = good + middle + bad
rng.shuffle(fits)

rows = []
for i, fit in enumerate(fits, start=1):
    dfu = rng.uniform(9000, 24000)
    astig = rng.uniform(120, 420)
    fom = max(0.06, 0.34 - 0.016 * fit + rng.uniform(-0.03, 0.03))
    rows.append({"micrograph": "mic_%03d" % i, "defocus_u_A": round(dfu),
                 "defocus_v_A": round(dfu - astig), "astigmatism_A": round(astig),
                 "ctf_max_resolution_A": fit, "ctf_figure_of_merit": round(fom, 3)})

# fits into noise: good-looking fit limit, near-zero figure of merit
for name, fom in (("mic_007", 0.031), ("mic_029", 0.042)):
    r = next(r for r in rows if r["micrograph"] == name)
    r["ctf_max_resolution_A"], r["ctf_figure_of_merit"] = (4.0 if name == "mic_007" else 4.4), fom
# strong astigmatism
for name, astig in (("mic_013", 1480), ("mic_034", 1215)):
    r = next(r for r in rows if r["micrograph"] == name)
    r["astigmatism_A"] = astig
    r["defocus_v_A"] = r["defocus_u_A"] - astig

with open(OUT, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print("wrote", OUT)
