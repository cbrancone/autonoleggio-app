import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Configurazione pagina
st.set_page_config(page_title="Gestione Autonoleggio", layout="wide", page_icon="🚗")

st.title("🚗 Gestione Autonoleggio")

# Inizializzazione della connessione a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Lettura dei dati con cache di 1 minuto per evitare troppe chiamate API
try:
    df = conn.read(ttl="1m")
except Exception as e:
    st.error("Impossibile connettersi a Google Sheets. Verifica i tuoi Secrets.")
    st.stop()

# Interfaccia a schede
tab_visualizza, tab_aggiungi = st.tabs(["📋 Registro Noleggi", "➕ Nuovo Noleggio"])

with tab_visualizza:
    st.subheader("Dati attuali dal Foglio Google")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Il foglio di calcolo è vuoto o non contiene intestazioni.")

with tab_aggiungi:
    st.subheader("Aggiungi una nuova prenotazione o veicolo")
    
    with st.form("form_noleggio", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            targa = st.text_input("Targa")
            modello = st.text_input("Modello Auto")
        with col2:
            cliente = st.text_input("Nome Cliente")
            stato = st.selectbox("Stato", ["Disponibile", "Noleggiata", "In Manutenzione"])

        submitted = st.form_submit_button("Salva su Google Sheets")

        if submitted:
            if targa and modello:
                # Crea la nuova riga
                nuova_riga = pd.DataFrame([{
                    "Targa": targa,
                    "Modello": modello,
                    "Cliente": cliente,
                    "Stato": stato
                }])

                # Unisci i dati esistenti con la nuova riga e aggiorna il foglio
                df_aggiornato = pd.concat([df, nuova_riga], ignore_index=True)
                conn.update(data=df_aggiornato)

                st.success("Dati salvati con successo!")
                st.rerun()
            else:
                st.warning("Inserisci almeno Targa e Modello.")
