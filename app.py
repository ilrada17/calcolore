import streamlit as st
import pdfplumber
import datetime
import pandas as pd

def calcola_durata(inizio, fine):
    fmt = '%H:%M'
    try:
        t_ini = datetime.datetime.strptime(inizio, fmt)
        t_fin = datetime.datetime.strptime(fine, fmt)
        if t_fin <= t_ini and t_fin.hour < 12: # Gestione scavalco mezzanotte
            delta = (t_fin + datetime.timedelta(days=1)) - t_ini
        else:
            delta = t_fin - t_ini
        return delta.total_seconds() / 3600
    except:
        return 0.0

st.title("Estrattore Ore Lavorative AM")
st.write("Carica i file PDF degli specchi riepilogativi per calcolare le ore mensili.")

uploaded_files = st.file_uploader("Scegli i file PDF", accept_multiple_files=True, type=['pdf'])

if uploaded_files:
    totale_generale = 0.0
    report_finale = []

    for uploaded_file in uploaded_files:
        ore_mensili = 0.0
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    for row in table:
                        # Identifica le colonne orario (solitamente indice 1 e 2)
                        ora_in = str(row[1]).strip() if len(row) > 1 else ""
                        ora_fi = str(row[2]).strip() if len(row) > 2 else ""
                        
                        if ":" in ora_in and ":" in ora_fi and ora_in != "00:00":
                            durata = calcola_durata(ora_in, ora_fi)
                            ore_mensili += durata
        
        totale_generale += ore_mensili
        h = int(ore_mensili)
        m = int((ore_mensili - h) * 60)
        report_finale.append({"File": uploaded_file.name, "Totale Ore": f"{h}h {m}m"})

    st.table(pd.DataFrame(report_finale))
    
    tg_h = int(totale_generale)
    tg_m = int((totale_generale - tg_h) * 60)
    st.metric("TOTALE COMPLESSIVO", f"{tg_h} ore e {tg_m} minuti")
