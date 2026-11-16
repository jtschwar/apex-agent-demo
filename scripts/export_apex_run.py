"""Export a real ApexAgent run as materials/apex_run.json, for the deck's timeline.

Usage: python scripts/export_apex_run.py <ApexAgent project dir>

Reads <project>/ApexAgent/apex.db read-only (the run's proposals, stage attempts, and
decision log) and <project>/PostProcess/*/postprocess.star for the final resolution.
Cluster paths are stripped from every exported string, since the file is published.
"""
import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Plain-language names for the audience; the RELION job type stays in the tooltip.
STEPS = {
    "import": ("Load the 24 microscope movies", "Clean up the photos"),
    "motioncorr": ("Undo the shake in each movie", "Clean up the photos"),
    "ctffind": ("Score each photo's sharpness", "Clean up the photos"),
    "filter_mics": ("Drop blurry photos", "Clean up the photos"),
    "autopick_bootstrap": ("Find the molecules in each photo", "Find and sort the copies"),
    "extract_preview": ("Cut out each copy", "Find and sort the copies"),
    "class2d_loop": ("Sort copies into look-alike groups (2 tries at once)", "Find and sort the copies"),
    "select_particles": ("Keep the good groups", "Find and sort the copies"),
    "initialmodel": ("Build a first 3D shape", "Build the 3D shape"),
    "refine3d_consensus": ("Sharpen the 3D shape", "Build the 3D shape"),
    "mask_consensus": ("Outline the molecule", "Build the 3D shape"),
    "class3d": ("Sort copies in 3D", "Build the 3D shape"),
    "select_3d_class": ("Keep the best 3D group", "Build the 3D shape"),
    "reextract_full": ("Cut out copies again at full detail", "Refine and check"),
    "remove_duplicates": ("Remove copies counted twice", "Refine and check"),
    "reconstruct_full": ("Rebuild at full detail", "Refine and check"),
    "mask_fullres": ("Outline the molecule again", "Refine and check"),
    "postprocess_check": ("Measure the detail (first check)", "Refine and check"),
    "refine3d": ("Final refinement", "Refine and check"),
    "postprocess": ("Measure the final detail", "Refine and check"),
    "apex_prepare": ("Prepare a flexibility analysis", "Refine and check"),
    "apex_train": ("Run the flexibility analysis", "Refine and check"),
}
PHASES = ["Clean up the photos", "Find and sort the copies", "Build the 3D shape", "Refine and check"]

JUDGEMENTS = {   # decision kind -> what the agent judged, in plain words
    "micrograph_evaluation": "Checked every photo's sharpness and motion",
    "pick_threshold": "Looked at 8 photos to decide how picky the molecule finder should be",
    "class_selection": "Chose which groups to keep",
    "view_reconciliation": "Compared the two sorting tries side by side",
    "mask_threshold": "Chose how tightly to outline the molecule",
}


def ts(s):
    return datetime.fromisoformat(s)


def scrub(text, limit=300):
    text = re.sub(r"/(?:hpc|home|Users)\S*", "…", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind(": "))
    return (cut[:end + 1] if end > limit // 2 else cut.rstrip() + "…").strip()


def main(project):
    project = Path(project)
    db = sqlite3.connect("file:%s?mode=ro" % (project / "ApexAgent" / "apex.db"), uri=True)
    db.row_factory = sqlite3.Row
    decisions = db.execute("select * from decision order by id").fetchall()
    t0 = ts(decisions[0]["created_at"])
    minutes = lambda s: round((ts(s) - t0).total_seconds() / 60, 2)

    jobs = {}
    for a in db.execute("select * from stageattempt where state='COMPLETED' order by id"):
        key = a["stage_key"]
        label, phase = STEPS.get(key, (key, PHASES[-1]))
        start, end = minutes(a["submitted_at"]), minutes(a["completed_at"])
        if key in jobs:                                   # parallel arms of one stage: one bar
            jobs[key]["start"] = min(jobs[key]["start"], start)
            jobs[key]["end"] = max(jobs[key]["end"], end)
            jobs[key]["jobs"].append(a["job_name"])
        else:
            jobs[key] = {"key": key, "label": label, "phase": phase, "start": start, "end": end,
                         "jobs": [a["job_name"]], "job_type": None}
    for p in db.execute("select stage_key, job_type from proposal"):
        if p["stage_key"] in jobs:
            jobs[p["stage_key"]]["job_type"] = p["job_type"]

    judgements = []
    for d in decisions:
        if d["kind"] in JUDGEMENTS:
            phase = STEPS.get(d["stage_key"], ("", PHASES[0]))[1]
            what = JUDGEMENTS[d["kind"]]
            if d["kind"] == "class_selection" and (d["job_name"] or "").startswith("Class3D"):
                what = "Chose the best 3D group"
            judgements.append({"t": minutes(d["created_at"]), "phase": phase, "what": what,
                               "job": d["job_name"], "reason": scrub(d["reason"])})

    final_res = None
    for star in sorted(project.glob("PostProcess/*/postprocess.star")):
        m = re.search(r"_rlnFinalResolution\s+([\d.]+)", star.read_text())
        if m:
            final_res = round(float(m.group(1)), 1)
    project_row = db.execute("select target_json, autonomy from project").fetchone()
    target = json.loads(project_row["target_json"] or "{}").get("name")

    out = {
        "target": target,
        "autonomy": project_row["autonomy"],
        "duration_min": minutes(decisions[-1]["created_at"]),
        "n_jobs": db.execute("select count(*) from stageattempt where state='COMPLETED'").fetchone()[0],
        "n_decisions": len(decisions),
        "n_human": sum(d["decided_by"] == "HUMAN" for d in decisions),
        "final_resolution_A": final_res,
        "phases": PHASES,
        "steps": sorted(jobs.values(), key=lambda j: j["start"]),
        "judgements": judgements,
    }
    (ROOT / "materials" / "apex_run.json").write_text(json.dumps(out, indent=1))
    print("wrote materials/apex_run.json: %d jobs, %d decisions (%d human), %d judgement calls, %.0f min, %s A"
          % (out["n_jobs"], out["n_decisions"], out["n_human"], len(judgements), out["duration_min"], final_res))


if __name__ == "__main__":
    main(sys.argv[1])
