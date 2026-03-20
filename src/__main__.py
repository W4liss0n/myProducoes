from __future__ import annotations

import logging

from .app.desktop.bootstrap import run
from .config.constants import DATA_DIR, LOG_FILE


def setup_logging() -> None:
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s",
        encoding="utf-8",
    )

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
    logging.getLogger("").addHandler(console)

    logging.info("=" * 60)
    logging.info("Gerenciador de Produções iniciando...")
    logging.info("=" * 60)


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logging.info("Diretório de dados: %s", DATA_DIR)


def main() -> int:
    setup_logging()
    ensure_directories()
    try:
        return run()
    except Exception as exc:
        logging.critical("Erro fatal ao iniciar aplicação: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
