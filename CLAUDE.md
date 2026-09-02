# AI-projects- — Claude harness guide

Personal workspace for Troy Dixon (Lead Technical Recruiter, Nike Global Technology / GPS stretch assignment).
Two things live here: the **TD Movement** portfolio site and recruiting/AI working files.

## Repo map (by domain)

| Path | Domain | What goes here |
|------|--------|----------------|
| `index.html` | Site | Single-page portfolio. **Stays at repo root** — GitHub Pages serves it from here. |
| `assets/images/` | Site | Images referenced by `index.html` (hero: `puzzle_head.png`). |
| `assets/documents/` | Site | Public downloads linked from the site (resume PDF). |
| `recruiting/job-descriptions/` | Recruiting | Nike GPS JDs and decoded intake summaries (Principal Architect, Event Planning, Inventory/Supply Chain). |
| `recruiting/trackers/` | Recruiting | Master Tracker exports and candidate tracker PDFs. |
| `recruiting/candidate-packets/` | Recruiting | ATS packets. **Git-ignored** — contains PII; never commit. |
| `ai-projects/` | AI | Agents, workflows, prompts, experiments. One subfolder per project. |
| `ai-projects/routines/` | AI | Source of truth for scheduled Routine prompts. Edit here → PR → apply with `update_trigger`. |
| `ai-projects/video-pipeline/` | AI | Audit, QC gate (`qc_video.py`), EXIF fixer and nightly runner for the TheScamFile avatar-video jobs on the PC. |
| `docs/` | Docs | Notes, screenshots, decision records. |
| `.claude/` | Harness | `settings.json` permissions for Claude Code. |

## Conventions

- **Site is a single static file.** No build step, no framework. Edit `index.html` directly; keep CSS/JS inline as they are.
- **Relative asset paths only** (`assets/images/...`), never absolute or `file:///` paths — the page must work on GitHub Pages and when opened locally.
- **New files go in their domain folder**, not the root. Root holds only `index.html`, `README.md`, `CLAUDE.md`, dotfiles.
- **Never commit candidate data** (resumes, ATS exports, phone screens). Keep them under `recruiting/candidate-packets/` (ignored) or outside the repo.
- Filenames: `kebab-case` for folders, `snake_case` or `Title_Case` for documents that are shared externally (e.g. `Troy_Dixon_Resume.pdf`).

## Working on the site

- Verify a change by opening `index.html` in a browser; there are no tests.
- Hero image: `assets/images/puzzle_head.png` (currently **missing** from the repo — the `<img onerror>` hides it silently). Add the file to restore the hero.
- Theme is dark-first with a `[data-theme="light"]` override; keep new colors as CSS variables in `:root`.

## Skills that map to this repo

- `job-decoder` → output to `recruiting/job-descriptions/`
- `recruiter-embedded-tracker` → output to `recruiting/trackers/`
- `pdf`, `docx`, `xlsx` → recruiting deliverables
