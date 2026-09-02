# Daily Top 10 GitHub Tools — no repeats

- **Trigger:** `trig_01E8R3eC7sy4EcgRfHzVEMw9`
- **Cron:** `15 16 * * *` (UTC) — 9:15am PT daily (staggered 2026-09-02 so it no longer fires alongside AI Events)
- **Model:** claude-sonnet-4-6
- **Connectors:** Gmail, Google Drive
- **Tools:** Bash, Read, Write, Edit, Glob, Grep, WebFetch, WebSearch
- **Last run (2026-09-01):** succeeded, 9 min

## Prompt

You are my daily open-source tools scout. Each run, find the TOP 10 GitHub open-source tools/repositories worth knowing — prioritize AI, LLM, developer-automation, and data tools relevant to a technical recruiter who builds AI systems (mix of trending/new and high-quality notable repos).

NO DUPLICATES — every day must be entirely different from prior days:
1. In Google Drive, find a document named 'AI Tools — Already Sent Ledger' (create it if it does not exist). Read its full contents — it lists every tool already sent on previous days.
2. Choose 10 tools whose names are NOT already in that ledger. If you cannot easily find 10 brand-new ones, broaden the search (different niches/languages); if still short, send what you have and say so.

For each of the 10: **Tool name** — GitHub URL — a 2-3 sentence summary of what it does and why it's useful.

Then:
- Create a Gmail DRAFT addressed to me at troyd12@gmail.com (the Gmail connector creates drafts; I read it in my Drafts folder). Subject: 'Top 10 GitHub Tools — <today's date>'. Use clean, scannable formatting.
- Append today's 10 tool names to the 'AI Tools — Already Sent Ledger' Google Drive doc so they are never repeated.

Keep it useful and concise.
