# Recruiting – phone screen forms

See `CLAUDE.md` in this directory for the full repeatable process.

## Layout

- `research/` — market and compensation research, one file per company or req.
- `templates/Nike_Phone_Screen_TEMPLATE_R-90323.docx` — blank, reusable phone screen
  form. Req header (R-90323, Eric Dwyer, grade 45) and the eight screening questions
  are pre-filled; every candidate field is empty. Open in Word, fill in, save under
  `phone-screens/<req>/`.
- `templates/ORIGINAL_phone_screen_form.doc` — the original Word 97-2003 form this was
  rebuilt from, kept for reference.
- `templates/generate_phone_screen.js` — the generator that produces both files.
- `phone-screens/<req>/` — completed screens, one file per candidate.

## Regenerating

```
npm install docx
node templates/generate_phone_screen.js out.docx blank    # empty form
node templates/generate_phone_screen.js out.docx filled   # the worked example
```

Candidate content lives in the `BLANK` and `FILLED` objects at the bottom of the
script. To start a new req, copy `REQ` and `QUESTIONS` and change the values —
questions 1–5 are specific to the identity/authorization role, questions 6–8 are
generic and apply to any screen.

## Form sections

Candidate header · Why interest / motivation for change · Screening questions 1–8 ·
Current projects · Areas of expertise · Compensation & logistics · Recruiter's
feedback and recommendation.
