---
name: chess-move-generation
description: Technique for implementing a correct chess move generator — structure, the five classic legality traps, and how to test it before trusting it.
---

# Chess move generation — technique

- **Structure:** 8×8 board array + per-piece pseudo-legal generators, then a legality
  filter: make the move, test own-king safety, unmake. Slower than clever, but *correct*,
  and correctness is what is being examined. Keep the engine pure (no DOM) so it is
  drivable from a test contract.
- **The five classic traps** (nearly every hand-rolled engine fails one):
  1. **Castling**: not through check, not out of check, not over occupied squares, rights
     lost on king *or rook* moves — and on rook *capture*.
  2. **En passant**: only immediately after the double push; the captured pawn is not on
     the target square; beware the discovered-check-on-your-own-king edge case (the
     make/unmake filter catches it if the *captured pawn* is actually removed in "make").
  3. **Pins**: never track pins explicitly — the make/unmake king-safety filter handles
     them for free.
  4. **Promotion**: enumerate all four pieces as distinct moves (`e7e8q/r/b/n`).
  5. **FEN bookkeeping**: halfmove clock resets on pawn moves *and captures*; fullmove
     increments after Black; en-passant square only when a double push just happened.
- **Test before UI:** count `legalMoves()` on the start position (20) and on the Kiwipete
  position (48) — if those two match, most of the engine is right. Then build the board.
- **UI:** Unicode glyphs (♔…♟) render everywhere; click source → highlight targets →
  click destination keeps the UI dumb and the engine authoritative.
