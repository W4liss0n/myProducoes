from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.app.desktop.bootstrap import build_runtime
from src.presentation.qt.main_window import MainWindow


class TestDesktopBootstrap(unittest.TestCase):
    def test_build_runtime_creates_main_window_offscreen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            runtime = build_runtime(
                db_path=tmp_path / "desktop.db",
                backup_dir=tmp_path / "backups",
            )
            self.assertIsInstance(runtime.window, MainWindow)
            self.assertEqual(runtime.app.applicationName(), "Gerenciador de Produções")
            runtime.window.close()

            bind = getattr(runtime.backend._sessions.Session, "kw", {}).get("bind")
            if bind is not None:
                bind.dispose()


if __name__ == "__main__":
    unittest.main()
