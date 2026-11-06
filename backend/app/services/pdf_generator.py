
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    HRFlowable,
    ListFlowable,
    ListItem,
)

from app.models import Video, VideoSummary


FONT_DIR = Path(__file__).parent / "fonts"


# --------------------------------------------------
# 1. Register fonts
# --------------------------------------------------

def register_pdf_fonts():
    """Register fonts required for multilingual PDF generation."""

    fonts = {
        "NotoSans": FONT_DIR / "NotoSans-Regular.ttf",
        "Hindi": FONT_DIR / "NotoSansDevanagari-Regular.ttf",
        "Punjabi": FONT_DIR / "NotoSerifGurmukhi-Regular.ttf",
    }

    for name, path in fonts.items():

        if not path.exists():
            raise FileNotFoundError(
                f"Required PDF font not found: {path}"
            )

        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(
                TTFont(name, str(path), shapable=True)
            )

    # Japanese built-in CID font.
    if "HeiseiKakuGo-W5" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(
            UnicodeCIDFont("HeiseiKakuGo-W5")
        )


# --------------------------------------------------
# 2. Get font according to selected language
# --------------------------------------------------

def get_font_for_language(language: str) -> str:

    language_fonts = {
        "English": "NotoSans",
        "Spanish": "NotoSans",
        "French": "NotoSans",
        "German": "NotoSans",
        "Hindi": "Hindi",
        "Punjabi": "Punjabi",
        "Japanese": "HeiseiKakuGo-W5",
    }

    font_name = language_fonts.get(language)

    if not font_name:
        raise ValueError(
            f"Unsupported PDF language: {language}"
        )

    return font_name


# --------------------------------------------------
# 3. Localized PDF labels
# --------------------------------------------------

PDF_LABELS = {
    "English": {
        "video_information": "Video Information",
        "title": "Title",
        "url": "URL",
        "overview": "Overview",
        "key_points": "Key Points",
        "topics": "Topics Covered",
        "no_key_points": "No key points available.",
        "no_topics": "No topics available.",
    },

    "Hindi": {
        "video_information": "वीडियो की जानकारी",
        "title": "शीर्षक",
        "url": "लिंक",
        "overview": "सारांश",
        "key_points": "मुख्य बिंदु",
        "topics": "शामिल विषय",
        "no_key_points": "कोई मुख्य बिंदु उपलब्ध नहीं हैं।",
        "no_topics": "कोई विषय उपलब्ध नहीं है।",
    },

    "Punjabi": {
        "video_information": "ਵੀਡੀਓ ਦੀ ਜਾਣਕਾਰੀ",
        "title": "ਸਿਰਲੇਖ",
        "url": "ਲਿੰਕ",
        "overview": "ਸੰਖੇਪ",
        "key_points": "ਮੁੱਖ ਨੁਕਤੇ",
        "topics": "ਸ਼ਾਮਲ ਵਿਸ਼ੇ",
        "no_key_points": "ਕੋਈ ਮੁੱਖ ਨੁਕਤੇ ਉਪਲਬਧ ਨਹੀਂ ਹਨ।",
        "no_topics": "ਕੋਈ ਵਿਸ਼ਾ ਉਪਲਬਧ ਨਹੀਂ ਹੈ।",
    },

    "Spanish": {
        "video_information": "Información del vídeo",
        "title": "Título",
        "url": "URL",
        "overview": "Resumen",
        "key_points": "Puntos clave",
        "topics": "Temas tratados",
        "no_key_points": "No hay puntos clave disponibles.",
        "no_topics": "No hay temas disponibles.",
    },

    "French": {
        "video_information": "Informations sur la vidéo",
        "title": "Titre",
        "url": "URL",
        "overview": "Aperçu",
        "key_points": "Points clés",
        "topics": "Sujets abordés",
        "no_key_points": "Aucun point clé disponible.",
        "no_topics": "Aucun sujet disponible.",
    },

    "German": {
        "video_information": "Videoinformationen",
        "title": "Titel",
        "url": "URL",
        "overview": "Übersicht",
        "key_points": "Wichtige Punkte",
        "topics": "Behandelte Themen",
        "no_key_points": "Keine wichtigen Punkte verfügbar.",
        "no_topics": "Keine Themen verfügbar.",
    },

    "Japanese": {
        "video_information": "動画情報",
        "title": "タイトル",
        "url": "URL",
        "overview": "概要",
        "key_points": "重要なポイント",
        "topics": "取り上げられたトピック",
        "no_key_points": "重要なポイントはありません。",
        "no_topics": "トピックはありません。",
    },
}


# --------------------------------------------------
# 4. Safely format dynamic text
# --------------------------------------------------

def safe_paragraph_text(value) -> str:
    """Escape dynamic text before inserting it into ReportLab markup."""

    if value is None:
        return ""

    return escape(str(value)).replace("\n", "<br/>")


# --------------------------------------------------
# 5. Add page numbers
# --------------------------------------------------

def add_page_number(canvas, document):

    canvas.saveState()

    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.grey)

    canvas.drawCentredString(
        A4[0] / 2,
        12 * mm,
        f"Page {document.page}",
    )

    canvas.restoreState()


# --------------------------------------------------
# 6. Generate PDF
# --------------------------------------------------

def generate_summary_pdf(
    video: Video,
    video_summary: VideoSummary,
) -> BytesIO:

    """
    Generate a multilingual PDF for a completed video summary.

    Returns:
        BytesIO containing the generated PDF.
    """

    if video_summary.status != "completed":
        raise ValueError(
            "Only completed video summaries can be exported."
        )

    if not video_summary.summary:
        raise ValueError("Video summary is empty.")

    # Register all required fonts.
    register_pdf_fonts()

    language = video_summary.language

    # English font for common English metadata.
    english_font = "NotoSans"

    # Selected language font for summary content.
    content_font = get_font_for_language(language)

    labels = PDF_LABELS.get(language, PDF_LABELS["English"])

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=22 * mm,
        title=f"Video Summary - {video.title or video.youtube_video_id}",
        author="YouTube RAG Bot",
    )

    styles = getSampleStyleSheet()

    # --------------------------------------------------
    # Styles
    # --------------------------------------------------

    title_style = ParagraphStyle(
        "PDFTitle",
        parent=styles["Title"],
        fontName=english_font,
        fontSize=20,
        leading=27,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#172554"),
        spaceAfter=8,
    )

    subtitle_style = ParagraphStyle(
        "PDFSubtitle",
        parent=styles["Normal"],
        fontName=english_font,
        fontSize=10,
        leading=15,
        alignment=TA_CENTER,
        textColor=colors.grey,
        spaceAfter=18,
    )

    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName=content_font,
        fontSize=14,
        leading=22,
        textColor=colors.HexColor("#1D4ED8"),
        spaceBefore=12,
        spaceAfter=8,
        wordWrap="CJK",
    )

    body_style = ParagraphStyle(
        "PDFBody",
        parent=styles["BodyText"],
        fontName=content_font,
        fontSize=10.5,
        leading=18,
        alignment=TA_LEFT,
        spaceAfter=8,
        wordWrap="CJK",
    )

    url_style = ParagraphStyle(
        "PDFURL",
        parent=styles["BodyText"],
        fontName=english_font,
        fontSize=9,
        leading=15,
        spaceAfter=8,
        wordWrap="CJK",
    )

    bullet_style = ParagraphStyle(
        "PDFBullet",
        parent=body_style,
        leftIndent=4,
        firstLineIndent=0,
        spaceAfter=4,
    )

    # --------------------------------------------------
    # Document content
    # --------------------------------------------------

    story = []

    # Document title: intentionally English.
    story.append(
        Paragraph(
            "YouTube Video Summary",
            title_style,
        )
    )

    story.append(
        Paragraph(
            f"Generated by YouTube RAG Bot | Language: "
            f"{safe_paragraph_text(language)}",
            subtitle_style,
        )
    )

    story.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor("#CBD5E1"),
            spaceAfter=15,
        )
    )

    # --------------------------------------------------
    # Video information
    # --------------------------------------------------

    story.append(
        Paragraph(
            safe_paragraph_text(labels["video_information"]),
            heading_style,
        )
    )

    video_title = video.title or video.youtube_video_id

    # Title label and value use the selected content font.
    story.append(
        Paragraph(
            f"<b>{safe_paragraph_text(labels['title'])}:</b> "
            f"{safe_paragraph_text(video_title)}",
            body_style,
        )
    )

    # URL uses NotoSans to ensure readable Latin characters.
    story.append(
        Paragraph(
            f"<b>{safe_paragraph_text(labels['url'])}:</b> "
            f"{safe_paragraph_text(video.url)}",
            url_style,
        )
    )

    story.append(Spacer(1, 8))

    # --------------------------------------------------
    # Overview
    # --------------------------------------------------

    story.append(
        Paragraph(
            f"1. {safe_paragraph_text(labels['overview'])}",
            heading_style,
        )
    )

    story.append(
        Paragraph(
            safe_paragraph_text(video_summary.summary),
            body_style,
        )
    )

    # --------------------------------------------------
    # Key points
    # --------------------------------------------------

    story.append(
        Paragraph(
            f"2. {safe_paragraph_text(labels['key_points'])}",
            heading_style,
        )
    )

    key_points = video_summary.key_points or []

    if key_points:

        bullet_items = [
            ListItem(
                Paragraph(
                    safe_paragraph_text(point),
                    bullet_style,
                ),
                leftIndent=10,
            )
            for point in key_points
        ]

        story.append(
            ListFlowable(
                bullet_items,
                bulletType="bullet",
                start="circle",
                leftIndent=20,
                bulletFontName=content_font,
                bulletFontSize=9,
            )
        )

    else:
        story.append(
            Paragraph(
                safe_paragraph_text(labels["no_key_points"]),
                body_style,
            )
        )

    # --------------------------------------------------
    # Topics covered
    # --------------------------------------------------

    story.append(
        Paragraph(
            f"3. {safe_paragraph_text(labels['topics'])}",
            heading_style,
        )
    )

    topics = video_summary.topics or []

    if topics:

        topic_items = [
            ListItem(
                Paragraph(
                    safe_paragraph_text(topic),
                    bullet_style,
                ),
                leftIndent=10,
            )
            for topic in topics
        ]

        story.append(
            ListFlowable(
                topic_items,
                bulletType="bullet",
                start="circle",
                leftIndent=20,
                bulletFontName=content_font,
                bulletFontSize=9,
            )
        )

    else:
        story.append(
            Paragraph(
                safe_paragraph_text(labels["no_topics"]),
                body_style,
            )
        )

    # --------------------------------------------------
    # Footer
    # --------------------------------------------------

    story.append(Spacer(1, 20))

    story.append(
        HRFlowable(
            width="100%",
            thickness=0.5,
            color=colors.HexColor("#CBD5E1"),
        )
    )

    story.append(
        Paragraph(
            "Generated using YouTube RAG Bot",
            subtitle_style,
        )
    )

    # --------------------------------------------------
    # Build PDF
    # --------------------------------------------------

    document.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number,
    )

    buffer.seek(0)

    return buffer
