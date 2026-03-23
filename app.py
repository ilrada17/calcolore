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

def calcola_ore_decimali(ora_in, ora_fi):
    if not ora_in or not ora_fi or (ora_in == "00:00" and ora_fi == "00:00"):
        return 0.0
    fmt = '%H:%M'
    try:
        t_ini = datetime.datetime.strptime(ora_in, fmt)
        t_fin = datetime.datetime.strptime(ora_fi, fmt)
        if t_fin <= t_ini:
            delta = (t_fin + datetime.timedelta(days=1)) - t_ini
        else:
            delta = t_fin - t_ini
        return delta.total_seconds() / 3600
    except:
        return 0.0

st.set_page_config(page_title="Gestione Ore Massaro", layout="wide")
st.title("📊 Calcolo Ore con Gestione Righe Multiple")

uploaded_files = st.file_uploader("Carica i PDF", accept_multiple_files=True, type=['pdf'])

if uploaded_files:
    tutti_i_dati = []

    for uploaded_file in uploaded_files:
        dati_giornalieri = {} # Dizionario per raggruppare righe per giorno
        
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if not table: continue
                
                for row in table:
                    giorno_raw = str(row[0]).strip().replace('\n', ' ')
                    # Salta righe vuote o intestazioni
                    if not giorno_raw or "GIORNO" in giorno_raw: continue
                    
                    ora_in = pulisci_orario(row[1])
                    ora_fi = pulisci_orario(row[2])
                    
                    if ora_in and ora_fi:
                        ore_riga = calcola_ore_decimali(ora_in, ora_fi)
                        if ore_riga > 0:
                            if giorno_raw not in dati_giornalieri:
                                dati_giornalieri[giorno_raw] = 0.0
                            dati_giornalieri[giorno_raw] += ore_riga

        # Ora processiamo i giorni raggruppati per questo file
        for giorno, ore_totali in dati_giornalieri.items():
            # Determina limite ordinario
            if "Ven" in giorno or "/03/" in giorno: # Venerdì
                limite = 4.0
            elif any(x in giorno for x in ["Sab", "Dom"]): # Weekend
                limite = 0.0
            else: # Lun-Gio
                limite = 8.5
            
            ordinario = min(ore_totali, limite)
            straordinario = max(0.0, ore_totali - limite)
            
            tutti_i_dati.append({
                "Mese": uploaded_file.name,
                "Giorno": giorno,
                "Ore Totali": ore_totali,
                "Ordinario": ordinario,
                "Straordinario": straordinario
            })

    df = pd.DataFrame(tutti_i_dati)
    
    # Visualizzazione Tabella
    st.subheader("Dettaglio Analitico (Giorni Raggruppati)")
    st.dataframe(df, use_container_width=True)

    # Widget di riepilogo
    st.divider()
    c1, c2, c3 = st.columns(3)
    t_tot = df["Ore Totali"].sum()
    t_ord = df["Ordinario"].sum()
    t_str = df["Straordinario"].sum()

    c1.metric("TOTALI", f"{int(t_tot)}h {int((t_tot%1)*60)}m")
    c2.metric("ORDINARIE", f"{int(t_ord)}h {int((t_ord%1)*60)}m")
    c3.metric("STRAORDINARIO", f"{int(t_str)}h {int((t_str%1)*60)}m")

    # Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Calcolo_Ore')
    st.download_button("📥 Scarica Report Excel", output.getvalue(), "riepilogo_ore.xlsx")
