# Routines (scheduled Claude jobs)

Source of truth for the prompts and schedules of Troy's Claude Routines. The live scheduler holds a copy; **edit here first, open a PR, then apply with `update_trigger`** so every prompt change has history and a review gate.

| File | Trigger ID | Schedule (UTC / PT) | Model |
|------|-----------|---------------------|-------|
| `ideas-daily.md` | `trig_01JyVevfGXD26JVFEjF1YbpC` | `0 14 * * *` — 7:00am PT (Friday = review edition) | claude-sonnet-5 |
| `ai-events-daily.md` | `trig_01QsJukpJ9tuBrbkwWcnPgpe` | `0 16 * * *` — 9:00am PT | claude-sonnet-4-6 |
| `github-tools-daily.md` | `trig_01E8R3eC7sy4EcgRfHzVEMw9` | `15 16 * * *` — 9:15am PT | claude-sonnet-4-6 |

Cron expressions are UTC; PT shown for PDT (UTC-7).

## Pending — apply in claude.ai → Routines (agents cannot edit UI-created Routines)
Decided 2026-09-02; the table above is the **target** state, not yet live:
1. **Delete** `Muse Glimmer NVIDIA Support Check` (`trig_011xYXLP72TG4hknf5GWkYqi`) — empty prompt, abandoned every run since Aug 11.
2. **Delete** `Friday Business Ideas — Collaboration Review` (`trig_01WJH7EvQ61ezHC97zsPFf8u`) — merged into the daily job.
3. **Edit** `Daily Business Ideas` (`trig_01JyVevfGXD26JVFEjF1YbpC`) — replace the prompt with the one in `ideas-daily.md`.
4. **Edit** `Daily Top 10 GitHub Tools` (`trig_01E8R3eC7sy4EcgRfHzVEMw9`) — schedule from 9:00am to 9:15am PT (`15 16 * * *`).
Once applied, move this block into a dated change-log entry.

## Conventions
- One file per routine. Header block = schedule/model/connectors; body = the exact prompt text.
- Every prompt must say what to do when its Drive ledger is missing (create it) and when results fall short (send what you have and say so).
- One outbound email or draft per run.
- Drive ledgers used for de-duplication: `Business Ideas — Used List`, `AI Events — Already Sent Ledger`, `AI Tools — Already Sent Ledger`.
