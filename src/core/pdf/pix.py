from __future__ import annotations

import logging
from io import BytesIO
from typing import Dict, Optional

import qrcode
from reportlab.lib.units import cm
from reportlab.platypus import Image


def generate_qr_code_pix(dados_pix: Dict[str, str], valor: float, logger: logging.Logger) -> Optional[Image]:
    try:
        chave_pix = dados_pix.get('chave_pix', '')
        nome_beneficiario = dados_pix.get('nome_beneficiario', '')

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )

        payload = f"PIX:{chave_pix}:{nome_beneficiario}:{valor:.2f}"
        qr.add_data(payload)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)

        return Image(img_buffer, width=5 * cm, height=5 * cm)
    except Exception as exc:
        logger.error("Erro ao gerar QR Code PIX: %s", exc)
        return None
