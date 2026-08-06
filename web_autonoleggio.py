import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# ---------------------------------------------------------
# 1. Configurazione Pagina e Layout
# ---------------------------------------------------------
st.set_page_config(
    page_title="Gestione Autonoleggio",
    page_icon="🚗",
    layout="wide"
)

st.title("🚗 Sistema Gestione Autonoleggio")
st.markdown("Gestione parco auto e prenotazioni sincronizzate con Google Sheets.")

# ---------------------------------------------------------
# 2. Connessione a Google Sheets
# ---------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def carica_dati():
    """Carica i dati dal foglio Google svuotando la cache."""
    try:
        # ttl=0 garantisce di leggere sempre i dati più aggiornati
        data = conn.read(ttl=0)
        return data
    except Exception as e:
        st.error(f"Errore durante la connessione a Google Sheets: {e}")
        return pd.DataFrame()

df = carica_dati()

# ---------------------------------------------------------
# 3. Interfaccia Principale (Tab)
# ---------------------------------------------------------
tab_registro, tab_nuovo, tab_statistiche = st.tabs([
    "📋 Registro Parco Auto", 
    "➕ Inserisci Veicolo/Noleggio", 
    "📊 Statistiche"
])

# --- TAB 1: Registro e Ricerca ---
with tab_registro:
    st.subheader("Elenco Veicoli e Prenotazioni")
    
    if not df.empty:
        # Filtri di ricerca
        col_filtro1, col_filtro2 = st.columns(2)
        with col_filtro1:
            search_query = st.text_input("🔍 Cerca per Targa o Cliente", "")
        with col_filtro2:
            stati_disponibili = ["Tutti"] + list(df["Stato"].dropna().unique()) if "Stato" in df.columns else ["Tutti"]
            filtro_stato = st.selectbox("Filtra per Stato", stati_disponibili)

        # Applicazione filtri
        df_filtrato = df.copy()
        if search_query:
            df_filtrato = df_filtrato[
                df_filtrato.astype(str).apply(lambda row: row.str.contains(search_query, case=False).any(), axis=1)
            ]
        if filtro_stato != "Tutti" and "Stato" in df_filtrato.columns:
            df_filtrato = df_filtrato[df_filtrato["Stato"] == filtro_stato]

        # Tabella dati
        st.dataframe(df_filtrato, use_container_width=True, hide_index=True)
        st.caption(f"Totale elementi visualizzati: {len(df_filtrato)}")
    else:
        st.info("Il foglio Google è vuoto o non è stato possibile caricare i dati.")

# --- TAB 2: Form Inserimento Dati ---
with tab_nuovo:
    st.subheader("Aggiungi un nuovo veicolo o aggiorna registro")
    
    with st.form("form_noleggio", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            targa = st.text_input("Targa *", placeholder="AA123BB").upper()
            modello = st.text_input("Modello Auto *", placeholder="es. Fiat Panda")
            tariffa = st.number_input("Tariffa Giornaliera (€)", min_value=0.0, step=5.0)

        with col2:
            cliente = st.text_input("Nome Cliente", placeholder="Mario Rossi")
            stato = st.selectbox("Stato Veicolo", ["Disponibile", "Noleggiata", "In Manutenzione"])
            note = st.text_area("Note aggiuntive", placeholder="Opzionale...")

        submit_button = st.form_submit_button("💾 Salva su Google Sheets")

        if submit_button:
            if not targa or not modello:
                st.warning("I campi **Targa** e **Modello Auto** sono obbligatori.")
            else:
                # Creazione del nuovo record
                nuovo_record = pd.DataFrame([{
                    "Targa": targa,
                    "Modello": modello,
                    "Cliente": cliente if cliente else "N/D",
                    "Stato": stato,
                    "Tariffa (€)": tariffa,
                    "Note": note
                }])

                # Unione con i dati esistenti e aggiornamento del foglio
                df_aggiornato = pd.concat([df, nuovo_record], ignore_index=True)
                
                try:
                    conn.update(data=df_aggiornato)
                    st.success(f"Veicolo {targa} aggiunto con successo!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore durante il salvataggio dei dati: {e}")

# --- TAB 3: Statistiche Rapide ---
with tab_statistiche:
    st.subheader("Panoramica Parco Auto")
    if not df.empty and "Stato" in df.columns:
        col_m1, col_m2, col_m3 = st.columns(3)
        
        totale_auto = len(df)
        disponibili = len(df[df["Stato"] == "Disponibile"])
        noleggiate = len(df[df["Stato"] == "Noleggiata"])
        
        col_m1.metric("Totale Veicoli", totale_auto)
        col_m2.metric("Disponibili", disponibili)
        col_m3.metric("In Noleggio", noleggiate)
    else:
        st.write("Dati insufficienti per generare le metriche.")
