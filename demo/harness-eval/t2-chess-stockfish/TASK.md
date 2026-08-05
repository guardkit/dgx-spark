# Task T2: a chess board that plays real chess

> This brief is identical in every harness tier. Deliverable: `index.html` in the
> workspace root (for the one-shot tier: reply with only that file's contents).

## The brief

A single-file, fully self-contained browser chess board for two humans (hot-seat). The UI
matters less than the rules engine: **every legal-move rule of chess, implemented
correctly** — the validator cross-examines your move generator against Stockfish.

## Hard constraints

1. **One `index.html`, zero external requests** — no CDN, no libraries, no fonts, no
   images. Unicode chess glyphs are fine. The page must work fully offline.
2. Full legality: castling (with all its restrictions), en passant, promotion (all four
   pieces offered — auto-queen in the *UI* is fine, but `legalMoves()` must enumerate all
   four), check/checkmate/stalemate detection, and correct FEN bookkeeping including the
   halfmove clock and fullmove number.
3. Click-to-move UI with the side to move shown; illegal moves refused.
4. Zero console errors.

## Testability contract (required — the validator drives it)

```js
window.__chess = {
  load(fen),        // -> boolean; replace the game state with this FEN
  fen(),            // -> string; current full FEN (all 6 fields correct)
  legalMoves(),     // -> string[]; every legal move in lowercase UCI ("e2e4", "e7e8q",
                    //    castling as king-move "e1g1"), any order
  move(uci),        // -> boolean; apply if legal, else false and unchanged state
  status(),         // -> "ongoing" | "check" | "checkmate" | "stalemate"
};
```

## Acceptance checklist

1. Self-contained single file; offline-clean; zero console errors.
2. The contract above is live and accurate.
3. `legalMoves()` agrees exactly with a real engine across scripted test positions
   (castling rights, pins, en passant, promotions).
4. `status()` correct on checkmate/stalemate/check positions; `fen()` exact after a
   scripted move sequence.
