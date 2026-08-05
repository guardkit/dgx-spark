// T5 fixture spec — the single source of truth shared by setup (reset), the validator,
// and the selftest. `expected` is the hand-derived correct destination; `mtime` values on
// name-dated files are deliberate DECOYS (a mtime-only implementation places them wrong).
export const FILES = [
  { path: "work/inbox/invoice_2026-03-12.pdf", content: "PDF-INVOICE-0312\n", mtime: "2026-07-30T10:00:00Z",
    expected: "work/organized/2026/03/docs/invoice_2026-03-12.pdf" },
  { path: "work/inbox/notes 14 Jul 2026.txt", content: "meeting notes: pins, gates, drift\n", mtime: "2026-01-02T09:00:00Z",
    expected: "work/organized/2026/07/docs/notes 14 Jul 2026.txt" },
  { path: "work/inbox/IMG_20260201_1200.jpg", content: "JPGDATA-A\n", mtime: "2026-07-30T10:00:00Z",
    expected: "work/organized/2026/02/images/IMG_20260201_1200.jpg" },
  { path: "work/inbox/holiday.PNG", content: "PNGDATA-B\n", mtime: "2026-05-20T14:30:00Z",
    expected: "work/organized/2026/05/images/holiday.PNG" },
  { path: "work/inbox/data-export.csv", content: "a,b\n1,2\n", mtime: "2026-04-02T08:15:00Z",
    expected: "work/organized/2026/04/data/data-export.csv" },
  { path: "work/inbox/archive_2025-12-30.zip", content: "ZIPBYTES\n", mtime: "2026-06-01T12:00:00Z",
    expected: "work/organized/2025/12/data/archive_2025-12-30.zip" },
  { path: "work/inbox/noext", content: "no extension bytes\n", mtime: "2026-03-03T03:03:03Z",
    expected: "work/organized/2026/03/other/noext" },
  { path: "work/desk/report.txt", content: "board pack draft\n", mtime: "2026-06-15T09:00:00Z",
    expected: "work/organized/2026/06/docs/report.txt" },
  { path: "work/downloads/report.txt", content: "quarterly report v1\n", mtime: "2026-06-11T17:45:00Z",
    expected: "work/organized/2026/06/docs/report-1.txt" },
  { path: "work/desk/todo.md", content: "- [ ] ship the harness eval\n", mtime: "2026-07-01T07:00:00Z",
    expected: "work/organized/2026/07/docs/todo.md" },
  { path: "work/downloads/deep/nested/old-scan_2026-01-05.jpeg", content: "JPEGDATA-C\n", mtime: "2026-07-30T10:00:00Z",
    expected: "work/organized/2026/01/images/old-scan_2026-01-05.jpeg" },
];
export const EMPTY_DIRS = ["work/desk/empty-drafts"];
