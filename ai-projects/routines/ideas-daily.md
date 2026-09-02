# Daily Business Ideas — 10 per day, Excel + Email

- **Trigger:** `trig_01JyVevfGXD26JVFEjF1YbpC`
- **Cron:** `0 14 * * *` (UTC) — 7:00am PT daily
- **Model:** claude-sonnet-5
- **Connectors:** Gmail, Google Drive
- **Tools:** Bash, Read, Write, Edit, Glob, Grep
- **Last run (2026-09-01):** succeeded, 54 min

## Prompt

You generate 10 unique near-autopilot business ideas for Troy daily, with zero duplicates.

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
3. Email the Excel file to troyd12@gmail.com via Gmail MCP with subject line: 'Daily Business Ideas - [today's date]' and body: 'Hi Troy, here are today's 10 near-autopilot business ideas. Pick your favorite and keep exploring!'
4. Append all 10 new idea names to the 'Business Ideas — Used List' Google Drive doc so they never repeat

Be creative, diverse, and ensure each idea is genuinely actionable for someone with limited time.
