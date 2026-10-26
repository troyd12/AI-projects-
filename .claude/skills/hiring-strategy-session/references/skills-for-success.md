# Skills for Success: narrowing the requisition's skills

"Skills for Success" is what the strategy session guide calls the agreed skills list. In
Workday it lives in the requisition's Optional Skills field. For Grade 20+ roles the field
arrives pre-filled with the Job Profile's validated skills (around 19), and the session's
job is to narrow it to the 3 to 10 most critical to success and add anything missing from
the Skills Cloud library. For Grade 10 and 15 roles the list stays as populated.

Read `skills-on-reqs-program.md` for the fields, grade workflows, phases, and scripts. This
file is about making the list good.

## What a Workday skill looks like

Skills are short library labels, technical or interpersonal: "Enterprise Architecture",
"Vendor Negotiation", "Data Analysis", "Communication". They are not sentences and they do
not carry evidence. That is why the recruiter keeps a note beside each one: what the HM
meant by it for this role, and what it looks like when someone has it. The note goes in
the recruiting plan and the recap email, never into Workday.

| Label on the req | Recruiter note (recap and recruiting plan) |
|---|---|
| Enterprise Architecture | Designs end-to-end architectures across platforms and regions; look for artifacts they authored that shipped at scale |
| Stakeholder Management | Gets standards adopted by teams they do not manage; ask for an example of a decision they influenced without authority |
| Vendor Negotiation | Runs build / buy / partner evaluations and negotiates the resulting contracts |

## Choosing between labels

- Prefer the specific label over the broad one when both exist ("Cloud Architecture" over
  "Information Technology"; "Demand Forecasting" over "Supply Chain").
- Drop duplicates: if "Communication" and "Presentation Skills" both sit on the list and
  the HM means one thing, keep the one closer to the work.
- Tools and products: the library has many. Prefer the capability unless the tool is the
  job (a Workday integration developer needs "Workday Integration"; an architect who happens
  to use Jira does not need "Jira").
- Interpersonal skills count. Senior and principal roles fail on influence more often than
  on depth; keep one or two that name how the person works with others.

## Working the list with the HM

Share the req on screen. The three moves from the enablement deck:

1. **Frame the purpose.** "We'll review the skills associated with this role and align on
   those most critical to success, so the requisition reflects the capabilities needed."
2. **Evaluate the defaulted skills.** Which connect most directly to the outcomes we
   discussed? Which are too broad, duplicative, or less relevant? Are any critical ones
   missing?
3. **Prioritize and confirm.** Land on 3 to 10. "I'll update the requisition to reflect our
   discussion, and you'll be able to review those skills in Workday once it is posted."

In practice this is three passes over the defaulted list: cut what the HM would not reject
a strong candidate for lacking, keep what they would refuse to hire without, add what the
best performer does that is missing (search it in the Optional Skills field). If the HM
pushes past ten, ask which could be learned in the first 90 days; those go to the
onboarding plan.

## Recording the agreed list

Use this block in the recap email and the recruiting plan. Workday gets only the labels.

```
AGREED SKILLS: [Job Title] (Req [number], Grade [grade])

Optional Skills on the requisition (final, N of 10)
1. [Label]  : [recruiter note]
2. [Label]  : [recruiter note]
...

Removed from the defaulted list: [labels]
Added from the Skills Cloud: [labels]
Learnable in first 90 days (onboarding plan, not the req): [items]
Required Skills field: empty (confirmed)
Finalized before posting on [date]; no changes after posting.

Other assessment inputs: experience, Leadership Defined, Connection to Sport
([named behaviors]), demonstrated performance. Skills are not assessment criteria in
the current phase.
```

## Common mistakes

- Editing a Grade 10 or 15 req. Leave it.
- Entering anything in Required Skills. Workday blocks the req.
- Keeping all 19 because removing feels rude. A long list hides what matters; the deck's
  own line is "prioritize relevance over volume".
- Telling the HM interviewers will score against the list. Not in Crawl.
- Changing the list after posting because a late stakeholder weighed in. Raise it with your
  Leader or Peer Coach instead.
- Not flagging a Job Profile whose defaults do not fit. The next recruiter inherits the
  same list.
