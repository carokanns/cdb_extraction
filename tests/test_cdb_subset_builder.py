import io
import sys
import unittest
from unittest import mock

import chess
import chess.pgn

import cdb_subset_builder


def _moves(*uci_moves):
    return [chess.Move.from_uci(uci) for uci in uci_moves]


class WriteSeedGroupsTests(unittest.TestCase):
    def test_writes_one_game_per_seed_with_variations(self):
        seed_groups = [
            [
                (_moves("e2e4", "e7e5", "g1f3"), 20),
                (_moves("e2e4", "e7e5", "f2f4"), 10),
            ],
            [
                (_moves("d2d4", "d7d5", "c2c4"), 30),
            ],
        ]

        mocked_open = mock.mock_open()
        with mock.patch("builtins.open", mocked_open):
            cdb_subset_builder.write_seed_groups_as_pgn(seed_groups, "out.pgn")

        written = "".join(call.args[0] for call in mocked_open().write.call_args_list)
        handle = io.StringIO(written)
        game1 = chess.pgn.read_game(handle)
        game2 = chess.pgn.read_game(handle)
        game3 = chess.pgn.read_game(handle)

        self.assertIsNotNone(game1)
        self.assertIsNotNone(game2)
        self.assertIsNone(game3)

        mainline1 = [move.uci() for move in game1.mainline_moves()]
        self.assertEqual(mainline1, ["e2e4", "e7e5", "g1f3"])

        node = game1
        for uci in ("e2e4", "e7e5"):
            node = next(v for v in node.variations if v.move.uci() == uci)
        variation_moves = [v.move.uci() for v in node.variations]
        self.assertIn("g1f3", variation_moves)
        self.assertIn("f2f4", variation_moves)

        mainline2 = [move.uci() for move in game2.mainline_moves()]
        self.assertEqual(mainline2, ["d2d4", "d7d5", "c2c4"])


class MainDedupeTests(unittest.TestCase):
    @mock.patch("cdb_subset_builder.write_seed_groups_as_pgn")
    @mock.patch("cdb_subset_builder.expand_from_seed")
    @mock.patch("cdb_subset_builder.read_seed_games")
    def test_dedupe_global_keeps_one_group_per_seed(
        self, mock_read_seed_games, mock_expand_from_seed, mock_write_seed_groups
    ):
        duplicate_line = _moves("e2e4", "e7e5")
        mock_read_seed_games.return_value = [["e2e4"], ["d2d4"]]
        mock_expand_from_seed.side_effect = [
            [(duplicate_line, 40)],
            [(duplicate_line, 20)],
        ]

        argv = [
            "cdb_subset_builder.py",
            "seed.pgn",
            "--out",
            "out.pgn",
            "--dedupe-global",
        ]
        with mock.patch.object(sys, "argv", argv):
            cdb_subset_builder.main()

        self.assertTrue(mock_write_seed_groups.called)
        seed_groups_arg = mock_write_seed_groups.call_args.args[0]
        self.assertEqual(len(seed_groups_arg), 2)
        self.assertEqual(len(seed_groups_arg[0]), 1)
        self.assertEqual(len(seed_groups_arg[1]), 1)

        first_group_line = [m.uci() for m in seed_groups_arg[0][0][0]]
        second_group_line = [m.uci() for m in seed_groups_arg[1][0][0]]
        self.assertEqual(first_group_line, ["e2e4", "e7e5"])
        self.assertEqual(second_group_line, ["e2e4", "e7e5"])


class CliErrorHandlingTests(unittest.TestCase):
    def test_missing_required_args_prints_error_and_usage(self):
        stderr = io.StringIO()
        with mock.patch.object(sys, "argv", ["cdb_subset_builder.py"]):
            with mock.patch("sys.stderr", stderr):
                with self.assertRaises(SystemExit) as exit_ctx:
                    cdb_subset_builder.run_cli()
        self.assertEqual(exit_ctx.exception.code, 2)
        out = stderr.getvalue()
        self.assertIn("[error]", out)
        self.assertIn("required", out)
        self.assertIn("Syntax:", out)
        self.assertIn("usage:", out)

    def test_invalid_input_prints_error_and_usage(self):
        with mock.patch(
            "cdb_subset_builder.main",
            side_effect=ValueError("Inga seed-linjer hittades i 'bad.pgn'."),
        ):
            stderr = io.StringIO()
            with mock.patch("sys.stderr", stderr):
                with self.assertRaises(SystemExit) as exit_ctx:
                    cdb_subset_builder.run_cli()
            self.assertEqual(exit_ctx.exception.code, 2)
            out = stderr.getvalue()
            self.assertIn("[error]", out)
            self.assertIn("Syntax:", out)
            self.assertIn("usage:", out)


if __name__ == "__main__":
    unittest.main()
