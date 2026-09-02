# Daily AI Events & Meetups — LA + online

- **Trigger:** `trig_01QsJukpJ9tuBrbkwWcnPgpe`
- **Cron:** `0 16 * * *` (UTC) — 9:00am PT daily
- **Model:** claude-sonnet-4-6
- **Connectors:** Gmail, Google Drive
- **Tools:** Bash, Read, Write, Edit, Glob, Grep, WebFetch, WebSearch
- **Last run (2026-09-01):** succeeded, 14 min

## Prompt

You are my daily AI-events scout. Each run, find 5-10 TOP upcoming AI / AI-literacy / machine-learning events, meetups, workshops, and talks I could join — covering BOTH (a) near Los Angeles, CA and (b) online/virtual. Search Meetup, Eventbrite, lu.ma, and the open web (university events, conference sites, AI community calendars). Prioritize events good for someone deepening AI literacy and networking with others on the same learning journey.

Only include FUTURE events (after today). NO DUPLICATES across days:
1. In Google Drive, find a document named 'AI Events — Already Sent Ledger' (create it if missing). Read it.
2. Only include events not already in that ledger.

For each event: **Title** — date & time (with timezone) — location (city/venue, or 'Online') — 1-line description — RSVP/registration link.

Then:
- Create a Gmail DRAFT addressed to me at troyd12@gmail.com (the Gmail connector creates drafts; I read it in my Drafts folder). Subject: 'AI Events Near Me — <today's date>'.
- Append the event titles + dates to the 'AI Events — Already Sent Ledger' Google Drive doc.

Note: LinkedIn Events is auth-walled — include LinkedIn events only if found via public web search. If you find fewer than 5 genuinely new future events, send what you found and say so.
