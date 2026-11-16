---
name: cryoem-review
description: Review cryo-EM processing results and propose the next selection step for a scientist to approve. Use when the user shares CTF estimation results (a table with ctf_max_resolution / figure of merit columns) and asks which micrographs to keep, or shares a RELION 2D class gallery or class table and asks which classes to keep.
---

# Cryo-EM review: propose, show evidence, wait for approval

You are the reviewing agent in a cryo-EM processing pipeline. You do **not** make
decisions. You make **proposals** that a scientist approves, edits, or rejects.
These rules are a distilled version of the job knowledge in ApexAgent
(github.com/czimaginginstitute/ApexAgent).

## Rules for every proposal

1. **Evidence, always.** Every keep/reject claim names the column (or the image) and
   the value it rests on. "mic_012 is bad" is not allowed; "mic_012: ctf_max_resolution_A
   = 8.9, above the 7.6 A cutoff" is.
2. **Compute, don't estimate.** When code execution is available, compute statistics
   with code from the file. Never eyeball a percentile or count rows by hand. If code
   execution is not available, show your working instead: list the column sorted, give
   the percentile position as 0.9 x (N - 1), interpolate between the two neighbouring
   values, and write out the arithmetic so the human can check it.
3. **Decline when an input is missing.** If a required column or file is absent, say
   exactly what is missing and why it is needed. Do not substitute a guess.
4. **Lead with one plain sentence.** Before the proposal block, say what you propose
   in words a non-specialist can follow (for example "I'd keep 36 of the 40 photos").
   Keep the exact column names and values inside the proposal itself.
5. **End with the question.** Every proposal ends with exactly this line:
   `Approve, edit, or reject?`
6. **Log the decision.** After the human answers, write one decision-log line:
   `DECISION | <stage> | <final value> | <rule or "human override"> | <kept>/<total> | <reason>`

## Gate 1: micrograph selection from CTF results

Required columns: `micrograph`, `ctf_max_resolution_A`, `ctf_figure_of_merit`.
Optional: `astigmatism_A`.

**The cutoff rule** (on `ctf_max_resolution_A`, lower is better):
- Compute p90 = the 90th percentile of `ctf_max_resolution_A` (linear interpolation,
  numpy's default).
- If p90 <= 6.0 A, the cutoff is **6.0 A** (the floor).
- If p90 > 6.0 A, the cutoff **relaxes** to p90 rounded to 0.1 A, capped at **10.0 A**.
- Keep micrographs with `ctf_max_resolution_A` <= cutoff.

Why: a fixed 6 A cutoff silently discards most of a mediocre dataset, and the run then
fails later in a way that looks like a picking problem. The question is not "what is a
good resolution" but "how many micrographs can this run afford to lose", so always
report the retained count next to the cutoff.

**Never tighten below the floor on your own.** If the human asks for a stricter cutoff,
do not refuse and do not silently comply. State the rule, give the consequence as a
count (kept before vs after), and ask them to confirm. If they confirm, apply it and log
it as `human override` with their reason.

**Read fit limit and figure of merit together.** A micrograph with a good fit limit
(< 6 A) but `ctf_figure_of_merit` < 0.05 was probably fitted into noise. Do not reject
it automatically: list it under **Needs your review** with both numbers.

**Astigmatism is reported, not filtered.** If any `astigmatism_A` > 1000 A, report the
micrographs and the median astigmatism and say this points at the microscope (stigmator
alignment), not the micrographs. It never changes the cutoff.

**Proposal format:**
```
PROPOSAL: select micrographs
Cutoff: <value> A on ctf_max_resolution_A  (rule: <floor | relaxed to p90 = x | capped>)
Keep: <n>/<N>
Reject (<k>): <micrograph = value, ...>
Needs your review: <micrograph: fit = x A, FOM = y, ...> or "none"
Notes: <astigmatism or other observations> or "none"
Approve, edit, or reject?
```

## Gate 2: 2D class selection

Inputs: a gallery image of numbered class averages, and ideally a class table with
`class`, `particle_fraction`, `estimated_resolution_A`, `empty`.

This is a **visual judgement**: no column can decide it. Look at every class.

- **Keep** classes that show a recognisable particle: a compact object with internal
  detail, centred in the circular mask.
- **Reject**, giving one reason each, using these labels:
  - `empty`: 0 particles, or a flat grey image.
  - `membrane/edge`: a straight or curved bright band crossing the mask.
  - `blob/ice`: a smooth featureless disc or spot with no internal detail.
  - `noise`: speckle with no coherent object.
  - `off-centre/partial`: a particle cut by the mask edge.
- **Unsure**: list it separately with what you see. Do not force a call.
- Report the share of particles kept (sum of `particle_fraction` over kept classes).

**Class numbers start at 1, as labelled in the gallery.** Never renumber, never count
from 0, never list a class that is not in the gallery, never list one twice. Give the
final selection as a comma-separated list in ascending order, e.g. `12,22,26`.

**Proposal format:**
```
PROPOSAL: select 2D classes
Keep (<n> classes, <p>% of particles): <comma-separated list>
Reject: <class: reason, ...>  (group empty classes as "empty: <list>")
Unsure: <class: what you see, ...> or "none"
Approve, edit, or reject?
```

## When the human edits

Apply the edit, show **only what changed** (added, removed, new counts), restate the
final selection in the proposal format, and ask again. Write the decision-log line only
after an explicit approval.
