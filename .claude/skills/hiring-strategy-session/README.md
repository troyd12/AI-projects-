# hiring-strategy-session

A Claude skill for Nike Corporate TA recruiters and hiring managers running a Hiring
Strategy Session (intake / kickoff) under the Workday skills implementation.

**What it does**

- Recruiter mode: pre-meeting form, HM prep email, role-specific agenda, draft Skills for
  Success, session notes capture, Workday-ready skills block, recap email, action tracker.
- Hiring Manager mode: one-page prep guide, draft answers to prep questions, plain-language
  Connection to Sport explanation, first-cut skills list to cut / rank / add.

**Layout**

```
hiring-strategy-session/
├── SKILL.md                      # workflow, modes, quality bar
├── references/
│   ├── skills-on-reqs-program.md # Workday fields, grade workflows, phases, scripts, scenarios
│   ├── session-guide.md          # the full before / during / after guide, sections A to G
│   ├── skills-for-success.md     # writing, prioritizing, formatting skills for Workday
│   ├── connection-to-sport.md    # definition, HM talking point, HM and candidate questions
│   └── roles/
│       ├── principal-architect.md
│       ├── event-planner.md
│       └── inventory-supply-chain.md
├── assets/                       # fill-in templates
│   ├── pre-meeting-form.md
│   ├── hm-prep-package.md
│   ├── hm-prep-email.md
│   ├── hm-prep-guide.md
│   ├── session-notes.md
│   ├── recap-email.md
│   └── action-tracker.md
└── evals/                        # three test prompts (claude plugin eval layout)
```

**Adding a role family**

Copy one of the files in `references/roles/`, keep the same headings (what makes the search
hard, starter skills with evidence lines, sharpest section A questions, Connection to Sport
angle, sourcing targets), and add a bullet for it under "Load the role family" in SKILL.md.

**Try it**

Ask Claude something like: "I have an intake with my HM Thursday for a Principal Architect
in Global Service and Places, get me ready" or "I'm the hiring manager, what do I bring to
the strategy session for my event planner role?"
