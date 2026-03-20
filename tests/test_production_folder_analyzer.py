from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.core.services.production_folder_analyzer import ProductionFolderAnalyzer


class TestProductionFolderAnalyzer(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.analyzer = ProductionFolderAnalyzer()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_nested_kit_folders_are_detected_and_matched_by_course(self) -> None:
        self._touch_images(
            self.base_path / "04 - Albuns" / "00 - Beca Azul" / "065",
            ["a.jpg", "b.jpg"],
        )
        self._touch_images(
            self.base_path / "04 - Albuns" / "00 - Beca Vermelha" / "065",
            ["c.jpg", "d.jpg", "e.jpg"],
        )
        self._touch_images(
            self.base_path / "04 - Albuns" / "00 - Beca Vermelha" / "065B",
            ["f.jpg", "g.jpg", "h.jpg", "i.jpg"],
        )
        self._touch_images(
            self.base_path / "KITs" / "10x15" / "00 - Beca Azul",
            ["065_I.JPG", "065_II.JPG"],
        )
        self._touch_images(
            self.base_path / "KITs" / "24x30" / "00 - Beca Azul",
            ["065.JPG"],
        )
        self._touch_images(
            self.base_path / "KITs" / "10x15" / "00 - Beca Vermelha",
            ["065B_I.JPG", "065B_II.JPG"],
        )
        self._touch_images(
            self.base_path / "KITs" / "24x30" / "00 - Beca Vermelha",
            ["065B.JPG"],
        )

        self.assertEqual(self.analyzer.calculate_totals(str(self.base_path)), (9, 3, 2))

        rows = self.analyzer.extract_students(str(self.base_path))

        self.assertEqual(len(rows), 3)
        self.assertEqual(sum(row["fotos"] for row in rows), 9)
        self.assertEqual(sum(row["kits"] for row in rows), 2)

        rows_by_key = {(row["id"], row["curso"]): row for row in rows}
        self.assertEqual(rows_by_key[("065", "00 - Beca Azul")]["fotos"], 2)
        self.assertEqual(rows_by_key[("065", "00 - Beca Vermelha")]["fotos"], 3)
        self.assertEqual(rows_by_key[("065B", "00 - Beca Vermelha")]["fotos"], 4)
        self.assertEqual(rows_by_key[("065", "00 - Beca Azul")]["kits"], 1)
        self.assertEqual(rows_by_key[("065", "00 - Beca Vermelha")]["kits"], 0)
        self.assertEqual(rows_by_key[("065B", "00 - Beca Vermelha")]["kits"], 1)

    def test_kits_without_matching_album_generate_their_own_row(self) -> None:
        self._touch_images(
            self.base_path / "KITs" / "10x15" / "00 - Beca Azul",
            ["200_I.JPG", "200_II.JPG"],
        )
        self._touch_images(
            self.base_path / "KITs" / "24x30" / "00 - Beca Azul",
            ["200.JPG"],
        )

        self.assertEqual(self.analyzer.calculate_totals(str(self.base_path)), (0, 1, 1))
        self.assertEqual(
            self.analyzer.extract_students(str(self.base_path)),
            [{"id": "200", "fotos": 0, "kits": 1, "capas": 0, "curso": "00 - Beca Azul"}],
        )

    @staticmethod
    def _touch_images(folder: Path, file_names: list[str]) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        for file_name in file_names:
            (folder / file_name).write_bytes(b"img")


if __name__ == "__main__":
    unittest.main()
