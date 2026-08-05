---
name: log-forensics
description: Technique for turning messy multi-format logs into strict, normalized JSON without losing edge cases.
---

# Log forensics — extraction technique

- **Parse per format family, never one mega-regex.** Write one matcher per line shape and
  classify each line first; a line that matches no family is either a continuation or noise
  — decide by inspecting it, don't guess.
- **Continuation lines**: detect by leading whitespace *before* classifying; attach to the
  previous event, then decide what the spec wants done with them.
- **Timestamps**: never `new Date(str)` a syslog date — build the ISO string by hand
  (month-name table, zero-padding) so the assumed year and UTC intent are explicit.
  Strip sub-second precision by string surgery, not float math.
- **Field extraction from prose** (`key=value` tokens): extract, then *remove* the token
  and repair whitespace (collapse doubles, trim) — leaving the hole is the classic miss.
- **Dedupe and sort last**, on the fully-normalized events — deduping raw lines misses
  near-duplicates that normalization would have unified.
- **Self-check before finishing**: re-read the spec's rules as a checklist against your
  actual output — count expected exclusions (wrong level, message-text traps) by hand.
