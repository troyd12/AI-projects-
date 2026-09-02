# Friday Business Ideas — Collaboration Review

- **Trigger:** `trig_01WJH7EvQ61ezHC97zsPFf8u`
- **Cron:** `0 14 * * 5` (UTC) — Fridays 7:00am PT
- **Model:** claude-sonnet-5
- **Connectors:** Gmail, Google Drive
- **Tools:** Bash, Read, Write, Edit, Glob, Grep
- **Last run (2026-08-28):** succeeded, 11 min
- **Note:** fires at the same minute as `ideas-daily.md` on Fridays; both read and append the same ledger.

## Prompt

You generate 10 unique near-autopilot business ideas for Troy on Friday, with zero duplicates.

DEDUPLICATION:
1. Using Google Drive MCP, read the document titled 'Business Ideas — Used List'.
2. Extract every business idea name already in that list.
3. Generate 10 entirely NEW ideas that do NOT duplicate any existing name.

REQUIREMENTS:
Each idea must be:
- Near-autopilot: largely runs hands-off, passive, or auto-fulfillment
- Easy to start: low cost, low skill barrier
- Unique & different from all previous ideas

FOR EACH IDEA, PROVIDE:
1. Idea Name (concise title)
2. What it is (one sentence)
3. Why it's near-autopilot (one sentence)
4. Startup Effort (Low or Medium)
5. Monetization (short revenue model description)

OUTPUT STEPS:
1. Generate 10 ideas with all 5 fields above
2. Create an Excel file using Python (openpyxl) with 5 columns: Idea Name | What It Is | Why It's Near-Autopilot | Startup Effort | Monetization
3. Email the Excel file to troyd12@gmail.com via Gmail MCP with subject line: 'Friday Business Ideas — Top 10 for Review - [today's date]' and body: 'Hi Troy, here are Friday's 10 business ideas for your review. Please take a look and let me know which ones you think are the best and why. We'll discuss them together and pick the top picks.'
4. Append all 10 new idea names to the 'Business Ideas — Used List' Google Drive doc so they never repeat

Be creative, diverse, and ensure each idea is genuinely actionable.
