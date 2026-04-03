"""
Generador de constancia de radicación en PDF usando ReportLab.
Produce un documento A4 con los datos mínimos exigidos.
"""
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


AZUL_INSTITUCIONAL = colors.HexColor("#1a237e")
AZUL_CLARO         = colors.HexColor("#e8eaf6")
GRIS_TEXTO         = colors.HexColor("#555555")


def generar_constancia(
    *,
    ruta_destino: str,
    numero_radicado: str,
    fecha_radicacion: datetime,
    # Entidad
    entidad_nombre: str,
    entidad_municipio: str = "",
    entidad_nit: str = "",
    entidad_email: str = "",
    entidad_telefono: str = "",
    # Remitente
    remitente_nombre: str,
    remitente_id: str = "",
    remitente_email: str = "",
    remitente_telefono: str = "",
    # Documento
    asunto: str,
    tipo_soporte: str,
    numero_anexos: int = 0,
    numero_referencia: str = "",
    # Dependencia y operador
    dependencia_nombre: str,
    operador_nombre: str,
    observaciones: str = "",
) -> str:
    """Genera el PDF y retorna la ruta del archivo."""
    os.makedirs(os.path.dirname(ruta_destino), exist_ok=True)

    doc = SimpleDocTemplate(
        ruta_destino,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    estilos = getSampleStyleSheet()

    titulo_doc = ParagraphStyle(
        "TituloDoc", parent=estilos["Normal"],
        fontSize=9, textColor=GRIS_TEXTO, alignment=TA_LEFT,
    )
    encabezado_entidad = ParagraphStyle(
        "EncabezadoEntidad", parent=estilos["Normal"],
        fontSize=13, textColor=AZUL_INSTITUCIONAL, fontName="Helvetica-Bold",
        alignment=TA_LEFT,
    )
    subtitulo_entidad = ParagraphStyle(
        "SubtituloEntidad", parent=estilos["Normal"],
        fontSize=9, textColor=GRIS_TEXTO, alignment=TA_LEFT,
    )
    numero_style = ParagraphStyle(
        "Numero", parent=estilos["Normal"],
        fontSize=26, textColor=AZUL_INSTITUCIONAL, fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceAfter=4,
    )
    label_style = ParagraphStyle(
        "Label", parent=estilos["Normal"],
        fontSize=8, textColor=GRIS_TEXTO, fontName="Helvetica-Bold",
        spaceBefore=4,
    )
    valor_style = ParagraphStyle(
        "Valor", parent=estilos["Normal"],
        fontSize=10, textColor=colors.black,
    )
    pie_style = ParagraphStyle(
        "Pie", parent=estilos["Normal"],
        fontSize=8, textColor=GRIS_TEXTO, alignment=TA_CENTER,
    )

    historia = []

    # ── Encabezado ──────────────────────────────────────────────────────────
    tabla_header = Table(
        [[
            Paragraph(entidad_nombre, encabezado_entidad),
            Paragraph("CONSTANCIA DE RADICACIÓN", titulo_doc),
        ]],
        colWidths=["65%", "35%"],
    )
    tabla_header.setStyle(TableStyle([
        ("VALIGN",    (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",     (1, 0), (1, 0),   "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    historia.append(tabla_header)

    if entidad_municipio or entidad_nit:
        historia.append(
            Paragraph(
                f"NIT: {entidad_nit} — {entidad_municipio}",
                subtitulo_entidad,
            )
        )

    historia.append(HRFlowable(width="100%", thickness=2, color=AZUL_INSTITUCIONAL))
    historia.append(Spacer(1, 0.5 * cm))

    # ── Número de radicado ───────────────────────────────────────────────────
    caja_radicado = Table(
        [[Paragraph(numero_radicado, numero_style)]],
        colWidths=["100%"],
    )
    caja_radicado.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AZUL_CLARO),
        ("ROUNDEDCORNERS", [8]),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    historia.append(caja_radicado)
    historia.append(Spacer(1, 0.4 * cm))

    fecha_str = fecha_radicacion.strftime("%d de %B de %Y — %H:%M")
    historia.append(
        Paragraph(f"Fecha y hora de radicación: <b>{fecha_str}</b>", valor_style)
    )
    historia.append(Spacer(1, 0.6 * cm))

    # ── Datos del remitente ──────────────────────────────────────────────────
    historia.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    historia.append(Spacer(1, 0.3 * cm))
    historia.append(Paragraph("DATOS DEL REMITENTE", label_style))
    historia.append(Spacer(1, 0.2 * cm))

    datos_remitente = [
        ["Nombre / Razón social:", remitente_nombre],
        ["Identificación:", remitente_id or "—"],
        ["Email:", remitente_email or "—"],
        ["Teléfono:", remitente_telefono or "—"],
    ]
    t_remitente = Table(datos_remitente, colWidths=[5 * cm, None])
    t_remitente.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",  (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), GRIS_TEXTO),
        ("VALIGN",    (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    historia.append(t_remitente)
    historia.append(Spacer(1, 0.5 * cm))

    # ── Datos del documento ──────────────────────────────────────────────────
    historia.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    historia.append(Spacer(1, 0.3 * cm))
    historia.append(Paragraph("DATOS DEL DOCUMENTO", label_style))
    historia.append(Spacer(1, 0.2 * cm))

    datos_doc = [
        ["Asunto:", asunto],
        ["Tipo de soporte:", tipo_soporte.capitalize()],
        ["Número de anexos:", str(numero_anexos)],
    ]
    if numero_referencia:
        datos_doc.append(["N° referencia:", numero_referencia])

    t_doc = Table(datos_doc, colWidths=[5 * cm, None])
    t_doc.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",  (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), GRIS_TEXTO),
        ("VALIGN",    (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    historia.append(t_doc)
    historia.append(Spacer(1, 0.5 * cm))

    # ── Direccionamiento ─────────────────────────────────────────────────────
    historia.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    historia.append(Spacer(1, 0.3 * cm))
    historia.append(Paragraph("DIRECCIONAMIENTO", label_style))
    historia.append(Spacer(1, 0.2 * cm))

    datos_dir = [
        ["Dependencia:", dependencia_nombre],
        ["Radicado por:", operador_nombre],
    ]
    if observaciones:
        datos_dir.append(["Observaciones:", observaciones])

    t_dir = Table(datos_dir, colWidths=[5 * cm, None])
    t_dir.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",  (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), GRIS_TEXTO),
        ("VALIGN",    (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    historia.append(t_dir)
    historia.append(Spacer(1, 1 * cm))

    # ── Pie ──────────────────────────────────────────────────────────────────
    historia.append(HRFlowable(width="100%", thickness=1, color=AZUL_INSTITUCIONAL))
    historia.append(Spacer(1, 0.3 * cm))
    historia.append(
        Paragraph(
            f"Documento generado por Radica Mun — {entidad_nombre} — "
            f"Este documento es constancia de la recepción del trámite con el número indicado.",
            pie_style,
        )
    )

    doc.build(historia)
    return ruta_destino
