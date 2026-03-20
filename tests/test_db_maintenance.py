from __future__ import annotations

import importlib
import sys
import unittest
from argparse import Namespace
from unittest.mock import patch


class TestDbMaintenance(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = importlib.import_module("scripts.db_maintenance")

    def test_build_parser_accepts_supported_subcommands(self) -> None:
        parser = self.module.build_parser()

        self.assertEqual(parser.parse_args(["preflight"]).command, "preflight")
        self.assertEqual(parser.parse_args(["migrate"]).command, "migrate")
        self.assertEqual(parser.parse_args(["postcheck"]).command, "postcheck")

    def test_bootstrap_project_root_is_idempotent(self) -> None:
        expected = str(self.module.ROOT_DIR)
        before = sys.path.count(expected)

        root = self.module._bootstrap_project_root()

        self.assertEqual(root, self.module.ROOT_DIR)
        self.assertEqual(sys.path.count(expected), before)

    def test_cmd_migrate_uses_concrete_bootstrap(self) -> None:
        with patch("src.infrastructure.sqlite.bootstrap.SqliteDatabaseBootstrap") as bootstrap_cls:
            result = self.module.cmd_migrate(Namespace(db=None))

        self.assertEqual(result, 0)
        bootstrap_cls.assert_called_once()
        bootstrap_cls.return_value.ensure_ready.assert_called_once()


if __name__ == "__main__":
    unittest.main()
