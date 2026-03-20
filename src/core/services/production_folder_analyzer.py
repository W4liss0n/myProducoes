from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".heic"}


class ProductionFolderAnalyzer:
    """Extrai métricas e dados de alunos a partir da estrutura de pastas da produção."""

    def find_folder(self, pasta_base: str, nome_busca: str) -> Optional[str]:
        try:
            for item in os.listdir(pasta_base):
                caminho = os.path.join(pasta_base, item)
                if os.path.isdir(caminho) and nome_busca.lower() in item.lower():
                    return caminho
        except Exception as exc:
            logger.error("Erro ao procurar pasta '%s' em '%s': %s", nome_busca, pasta_base, exc)
        return None

    def count_direct_photo_folders(self, pasta_raiz: str, extensoes_imagem: set[str] | None = None) -> tuple[int, int]:
        exts = extensoes_imagem or IMAGE_EXTENSIONS
        total_fotos = 0
        total_pastas = 0

        def percorrer_recursivo(pasta_atual: str) -> None:
            nonlocal total_fotos, total_pastas
            try:
                fotos_nesta_pasta = 0
                for item in os.listdir(pasta_atual):
                    caminho_completo = os.path.join(pasta_atual, item)
                    if os.path.isdir(caminho_completo):
                        percorrer_recursivo(caminho_completo)
                    elif os.path.isfile(caminho_completo):
                        ext = os.path.splitext(item.lower())[1]
                        if ext in exts:
                            fotos_nesta_pasta += 1
                            total_fotos += 1
                if fotos_nesta_pasta > 0:
                    total_pastas += 1
            except Exception as exc:
                logger.error("Erro ao percorrer pasta '%s': %s", pasta_atual, exc)

        percorrer_recursivo(pasta_raiz)
        return total_fotos, total_pastas

    def calculate_totals(self, pasta_producao: str) -> tuple[int, int, int]:
        alunos_data = self._collect_students_data(pasta_producao)
        total_fotos = sum(aluno["fotos"] for aluno in alunos_data.values())
        total_alunos = len(alunos_data)
        total_kits = sum(aluno["kits"] for aluno in alunos_data.values())
        return total_fotos, total_alunos, total_kits

    def extract_students(self, pasta_producao: str) -> List[Dict[str, Any]]:
        alunos_data = self._collect_students_data(pasta_producao)
        alunos = [
            {
                "id": aluno["id"],
                "fotos": aluno["fotos"],
                "kits": aluno["kits"],
                "capas": aluno["capas"],
                "curso": aluno["curso"],
            }
            for aluno in alunos_data.values()
        ]
        return sorted(alunos, key=lambda aluno: (aluno["id"], aluno["curso"]))

    def _collect_students_data(self, pasta_producao: str) -> dict[str, dict[str, Any]]:
        alunos_data: dict[str, dict[str, Any]] = {}
        registros_por_id: dict[str, list[str]] = {}
        registros_por_id_e_curso: dict[tuple[str, str], list[str]] = {}

        pasta_albuns = self.find_folder(pasta_producao, "albuns")
        if pasta_albuns:
            pasta_albuns_path = Path(pasta_albuns)

            def percorrer_albuns(pasta_atual: Path) -> None:
                try:
                    tem_fotos_diretas = False
                    fotos_count = 0
                    subpastas: list[Path] = []

                    for item in pasta_atual.iterdir():
                        if item.is_file():
                            if item.suffix.lower() in IMAGE_EXTENSIONS:
                                tem_fotos_diretas = True
                                fotos_count += 1
                        elif item.is_dir():
                            subpastas.append(item)

                    if tem_fotos_diretas:
                        aluno_id = pasta_atual.name
                        record_key = self._build_album_record_key(pasta_albuns_path, pasta_atual)
                        curso = self._build_course_label(pasta_albuns_path, pasta_atual)
                        aluno = alunos_data.setdefault(record_key, self._new_student_entry(aluno_id, curso))
                        aluno["fotos"] += fotos_count
                        registros_por_id.setdefault(aluno_id, []).append(record_key)
                        registros_por_id_e_curso.setdefault((aluno_id, curso), []).append(record_key)
                        return

                    for caminho_subpasta in subpastas:
                        percorrer_albuns(caminho_subpasta)
                except Exception as exc:
                    logger.error("Erro ao percorrer Albuns em '%s': %s", pasta_atual, exc)

            percorrer_albuns(pasta_albuns_path)

        pasta_kits = self.find_folder(pasta_producao, "kits")
        if pasta_kits:
            for (aluno_id, curso), num_fotos in self._count_kit_photos_by_student(pasta_kits).items():
                kits = num_fotos // 3
                if kits <= 0:
                    continue

                matching_records = sorted(set(registros_por_id_e_curso.get((aluno_id, curso), [])))
                if not matching_records:
                    matching_records = sorted(set(registros_por_id.get(aluno_id, [])))

                if not matching_records:
                    record_key = self._build_kit_only_record_key(aluno_id, curso)
                    aluno = alunos_data.setdefault(record_key, self._new_student_entry(aluno_id, curso))
                    aluno["kits"] = kits
                    continue

                if len(matching_records) > 1:
                    logger.warning(
                        "ID '%s' possui kits ambiguos para o curso '%s' em %d albuns; associando ao registro '%s'.",
                        aluno_id,
                        curso,
                        len(matching_records),
                        matching_records[0],
                    )

                alunos_data[matching_records[0]]["kits"] = kits

        return alunos_data

    def _count_kit_photos_by_student(self, pasta_kits: str) -> dict[tuple[str, str], int]:
        fotos_por_aluno: dict[tuple[str, str], int] = {}
        try:
            pasta_kits_path = Path(pasta_kits)
            for arquivo in pasta_kits_path.rglob("*"):
                if not arquivo.is_file():
                    continue
                if arquivo.suffix.lower() not in IMAGE_EXTENSIONS:
                    continue

                nome_sem_ext = arquivo.stem
                aluno_id = nome_sem_ext.split("_")[0].strip()
                curso = self._build_kit_course_label(pasta_kits_path, arquivo)
                key = (aluno_id, curso)
                fotos_por_aluno[key] = fotos_por_aluno.get(key, 0) + 1
        except Exception as exc:
            logger.error("Erro ao processar pasta Kits: %s", exc)
        return fotos_por_aluno

    @staticmethod
    def _new_student_entry(aluno_id: str, curso: str) -> dict[str, Any]:
        return {
            "id": aluno_id,
            "fotos": 0,
            "kits": 0,
            "capas": 0,
            "curso": curso,
        }

    @staticmethod
    def _build_album_record_key(albuns_root: Path, album_path: Path) -> str:
        return album_path.relative_to(albuns_root).as_posix()

    @staticmethod
    def _build_course_label(albuns_root: Path, album_path: Path) -> str:
        relative_parts = album_path.relative_to(albuns_root).parts[:-1]
        return " - ".join(relative_parts)

    @staticmethod
    def _build_kit_course_label(kits_root: Path, kit_file_path: Path) -> str:
        relative_parts = kit_file_path.relative_to(kits_root).parts
        course_parts = relative_parts[1:-1]
        return " - ".join(course_parts)

    @staticmethod
    def _build_kit_only_record_key(aluno_id: str, curso: str) -> str:
        if not curso:
            return f"kit::{aluno_id}"
        return f"kit::{curso}::{aluno_id}"
