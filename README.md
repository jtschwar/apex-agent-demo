# Propose, check, approve: AI agents in scientific workflows

A hands-on, 15-minute lesson from **AI Quick Builds** (CZI peer learning series,
November 16, 2026). You use a Claude Skill to review real cryo-EM processing results:
Claude proposes which data to keep, shows its evidence, and waits for you to approve,
edit, or reject.

The Skill is a deliberately small, distilled slice of
[ApexAgent](https://github.com/czimaginginstitute/ApexAgent). ApexAgent is the full agent:
it runs whole cryo-EM pipelines on a computing cluster, reads every result, and holds key
decisions for a scientist in a dashboard. Here you get only its review rules, so that you
can try the pattern in a browser in a few minutes.

## Open the deck

**Online, nothing to install:** <https://jtschwar.github.io/apex-agent-demo/>

Use ← and → (or a presentation clicker) to move between slides. Press `F` for full
screen. Every slide has its own link, for example `#/3` for set-up.

**Offline:** download this repository (green **Code** button → **Download ZIP**), unzip
it, and double-click `index.html`. It opens in your browser with no server needed.

## Do the exercise

You need a claude.ai account. Everything else is on the deck's set-up slide.

1. Download the Skill, [`materials/cryoem-review.zip`](materials/cryoem-review.zip), and
   the data files in [`materials/`](materials/).
2. In claude.ai, go to **Settings → Customize → Skills** and upload the zip. If
   **Settings → Capabilities** has a **Code execution** setting, turn it on. Without it,
   Claude writes out its arithmetic instead.
3. Start a new chat and follow Steps 1–3 in the deck.

If your account can't upload Skills, use the deck's **Copy the Skill text** button and
paste the text as the first message of a new chat.

### Using Claude Code instead

The same zip installs as a Claude Code Skill:

```bash
mkdir -p ~/.claude/skills && unzip ~/Downloads/cryoem-review.zip -d ~/.claude/skills
```

Then run `claude` in the folder that holds the data files and use the same prompts.

## What's in the repository

```
index.html                  the deck (one file, no build step)
skill/cryoem-review/        the Skill (SKILL.md is the source of truth)
materials/                  what attendees download: the Skill zip and the data
assets/                     generated data and class images used by the deck
scripts/                    generators (Python standard library, numpy, Pillow)
```

To change the Skill or the data, edit the source and regenerate. The deck embeds the
Skill text, so always rebuild `assets/data.js`:

```bash
python3 scripts/build_skill_zip.py && python3 scripts/build_data.py   # after editing SKILL.md
python3 scripts/make_ctf_data.py && python3 scripts/build_data.py     # after changing the CTF data
python3 -m http.server 8765                                           # preview at http://localhost:8765
```

## Data

- **CTF results** (`ctf_results.csv`): synthetic. There are 40 micrographs, shaped so that
  each rule in the Skill has something to catch.
- **2D classes** (`class2d_gallery.png`, `class2d_classes.csv`): real. They come from
  a fully automatic ApexAgent run on the RELION 3.0 tutorial dataset (β-galactosidase):
  Class2D, 16 classes, 7,433 particles.
- **The run timeline** (`apex_run.json`): the same run's jobs and decision log, exported
  from ApexAgent's project database with file paths removed.

## Credits

Jonathan Schwartz, CZ Imaging Institute. The Skill's rules are condensed from
ApexAgent's job knowledge for micrograph selection, CTF estimation, and class selection.
