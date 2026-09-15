      import streamlit as st
import pandas as pd
import re
from datetime import date
from io import BytesIO
from streamlit_gsheets import GSheetsConnection

# ReportLab libraries for PDF Generation
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ---------------------------------------------------------
# ১. গুগল শিট কানেকশন
# ---------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

st.set_page_config(page_title="Hydrological Bulletin Generator", layout="wide")
st.title("Daily Water Level Bulletin Generator")

# ---------------------------------------------------------
# ২. ১৭টি স্টেশনের মাস্টার লিস্ট (ছবি অনুযায়ী)
# ---------------------------------------------------------
STATION_MASTER_DATA = [
    {"SL": 1,  "River": "Surma",        "Station": "Kanaighat(Knt)",       "Code": "KNT", "DL": 12.75},
    {"SL": 2,  "River": "Surma",        "Station": "Sylhet Sadar(Syl)",    "Code": "SYL", "DL": 10.80},
    {"SL": 3,  "River": "Surma",        "Station": "Chhatak(Cht)",         "Code": "CHH", "DL": 8.70},
    {"SL": 4,  "River": "Surma",        "Station": "Sunamganj(Sun)",       "Code": "SUN", "DL": 7.80},
    {"SL": 5,  "River": "Surma",        "Station": "Dirai(Dir)",           "Code": "DIR", "DL": 6.55},
    {"SL": 6,  "River": "Kushiyara",     "Station": "Amalshid(Ams)",        "Code": "AMS", "DL": 15.40},
    {"SL": 7,  "River": "Kushiyara",     "Station": "Sheola(Shl)",          "Code": "SHL", "DL": 13.05},
    {"SL": 8,  "River": "Kushiyara",     "Station": "Sherpur(Shr)",         "Code": "SHR", "DL": 8.85},
    {"SL": 9,  "River": "Manu",         "Station": "Manu Rly Bridge(Mnr)", "Code": "MNR", "DL": 17.55},
    {"SL": 10, "River": "Manu",         "Station": "Moulvibazar Sadar(Moi)","Code": "MOI", "DL": 11.30},
    {"SL": 11, "River": "Dhalai",       "Station": "Kamalganj(Kmg)",       "Code": "KMG", "DL": 19.35},
    {"SL": 12, "River": "Jadukata",     "Station": "Laurergor(Sak)",       "Code": "SAK", "DL": 8.00},
    {"SL": 13, "River": "Piyan",        "Station": "Jaflong(Jaf)",         "Code": "JAF", "DL": 13.00},
    {"SL": 14, "River": "Sari-Gowain",  "Station": "Sarighat(Srg)",        "Code": "SRG", "DL": 12.35},
    {"SL": 15, "River": "Sari-Gowain",  "Station": "Gowainghat(Gow)",      "Code": "GOW", "DL": 10.82},
    {"SL": 16, "River": "Khowai",       "Station": "Balla",                "Code": "BAL", "DL": 21.20},
    {"SL": 17, "River": "Khowai",       "Station": "Habiganj",             "Code": "HAB", "DL": 9.00},
]

# ---------------------------------------------------------
# ৩. কাঁচা ডাটা (GR Data) পার্সিং ফাংশন
# ---------------------------------------------------------
def parse_raw_sms(text):
    data_map = {}
    lines = text.strip().split('\n')
    for line in lines:
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split('*')]
        if len(parts) >= 5:
            st_code = parts[0].upper()
            try:
                wl_6pm = float(parts[2]) / 100.0 if parts[2] != '0' else None
                wl_6am = float(parts[3]) / 100.0 if parts[3] != '0' else None
                wl_9am = float(parts[4]) / 100.0 if parts[4] != '0' else None
                rf = float(parts[5]) if len(parts) > 5 else 0.0
                
                data_map[st_code] = {
                    "wl_6pm": wl_6pm,
                    "wl_6am": wl_6am,
                    "wl_9am": wl_9am,
                    "rainfall": rf
                }
            except ValueError:
                continue
    return data_map

# ---------------------------------------------------------
# ৪. বুলেটিন ডাটাফ্রেম তৈরির ফাংশন
# ---------------------------------------------------------
def build_bulletin_df(parsed_map, selected_date):
    rows = []
    for item in STATION_MASTER_DATA:
        code = item["Code"]
        sl = item["SL"]
        river = item["River"]
        st_name = item["Station"]
        dl = item["DL"]
        
        info = parsed_map.get(code, {})
        wl_6pm = info.get("wl_6pm", None)
        wl_9am = info.get("wl_9am", None)
        rf = info.get("rainfall", "-")
        
        trend = "-"
        status_vs_dl = None
        
        if wl_6pm is not None and wl_9am is not None:
            if wl_9am > wl_6pm:
                trend = "Rising"
            elif wl_9am < wl_6pm:
                trend = "Falling"
            else:
                trend = "Steady"
                
        if wl_9am is not None:
            status_vs_dl = round(wl_9am - dl, 2)
            
        rows.append({
            "SL": sl,
            "River": river,
            "Station": st_name,
            "WL Prev Day 06.00 PM(m)": wl_6pm if wl_6pm is not None else "-",
            "WL Today 09.00 AM(m)": wl_9am if wl_9am is not None else "-",
            "Trend": trend,
            "Danger Level (m)": f"{dl:.2f}",
            "Status vs DL (m)": f"{status_vs_dl:+.2f}" if status_vs_dl is not None else "-",
            "Rainfall (mm)": rf,
            "Date": str(selected_date)
        })
    return pd.DataFrame(rows)

# ---------------------------------------------------------
# ৫. PDF জেনারেট করার ফাংশন
# ---------------------------------------------------------
def generate_pdf(df, rep_date):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter),
                            rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=14,
        alignment=1,
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'SubTitleStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        alignment=1,
        spaceAfter=10
    )
    
    elements.append(Paragraph("Daily Water Level Bulletin", title_style))
    elements.append(Paragraph(f"Date: {rep_date.strftime('%d/%m/%Y')}, Report Time: 09:00 AM", subtitle_style))
    
    # PDF এর জন্য টেবিল ডাটা প্রস্তুতকরণ
    headers = ["SL", "River", "Station", "WL Prev Day\n06.00 PM(m)", "WL Today\n09.00 AM(m)", "Trend", "Danger Level\n(m)", "Status vs\nDL (m)", "Rainfall\n(mm)"]
    table_data = [headers]
    
    for idx, row in df.iterrows():
        table_data.append([
            str(row["SL"]),
            row["River"],
            row["Station"],
            str(row["WL Prev Day 06.00 PM(m)"]),
            str(row["WL Today 09.00 AM(m)"]),
            row["Trend"],
            str(row["Danger Level (m)"]),
            str(row["Status vs DL (m)"]),
            str(row["Rainfall (mm)"])
        ])
        
    t = Table(table_data, colWidths=[30, 85, 130, 80, 80, 55, 75, 75, 55])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ---------------------------------------------------------
# ৬. ইন্টারফেস ও ইউজার ইনপুট
# ---------------------------------------------------------
st.header("১. কাঁচা ডাটা প্রবেশ করুন ও বুলেটিন তৈরি করুন")

report_date = st.date_input("তারিখ নির্বাচন করুন", date.today())
raw_input = st.text_area("please insert field data( SMS format must be: Station *Date *6PM(WL) *6AM(WL) *9AM(WL) *Rainfall(mm) (if any) ) from GR:", height=150)

col1, col2 = st.columns(2)

with col1:
    if st.button("Generate Bulletin & PDF"):
        if raw_input.strip():
            parsed_dict = parse_raw_sms(raw_input)
            df = build_bulletin_df(parsed_dict, report_date)
            st.session_state['bulletin_df'] = df
            st.success("বুলেটিন সফলভাবে তৈরি করা হয়েছে!")
        else:
            st.error("অনুগ্রহ করে GR থেকে পাওয়া ডাটা পেস্ট করুন।")

if 'bulletin_df' in st.session_state:
    df_to_show = st.session_state['bulletin_df']
    st.write("### তৈরি হওয়া বুলেটিন:")
    st.dataframe(df_to_show, use_container_width=True)
    
    # PDF ডাউনলোড বাটন
    pdf_data = generate_pdf(df_to_show, report_date)
    st.download_button(
        label="📄 Download PDF Bulletin",
        data=pdf_data,
        file_name=f"Water_Level_Bulletin_{report_date}.pdf",
        mime="application/pdf"
    )

with col2:
    if st.button("Save Bulletin to Archive"):
        if 'bulletin_df' in st.session_state and not st.session_state['bulletin_df'].empty:
            try:
                current_df = st.session_state['bulletin_df']
                existing_data = conn.read(ttl=0)
                
                if existing_data is not None and not existing_data.empty:
                    updated_df = pd.concat([existing_data, current_df], ignore_index=True)
                else:
                    updated_df = current_df
                    
                conn.update(data=updated_df)
                st.success("১৭টি স্টেশনের পুরো বুলেটিন সফলভাবে গুগল শিটে সেভ হয়েছে!")
            except Exception as e:
                st.error(f"ডাটা সেভ করতে সমস্যা হয়েছে: {e}")
        else:
            st.warning("⚠️ আগে 'Generate Bulletin & PDF' বাটনে চাপ দিয়ে বুলেটিন তৈরি করুন!")

# ---------------------------------------------------------
# ৭. সংরক্ষিত ডাটা সার্চ সেকশন
# ---------------------------------------------------------
st.divider()
st.header("২. সংরক্ষিত ডাটা সার্চ করুন (Archive Search)")

station_list = [item["Station"] for item in STATION_MASTER_DATA]

sc1, sc2 = st.columns(2)
with sc1:
    search_station = st.selectbox("স্টেশন নির্বাচন করুন", station_list)
with sc2:
    search_date = st.date_input("তারিখ নির্বাচন করুন", key="archive_search_date")

if st.button("Search Water Level"):
    try:
        data_df = conn.read(ttl="1m")
        if not data_df.empty:
            data_df['Date'] = data_df['Date'].astype(str)
            filtered_df = data_df[(data_df['Station'] == search_station) & (data_df['Date'] == str(search_date))]
            
            if not filtered_df.empty:
                st.write(f"### 📍 {search_station} স্টেশনের ফলাফল ({search_date}):")
                st.dataframe(filtered_df, use_container_width=True)
            else:
                st.warning(f"⚠️ {search_station} স্টেশনের জন্য {search_date} তারিখে কোনো তথ্য পাওয়া যায়নি।")
        else:
            st.info("আর্কাইভে এখনো কোনো ডাটা নেই।")
    except Exception as e:
        st.error(f"ডাটা লোড করতে সমস্যা হয়েছে: {e}")
          
