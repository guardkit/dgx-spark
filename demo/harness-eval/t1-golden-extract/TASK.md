# Task T1: log extraction to strict JSON

> This brief is identical in every harness tier. Deliverable: `extract.json` in the
> workspace root (for the one-shot tier: reply with only that file's contents).

## The brief

`input/server.log` is a mixed-format server log. Produce `extract.json`: a JSON array of
**only the ERROR and FATAL events**, normalized per the rules below.

## Event shape (exactly these keys, in this order; `ip` only when present)

```json
{ "ts": "2026-07-14T09:12:05Z", "service": "llama-swap", "level": "ERROR",
  "message": "...", "ip": "10.44.2.17" }
```

## Rules

1. **Two line formats.**
   ISO: `2026-07-14T09:12:03.412Z <service> <LEVEL> <message…>`
   Syslog: `Jul 14 09:12:05 <host> <service>[pid]: <LEVEL> <message…>` — no year: assume
   **2026**; all times are UTC. `service` is the name before `[pid]` (the host is not the service).
2. **Level is the dedicated LEVEL field only**, matched case-insensitively (`error`,
   `Fatal`, …). The word "ERROR" appearing inside a message text does **not** make a line
   an event. Output levels uppercased.
3. **Timestamps** normalize to ISO 8601 UTC at **seconds** precision with `Z` suffix
   (strip milliseconds).
4. **Continuation lines** (indented) belong to the previous line; keep **only the first
   line** as the event's message.
5. An **`ip=<value>` token** anywhere in a message becomes the `ip` field and is
   **removed from the message** (collapse any doubled spaces; trim).
6. **Dedupe** on `(service, level, message)` — keep the **earliest** occurrence only.
7. **Sort** ascending by `ts` (ties: input order).

## Acceptance checklist

1. `extract.json` parses as a JSON array of event objects.
2. Every event matches the shape above — no extra keys, `ts` in seconds-precision UTC.
3. ERROR/FATAL only; the message-text trap not taken; continuations folded; `ip` extracted.
4. Deduped, sorted, levels uppercased.
