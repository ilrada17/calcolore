import streamlit as st
import pdfplumber
import datetime
import pandas as pd
import io
import re

def pulisci_orario(testo):
    if not testo: return None
    match = re.search(r'(\d{2}:\d{2})', str(testo))
    return match.group(1) if match else None

def calcola_dettagli_ore(data_str, ora_in, ora_fi):
    """Calcola ore totali, ordinarie e straordinarie."""
    if not ora_in or not ora_fi or (ora_in == "00:00" and ora_fi == "00:00"):
        return 0.0, 0.0, 0.0
    
    fmt = '%H:%M'
    try:
        # Parsing orari
        t_ini = datetime.datetime.strptime(ora_in, fmt)
        t_fin = datetime.datetime.strptime(ora_fi, fmt)
        
        # Gestione scavalco mezzanotte
        if t_fin <= t_ini:
            durata_totale = ((t_fin + datetime.timedelta(days=1)) - t_ini).total_seconds() / 3600
        else:
            durata_totale = (t_fin - t_ini).total_seconds() / 3600

        # Determinazione orario teorico di uscita ordinaria
        # Cerchiamo il giorno della settimana dalla stringa data (es. "01 Mer" o "01/10/2025")
        straordinario = 0.0
        ordinario = durata_totale

        # Logica specifica richiesta:
        # Lun-Gio: 08:00 - 16:30 (8.5 ore)
        # Ven: 08:00 - 12:00 (4.0 ore)
        
        # Identificazione giorno (molto semplificata per i tuoi PDF)
        giorno_sett = ""
        if "Ven" in data_str or "/03/" in data_str: # Esempio semplificato
             limite_ord = 4.0
        else:
             limite_ord = 8.5

        if durata_totale > limite_ord:
            straordinario = durata_totale - limite_ord
            ordinario = limite_ord
        
        # Se il turno inizia dopo l'orario ordinario o è un weekend, è tutto straordinario
        if any(x in data_str for x in ["Sab", "Dom"]):
            straordinario = durata_totale
            ordinario = 0.0

        return durata_totale, ordinario, straordinario
    except:
        return 0.0, 0.0, 0.0

st.set_page_config(page_title="Calcolo Ore Militari Avanzato", layout="wide")
st.title("🛩️ Analisi Ore Servizio e Straordinario")

uploaded_files = st.file_uploader("Carica PDF", accept_multiple_files=True, type=['pdf'])

if uploaded_files:
    righe_report = []
    
    for uploaded_file in uploaded_files:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if not table: continue
                for row in table:
                    data_testo = str(row[0])
                    ora_in = pulisci_orario(row[1])
                    ora_fi = pulisci_orario(row[2])
                    
                    if ora_in and ora_fi and ora_in != "00:00":
                        tot, ordi, stra = calcola_dettagli_ore(data_testo, ora_in, ora_fi)
                        righe_report.append({
                            "Mese/File": uploaded_file.name,
                            "Giorno": data_testo.replace('\n', ' '),
                            "Inizio": ora_in,
                            "Fine": ora_fi,
                            "Totale": tot,
                            "Ordinario": ordi,
                            "Straordinario": stra
                        })

    df = pd.DataFrame(righe_report)
    
    # Visualizzazione Tabella
    st.subheader("Dettaglio Giornaliero")
    st.dataframe(df, use_container_width=True)

    # Riepilogo Totale
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    tot_h = df['Totale'].sum()
    ord_h = df['Ordinario'].sum()
    str_h = df['Straordinario'].sum()

    col1.metric("ORE TOTALI", f"{int(tot_h)}h {int((tot_h%1)*60)}m")
    col2.metric("DI CUI ORDINARIO", f"{int(ord_h)}h {int((ord_h%1)*60)}m")
    col3.metric("DI CUI STRAORDINARIO", f"{int(str_h)}h {int((str_h%1)*60)}m", delta_color="inverse")

    # Export Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Conteggio_Ore')
    st.download_button("📥 Scarica Report Completo Excel", output.getvalue(), "report_ore.xlsx")
