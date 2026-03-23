import streamlit as st
import pdfplumber
import datetime
import pandas as pd
import io
import re

def pulisci_orario(testo):
    """Estrae l'orario ignorando sporcizia nel testo."""
    if not testo: return None
    match = re.search(r'(\d{2}:\d{2})', str(testo))
    return match.group(1) if match else None

def calcola_ore_decimali(ora_in, ora_fi):
    """Calcola la differenza tra gli orari (in ore decimali)."""
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
st.title("📊 Calcolo Ore di Sfruttamento")

uploaded_files = st.file_uploader("Carica i PDF", accept_multiple_files=True, type=['pdf'])

if uploaded_files:
    tutti_i_dati = []

    for uploaded_file in uploaded_files:
        dati_giornalieri = {} 
        
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if not table: continue
                
                ultimo_giorno_valido = None # <--- LA SOLUZIONE È QUI
                
                for row in table:
                    # Evitiamo errori se la riga ha meno di 3 colonne
                    if len(row) < 3: continue

                    giorno_raw = str(row[0]).strip().replace('\n', ' ') if row[0] else ""
                    
                    # Ignoriamo le intestazioni del PDF
                    if "GIORNO" in giorno_raw.upper() or "ATTIVITA" in giorno_raw.upper(): 
                        continue
                    
                    # Se c'è almeno un numero nella colonna "Giorno" (es: "01 Mer" o "01/03/2026")
                    # lo salviamo in memoria
                    if giorno_raw and re.search(r'\d', giorno_raw):
                        ultimo_giorno_valido = giorno_raw
                    
                    # Estraiamo gli orari
                    ora_in = pulisci_orario(row[1])
                    ora_fi = pulisci_orario(row[2])
                    
                    # Se ci sono orari, li sommiamo al giorno memorizzato!
                    if ora_in and ora_fi and ultimo_giorno_valido:
                        ore_riga = calcola_ore_decimali(ora_in, ora_fi)
                        if ore_riga > 0:
                            if ultimo_giorno_valido not in dati_giornalieri:
                                dati_giornalieri[ultimo_giorno_valido] = 0.0
                            dati_giornalieri[ultimo_giorno_valido] += ore_riga

        # Terminata la lettura del file, calcoliamo Ordinario e Straordinario
        for giorno, ore_totali in dati_giornalieri.items():
            # Regole per stabilire il limite ordinario
            if "Ven" in giorno or "/03/" in giorno: 
                limite = 4.0
            # A volte "Sab" viene letto dal PDF come "Sah" per via di imperfezioni
            elif any(x in giorno for x in ["Sab", "Dom", "Sah"]): 
                limite = 0.0
            else: 
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
    
    # Visualizzazione Tabella Analitica
    st.subheader("Dettaglio Analitico (Giorni Raggruppati Correttamente)")
    st.dataframe(df, use_container_width=True)

    # Widget di riepilogo
    st.divider()
    c1, c2, c3 = st.columns(3)
    t_tot = df["Ore Totali"].sum()
    t_ord = df["Ordinario"].sum()
    t_str = df["Straordinario"].sum()

    c1.metric("TOTALI (Tutti i file)", f"{int(t_tot)}h {int(round((t_tot%1)*60))}m")
    c2.metric("DI CUI ORDINARIE", f"{int(t_ord)}h {int(round((t_ord%1)*60))}m")
    c3.metric("DI CUI STRAORDINARIO", f"{int(t_str)}h {int(round((t_str%1)*60))}m")

    # Tasto Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Calcolo_Ore')
    st.download_button("📥 Scarica Report Excel Corretto", output.getvalue(), "riepilogo_ore.xlsx")
