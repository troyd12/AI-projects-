const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  WidthType, ShadingType, AlignmentType, BorderStyle, HeadingLevel,
  Footer, Header, PageNumber, VerticalAlign,
} = require('docx');

const CONTENT = 10080;           // usable width in DXA (Letter, 0.75" margins)
const GREY = "D9D9D9";
const LIGHT = "F2F2F2";
const HAIR = { style: BorderStyle.SINGLE, size: 4, color: "9E9E9E" };
const BORDERS = { top: HAIR, bottom: HAIR, left: HAIR, right: HAIR,
                  insideHorizontal: HAIR, insideVertical: HAIR };

const t = (text, o = {}) => new TextRun({ text, font: "Calibri", size: o.size || 20,
  bold: !!o.bold, italics: !!o.italics, color: o.color || "000000" });

// A block of text where blank-line-separated chunks become paragraphs and
// lines beginning with "- " become simple indented dashes.
function body(value, o = {}) {
  const txt = (value === undefined || value === null || value === "") ? " " : String(value);
  return txt.split("\n").map((line) => {
    const dash = line.startsWith("- ");
    return new Paragraph({
      spacing: { before: 20, after: 60, line: 264 },
      indent: dash ? { left: 220, hanging: 160 } : undefined,
      children: [t(dash ? "– " + line.slice(2) : line, o)],
    });
  });
}

const cell = (children, o = {}) => new TableCell({
  width: { size: o.w, type: WidthType.DXA },
  columnSpan: o.span,
  shading: o.fill ? { type: ShadingType.CLEAR, fill: o.fill, color: "auto" } : undefined,
  margins: { top: 60, bottom: 60, left: 110, right: 110 },
  verticalAlign: VerticalAlign.CENTER,
  children,
});

const labelCell = (text, w, fill) =>
  cell([new Paragraph({ children: [t(text.toUpperCase(), { bold: true, size: 17 })] })],
       { w, fill: fill || GREY });

const valueCell = (text, w) => cell(body(text), { w });

// ---------- document sections ----------------------------------------------

function headerTable(d) {
  const W = [2160, 2880, 2160, 2880];
  const row = (l1, v1, l2, v2) => new TableRow({ children: [
    labelCell(l1, W[0]), valueCell(v1, W[1]), labelCell(l2, W[2]), valueCell(v2, W[3]),
  ]});
  return new Table({
    width: { size: CONTENT, type: WidthType.DXA },
    columnWidths: W, borders: BORDERS,
    rows: [
      row("Candidate name", d.name,     "Req #",          d.req),
      row("Title",          d.title,    "Hiring mgr",     d.hiringMgr),
      row("Company",        d.company,  "Position title", d.positionTitle),
      row("Date",           d.date,     "Grade level",    d.grade),
      row("Source/channel", d.source,   "Active/passive", d.activePassive),
    ],
  });
}

// Full-width section: shaded caption row + one content row.
function section(caption, sub, content) {
  const capKids = [new Paragraph({ children: [t(caption.toUpperCase(), { bold: true, size: 18 })] })];
  if (sub) capKids.push(new Paragraph({ children: [t(sub, { italics: true, size: 16, color: "595959" })] }));
  return new Table({
    width: { size: CONTENT, type: WidthType.DXA },
    columnWidths: [CONTENT], borders: BORDERS,
    rows: [
      new TableRow({ children: [cell(capKids, { w: CONTENT, fill: GREY })] }),
      new TableRow({ children: [cell(content, { w: CONTENT })] }),
    ],
  });
}

// Screening questions: shaded caption, then Q (bold) / A rows.
function questionTable(caption, items) {
  const rows = [new TableRow({ children: [
    cell([new Paragraph({ children: [t(caption.toUpperCase(), { bold: true, size: 18 })] })],
         { w: CONTENT, fill: GREY }),
  ]})];
  items.forEach((it, i) => {
    rows.push(new TableRow({ children: [cell(
      [new Paragraph({ spacing: { after: 40 }, children: [t(`${i + 1}. ${it.q}`, { bold: true })] })],
      { w: CONTENT, fill: LIGHT })] }));
    rows.push(new TableRow({ children: [cell(body(it.a), { w: CONTENT })] }));
  });
  return new Table({ width: { size: CONTENT, type: WidthType.DXA },
    columnWidths: [CONTENT], borders: BORDERS, rows });
}

// Two-column label / value block.
function detailTable(caption, pairs) {
  const W = [3240, 6840];
  const rows = [new TableRow({ children: [
    cell([new Paragraph({ children: [t(caption.toUpperCase(), { bold: true, size: 18 })] })],
         { w: CONTENT, span: 2, fill: GREY }),
  ]})];
  pairs.forEach(([label, sub, value]) => {
    const kids = [new Paragraph({ children: [t(label.toUpperCase(), { bold: true, size: 17 })] })];
    if (sub) kids.push(new Paragraph({ children: [t(sub, { italics: true, size: 15, color: "595959" })] }));
    rows.push(new TableRow({ children: [
      cell(kids, { w: W[0], fill: LIGHT }), valueCell(value, W[1]),
    ]}));
  });
  return new Table({ width: { size: CONTENT, type: WidthType.DXA },
    columnWidths: W, borders: BORDERS, rows });
}

const gap = (n) => new Paragraph({ spacing: { after: n || 160 }, children: [t("")] });

// ---------- assemble --------------------------------------------------------

function build(d) {
  const children = [
    new Paragraph({
      spacing: { after: 40 },
      children: [t("NIKE  |  GLOBAL TECHNOLOGY  –  TALENT ACQUISITION", { bold: true, size: 16, color: "595959" })],
    }),
    new Paragraph({
      spacing: { after: 180 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 10, color: "000000", space: 6 } },
      children: [t("Candidate Phone Screen", { bold: true, size: 32 })],
    }),
    headerTable(d), gap(),
    section("Why interest in this role / motivation for change", null, body(d.motivation)), gap(),
    questionTable("Screening questions", d.questions), gap(),
    section("Current projects", null, body(d.currentProjects)), gap(),
    section("Areas of expertise", "Fits job requirements?", body(d.expertise)), gap(),
    detailTable("Compensation & logistics", [
      ["Compensation expectations", "Base, bonus, equity – what are they walking away from", d.comp.expectations],
      ["Base salary", null, d.comp.base],
      ["Bonus %", null, d.comp.bonus],
      ["Unvested stock", null, d.comp.stock],
      ["Competing interviews", "If so, what stage", d.comp.competingInterviews],
      ["Competing offers", "If so, timing", d.comp.competingOffers],
      ["Timeline", "To interview / start if offer accepted", d.comp.timeline],
      ["Non-compete", "If from a competitor", d.comp.nonCompete],
      ["Location / relocation", "Role is in-office preferred", d.comp.location],
    ]), gap(),
    section("Recruiter's feedback & recommendation on next step", null, body(d.recommendation)),
  ];

  return new Document({
    creator: "Nike Global Technology – Talent Acquisition",
    title: d.docTitle,
    description: "Candidate phone screen form",
    styles: { default: { document: { run: { font: "Calibri", size: 20 } } } },
    sections: [{
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1080, bottom: 1080, left: 1080, right: 1080, footer: 540 },
        },
      },
      footers: {
        default: new Footer({ children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          border: { top: { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF", space: 6 } },
          children: [
            t("Nike Global Technology – Talent Acquisition – Candidate Screen        ", { size: 15, color: "808080" }),
            new TextRun({ children: ["Page ", PageNumber.CURRENT, " of ", PageNumber.TOTAL_PAGES],
                          font: "Calibri", size: 15, color: "808080" }),
          ],
        })]}),
      },
      children,
    }],
  });
}

// ---------- data ------------------------------------------------------------

const QUESTIONS = [
  "What's the last thing you personally coded that shipped to production? Tell me what it was and what you wrote.",
  "Walk me through an authorization system you've built at scale. What did you have to give up to make it work?",
  "Tell me about a system you ran across multiple regions. What broke, and how did you handle it?",
  "When did you get another team to adopt something you built? What pushback did you hit?",
  "We're replacing a company-wide access system with policy-based authorization. Nothing's built yet. What goes wrong?",
  "Please provide two dates and times that you are available for a 30-minute conversation.",
  "So we can align early and avoid surprises later, please share your compensation expectations.",
  "This role is in-office preferred. Please let us know your current location and whether relocation is something you'd consider.",
];

const REQ = {
  req: "R-90323",
  positionTitle: "Principal Engineer, Identity & Authorization",
  hiringMgr: "Eric Dwyer – Director, CIS Application Security Consulting",
  grade: "45",
};

const BLANK = Object.assign({}, REQ, {
  docTitle: "Nike Phone Screen Template – R-90323",
  name: "", title: "", company: "", date: "", source: "", activePassive: "",
  motivation: "", currentProjects: "", expertise: "", recommendation: "",
  questions: QUESTIONS.map((q) => ({ q, a: "" })),
  comp: { expectations: "", base: "", bonus: "", stock: "", competingInterviews: "",
          competingOffers: "", timeline: "", nonCompete: "", location: "" },
});

const FILLED = Object.assign({}, REQ, {
  docTitle: "Phone Screen – R-90323 – 09/02/2026",
  name: "[Not captured on recording]",
  title: "",
  company: "DocuSign\nPrior: Microsoft – 13 years",
  date: "09/02/2026",
  source: "",
  activePassive: "",

  motivation: "- Wants platform-level work with impact across an entire company, not a single product line.\n- Doing a version of this at DocuSign, but says the scale is not there – it was at Microsoft.\n- Interested in how AI agents will use policy-based authorization; no avenue for that at DocuSign.",

  currentProjects: "API Access Management at DocuSign – policy-based first-party access control.\n- In production as of last week, serving ~5–10 internal applications on the core e-Sign platform (Maestro, Workspaces).\n- In discussion at CVP level to extend it across DocuSign next quarter as the onboarding control plane and enforcement point.",

  expertise: "- Identity, authorization, cryptography, key management – ~10 years in security, 14 years building services.\n- Cloud, microservices, distributed systems; building services and frameworks.\n- Hands-on with both Zanzibar and Topaz.\n- Simplifies complex problems so partner teams can onboard; stakeholder communication up to CVP level.",

  questions: [
    { q: QUESTIONS[0], a: "API Access Management at DocuSign – first-party access control so internal applications can call each other with fine-grained policy.\n- Wrote a Topaz-like policy layer on top of DocuSign's own authorization service. Evaluated Topaz directly; it did not fit their needs.\n- Shipped to production last week; live for the core e-Sign platform across ~5–10 internal applications." },
    { q: QUESTIONS[1], a: "Gave up a clean cutover – refused a big-bang replacement of e-Sign's legacy authorization logic.\n- Rolled out API-level access policy first, then six business-level access policies in parallel.\n- Ran new and legacy paths side by side with monitoring and fallback controls.\n- Roughly two months to complete the rollout." },
    { q: QUESTIONS[2], a: "Microsoft 365 Security & Entitlement Service – M365 licensing, built 0 to 1, ~5 billion requests per week.\n- Challenge was cross-region consistency without a latency penalty.\n- Solved with region isolation by account/tenant plus an account-level cache; each request resolves the owning shard and routes there.\n- Failure boundaries drawn at shard level, one below region." },
    { q: QUESTIONS[3], a: "The DocuSign authorization platform.\n- Schema conformance – partner teams have their own resource-relationship models. Reconciling the Maestro team's schema took five or six meetings.\n- Confidence in migrating – answered with data: cost efficiency, issues eliminated, results from teams already migrated." },
    { q: QUESTIONS[4], a: "- Policy model correctness – years of implicit authorization semantics sit in legacy code and must be captured exactly.\n- Hot critical path – availability, latency, caching, regional failure behavior, and an explicit fail-open vs fail-closed decision. Chose fail-open at DocuSign during rollout because consumers were internal.\n- Migration and adoption – tiered migration based on legacy complexity, then getting teams to move.\n- Governance – track who changed a policy, when and why, so behavior changes are traceable." },
    { q: QUESTIONS[5], a: "Can provide dates for early next week." },
    { q: QUESTIONS[6], a: "None given, and would not share current salary. Asked for the range first, then asked for total comp – likely carrying stock today.\n- Cited Seattle vs Portland cost of living; Seattle market pays higher." },
    { q: QUESTIONS[7], a: "Bellevue, WA. Open to relocation." },
  ],

  comp: {
    expectations: "Not provided; would not share current salary. Asked for the range, then for total comp – likely carrying stock today.\n- Reservation: Seattle market pays higher than Portland. Expect him at the higher end of the range.\n- Flag: salary may be an issue later in the process.",
    base: "Not disclosed.",
    bonus: "Not disclosed.",
    stock: "Not disclosed.",
    competingInterviews: "Interviewing; nothing at a late stage.",
    competingOffers: "None.",
    timeline: "Can provide dates for early next week.",
    nonCompete: "Not discussed.",
    location: "Bellevue, WA. Open to relocation.",
  },

  recommendation: "- Strong overall. Has the skill and discipline for the role.\n- Familiar with the key concepts and frameworks needed for the security layer.\n- Already doing similar work today.\n- Spoke well to evangelizing his work with larger teams and at larger scale.\n- Advance to hiring manager conversation with Eric Dwyer.",
});

// ---------- write -----------------------------------------------------------

const out = process.argv[2];
const which = process.argv[3];
Packer.toBuffer(build(which === "filled" ? FILLED : BLANK)).then((b) => {
  fs.writeFileSync(out, b);
  console.log("wrote", out, b.length, "bytes");
});
