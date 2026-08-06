import streamlit as st
import pandas as pd
import requests
from datetime import date

# ---------------------------------------------------------
# CONFIGURAZIONE URL (Sostituisci con i tuoi link)
# ---------------------------------------------------------
# 1. URL fornito da Google Apps Script durante la distribuzione
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwyQyyVasHzYp0OPPdXj0PqHntIMyCPGDgs5fVL2DvcprhvW7jadA7aTXo7f_n2_OBBHQ/exec"

# 2. URL del tuo foglio Google per l'esportazione in CSV (sostituisci l'ID del foglio)
# Nota: Il foglio deve essere impostato su "Chiunque abbia il link può visualizzare"
SPREADSHEET_ID = "https://docs.google.com/spreadsheets/d/1hktUuKCvomCuvhbklmXs-A93usdhdouC/edit?usp=drive_link&ouid=114374870114697389870&rtpof=true&sd=true"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv"

# ---------------------------------------------------------
# 1. Setup Pagina
# ---------------------------------------------------------
st.set_page_config(page_title="Gestione Autonoleggio", page_icon="🚗", layout="wide")
st.title("🚗 Sistema Gestione Autonoleggio")

# ---------------------------------------------------------
# 2. Lettura Dati via CSV
# ---------------------------------------------------------
@st.cache_data(ttl=2) # Pulisce la cache ogni 2 secondi per dati sempre freschi
def carica_dati():
    try:
        data = pd.read_csv(CSV_URL)
        return data
    except Exception as e:
        st.error(f"Impossibile leggere il Foglio Google. Verifica che il link sia pubblico: {e}")
        return pd.DataFrame()

df = carica_dati()

# ---------------------------------------------------------
# 3. Layout a Schede (Tab)
# ---------------------------------------------------------
tab_dash, tab_registro, tab_nuovo = st.tabs([
    "📊 Dashboard & Analytics",
    "📋 Registro Parco Auto", 
    "➕ Inserisci Veicolo / Noleggio"
])

# --- TAB 1: Dashboard ---
with tab_dash:
    st.subheader("📊 Panoramica Generale")
    if not df.empty:
        df_valid = df.copy()
        df_valid["Costo Totale (€)"] = pd.to_numeric(df_valid["Costo Totale (€)"], errors='coerce').fillna(0)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Totale Veicoli", len(df_valid))
        c2.metric("In Noleggio", len(df_valid[df_valid["Stato"] == "Noleggiata"]) if "Stato" in df_valid.columns else 0)
        c3.metric("Disponibili", len(df_valid[df_valid["Stato"] == "Disponibile"]) if "Stato" in df_valid.columns else 0)
        c4.metric("Incasso Totale", f"€ {df_valid['Costo Totale (€)'].sum():,.2f}")
        
        st.divider()
        if "Categoria" in df_valid.columns:
            st.write("**Veicoli per Categoria**")
            st.bar_chart(df_valid["Categoria"].value_counts())
    else:
        st.info("Nessun dato disponibile.")

# --- TAB 2: Registro ---
with tab_registro:
    st.subheader("📋 Registro Completo")
    if not df.empty:
        search_query = st.text_input("🔍 Cerca (Targa, Marca, Cliente...)", "")
        if search_query:
            df_filtrato = df[df.astype(str).apply(lambda r: r.str.contains(search_query, case=False).any(), axis=1)]
            st.dataframe(df_filtrato, use_container_width=True, hide_index=True)
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.warning("Nessun dato trovato.")

# --- TAB 3: Nuovo Inserimento e Scrittura tramite Apps Script ---
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

        # Calcolo preventivo
        giorni = (data_fine - data_inizio).days
        giorni = 1 if giorni < 1 else giorni
        costo_totale = giorni * prezzo_giornaliero if stato == "Noleggiata" else 0.0

        if stato == "Noleggiata":
            st.info(f"📐 **Costo Calcolato:** {giorni} giorni × €{prezzo_giornaliero:.2f} = **€{costo_totale:.2f}**")

        submit = st.form_submit_button("💾 Salva su Google Sheets")

        if submit:
            if not targa or not marca or not modello:
                st.error("Compila i campi obbligatori: Targa, Marca e Modello.")
            else:
                # Payload JSON inviato a Google Apps Script
                payload = {
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
                
                # Invio HTTP POST
                try:
                    response = requests.post(APPS_SCRIPT_URL, json=payload)
                    if response.status_code == 200:
                        st.success(f"Veicolo {targa} salvato correttamente!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"Errore nella risposta dello script: {response.status_code}")
                except Exception as e:
                    st.error(f"Errore di connessione: {e}")
