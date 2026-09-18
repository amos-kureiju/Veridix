import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_verification_pdf(detection_data: dict) -> io.BytesIO:
    """
    Membuat file PDF resmi laporan hasil verifikasi berita
    berisi naskah, status vonis, skor keyakinan, dan kata pemicu LIME.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    styles = getSampleStyleSheet()

    # Style Kustom
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, leading=22, textColor=colors.HexColor("#1e293b"))
    verdict_color = colors.HexColor("#dc2626") if detection_data['prediction'] == 'HOAX' else colors.HexColor("#16a34a")
    verdict_style = ParagraphStyle('VerdictStyle', parent=styles['Heading2'], fontSize=14, leading=18, textColor=verdict_color)

    # 1. Header Laporan
    story.append(Paragraph("INSPECT-AI: Laporan Hasil Verifikasi Berita Politik", title_style))
    story.append(Paragraph(f"Tanggal Cetak: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} WIB", styles['Normal']))
    story.append(Spacer(1, 15))

    # 2. Kotak Ringkasan Vonis
    status_text = "🔴 TERINDIKASI DISINFORMASI (HOAKS)" if detection_data['prediction'] == 'HOAX' else "🟢 TERINDIKASI FAKTA/VALID"
    summary_data = [
        ["Status Deteksi", status_text],
        ["Tingkat Keyakinan", f"{detection_data['confidence_score'] * 100:.1f}%"],
        ["Waktu Inferensi", f"{detection_data['inference_time_seconds']} Detik"]
    ]
    t = Table(summary_data, colWidths=[150, 350])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))

    # 3. Naskah Berita yang Diperiksa
    story.append(Paragraph("<b>Naskah Berita yang Diperiksa:</b>", styles['Heading3']))
    story.append(Paragraph(f"<i>\"{detection_data['extracted_text']}\"</i>", styles['Normal']))
    story.append(Spacer(1, 15))

    # 4. Analisis Kata Pemicu (LIME)
    story.append(Paragraph("<b>Kata Kunci Paling Berpengaruh (Explainable AI):</b>", styles['Heading3']))
    top_words = detection_data.get('explanation', {}).get('top_hoax_words', [])
    word_list = ", ".join([f"'{item['word']}' (+{item['score']:.2f})" for item in top_words[:5]]) or "Tidak ada pemicu dominan"
    story.append(Paragraph(f"Pemicu Utama: {word_list}", styles['Normal']))
    story.append(Spacer(1, 25))

    # 5. Disclaimer Etis
    disclaimer_text = "<b>Catatan & Disclaimer:</b> Hasil pemeriksaan ini dihasilkan oleh sistem kecerdasan buatan (IndoBERT Base P1) berbasis pola bahasa dan probabilitas data pelatihan. Hasil ini berfungsi sebagai alat bantu pengambil keputusan (Decision Support), bukan vonis hukum mutlak. Verifikasi rujukan resmi di TurnBackHoax.id dan CekFakta.com."
    story.append(Paragraph(disclaimer_text, styles['Italic']))

    doc.build(story)
    buffer.seek(0)
    return buffer