import streamlit as st
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="Water Level Bulletin", layout="centered")
st.title("🌊 Water Level Bulletin Generator")

STATIONS_META = [
    (1, "Surma", "Kanaighat(Kan)", "KAN", 12.75),
    (2, "Surma", "Sylhet Sadar(Syl)", "SYL", 10.80),
    (3, "Surma", "Chatak(Chh)", "CHH", 8.70),
    (4, "Surma", "Sunamgonj(Sun)", "SUN", 7.80),
    (5, "Surma", "Derai(Der)", "DER", 6.55),
    (6, "Kushiyara", "Amalshid(Ama)", "AMA", 15.40),
    (7, "Kushiyara", "Sheola(She)", "SHE", 13.05),
    (8, "Kushiyara", "Sherpur(Shr)", "SHR", 8.55),
    (9, "Monu", "Monu Rail Brigde(Man)", "MAN", 17.55),
    (10, "Monu", "Moulvibazar Sadar(Mou)", "MOU", 11.30),
    (11, "Dhalai", "Kamalgonj(Kam)", "KAM", 19.35),
    (12, "Jadukata", "Laurergroh(Sak)", "LOR", 8.05),
    (13, "Piyan", "Jaflong(Jaf)", "JAF", 13.00),
    (14, "Sarigowain", "Sarighat(Sag)", "SAG", 12.35),
    (15, "Sarigowain", "Gowainghat(Gow)", "GOW", 10.82),
    (16, "Khowai", "Balla", "BALLA", 21.20),
    (17, "Khowai", "Habiganj", "HABIGANJ", 9.00),
]

raw_data = st.text_area("please insert field data from GR", height=180, placeholder="Kan*150926*1050*1021*1016*0.0\n...")

if st.button("Generate Bulletin & PDF"):
    if not raw_data.strip():
        st.error("অনুগ্রহ করে ডাটা ইনপুট দিন!")
    else:
        parsed_data = {}
        report_date = ""

        for line in raw_data.strip().split('\n'):
            line = line.strip().replace('\u200e', '')
            if not line:
                continue
            parts = line.split('*')
            code = parts[0].strip().upper()

            if len(parts) >= 5:
                if not report_date and len(parts[1]) == 6:
                    d = parts[1]
                    report_date = f"{d[:2]}/{d[2:4]}/20{d[4:]}"

                p_6pm = float(parts[2].strip()) / 100.0
                t_9am = float(parts[4].strip()) / 100.0
                rf = parts[5].strip() if len(parts) > 5 else "-"
                if rf in ["00", "0", "0.0"]:
                    rf = "0.0"

                parsed_data[code] = {'prev_6pm': p_6pm, 'today_9am': t_9am, 'rf': rf}

        report_rows = []
        for sl, river, name, code, dl in STATIONS_META:
            lookup = code.upper()
            if lookup in parsed_data:
                d = parsed_data[lookup]
                p_6pm, t_9am, rf = d['prev_6pm'], d['today_9am'], d['rf']
                diff = round(t_9am - p_6pm, 2)
                
                trend = "Rising" if diff >= 0.01 else ("Falling" if diff <= -0.01 else "Steady")
                status = f"{round(t_9am - dl, 2):+.2f}"

                report_rows.append({
                    'sl': sl, 'river': river, 'station': name,
                    'prev_6pm': f"{p_6pm:.2f}", 'today_9am': f"{t_9am:.2f}",
                    'trend': trend, 'dl': f"{dl:.2f}", 'status': status, 'rf': rf
                })

        st.success(f"রিপোর্ট তৈরি সফল হয়েছে! (তারিখ: {report_date})")
        st.dataframe(report_rows, use_container_width=True)

        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, leftMargin=15, rightMargin=15, topMargin=15, bottomMargin=15)
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('TStyle', parent=styles['Heading1'], fontName='Times-Bold', fontSize=13, alignment=1, spaceAfter=2)
        sub_style = ParagraphStyle('SStyle', parent=styles['Normal'], fontName='Times-Bold', fontSize=8, alignment=1, spaceAfter=8)
        cell_style = ParagraphStyle('CStyle', parent=styles['Normal'], fontName='Times-Roman', fontSize=8, leading=9, alignment=1)
        cell_bold = ParagraphStyle('CBold', parent=cell_style, fontName='Times-Bold')
        cell_left = ParagraphStyle('CLeft', parent=cell_style, alignment=0)
        cell_left_bold = ParagraphStyle('CLeftBold', parent=cell_style, fontName='Times-Bold', alignment=0)

        story.append(Paragraph("Daily Water Level Bulletin", title_style))
        story.append(Paragraph(f"Date: {report_date}, Report Time: 09:00 AM", sub_style))

        headers = [
            Paragraph("<b>SL</b>", cell_style), Paragraph("<b>River</b>", cell_style), Paragraph("<b>Station</b>", cell_style),
            Paragraph("<b>WL Prev Day<br/>06:00 PM(m)</b>", cell_style), Paragraph("<b>WL Today<br/>09:00 AM(m)</b>", cell_style),
            Paragraph("<b>Trend</b>", cell_style), Paragraph("<b>Danger Level<br/>(msl)</b>", cell_style),
            Paragraph("<b>Status vs<br/>DL (m)</b>", cell_style), Paragraph("<b>Rainfall<br/>(mm)</b>", cell_style)
        ]
        table_data = [headers]

        for r in report_rows:
            table_data.append([
                Paragraph(str(r['sl']), cell_style), Paragraph(r['river'], cell_left_bold), Paragraph(r['station'], cell_left),
                Paragraph(r['prev_6pm'], cell_style), Paragraph(r['today_9am'], cell_style), Paragraph(r['trend'], cell_style),
                Paragraph(r['dl'], cell_bold), Paragraph(r['status'], cell_style), Paragraph(r['rf'], cell_style)
            ])

        col_widths = [22, 58, 110, 68, 68, 44, 62, 60, 42]
        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#D3D3D3')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
            ('TOPPADDING', (0,0), (-1,-1), 2.5),
            ('SPAN', (1, 1), (1, 5)), ('SPAN', (1, 6), (1, 8)), ('SPAN', (1, 9), (1, 10)),
            ('SPAN', (1, 11), (1, 11)), ('SPAN', (1, 12), (1, 12)), ('SPAN', (1, 13), (1, 13)),
            ('SPAN', (1, 14), (1, 15)), ('SPAN', (1, 16), (1, 17))
        ]))
        story.append(t)
        doc.build(story)

        st.download_button(
            label="📥 Download PDF Bulletin",
            data=pdf_buffer.getvalue(),
            file_name=f"Water_Level_Bulletin_{report_date.replace('/', '')}.pdf",
            mime="application/pdf"
        )
