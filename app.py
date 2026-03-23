import streamlit as st
import pdfplumber
import datetime
import pandas as pd
import io
import re

def pulisci_orario(testo):
    """Estrae il formato HH:MM da una stringa sporca."""
    if not testo: return None
    match = re.search(r'(\d{2}:\d{2})', str(testo))
    return match.group(1) if match else None

def calcola_durata(inizio, fine):
    """Calcola la differenza tra orari gestendo il passaggio del giorno."""
    if not inizio or not fine or inizio == "00:00" and fine == "00:00":
        return 0.0
    
    fmt = '%H:%M'
    try:
        t_ini = datetime.datetime.strptime(inizio, fmt)
        t_fin = datetime.datetime.strptime(fine, fmt)
        
        if t_fin <= t_ini:
            # Se l'ora di fine è minore o uguale, assumiamo sia il giorno dopo (es. 20:00 - 04:00)
            delta = (t_fin + datetime.timedelta(days=1)) - t_ini
        else:
            delta = t_fin - t_ini
        return delta.total_seconds() / 3600
    except:
        return 0.0

st.set_page_config(page_title="Calcolo Ore Militari", layout="wide")
st.title("🛩️ Estrattore Ore Lavorative Massaro")
st.write("Carica i tuoi specchi riepilogativi PDF per un calcolo esatto.")

uploaded_files = st.file_uploader("Trascina qui i file PDF", accept_multiple_files=True, type=['pdf'])

if uploaded_files:
    dati_finali = []
    totale_generale_ore = 0.0

    for uploaded_file in uploaded_files:
        ore_file = 0.0
        nome_mese = uploaded_file.name
        
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if not table: continue
                
                for row in table:
                    # Filtriamo le righe: cerchiamo orari nelle prime 3 colonne
                    # Spesso l'orario è in row[1] e row[2] o row[1] contiene entrambi
                    candidato_in = pulisci_orario(row[1]) if len(row) > 1 else None
                    candidato_fi = pulisci_orario(row[2]) if len(row) > 2 else None
                    
                    if candidato_in and candidato_fi:
                        durata = calcola_durata(candidato_in, candidato_fi)
                        ore_file += durata

        h_mese = int(ore_file)
        m_mese = int((ore_file - h_mese) * 60)
        dati_finali.append({"File": nome_mese, "Ore Decimali": round(ore_file, 2), "Formato H:M": f"{h_mese}h {m_mese}m"})
        totale_generale_ore += ore_file

    # Visualizzazione Risultati
    df = pd.DataFrame(dati_finali)
    st.subheader("Riepilogo per Mese")
    st.table(df)

    # Calcolo Totale Finale
    tg_h = int(totale_generale_ore)
    tg_m = int((totale_generale_ore - tg_h) * 60)
    
    st.divider()
    c1, c2 = st.columns(2)
    c1.metric("ORE TOTALI COMPLESSIVE", f"{tg_h}h {tg_m}m")
    
    # Bottone per Scaricare Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Ore_Lavorate')
    
    st.download_button(
        label="📥 Scarica Report Excel",
        data=output.getvalue(),
        file_name="riepilogo_ore_massaro.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
