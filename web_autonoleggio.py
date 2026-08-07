import streamlit as st
import pandas as pd
import requests
import time
from datetime import date

# ---------------------------------------------------------
# CONFIGURAZIONE URL
# ---------------------------------------------------------
SPREADSHEET_ID = "1-XQnKHP1vWFNcvjCdG631FrqIST4PmJ-MtIGdvFesEE"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzIMY05XhfUpztNADq1KlBC3vJxxdOGWisOdJDyrDXR2c6ZWiAiphJkL3aNvjAoBhS0-Q/exec"

# ---------------------------------------------------------
# 1. Setup Pagina
# ---------------------------------------------------------
st.set_page_config(page_title="Gestione Autonoleggio", page_icon="🚗", layout="wide")
st.title("🚗 Sistema Gestione Autonoleggio")

# ---------------------------------------------------------
# 2. Lettura Dati via CSV (con Anti-Cache)
# ---------------------------------------------------------
@st.cache_data(ttl=1)
def carica_dati():
    try:
        timestamp_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&nocache={int(time.time())}"
        data = pd.read_csv(timestamp_url)
        return data
    except Exception as e:
        st.error(f"Impossibile leggere il Foglio Google: {e}")
        return pd.DataFrame()

df = carica_dati()

# ---------------------------------------------------------
# 3. Layout a Schede (Tab)
# ---------------------------------------------------------
tab_dash, tab_registro, tab_nuovo = st.tabs([
    "📊 Dashboard & Analytics",
    "📋 Registro Parco Auto (Modificabile)", 
    "➕ Inserisci Veicolo / Noleggio"
])

# --- TAB 1: Dashboard ---
with tab_dash:
    st.subheader("📊 Panoramica Generale")
    
    if not df.empty:
        df_valid = df.copy()
        df_valid.columns = df_valid.columns.str.strip()
        
        col_costo = "Costo Totale (€)"
        if col_costo in df_valid.columns:
            valori_puliti = (
                df_valid[col_costo]
                .astype(str)
                .str.replace('€', '', regex=False)
                .str.replace(' ', '', regex=False)
                .str.replace(',', '.', regex=False)
            )
            df_valid[col_costo] = pd.to_numeric(valori_puliti, errors='coerce').fillna(0)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Totale Veicoli", len(df_valid))
        
        if "Stato" in df_valid.columns:
            noleggiati = len(df_valid[df_valid["Stato"] == "Noleggiata"])
            m2.metric("Veicoli Noleggiati", noleggiati)
        
        if col_costo in df_valid.columns:
            incasso_totale = df_valid[col_costo].sum()
            m3.metric("Incasso Totale", f"€ {incasso_totale:,.2f}")
        
        st.divider()
        
        g1, g2 = st.columns(2)
        with g1:
            if "Categoria" in df_valid.columns:
                st.write("**Veicoli per Categoria**")
                st.bar_chart(df_valid["Categoria"].value_counts())
        with g2:
            if "Stato" in df_valid.columns:
                st.write("**Stato del Parco Auto**")
                st.bar_chart(df_valid["Stato"].value_counts())
    else:
        st.info("Nessun dato disponibile nel Foglio Google.")

# --- TAB 2: Registro con Modifica e Salvataggio ---
with tab_registro:
    st.subheader("📋 Registro Completo (Modifica Diretta)")
    st.caption("💡 Puoi modificare le celle direttamente nella tabella sottostante e cliccare su **Salva Modifiche** per aggiornare il Foglio Google.")
    
    if not df.empty:
        search_query = st.text_input("🔍 Cerca nel registro", "")
        
        if search_query:
            df_filtrato = df[df.astype(str).apply(lambda r: r.str.contains(search_query, case=False).any(), axis=1)]
        else:
            df_filtrato = df.copy()

        # Tabella INTERATTIVA modificabile
        edited_df = st.data_editor(
            df_filtrato, 
            use_container_width=True, 
            hide_index=True, 
            num_rows="dynamic"
        )
        
        # Tasto per salvare le modifiche su Google Sheets
      # Tasto per salvare le modifiche su Google Sheets
        if st.button("💾 Salva Modifiche su Google Sheets", type="primary"):
            try:
                # 1. Sostituisce tutti i valori NaN / vuoti per renderli compatibili con il JSON
                df_pulito = edited_df.fillna("")
                
                payload = {
                    "action": "update_all",
                    "rows": df_pulito.to_dict(orient="records")
                }
                
                response = requests.post(APPS_SCRIPT_URL, json=payload)
                if response.status_code == 200:
                    st.success("✅ Foglio Google aggiornato con successo!")
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Errore durante il salvataggio: {response.status_code}")
            except Exception as e:
                st.error(f"Errore di connessione: {e}")
    else:
        st.warning("Nessun dato trovato.")

# --- TAB 3: Nuovo Inserimento ---
with tab_nuovo:
    st.subheader("➕ Inserisci Registrazione")
    
    with st.form("form_noleggio", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            targa = st.text_input("Targa Auto *").upper()
            marca = st.text_input("Marca *")
            modello = st.text_input("Modello *")
            categoria = st.selectbox("Categoria", ["Utilitaria", "Berlina", "SUV", "Station Wagon", "Furgone"])
            anno_imm = st.number_input("Anno immatricolazione", min_value=1990, max_value=2030, value=2023)

        with col2:
            prezzo_giornaliero = st.number_input("Prezzo Giornaliero (€) *", min_value=0.0, value=50.0)
            cliente = st.text_input("Cliente")
            stato = st.selectbox("Stato Veicolo", ["Disponibile", "Noleggiata", "In Manutenzione"])
            
            data_inizio = st.date_input("Data Inizio Noleggio", date.today())
            data_fine = st.date_input("Data Fine Noleggio", date.today())
            note = st.text_area("Note")

        giorni = (data_fine - data_inizio).days
        giorni = 1 if giorni < 1 else giorni
        costo_totale = giorni * prezzo_giornaliero if stato == "Noleggiata" else 0.0

        if stato == "Noleggiata":
            st.info(f"📐 **Costo Calcolato:** {giorni} giorni × €{prezzo_giornaliero:.2f} = **€{costo_totale:.2f}**")

        submit = st.form_submit_button("💾 Aggiungi Nuovo Veicolo")

        if submit:
            if not targa or not marca or not modello:
                st.error("Compila i campi obbligatori: Targa, Marca e Modello.")
            else:
                payload = {
                    "action": "append",
                    "Targa Auto": targa,
                    "Marca": marca,
                    "Modello": modello,
                    "Categoria": categoria,
                    "Prezzo Giornaliero": prezzo_giornaliero,
                    "Anno immatricolazione": int(anno_imm),
                    "Cliente": cliente if cliente else "N/D",
                    "Stato": stato,
                    "Data Inizio": str(data_inizio) if stato == "Noleggiata" else "",
                    "Data Fine": str(data_fine) if stato == "Noleggiata" else "",
                    "Giorni": giorni if stato == "Noleggiata" else 0,
                    "Costo Totale (€)": costo_totale,
                    "Note": note
                }
                
                try:
                    response = requests.post(APPS_SCRIPT_URL, json=payload)
                    if response.status_code == 200:
                        st.success(f"Veicolo {targa} salvato correttamente!")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Errore nella risposta dello script: {response.status_code}")
                except Exception as e:
                    st.error(f"Errore di connessione: {e}")
