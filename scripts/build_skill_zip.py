"""Package skill/cryoem-review/ as materials/cryoem-review.zip for upload to claude.ai.

The zip holds the skill folder itself (cryoem-review/SKILL.md), which is the layout
claude.ai's skill upload expects. Re-run after editing SKILL.md.
"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
src = ROOT / "skill" / "cryoem-review"
out = ROOT / "materials" / "cryoem-review.zip"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(src.rglob("*")):
        if f.is_file() and f.name != ".DS_Store":
            z.write(f, f.relative_to(src.parent))
print("wrote", out, [n for n in zipfile.ZipFile(out).namelist()])
