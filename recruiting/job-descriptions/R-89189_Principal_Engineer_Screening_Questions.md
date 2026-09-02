# R-89189 — Principal Software Engineer, Identity & Authorization
## Screening Questions

**Req:** R-89189
**Hiring Manager:** Eric Dwyer
**Recruiter:** Troy Dixon — Lead Technical Recruiter, Nike Global Technology
**Status:** Active — use these for all initial candidate screens

---

## Candidate-facing text

Send as-is. Candidates may answer live or in advance.

> We'd also like to ask you a few questions during our conversation. If you'd prefer, please feel free to address them in advance:
>
> 1. What's the last thing you personally coded that shipped to production? Tell me what it was and what you wrote.
>
> 2. Walk me through an authorization system you've built at scale. What did you have to give up to make it work?
>
> 3. Tell me about a system you ran across multiple regions. What broke, and how did you handle it?
>
> 4. When did you get another team to adopt something you built? What pushback did you hit?
>
> 5. We're replacing a company-wide access system with policy-based authorization. Nothing's built yet. What goes wrong?
>
> 6. Please provide two dates and times that you are available for a 30-minute conversation.
>
> 7. So we can align early and avoid surprises later, please share your compensation expectations.
>
> 8. This role is in-office preferred. Please let us know your current location and whether relocation is something you'd consider.

---

## What each question screens for

Mapped to the must-haves from the Aug 5, 2026 intake call with Eric Dwyer.

| # | Screens for | Listen for | Concern signal |
|---|---|---|---|
| 1 | **Hands-on coding.** Eric was explicit: hands-on, not architecture-only. | A specific artifact — a service, a module, a migration — and what they personally wrote. Recent. | Vague "I led the team that…" with no personal code. Nothing shipped in 2+ years. |
| 2 | **Authorization at scale + engineering judgment.** The "what did you give up" is the real question. | A named tradeoff: latency vs. flexibility, consistency vs. availability, expressiveness vs. evaluability. | No tradeoff named. Describes an off-the-shelf tool they configured rather than a system they built. |
| 3 | **Multi-region deployment, operated for real.** | An actual failure — replication lag, region failover, a partition — and what they did during it. | Theoretical answer. "It worked fine." Never been on call for it. |
| 4 | **Evangelism and adoption.** Named by Eric as a big part of the role, not an afterthought. | Real resistance, and a strategy for it. Willingness to sell internally. | No pushback recalled, or contempt for the teams that resisted. |
| 5 | **Judgment on a greenfield problem.** Unscripted — there's no right answer. | Migration risk, adoption inertia, policy sprawl, the cutover, break-glass access, performance under evaluation load. | Only technical answers with no organizational risk. Or no substantive answer at all. |
| 6 | Scheduling. | — | — |
| 7 | **Comp alignment.** Range is $200K–$260K. | Expectation inside or near range. | Materially above $260K — surface early rather than late. |
| 8 | **Location.** Texas, in-office preferred. | Already in Texas, or genuinely open to relocating. | Remote-only requirement. This is the most common disqualifier for this req — ask early. |

---

## Notes

- **Q1–Q5 are the substance.** Q6–Q8 are logistics and should never be the reason a strong technical answer gets deprioritized — but Q8 in particular is worth confirming before investing screen time, since the posting may still read "remote" (Eric flagged a correction was needed).
- **Knockout questions from the hiring manager are still outstanding.** The intake note lists "Eric: Provide 1–2 knockout questions for initial candidate screening" as *Pending*. Nudge via Slack; his knockouts may change advancement criteria.
- **Not a fit:** primarily mobile background (this is backend), architecture-only with no deployment track record, or seeking a people-management role (this is a principal IC seat).

---

*Source: R-89189 intake call, August 5, 2026 · Handoff packet for backup recruiter coverage*
