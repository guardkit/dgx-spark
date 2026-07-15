# llama-swap seat leases

**Truly reserve a serving seat before an attended gate or film run — so "the endpoint is free" is _enforced_, not believed.**

This closes MA-26 on the estate side. Endpoint reservation used to be prose in two receipt docs and nothing else; a rehearsal died because a lane touched a seat another run was using, on the belief the seat was free. A seat lease turns that belief into a file with a law behind it.

- **Convention + writer (this repo):** the lease-file layout, the `acquire`/`status`/`release` tool.
- **Readers (elsewhere):** `deckhand gate`/`run` reads a lease and refuses to run on a live foreign one; `showcard` is the **named next** checker (not yet wired).

---

## The convention

- **Lease directory** on a llama-swap host: `/opt/llama-swap/leases/` (override with `LEASE_DIR` for testing).
- **One file per seat:** `<model-alias>.lease.json`, where `<model-alias>` is the configured llama-swap model name the endpoint call uses (the `models.<name>` keys in the config-of-record — see `examples/llama-swap-config.gb10-live-2026-07-15.yaml`).
- **JSON keys** (field names are shared verbatim with the deckhand reader — do not rename):

  | key           | type            | meaning                                            |
  | ------------- | --------------- | -------------------------------------------------- |
  | `seat`        | string          | the model alias (matches the filename stem)        |
  | `owner`       | string          | who holds the seat (matched on release + by checkers) |
  | `purpose`     | string          | what the seat is held for (shown when a run is refused) |
  | `acquired_at` | string ISO-8601 | when the lease was taken (UTC, `...Z`)              |
  | `expires_at`  | string ISO-8601 | when the lease goes stale (UTC, `...Z`)             |
  | `host`        | string          | the box the lease was taken on                     |
  | `pid`         | string (optional) | the acquiring process id, informational          |

  Timestamps are ISO-8601 UTC. A naive timestamp (no zone) is read as UTC — identical to the deckhand parser (`Z` → `+00:00`, naive → UTC).

## The laws

- **Absent file → the seat is FREE, proceed.**
- **`acquire` is atomic-exclusive** (a hardlink create that fails if the seat file exists) and **FAILS if a LIVE lease exists** — two racing acquirers cannot both win, and the winner's file carries full content the instant it appears (no empty-file window a reader could catch mid-write).
- **An EXPIRED lease may be replaced** (`expires_at` in the past → crash tolerance; a run that died without releasing does not wedge the seat forever).
- **A CORRUPT lease is never treated as free** — an unparseable `expires_at` refuses, rather than being silently overwritten.
- **`release` deletes only YOUR OWN lease** — a foreign lease is refused, even if expired.
- **Checkers refuse on a live foreign lease** before any model is constructed or any endpoint call is made.

## The tool

`scripts/seat-lease.sh` — the estate-side writer. Requires `bash`, GNU `date`, and `python3` (used only for safe JSON read/write; the atomic path is pure bash). shellcheck-clean.

```
seat-lease.sh acquire <seat> --owner <owner> --purpose <purpose> --minutes <n>
seat-lease.sh status  [seat]
seat-lease.sh release <seat> --owner <owner>
```

Exit codes: `0` success · `1` usage error · `2` environment error (no `python3` / unwritable dir) · `3` **refused** (live lease on acquire, corrupt lease, foreign release).

`LEASE_DIR` overrides the directory (default `/opt/llama-swap/leases`). `SEAT_LEASE_NOW_EPOCH` is a test-only clock override (unix seconds), mirroring deckhand's injected `now` for hermetic expiry tests.

## The checkers

- **deckhand** (`deckhand gate` / `deckhand run`) reads a lease and refuses on a live foreign one. It is **default-OFF** and env-gated — a config that never sets these runs exactly as before:
  - `DECKHAND_SEAT_LEASE_DIR` — the lease directory to check (unset = the check is a no-op).
  - `DECKHAND_SEAT_LEASE_OWNER` — who "we" are (unset = the current OS user via `getpass.getuser()`); a live lease with this owner is ours and the run proceeds.
- **showcard** is the **NAMED NEXT** checker — its whole-box residency law is the other consumer of this convention, but it is **not yet wired** (today's competing-seat unload is still a manual `GET :9000/unload` operator move in every live run). When it is wired, it reads the same field names.

## Worked example — an attended gate

Reserve the seat, run the gate, release. On the box, `<owner>` is typically your username; the checker defaults `DECKHAND_SEAT_LEASE_OWNER` to it.

```bash
# 1. reserve the seat you're about to film/gate for two hours
scripts/seat-lease.sh acquire gemma4-coach \
    --owner "$USER" --purpose "attended KR-0 film" --minutes 120

# 2. run the attended gate with the checker pointed at the lease dir
DECKHAND_SEAT_LEASE_DIR=/opt/llama-swap/leases \
DECKHAND_SEAT_LEASE_OWNER="$USER" \
    deckhand gate ...        # a live foreign lease here refuses BEFORE any endpoint call

# 3. release when done (deletes only your own lease)
scripts/seat-lease.sh release gemma4-coach --owner "$USER"

# any time: see who holds what
scripts/seat-lease.sh status
```

A second lane that runs step 2 against a seat you hold is refused loudly, naming your owner, purpose and expiry — instead of silently colliding with your film slot.

## Cross-reference — the factory seat rows

The factory register (`ai-transition docs/factory-gap-analysis-2026-07-13.md`) carries the factory-side seat/reservation rows. This convention is the shared mechanism they point at — **coordinate, do not duplicate**: the lease-file layout and laws live here; factory rows describe how each factory surface consumes them.

## Residue — Node B and the granite-vision cap (Rich-queue / attended)

The following are **out of this pass** and stay on Rich's attended queue:

- **Node B (`spark-fcf6`) legs — ssh denied.** This pass covered Node A (`promaxgb10-41b1`) only: the lease tool, convention, live `/opt/llama-swap/leases/` directory, and the config-of-record are Node A's. Node B needs its own lease directory drop and its **own topology capture** (its `config.yaml` is not yet tracked here); both require box access this session did not have.
- **The granite-vision launch-script image-cap `1 → 6` change on Node B.** A lane mutated Node B's granite-vision launch script (image cap raised from 1 to 6) leaving a `.bak` on the box and **no ratify-or-revert record** — a re-provision silently reverts it (register MA-26; related recorded Node B granite-vision drift in [`DRIFT-granite-vision-seat-2026-07-11.md`](./DRIFT-granite-vision-seat-2026-07-11.md)). For reference, Node A's granite-vision launch script (`scripts/vllm-granite-vision.sh`) still ships the original `--limit-mm-per-prompt.image=1`. Committing that cap change as configuration-of-record (ratify or revert) needs Node B access and is Rich's call.
