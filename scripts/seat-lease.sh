#!/usr/bin/env bash
# seat-lease.sh
#
# Truly reserve a llama-swap serving seat before an attended gate/film run, so
# "the endpoint is free" is *enforced*, not believed (MA-26). The rehearsal
# that died — a lane touched a seat another run had, because reservation was
# only prose in two receipt docs — is the failure this closes.
#
# This is the estate-side WRITER of the seat-lease convention. The READER half
# lives in deckhand (`deckhand gate`/`run`, env-gated by DECKHAND_SEAT_LEASE_DIR
# + DECKHAND_SEAT_LEASE_OWNER) and, next, in showcard. Field names here are
# identical to what those checkers read — see llama-swap-seat-leases.md.
#
# Convention:
#   Lease dir on a llama-swap host: /opt/llama-swap/leases/ (override: LEASE_DIR)
#   One file per seat:              <lease-dir>/<model-alias>.lease.json
#   JSON keys: seat, owner, purpose, acquired_at, expires_at (ISO-8601 UTC),
#              host, optional pid.
#
# Laws:
#   acquire  atomic-exclusive (hardlink create); FAILS if a live lease exists;
#            an EXPIRED lease may be replaced; a CORRUPT lease is never "free".
#   release  deletes only YOUR OWN lease; refuses a foreign lease.
#   status   reports live/expired/free without touching anything.
#
# Usage:
#   seat-lease.sh acquire <seat> --owner <o> --purpose <p> --minutes <n>
#   seat-lease.sh status  [seat]
#   seat-lease.sh release <seat> --owner <o>
#
# Env:
#   LEASE_DIR              lease directory (default /opt/llama-swap/leases)
#   SEAT_LEASE_NOW_EPOCH   test-only: override "now" (unix seconds) for hermetic
#                          expiry tests, mirroring deckhand's injected clock.
#
# Exit codes:
#   0  success
#   1  usage error
#   2  environment error (missing python3 / unwritable lease dir)
#   3  refused (live foreign/own lease on acquire, corrupt lease, foreign release)

set -u
set -o pipefail

LEASE_DIR="${LEASE_DIR:-/opt/llama-swap/leases}"
PROG="$(basename "$0")"

# --- helpers ----------------------------------------------------------------

die() {          # die <exit-code> <message...>
	local code="$1"
	shift
	printf '%s: %s\n' "$PROG" "$*" >&2
	exit "$code"
}

usage() {
	cat >&2 <<EOF
usage:
  $PROG acquire <seat> --owner <owner> --purpose <purpose> --minutes <n>
  $PROG status  [seat]
  $PROG release <seat> --owner <owner>

env: LEASE_DIR (default /opt/llama-swap/leases)
EOF
	exit 1
}

require_python3() {
	command -v python3 >/dev/null 2>&1 ||
		die 2 "python3 is required to read/write lease JSON but was not found on PATH"
}

# Reject an alias we cannot turn into a safe single-file lease path. Matches the
# spirit of deckhand's reader, which refuses '/' and '..' outright.
validate_seat() {
	local seat="$1"
	case "$seat" in
	'' | *[!A-Za-z0-9._-]*)
		die 1 "seat alias '$seat' must be non-empty and only [A-Za-z0-9._-] (a seat we cannot form a safe lease path for is never 'free')"
		;;
	.. | */*)
		die 1 "seat alias '$seat' may not be a path"
		;;
	esac
}

now_epoch() {
	if [ -n "${SEAT_LEASE_NOW_EPOCH:-}" ]; then
		printf '%s\n' "$SEAT_LEASE_NOW_EPOCH"
	else
		date -u +%s
	fi
}

iso_utc() { # iso_utc <epoch>
	date -u -d "@$1" +%Y-%m-%dT%H:%M:%SZ
}

lease_path() { printf '%s/%s.lease.json' "$LEASE_DIR" "$1"; }

# Read one string field from a lease file. Empty output on any error.
lease_field() { # lease_field <file> <key>
	python3 -c 'import json,sys
try:
    d=json.load(open(sys.argv[1]))
    v=d.get(sys.argv[2],"")
    print(v if isinstance(v,str) else "")
except Exception:
    pass' "$1" "$2" 2>/dev/null
}

# Print the lease expiry as a unix epoch, mirroring deckhand's parser exactly
# (Z -> +00:00; a naive timestamp is treated as UTC). Exit 1 if unparseable.
lease_expires_epoch() { # lease_expires_epoch <file>
	python3 -c 'import json,sys
from datetime import datetime,timezone
try:
    d=json.load(open(sys.argv[1]))
    raw=d["expires_at"]
    p=datetime.fromisoformat(str(raw).replace("Z","+00:00"))
    if p.tzinfo is None: p=p.replace(tzinfo=timezone.utc)
    print(int(p.timestamp()))
except Exception:
    sys.exit(1)' "$1" 2>/dev/null
}

# Emit a valid lease JSON object on stdout (json.dumps handles escaping).
build_lease_json() { # build_lease_json <seat> <owner> <purpose> <acq> <exp> <host> <pid>
	python3 -c 'import json,sys
seat,owner,purpose,acq,exp,host,pid=sys.argv[1:8]
d={"seat":seat,"owner":owner,"purpose":purpose,
   "acquired_at":acq,"expires_at":exp,"host":host}
if pid: d["pid"]=pid
print(json.dumps(d,indent=2))' "$@"
}

# --- subcommands ------------------------------------------------------------

cmd_acquire() {
	local seat="" owner="" purpose="" minutes=""
	[ "$#" -ge 1 ] || usage
	seat="$1"
	shift
	while [ "$#" -gt 0 ]; do
		case "$1" in
		--owner)
			owner="${2:-}"
			shift 2 || usage
			;;
		--purpose)
			purpose="${2:-}"
			shift 2 || usage
			;;
		--minutes)
			minutes="${2:-}"
			shift 2 || usage
			;;
		*) die 1 "unknown argument to acquire: $1" ;;
		esac
	done
	[ -n "$owner" ] || die 1 "acquire requires --owner"
	[ -n "$purpose" ] || die 1 "acquire requires --purpose"
	[ -n "$minutes" ] || die 1 "acquire requires --minutes"
	case "$minutes" in
	'' | *[!0-9]*) die 1 "--minutes must be a positive integer, got '$minutes'" ;;
	esac
	[ "$minutes" -gt 0 ] || die 1 "--minutes must be greater than zero"
	validate_seat "$seat"
	require_python3

	mkdir -p "$LEASE_DIR" 2>/dev/null ||
		die 2 "cannot create lease dir $LEASE_DIR"
	[ -w "$LEASE_DIR" ] || die 2 "lease dir $LEASE_DIR is not writable"

	local now expires acquired lease host pid content tmp
	now="$(now_epoch)"
	expires="$(iso_utc "$((now + minutes * 60))")"
	acquired="$(iso_utc "$now")"
	lease="$(lease_path "$seat")"
	host="$(hostname)"
	pid="$$"
	content="$(build_lease_json "$seat" "$owner" "$purpose" "$acquired" "$expires" "$host" "$pid")" ||
		die 2 "failed to build lease JSON"

	tmp="$(mktemp "${LEASE_DIR}/.${seat}.XXXXXX.tmp")" ||
		die 2 "cannot create temp file in $LEASE_DIR"
	printf '%s\n' "$content" >"$tmp"

	# Atomic-exclusive create: hardlink fails if the seat file already exists, so
	# two racing acquirers cannot both win, and the winner's file has full
	# content the instant it appears (no empty-file window a reader could see).
	if ln "$tmp" "$lease" 2>/dev/null; then
		rm -f "$tmp"
		printf 'acquired seat %s until %s (owner %s)\n' "$seat" "$expires" "$owner"
		printf '  lease: %s\n' "$lease"
		return 0
	fi

	# The seat file exists. It refuses ONLY if the lease is still live; an expired
	# lease may be replaced; a corrupt lease is never treated as free.
	local exp_epoch
	if ! exp_epoch="$(lease_expires_epoch "$lease")"; then
		rm -f "$tmp"
		die 3 "seat '$seat' has a CORRUPT lease at $lease (unparseable expires_at) — never treated as free; inspect/remove it by hand"
	fi
	if [ "$exp_epoch" -gt "$now" ]; then
		local held_by held_until held_for
		held_by="$(lease_field "$lease" owner)"
		held_until="$(lease_field "$lease" expires_at)"
		held_for="$(lease_field "$lease" purpose)"
		rm -f "$tmp"
		die 3 "seat '$seat' is LIVE-leased by '${held_by}' for '${held_for}' until ${held_until} (lease: $lease) — wait for it to expire or have the owner release it"
	fi

	# Expired lease: replace it. Remove then re-attempt the exclusive create so a
	# racing acquirer of the freed seat still cannot double-win.
	rm -f "$lease"
	if ln "$tmp" "$lease" 2>/dev/null; then
		rm -f "$tmp"
		printf 'acquired seat %s (replaced an expired lease) until %s (owner %s)\n' "$seat" "$expires" "$owner"
		printf '  lease: %s\n' "$lease"
		return 0
	fi
	rm -f "$tmp"
	die 3 "seat '$seat' was taken by another acquirer while replacing an expired lease — re-run"
}

# Describe one lease file to stdout; returns 0 always (status never fails on state).
describe_lease() { # describe_lease <seat> <now>
	local seat="$1" now="$2" lease exp_epoch state owner purpose expires
	lease="$(lease_path "$seat")"
	if [ ! -f "$lease" ]; then
		printf '%-28s FREE\n' "$seat"
		return 0
	fi
	owner="$(lease_field "$lease" owner)"
	purpose="$(lease_field "$lease" purpose)"
	expires="$(lease_field "$lease" expires_at)"
	if ! exp_epoch="$(lease_expires_epoch "$lease")"; then
		printf '%-28s CORRUPT   %s\n' "$seat" "$lease"
		return 0
	fi
	if [ "$exp_epoch" -gt "$now" ]; then
		state="LIVE"
	else
		state="EXPIRED"
	fi
	printf '%-28s %-8s owner=%s until=%s purpose=%s\n' \
		"$seat" "$state" "$owner" "$expires" "$purpose"
}

cmd_status() {
	require_python3
	local now
	now="$(now_epoch)"
	if [ "$#" -ge 1 ]; then
		validate_seat "$1"
		describe_lease "$1" "$now"
		return 0
	fi
	if [ ! -d "$LEASE_DIR" ]; then
		printf '(no lease dir at %s — all seats free)\n' "$LEASE_DIR"
		return 0
	fi
	local found=0 f seat
	for f in "$LEASE_DIR"/*.lease.json; do
		[ -e "$f" ] || continue
		found=1
		seat="$(basename "$f" .lease.json)"
		describe_lease "$seat" "$now"
	done
	[ "$found" -eq 1 ] || printf '(no leases in %s — all seats free)\n' "$LEASE_DIR"
}

cmd_release() {
	local seat="" owner=""
	[ "$#" -ge 1 ] || usage
	seat="$1"
	shift
	while [ "$#" -gt 0 ]; do
		case "$1" in
		--owner)
			owner="${2:-}"
			shift 2 || usage
			;;
		*) die 1 "unknown argument to release: $1" ;;
		esac
	done
	[ -n "$owner" ] || die 1 "release requires --owner"
	validate_seat "$seat"
	require_python3

	local lease held_by
	lease="$(lease_path "$seat")"
	if [ ! -f "$lease" ]; then
		printf 'no lease for seat %s — nothing to release\n' "$seat"
		return 0
	fi
	held_by="$(lease_field "$lease" owner)"
	if [ "$held_by" != "$owner" ]; then
		die 3 "seat '$seat' is leased by '${held_by}', not '${owner}' — release deletes only your OWN lease; refusing"
	fi
	rm -f "$lease" || die 2 "failed to remove lease $lease"
	printf 'released seat %s (owner %s)\n' "$seat" "$owner"
}

# --- dispatch ---------------------------------------------------------------

[ "$#" -ge 1 ] || usage
subcommand="$1"
shift
case "$subcommand" in
acquire) cmd_acquire "$@" ;;
status) cmd_status "$@" ;;
release) cmd_release "$@" ;;
-h | --help | help) usage ;;
*) die 1 "unknown subcommand '$subcommand' (acquire|status|release)" ;;
esac
