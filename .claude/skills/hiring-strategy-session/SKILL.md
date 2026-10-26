---
name: hiring-strategy-session
description: >
  Facilitate, prepare for, and follow up on a Nike Hiring Strategy Session (intake / kickoff
  meeting) for the Workday skills implementation. Produces the recruiter pre-meeting form,
  Hiring Manager prep email and prep answers, a role-specific session agenda, the agreed
  Skills for Success block (3-10 optional skills, critical skills first) ready to paste into
  the Workday job requisition, the recap email, and the post-session action tracker.
  Use this whenever a recruiter or hiring manager mentions an intake, kickoff, strategy
  session, hiring manager meeting, new req, opening a role, Skills for Success, optional
  skills on a req, Connection to Sport, MYNEXT, or asks "what should I bring to the meeting
  with my recruiter / hiring manager", even if they do not say "strategy session". Also use
  it when someone pastes a job description or Workday req details and wants to get ready to
  launch the search.
---

# Hiring Strategy Session

The Hiring Strategy Session is the recruiter-led meeting that turns a business need into a
search plan before anything is posted. Nike's Workday skills implementation changed what
"done" looks like for this meeting: it now has to end with an agreed, prioritized set of
Skills for Success that goes onto the Workday requisition, because those skills drive the
posting, the screen, and the interview scorecard. Everything this skill produces exists to
get the recruiter and the Hiring Manager (HM) to that agreement quickly and with the same
quality every time.

Two people use this skill. Work out which one you are helping before doing anything else.

| Mode | Who | What they need |
|---|---|---|
| **Recruiter** | Corporate TA recruiter running the session | Prep checklist, pre-meeting form, HM prep email, facilitation agenda, live note capture, Skills for Success block for Workday, recap email, action tracker |
| **Hiring Manager** | Leader opening the role | A short prep guide, draft answers to the prep questions, a first cut at Skills for Success to react to, plain-language explanation of Connection to Sport and the internal-candidate feedback obligation |

If the person does not say which they are, infer it from context (a recruiter talks about
reqs, Workday, posting strategy, and "my HM"; a hiring manager talks about "my recruiter",
"my team", and the work the role will do). When it is still unclear, ask one short question.

## Workflow

### 1. Establish the stage and the role

Ask for, or pull from pasted material, the basics: job title, req number if it exists, HM
name, global grade, location, whether the role is new or a backfill, and the business group.
Then establish which stage the person is at:

- **Before the session** (most common): the user wants to prepare.
- **During the session**: the user wants live prompts and a place to capture decisions.
- **After the session**: the user wants the recap, the Workday skills block, and actions.

Read `references/session-guide.md` for the full three-stage checklist and the question bank.
It is the source of truth for what the session has to cover, so do not improvise core
sections; customize depth and emphasis instead.

### 2. Load the role family

Skills for Success are only useful if they are specific to the work, so pull the matching
role library before drafting anything:

- `references/roles/principal-architect.md` for principal / enterprise / solution / technology
  architects and senior engineering leadership roles.
- `references/roles/event-planner.md` for event planning, event production, experiential,
  and workplace experience roles.
- `references/roles/inventory-supply-chain.md` for inventory, planning, demand/supply
  planning, logistics, and supply chain operations roles.
- For any other role, read `references/skills-for-success.md` and build the library from the
  job description using the same structure (critical skills, supporting skills, evidence).

Each role file gives a starter Skills for Success list, the sharpest Team and Role Insight
questions for that family, sourcing targets, and the Connection to Sport angle. They are
starting points, not answers; the HM's input always wins.

### 3. Produce the stage-appropriate deliverables

**Before the session (recruiter mode)**

1. Fill the Strategy Pre-Meeting Form from `assets/pre-meeting-form.md`. Mark every field you
   could not fill as `[CONFIRM IN WORKDAY]` rather than guessing a grade, salary, or req number.
   Wrong numbers in this form end up in offers.
2. Draft the HM prep email from `assets/hm-prep-email.md`, sent 24 to 48 hours ahead so the HM
   has time to think about skills before the meeting.
3. Build the session agenda using the A to G structure in `references/session-guide.md`,
   trimmed to the role's complexity. A backfill of a well-understood role needs a 30-minute
   agenda; a new principal architect role needs the full hour.
4. Draft a **proposed** Skills for Success list from the role library and the JD, labeled as a
   draft for the HM to react to. Reacting to a draft is far faster for an HM than inventing a
   list from scratch, and it keeps the list within the 3 to 10 range.

**Before the session (hiring manager mode)**

1. Give the HM the one-page prep guide from `assets/hm-prep-guide.md`, personalized to the role.
2. Draft answers to the prep questions from whatever they have told you, with gaps marked for
   them to fill. Keep the HM's own words when they gave them.
3. Explain Connection to Sport in two or three sentences using `references/connection-to-sport.md`.
   HMs often assume it means "played sports"; it does not, and getting this wrong skews the
   panel's assessment.
4. Offer a first-cut Skills for Success list and ask them to rank, cut, and add.

**During the session (either mode)**

Use `assets/session-notes.md` as the capture template. Keep the seven lettered sections in
order, and for each decision write who owns it and by when. The only sections that can be
skipped are those already resolved in prep, and say so in the notes.

**After the session (recruiter mode)**

1. Produce the Workday-ready Skills for Success block using the format in
   `references/skills-for-success.md`. Critical skills first, then supporting skills, each
   with the one-line evidence statement the panel will use.
2. Draft the recap email from `assets/recap-email.md`: decisions, the skills list, interview
   panel and timing, open items with owners and due dates, and the check-in cadence agreed.
3. Produce the action tracker (the five post-session items plus anything role-specific).

### 4. Quality bar before handing anything back

- Skills for Success: 3 to 10 skills, critical ones first, each phrased as an observable
  capability ("Designs multi-region integration architectures" not "Architecture"). A list
  of 15 is a wish list, and the guide is explicit that wish lists get cut.
- Skills are one input alongside experience, Leadership Defined, Connection to Sport, and
  demonstrated performance. Do not let the skills block imply it is the whole scorecard.
- Internal candidate feedback: for Global Corporate Grade 20+ and Americas Supply Chain 20+,
  remind the HM they must deliver verbal feedback to internal candidates who complete the
  Business Interview, preferably within 3 to 5 business days, and that a Workday task will
  prompt them. Put this in the recap every time it applies.
- Posting: confirm internal-only vs internal/external, duration (minimum one calendar week),
  MYNEXT promotion to retail teammates where the skills translate, and compliance items
  (drug screen, non-compete).
- Never invent compensation, grade, approval, or Workday configuration details. Mark them
  for confirmation. The guide points to the Offer Modeling Tool, Proactive Teaming guidance,
  and TRC; name those sources rather than numbers.

## Output conventions

Return documents in Markdown unless the user asks for a file. When they do, a Word document
or a shared doc is the right fit for anything the HM will read; a Markdown file in the repo is
right for anything the recruiter will keep editing. Keep HM-facing documents short and free
of TA jargon; keep recruiter-facing documents complete.

Use the exact section letters and names from the guide (A Team and Role Insight through G
Interview Reminders) so that notes from different recruiters line up.

## Reference index

- `references/session-guide.md`: the full before / during / after guide, question bank, checklists.
- `references/skills-for-success.md`: how to write, prioritize, and format Skills for Success for Workday.
- `references/connection-to-sport.md`: what it is, HM talking point, HM and candidate questions.
- `references/roles/*.md`: role-family libraries (principal architect, event planner, inventory and supply chain).
- `assets/`: fill-in templates (pre-meeting form, HM prep email, HM prep guide, session notes, recap email, action tracker).
