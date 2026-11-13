"""
Student-facing bilingual PDF reports for LaserPrep.

The Report object remains responsible for collecting analysis results.
This module only presents those results in French or English.
"""

from datetime import datetime
from html import escape
import os
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


TEXT = {
    "en": {
        "title": "LASERPREP — PROJECT REPORT",
        "subtitle": "Student copy",
        "project": "Project",
        "generated": "Generated",
        "overview": "OVERVIEW",
        "files": "FILES",
        "file_count": "PDF files",
        "objects": "Vector objects",
        "accepted": "Accepted without warnings",
        "warnings": "Accepted with warnings",
        "rejected": "Not accepted",
        "status_pass": "ACCEPTED",
        "status_warning": "ACCEPTED — WITH WARNINGS",
        "status_rejected": "NOT ACCEPTED",
        "details": "Details",
        "alerts": "Reasons for rejection",
        "warning_details": "Warnings",
        "repairs": "Automatic corrections",
        "drawing_size": "Drawing size",
        "maximum_size": "Maximum permitted size",
        "object_count": "Vector objects",
        "no_details": "No additional details.",
        "svg_warning_title": "CHECK BEFORE BOOKING — ",
        "svg_warning": (
            "LaserPrep can make mistakes. Review the final SVG in Inkscape or Adobe Illustrator "
            "before booking. All accepted PDFs are included, each on its own layer."
        ),
        "footer": "Generated automatically by LaserPrep.",
    },
    "fr": {
        "title": "LASERPREP — RAPPORT DU PROJET",
        "subtitle": "Copie destinée à l’étudiant",
        "project": "Projet",
        "generated": "Généré le",
        "overview": "RÉSUMÉ",
        "files": "FICHIERS",
        "file_count": "Fichiers PDF",
        "objects": "Objets vectoriels",
        "accepted": "Acceptés sans avertissement",
        "warnings": "Acceptés avec avertissements",
        "rejected": "Non acceptés",
        "status_pass": "ACCEPTÉ",
        "status_warning": "ACCEPTÉ — AVEC AVERTISSEMENTS",
        "status_rejected": "NON ACCEPTÉ",
        "details": "Détails",
        "alerts": "Motifs de refus",
        "warning_details": "Avertissements",
        "repairs": "Corrections automatiques",
        "drawing_size": "Dimensions du dessin",
        "maximum_size": "Dimensions maximales autorisées",
        "object_count": "Objets vectoriels",
        "no_details": "Aucun détail supplémentaire.",
        "svg_warning_title": "À VÉRIFIER AVANT RENDEZ-VOUS — ",
        "svg_warning": (
            "LaserPrep peut faire des erreurs. Vérifiez le SVG final dans Inkscape ou Adobe Illustrator "
            "avant de réserver. Tous les PDF acceptés y figurent, chacun sur un calque distinct."
        ),
        "footer": "Document généré automatiquement par LaserPrep.",
    },
}

STATUS_LABELS = {
    "PASS": "status_pass",
    "WARNING": "status_warning",
    "REJECTED": "status_rejected",
}

STATUS_COLORS = {
    "PASS": colors.HexColor("#287A50"),
    "WARNING": colors.HexColor("#A66A00"),
    "REJECTED": colors.HexColor("#B23B3B"),
}


def _paragraph(text, style):
    """Create a safely escaped paragraph from report text."""
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


def _build_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "StudentTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            textColor=colors.HexColor("#202B36"),
            alignment=TA_LEFT,
            spaceAfter=2 * mm,
        ),
        "subtitle": ParagraphStyle(
            "StudentSubtitle",
            parent=base["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#66727E"),
            spaceAfter=6 * mm,
        ),
        "section": ParagraphStyle(
            "StudentSection",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#263746"),
            spaceBefore=5 * mm,
            spaceAfter=2 * mm,
        ),
        "body": ParagraphStyle(
            "StudentBody",
            parent=base["BodyText"],
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#29343D"),
            spaceAfter=1.2 * mm,
        ),
        "small": ParagraphStyle(
            "StudentSmall",
            parent=base["BodyText"],
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#596671"),
        ),
        "summary_label": ParagraphStyle(
            "StudentSummaryLabel",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.2,
            leading=8.5,
            textColor=colors.HexColor("#596671"),
        ),
        "file": ParagraphStyle(
            "StudentFile",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#202B36"),
        ),
        "status": ParagraphStyle(
            "StudentStatus",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.2,
            leading=9,
            alignment=TA_RIGHT,
        ),
        "bullet": ParagraphStyle(
            "StudentBullet",
            parent=base["BodyText"],
            fontSize=8,
            leading=11,
            leftIndent=3 * mm,
            firstLineIndent=-2 * mm,
            spaceAfter=0.8 * mm,
        ),
        "footer": ParagraphStyle(
            "StudentFooter",
            parent=base["Normal"],
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#7A858E"),
            alignment=TA_CENTER,
        ),
    }


def _format_int(value, language):
    number = int(str(value or 0).replace(",", "").replace(" ", ""))
    return f"{number:,}".replace(",", " ") if language == "fr" else f"{number:,}"


def _format_decimal(value, language, places=2):
    formatted = f"{float(value):,.{places}f}"
    return formatted.replace(",", " ").replace(".", ",") if language == "fr" else formatted


def _has_warnings(item):
    return item.get("status") == "WARNING" or bool(item.get("warnings"))


def _status_summary(files):
    total_objects = sum(item.get("objects", 0) for item in files)
    rejected = sum(item.get("status") == "REJECTED" for item in files)
    accepted_with_warnings = sum(
        item.get("status") != "REJECTED" and _has_warnings(item)
        for item in files
    )
    accepted_without_warnings = sum(
        item.get("status") != "REJECTED" and not _has_warnings(item)
        for item in files
    )
    return total_objects, accepted_without_warnings, accepted_with_warnings, rejected


def _translate_detail(message, language):
    """Translate the known diagnostic messages without changing their data."""
    value = str(message)

    if language == "en":
        english_patterns = [
            (r"^Removed (\d+) duplicate lines$", lambda m:
                f"Removed {m.group(1)} duplicate line" + ("" if int(m.group(1)) == 1 else "s")),
            (r"^Corrected (\d+) colours$", lambda m:
                f"Corrected {m.group(1)} colour" + ("" if int(m.group(1)) == 1 else "s")),
            (r"^Removed (\d+) zero-length lines$", lambda m:
                f"Removed {m.group(1)} zero-length line" + ("" if int(m.group(1)) == 1 else "s")),
            (r"^Removed (\d+) near-duplicate lines$", lambda m:
                f"Removed {m.group(1)} near-duplicate line" + ("" if int(m.group(1)) == 1 else "s")),
        ]
        for pattern, replacement in english_patterns:
            match = re.match(pattern, value)
            if match:
                return replacement(match)
        return value

    exact = {
        "Could not read the PDF to determine its page count.":
            "Impossible de lire le PDF afin de déterminer son nombre de pages.",
        "Could not analyse the PDF's vector complexity before processing.":
            "Impossible d’analyser la complexité vectorielle du PDF avant son traitement.",
        "This PDF contains an excessive amount of vector geometry and is too complex for LaserPrep to process reliably. Please simplify the vector artwork before submitting it.":
            "Ce PDF contient trop de géométrie vectorielle et est trop complexe pour être traité de manière fiable par LaserPrep. Veuillez simplifier le dessin vectoriel avant de le soumettre.",
        "This PDF contains no usable vector artwork. The submitted artwork appears to be raster/image-based. Please submit a vector PDF suitable for laser cutting.":
            "Ce PDF ne contient aucun dessin vectoriel exploitable. Le visuel semble être une image matricielle. Veuillez soumettre un PDF vectoriel adapté à la découpe laser.",
        "Drawing complexity exceeds the allowed limit.":
            "La complexité du dessin dépasse la limite autorisée.",
        "No usable vector geometry was found in this PDF. LaserPrep could not produce any geometry to process.":
            "Aucune géométrie vectorielle exploitable n’a été trouvée dans ce PDF. LaserPrep n’a pas pu traiter le dessin.",
        "Complexity exceeds supported limit.":
            "La complexité du dessin dépasse la limite prise en charge.",
    }
    if value in exact:
        return exact[value]

    plural_patterns = [
        (r"^Removed (\d+) duplicate lines$", lambda m: (
            f"{_format_int(m.group(1), 'fr')} ligne en double supprimée"
            if int(m.group(1)) == 1 else
            f"{_format_int(m.group(1), 'fr')} lignes en double supprimées"
        )),
        (r"^Corrected (\d+) colours$", lambda m: (
            f"{_format_int(m.group(1), 'fr')} couleur corrigée"
            if int(m.group(1)) == 1 else
            f"{_format_int(m.group(1), 'fr')} couleurs corrigées"
        )),
        (r"^Removed (\d+) zero-length lines$", lambda m: (
            f"{_format_int(m.group(1), 'fr')} ligne de longueur nulle supprimée"
            if int(m.group(1)) == 1 else
            f"{_format_int(m.group(1), 'fr')} lignes de longueur nulle supprimées"
        )),
        (r"^Removed (\d+) near-duplicate lines$", lambda m: (
            f"{_format_int(m.group(1), 'fr')} ligne presque identique supprimée"
            if int(m.group(1)) == 1 else
            f"{_format_int(m.group(1), 'fr')} lignes presque identiques supprimées"
        )),
    ]
    for pattern, replacement in plural_patterns:
        match = re.match(pattern, value)
        if match:
            return replacement(match)

    patterns = [
        (
            r"^PDF contains (\d+) pages\. LaserPrep only accepts single-page PDFs\.$",
            lambda m: f"Le PDF contient {m.group(1)} pages. LaserPrep accepte uniquement les PDF d’une seule page.",
        ),
        (
            r"^Exceeds maximum permitted size by ([\d.]+) mm\.$",
            lambda m: f"Le dessin dépasse les dimensions maximales autorisées de {_format_decimal(m.group(1), 'fr')} mm.",
        ),
        (
            r"^(\d+) tiny segments detected\.$",
            lambda m: f"{_format_int(m.group(1), 'fr')} segments très courts détectés.",
        ),
        (
            r"^Unsupported colour (#[0-9A-Fa-f]{6}) \((\d+) objects\)\.$",
            lambda m: f"Couleur non prise en charge {m.group(1)} ({_format_int(m.group(2), 'fr')} objets).",
        ),
        (
            r"^Removed (\d+) zero-length lines$",
            lambda m: f"{m.group(1)} lignes de longueur nulle supprimées",
        ),
        (
            r"^Removed (\d+) duplicate lines$",
            lambda m: f"{m.group(1)} lignes en double supprimées",
        ),
        (
            r"^Removed (\d+) near-duplicate lines$",
            lambda m: f"{m.group(1)} lignes presque identiques supprimées",
        ),
        (
            r"^Corrected (\d+) colours$",
            lambda m: f"{m.group(1)} couleurs corrigées",
        ),
        (
            r"^SVG clipping removed (\d+) paths\. Proof: (.+) \(in reports/\)\.$",
            lambda m: f"Le découpage SVG a supprimé {_format_int(m.group(1), 'fr')} tracés. Fichier de vérification : {m.group(2)} (dans reports/).",
        ),
    ]
    for pattern, replacement in patterns:
        match = re.match(pattern, value)
        if match:
            return replacement(match)

    overlap = re.match(
        r"^Potential geometry overlap: (\d+) groups detected\. See (.+) in the project reports\.$",
        value,
    )
    if overlap:
        return (
            f"Chevauchements géométriques potentiels : {_format_int(overlap.group(1), 'fr')} groupes détectés. "
            f"Voir {overlap.group(2)} dans les rapports du projet."
        )

    complexity = re.match(
        r"^(Elevated|High) geometry complexity: ([\d,]+) vector objects; "
        r"([\d,]+) filled paths\. Processing may take longer than usual\."
        r"( Filled areas may significantly increase laser engraving time\.)?"
        r" Consider simplifying the artwork where practical\.$",
        value,
    )
    if complexity:
        level = "élevée" if complexity.group(1) == "High" else "accrue"
        translated = (
            f"Complexité géométrique {level} : "
            f"{_format_int(complexity.group(2), 'fr')} objets vectoriels et "
            f"{_format_int(complexity.group(3), 'fr')} tracés remplis. "
            "Le traitement peut prendre plus de temps que d’habitude."
        )
        if complexity.group(4):
            translated += (
                " Les zones remplies peuvent augmenter considérablement "
                "le temps de gravure laser."
            )
        translated += (
            " Dans la mesure du possible, veuillez simplifier le dessin."
        )
        return translated

    overlap = re.match(
        r"^Excessive potential geometry overlap: (\d+) groups detected\. Rejection threshold: (\d+) groups\. See (.+) in the project reports\.$",
        value,
    )
    if overlap:
        return (
            f"Chevauchements géométriques potentiels excessifs : {_format_int(overlap.group(1), 'fr')} groupes détectés. "
            f"Seuil de refus : {_format_int(overlap.group(2), 'fr')} groupes. "
            f"Voir {overlap.group(3)} dans les rapports du projet."
        )

    scale = re.match(
        r"^⚠️ Suspicious scale: drawing is ([\d.]+) × ([\d.]+) mm with (\d+) vector objects\. This may indicate an incorrect PDF export scale\. Please verify the original drawing size\.$",
        value,
    )
    if scale:
        return (
            f"Échelle suspecte : le dessin mesure {_format_decimal(scale.group(1), 'fr')} × {_format_decimal(scale.group(2), 'fr')} mm "
            f"et contient {_format_int(scale.group(3), 'fr')} objets vectoriels. Cela peut indiquer une échelle "
            "d’export PDF incorrecte. Veuillez vérifier les dimensions du dessin original."
        )

    return value


def _add_bullet_section(story, heading, items, styles, language):
    if not items:
        return
    story.append(Paragraph(escape(heading), styles["body"]))
    for item in items:
        story.append(
            Paragraph(
                "• " + escape(_translate_detail(item, language)).replace("\n", "<br/>"),
                styles["bullet"],
            )
        )


def save_student_report(report, path, project, language="en", svg_created=False):
    """
    Render one language version of a Report object as a student PDF.

    Call this twice with the same report data, once with language="fr"
    and once with language="en".
    """
    if language not in TEXT:
        raise ValueError("language must be 'fr' or 'en'")

    if report.current:
        report.files.append(report.current)
        report.current = None

    labels = TEXT[language]
    styles = _build_styles()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")

    (
        total_objects,
        accepted_without_warnings,
        accepted_with_warnings,
        rejected,
    ) = _status_summary(report.files)

    story = [
        Paragraph(labels["title"], styles["title"]),
        Paragraph(labels["subtitle"], styles["subtitle"]),
    ]

    metadata = [
        [
            Paragraph(f"<b>{labels['project']}</b>", styles["small"]),
            Paragraph(escape(str(project)), styles["body"]),
            Paragraph(f"<b>{labels['generated']}</b>", styles["small"]),
            Paragraph(report.generated.strftime("%Y-%m-%d %H:%M"), styles["body"]),
        ]
    ]
    metadata_table = Table(
        metadata,
        colWidths=[22 * mm, 65 * mm, 22 * mm, 55 * mm],
    )
    metadata_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F5F7")),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#DCE2E7")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
    ]))
    story.extend([metadata_table, Spacer(1, 4 * mm)])

    story.append(Paragraph(labels["overview"], styles["section"]))
    summary_rows = [
        [
            Paragraph(escape(labels["file_count"]), styles["summary_label"]),
            str(len(report.files)),
            Paragraph(escape(labels["objects"]), styles["summary_label"]),
            _format_int(total_objects, language),
        ],
        [
            Paragraph(escape(labels["accepted"]), styles["summary_label"]),
            str(accepted_without_warnings),
            Paragraph(escape(labels["warnings"]), styles["summary_label"]),
            str(accepted_with_warnings),
        ],
        [
            Paragraph(escape(labels["rejected"]), styles["summary_label"]),
            str(rejected), "", "",
        ],
    ]
    summary_table = Table(
        summary_rows,
        colWidths=[43 * mm, 13 * mm, 43 * mm, 13 * mm],
    )
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F8F9")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E0E5E9")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (0, 0), colors.HexColor("#596671")),
        ("TEXTCOLOR", (2, 0), (2, 0), colors.HexColor("#596671")),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTNAME", (3, 0), (3, 1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("ALIGN", (3, 0), (3, 1), "CENTER"),
        # Status categories use the same green / amber / red palette
        # as the individual file status labels.
        ("BACKGROUND", (0, 1), (1, 1), colors.HexColor("#EAF4EE")),
        ("TEXTCOLOR", (0, 1), (1, 1), colors.HexColor("#287A50")),
        ("BACKGROUND", (2, 1), (3, 1), colors.HexColor("#FBF3E5")),
        ("TEXTCOLOR", (2, 1), (3, 1), colors.HexColor("#A66A00")),
        ("BACKGROUND", (0, 2), (3, 2), colors.HexColor("#F9EBEB")),
        ("TEXTCOLOR", (0, 2), (0, 2), colors.HexColor("#B23B3B")),
        ("TEXTCOLOR", (1, 2), (1, 2), colors.HexColor("#B23B3B")),
        ("FONTNAME", (1, 2), (1, 2), "Helvetica-Bold"),
        ("SPAN", (1, 2), (3, 2)),
        ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2.2 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2 * mm),
    ]))
    story.append(summary_table)

    if svg_created:
        warning_style = ParagraphStyle(
            "StudentSvgWarning",
            parent=styles["body"],
            fontSize=7.8,
            leading=10,
            spaceAfter=0,
        )
        warning_text = (
            f'<font color="#8A5700"><b>{escape(labels["svg_warning_title"])}</b></font>'
            f'{escape(labels["svg_warning"])}'
        )
        warning_box = Table(
            [[Paragraph(warning_text, warning_style)]],
            colWidths=[170 * mm],
        )
        warning_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FBF3E5")),
            ("LINEBEFORE", (0, 0), (0, -1), 2.2, colors.HexColor("#D49A35")),
            ("LEFTPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 1.5 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm),
        ]))
        story.extend([Spacer(1, 2 * mm), warning_box])

    story.append(Paragraph(labels["files"], styles["section"]))

    for item in report.files:
        status = item.get("status", "PASS")
        if status != "REJECTED" and _has_warnings(item):
            status = "WARNING"
        status_label = labels[STATUS_LABELS.get(status, "status_pass")]
        status_color = STATUS_COLORS.get(status, STATUS_COLORS["PASS"])

        title_row = Table(
            [[
                Paragraph(escape(item.get("name", "Unknown")), styles["file"]),
                Paragraph(
                    f'<font color="{status_color.hexval()}">{escape(status_label)}</font>',
                    styles["status"],
                ),
            ]],
            colWidths=[112 * mm, 58 * mm],
        )
        title_row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F5F7")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE2E7")),
            ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ]))

        block = [title_row, Spacer(1, 2 * mm)]
        block.append(
            Paragraph(
                f'{escape(labels["object_count"])}: '
                + _format_int(item.get("objects", 0), language),
                styles["small"],
            )
        )

        drawing_size = item.get("drawing_size")
        maximum_size = item.get("maximum_permitted_size")
        if drawing_size:
            block.append(
                Paragraph(
                    f'{escape(labels["drawing_size"])}: '
                    f'{_format_decimal(drawing_size[0], language)} × {_format_decimal(drawing_size[1], language)} mm',
                    styles["small"],
                )
            )
        if maximum_size:
            block.append(
                Paragraph(
                    f'{escape(labels["maximum_size"])}: '
                    f'{_format_decimal(maximum_size[0], language)} × {_format_decimal(maximum_size[1], language)} mm',
                    styles["small"],
                )
            )

        _add_bullet_section(
            block, labels["alerts"], item.get("alerts", []), styles, language
        )
        _add_bullet_section(
            block, labels["warning_details"], item.get("warnings", []), styles, language
        )
        _add_bullet_section(
            block, labels["repairs"], item.get("repairs", []), styles, language
        )

        story.append(KeepTogether(block))
        story.append(Spacer(1, 3 * mm))

    def draw_footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#DCE2E7"))
        canvas.setLineWidth(0.4)
        canvas.line(20 * mm, 15 * mm, A4[0] - 20 * mm, 15 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#7A858E"))
        canvas.drawCentredString(
            A4[0] / 2,
            10 * mm,
            f'{labels["footer"]}  •  {document.page}',
        )
        canvas.restoreState()

    document = SimpleDocTemplate(
        str(temporary_path),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=22 * mm,
        title=f"LaserPrep — {project}",
        author="LaserPrep",
    )
    try:
        document.build(
            story,
            onFirstPage=draw_footer,
            onLaterPages=draw_footer,
        )
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
