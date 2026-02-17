#!/usr/bin/env python3
"""Build a subset PGN tree from seed lines using ChessDB queryall responses."""

import argparse
import math
import sys
import time

import chess
import chess.pgn
import requests
from requests import RequestException

CDB_URL = "https://www.chessdb.cn/cdb.php"
MATE_SCORE_THRESHOLD = 30000
MATE_SCORE_BASE = 32000


def cdb_queryall(fen: str, learn: int = 1) -> str:
    params = {"action": "queryall", "board": fen, "learn": str(learn)}
    response = requests.get(CDB_URL, params=params, timeout=30)
    response.raise_for_status()
    return response.text.strip()


def cdb_queue(fen: str) -> str:
    params = {"action": "queue", "board": fen}
    response = requests.get(CDB_URL, params=params, timeout=30)
    response.raise_for_status()
    return response.text.strip()


def parse_queryall(text: str):
    """Parse CDB queryall output into move dictionaries."""
    normalized = text.strip().lower()
    if normalized in {
        "unknown",
        "invalid board",
        "checkmate",
        "stalemate",
        "",
    }:
        return []

    out = []
    for item in text.split("|"):
        move_data = {}
        for field in item.split(","):
            field = field.strip()
            if field.startswith("move:"):
                move_data["uci"] = field.split(":", 1)[1]
            elif field.startswith("score:"):
                try:
                    move_data["score"] = int(field.split(":", 1)[1])
                except ValueError:
                    pass
            elif field.startswith("rank:"):
                try:
                    move_data["rank"] = int(field.split(":", 1)[1])
                except ValueError:
                    pass
            elif field.startswith("winrate:"):
                try:
                    move_data["winrate"] = int(field.split(":", 1)[1])
                except ValueError:
                    pass
            elif field.startswith("note:"):
                move_data["note"] = field.split(":", 1)[1]
        if "uci" in move_data:
            out.append(move_data)

    return out


def pick_moves(
    moves,
    topn: int,
    delta: int | None,
    min_score: int | None,
    min_winrate: int | None,
):
    """Pick candidate moves from CDB output according to score/rank and filters."""
    if not moves:
        return []

    def sort_key(move):
        return (move.get("score", -10**9), move.get("rank", -10**9))

    ordered = sorted(moves, key=sort_key, reverse=True)
    best_score = ordered[0].get("score")
    filtered = ordered

    if best_score is not None and delta is not None:
        filtered = [m for m in filtered if m.get("score", -10**9) >= best_score - delta]

    if min_score is not None:
        filtered = [m for m in filtered if m.get("score", -10**9) >= min_score]

    if min_winrate is not None:
        filtered = [m for m in filtered if m.get("winrate", -10**9) >= min_winrate]

    return filtered[:topn] if topn > 0 else filtered


def expand_from_seed(
    seed_moves_uci,
    max_plies_total,
    topn,
    delta,
    min_score,
    min_winrate,
    learn,
    queue_unknown,
    sleep_s,
):
    board0 = chess.Board()
    for uci in seed_moves_uci:
        board0.push_uci(uci)

    target_len = max_plies_total
    stack = [(list(board0.move_stack), None)]
    done = []

    while stack:
        line, line_score = stack.pop()
        board = chess.Board()
        for move in line:
            board.push(move)

        if len(line) >= target_len:
            done.append((line, line_score))
            continue

        fen = board.fen()
        try:
            raw = cdb_queryall(fen, learn=learn)
        except RequestException as error:
            print(f"[warn] cdb query failed for fen '{fen}': {error}", file=sys.stderr)
            done.append((line, line_score))
            continue

        if raw.strip().lower() == "unknown":
            if queue_unknown:
                try:
                    cdb_queue(fen)
                except RequestException as error:
                    print(
                        f"[warn] cdb queue failed for fen '{fen}': {error}",
                        file=sys.stderr,
                    )
            done.append((line, line_score))
            continue

        candidates = pick_moves(
            parse_queryall(raw),
            topn=topn,
            delta=delta,
            min_score=min_score,
            min_winrate=min_winrate,
        )

        if not candidates:
            done.append((line, line_score))
            continue

        for candidate in candidates:
            try:
                move = chess.Move.from_uci(candidate["uci"])
                if move in board.legal_moves:
                    stack.append((line + [move], candidate.get("score")))
            except Exception as error:  # noqa: BLE001
                print(
                    f"[warn] invalid candidate move '{candidate.get('uci')}' ({error})",
                    file=sys.stderr,
                )

        if sleep_s > 0:
            time.sleep(sleep_s)

    # Deduplicate while preserving order.
    seen = set()
    unique = []
    for line, line_score in done:
        key = tuple(m.uci() for m in line)
        if key not in seen:
            seen.add(key)
            unique.append((line, line_score))

    return unique


def read_seed_games(pgn_path):
    seeds = []
    with open(pgn_path, "r", encoding="utf-8") as handle:
        while True:
            game = chess.pgn.read_game(handle)
            if game is None:
                break
            uci_moves = [move.uci() for move in game.mainline_moves()]
            if uci_moves:
                seeds.append(uci_moves)
    return seeds


def format_eval_tag(score: int | None) -> str | None:
    if score is None:
        return None

    # Common engine convention: large centipawn-like values encode mate distance.
    if abs(score) >= MATE_SCORE_THRESHOLD:
        plies_to_mate = max(1, MATE_SCORE_BASE - abs(score))
        moves_to_mate = max(1, math.ceil(plies_to_mate / 2))
        sign = "" if score > 0 else "-"
        return f"[%eval {sign}#{moves_to_mate}]"

    return f"[%eval {score / 100:.2f}]"


def write_lines_as_pgn(lines, out_path):
    with open(out_path, "w", encoding="utf-8") as handle:
        for idx, (line, line_score) in enumerate(lines, 1):
            game = chess.pgn.Game()
            game.headers["Event"] = "CDB subset"
            game.headers["Round"] = str(idx)
            node = game
            for move in line:
                node = node.add_variation(move)
            eval_tag = format_eval_tag(line_score)
            if eval_tag is not None and node is not game:
                node.comment = eval_tag
            print(game, file=handle, end="\n\n")


def main():
    parser = argparse.ArgumentParser(
        description="Bygg en delmängd av CDB från seed-PGN."
    )
    parser.add_argument("--pgn", required=True, help="Seed-PGN med öppningslinjer.")
    parser.add_argument(
        "--out", default="cdb_subset.pgn", help="Ut-PGN med genererade linjer."
    )
    parser.add_argument(
        "--max-plies",
        type=int,
        default=18,
        help="Max plies totalt (inklusive seed).",
    )
    parser.add_argument(
        "--topn", type=int, default=3, help="Max antal drag att behålla per position."
    )
    parser.add_argument(
        "--delta",
        type=int,
        default=30,
        help="Behåll drag inom (bästa score - delta). Sätt -1 för att stänga av.",
    )
    parser.add_argument(
        "--min-score", type=int, default=None, help="Släng drag med score under detta."
    )
    parser.add_argument(
        "--min-winrate",
        type=int,
        default=None,
        help="Släng drag med winrate under detta (om CDB ger winrate).",
    )
    parser.add_argument("--learn", type=int, default=1, help="CDB learn=1 (default).")
    parser.add_argument(
        "--queue-unknown",
        action="store_true",
        help="Köa okända positioner i CDB (action=queue).",
    )
    parser.add_argument("--sleep", type=float, default=0.15, help="Paus mellan API-anrop.")
    parser.add_argument(
        "--dedupe-global",
        action="store_true",
        help="Ta bort dubletter även mellan olika seed-partier.",
    )
    args = parser.parse_args()

    delta = None if args.delta < 0 else args.delta

    seeds = read_seed_games(args.pgn)
    all_lines = []

    for seed in seeds:
        lines = expand_from_seed(
            seed_moves_uci=seed,
            max_plies_total=args.max_plies,
            topn=args.topn,
            delta=delta,
            min_score=args.min_score,
            min_winrate=args.min_winrate,
            learn=args.learn,
            queue_unknown=args.queue_unknown,
            sleep_s=args.sleep,
        )
        all_lines.extend(lines)

    if args.dedupe_global:
        seen = set()
        unique = []
        for line, line_score in all_lines:
            key = tuple(move.uci() for move in line)
            if key not in seen:
                seen.add(key)
                unique.append((line, line_score))
        all_lines = unique

    write_lines_as_pgn(all_lines, args.out)
    print(f"Skrev {len(all_lines)} linjer till {args.out}")


if __name__ == "__main__":
    main()
