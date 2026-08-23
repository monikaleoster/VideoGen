// Regenerates tests/fixtures/sample_deck.pptx.
//
// Run from repo root: node tests/fixtures/generate_sample_deck.js
// Requires pptxgenjs (not a project dependency — install locally with
// `npm install pptxgenjs` in a scratch directory if regenerating).
//
// 3 slides, matching what tests/test_download.py and
// tests/test_notes_extraction.py both assert against:
//   1. "Welcome" — has speaker notes.
//   2. "Agenda" — has speaker notes.
//   3. "Thank You" — deliberately has NO speaker notes, so this fixture
//      also exercises notes_extraction's empty-notes handling without
//      changing the slide count download's tests hardcode.
const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";

const slides = [
  { title: "Welcome", notes: "Speaker notes for slide 1: Welcome." },
  { title: "Agenda", notes: "Speaker notes for slide 2: Agenda." },
  { title: "Thank You", notes: null },
];

slides.forEach(({ title, notes }, i) => {
  const slide = pres.addSlide();
  slide.addText(title, { x: 0.5, y: 0.5, w: 12.3, h: 1, fontSize: 40, bold: true, fontFace: "Arial" });
  slide.addText(`Sample slide ${i + 1} for Phase 4 fixture testing.`, {
    x: 0.5, y: 2, w: 12.3, h: 1, fontSize: 18, fontFace: "Arial",
  });
  if (notes) {
    slide.addNotes(notes);
  }
});

pres.writeFile({ fileName: `${__dirname}/sample_deck.pptx` }).then(() => {
  console.log("written");
});
