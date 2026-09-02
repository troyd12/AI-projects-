# Recruiting workspace — repeatable process

Troy is a corporate technical recruiter at Nike (Global Service & Places stretch
assignment: principal architects, event planning, inventory/supply chain). This
directory holds phone screen forms and supporting research.

## Directory convention

```
recruiting/
  templates/        blank reusable forms + the generator script + original source docs
  phone-screens/    completed screens, one folder per req (GITIGNORED — candidate PII)
  research/         market/comp research, one file per company or req
```

Completed screens **stay out of git**. They carry candidate location, family
situation and compensation. `phone-screens/` is in `.gitignore` — keep it that way.
Deliver finished screens to Troy as file attachments instead.

## Building a screen from a new template

1. **Extract the source form.** Legacy `.doc` files: LibreOffice is broken in this
   environment (it fails on every file, including plain text), so don't trust a
   conversion error as evidence the file is damaged. Parse the OLE piece table
   directly with `olefile` — see the approach in `templates/generate_phone_screen.js`
   history, or re-derive it: read the `WordDocument` and `1Table` streams, walk the
   FIB to `fcClx`, then the piece table.
2. **Rebuild as `.docx`** with the `docx` npm package rather than editing in place.
   Preserve every field and question in the original order. Fix obvious typos in
   boilerplate (the original footer read "Technoloy Ta Canidate screen").
3. **Fill from the transcript.** Troy usually pastes an Otter.ai transcript.
4. **Verify** with `scripts/office/validate.py` from the docx skill, then dump
   `word/document.xml` to confirm each question sits above its own answer.
5. **Deliver** with `SendUserFile`, and commit only the template + generator.

## How Troy wants screens written

- **Candidate answers only.** No assessment language mixed into the Q&A, and no
  Nike-side context (the range you quoted, relocation package, perks) — that is not
  what the candidate said.
- **Sparse and scannable.** Short lead sentence, then dashes. Not paragraphs.
- **Leave blanks rather than inventing.** If the candidate didn't state a title, or
  the recording didn't capture his name, leave the field empty and flag it.
- **Compensation and relocation: light touch.** A brief factual note; Troy fills in
  the rest himself.
- **Recruiter's feedback: one short paragraph**, in Troy's voice, from what he tells
  you about the candidate. Never write the assessment yourself.
- Ask before guessing when two readings would change the document.

## Generator

`templates/generate_phone_screen.js` — `node generate_phone_screen.js out.docx blank|filled`.
Content lives in the `BLANK` / `FILLED` objects at the bottom; `REQ` and `QUESTIONS`
hold the per-req header and screening questions. For a new req, copy those two and
swap the values. Questions 6–8 (availability, compensation, location) are generic and
carry over to any role; 1–5 are role-specific.

US Letter, 0.75" margins, Calibri, grey section headers, table-based layout at
10080 DXA content width.
