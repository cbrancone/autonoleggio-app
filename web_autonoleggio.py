import streamlit as st
import pandas as pd
import requests

# Configurazione della pagina Streamlit
st.set_page_config(page_title="Gestione Autonoleggio", layout="wide")

# ==========================================
# CONFIGURAZIONE INTESTAZIONI E URL
# ==========================================
# IMPORTANTE: Questo nome deve corrispondere ESATTAMENTE 
# all'intestazione della colonna della targa nel tuo Google Sheet
COL_TARGA = "Targa" 

# Recupera l'URL di Google Apps Script dai secrets di Streamlit
APPS_SCRIPT_URL = st.secrets.get("APPS_SCRIPT_URL", "")

# URL per leggere il foglio Google come CSV (Opzionale ma consigliato per velocità)
# Sostituisci con il link di pubblicazione CSV del tuo foglio, oppure usa la lettura via API
SHEET_CSV_URL = st.secrets.get("SHEET_CSV_URL", "")

st.title("🚗 Sistema di Gestione Autonoleggio")

# ==========================================
# FUNZIONI DI UTILITY
# ==========================================
@st.cache_data(ttl=2)
def carica_dati():
    """Carica i dati dal foglio Google gestendo eventuali errori di formattazione"""
    try:
        if SHEET_CSV_URL:
            df = pd.read_csv(SHEET_CSV_URL)
            # Rimuove spazi accidentali dai nomi delle colonne
            df.columns = [str(c).strip() for c in df.columns]
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Errore durante il caricamento dei dati: {e}")
        return pd.DataFrame()

def invia_dati_a_sheets(payload):
    """Invia i dati ad Apps Script gestendo la connessione"""
    try:
        if not APPS_SCRIPT_URL:
            return {"status": "error", "message": "APPS_SCRIPT_URL non configurato nei secrets."}
        
        response = requests.post(APPS_SCRIPT_URL, json=payload)
        return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Caricamento dati iniziale
df_noleggiate = carica_dati()

# ==========================================
# INTERFACCIA UTENTE (MENU)
# ==========================================
menu = st.sidebar.selectbox("Navigazione", ["Rientro / Gestione Veicoli", "Inserisci Nuova Registrazione"])

if menu == "Rientro / Gestione Veicoli":
    st.header("📋 Gestione e Rientro Veicoli")
    
    # 🛡️ CONTROLLO DIFENSIVO: Evita il KeyError controllando se il DF non è vuoto 
    # e se la colonna della targa esiste realmente tra le intestazioni.
    if not df_noleggiate.empty and COL_TARGA in df_noleggiate.columns:
        
        # Estrae le targhe disponibili in modo sicuro
        targhe_disponibili = df_noleggiate[COL_TARGA].dropna().astype(str).unique()
        
        if len(targhe_disponibili) > 0:
            targa_selezionata = st.selectbox("Seleziona Targa Veicolo", targhe_disponibili)
            
            # Filtro sicuro protetto da KeyError
            df_filtrato = df_noleggiate[df_noleggiate[COL_TARGA].astype(str) == str(targa_selezionata)]
            
            st.write("Dettagli veicolo selezionato:")
            st.dataframe(df_filtrato, use_container_width=True)
            
            # Pulsante per confermare modifiche o rientro
            if st.button("Conferma e Salva Aggiornamenti"):
                # Pulisce completamente il DataFrame da valori NaN o None prima dell'invio
                df_pulito = df_noleggiate.fillna("")
                
                payload = {
                    "action": "update_all",
                    "rows": df_pulito.to_dict(orient="records")
                }
                
                with st.spinner("Salvataggio in corso su Google Sheets..."):
                    risultato = invia_dati_a_sheets(payload)
                    
                if risultato.get("status") == "success":
                    st.success("Dati aggiornati correttamente su Google Sheets!")
                    st.cache_data.clear() # Pulisce la cache per ricaricare i dati freschi
                    st.rerun()
                else:
                    st.error(f"Errore dal server: {risultato.get('message')}")
        else:
            st.info("Nessuna targa trovata all'interno del registro.")
            
    else:
        # Messaggio chiaro se la colonna non corrisponde o il foglio è vuoto
        st.warning(f"⚠️ Impossibile trovare la colonna '{COL_TARGA}' nel DataFrame o il registro è vuoto.")
        st.info("Controlla che la prima riga del tuo Google Sheet contenga esattamente il nome della colonna impostato in `COL_TARGA`.")

elif menu == "Inserisci Nuova Registrazione":
    st.header("➕ Inserisci Nuova Registrazione")
    
    with st.form("form_inserimento"):
        # Adatta questi campi in base alle colonne del tuo foglio
        targa_input = st.text_input("Targa del Veicolo")
        modello_input = st.text_input("Modello / Descrizione")
        
        submit_btn = st.form_submit_button("Registra su Google Sheets")
        
        if submit_btn:
            if not targa_input:
                st.warning("Inserisci almeno la targa.")
            else:
                payload = {
                    "action": "append",
                    "Targa": targa_input,
                    "Modello": modello_input
                }
                
                with st.spinner("Invio in corso..."):
                    risultato = invia_dati_a_sheets(payload)
                    
                if risultato.get("status") == "success":
                    st.success("Nuova registrazione aggiunta con successo!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Errore: {risultato.get('message')}")
