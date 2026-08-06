import streamlit as st
import pandas as pd
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# ---------------------------------------------------------
# 1. Configurazione Pagina e Layout
# ---------------------------------------------------------
st.set_page_config(
    page_title="Gestione Autonoleggio & Dashboard",
    page_icon="🚗",
    layout="wide"
)

st.title("🚗 Sistema Gestione Autonoleggio & Costi")
st.markdown("Monitoraggio parco auto, calcolo preventivi e registrazioni sincronizzate su Google Sheets.")

# ---------------------------------------------------------
# 2. Connessione a Google Sheets
# ---------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def carica_dati():
    """Carica i dati dal foglio Google senza usare la cache per avere dati sempre aggiornati."""
    try:
        data = conn.read(ttl=0)
        # Assicura la presenza delle colonne base se il foglio è nuovo o vuoto
        colonne_richieste = ["Targa", "Modello", "Cliente", "Stato", "Data Inizio", "Data Fine", "Giorni", "Tariffa al Giorno (€)", "Costo Totale (€)", "Note"]
        for col in colonne_richieste:
            if col not in data.columns:
                data[col] = None
        return data
    except Exception as e:
        st.error(f"Errore durante la connessione a Google Sheets: {e}")
        return pd.DataFrame()

df = carica_dati()

# ---------------------------------------------------------
# 3. Interfaccia Principale (Tab)
# ---------------------------------------------------------
tab_dash, tab_registro, tab_nuovo = st.tabs([
    "📊 Dashboard & Analytics",
    "📋 Registro Noleggi", 
    "➕ Nuovo Noleggio & Calcolo Costi"
])

# --- TAB 1: Dashboard Analitica ---
with tab_dash:
    st.subheader("📊 Panoramica Generale e Incassi")
    
    if not df.empty and "Stato" in df.columns:
        # Pulizia tipi di dato per le metriche
        df_valid = df.copy()
        df_valid["Costo Totale (€)"] = pd.to_numeric(df_valid["Costo Totale (€)"], errors='coerce').fillna(0)
        
        totale_veicoli = len(df_valid)
        noleggiate = len(df_valid[df_valid["Stato"] == "Noleggiata"])
        disponibili = len(df_valid[df_valid["Stato"] == "Disponibile"])
        in_manutenzione = len(df_valid[df_valid["Stato"] == "In Manutenzione"])
        incasso_totale = df_valid["Costo Totale (€)"].sum()

        # Indicatori di sintesi (KPI)
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Totale Parco Auto", totale_veicoli)
        col2.metric("In Noleggio", noleggiate)
        col3.metric("Disponibili", disponibili)
        col4.metric("In Manutenzione", in_manutenzione)
        col5.metric("Incasso Totale Registrato", f"€ {incasso_totale:,.2f}")

        st.divider()

        # Grafici e Distribuzione
        g_col1, g_col2 = st.columns(2)
        
        with g_col1:
            st.write("**Distribuzione Stato Veicoli**")
            stato_counts = df_valid["Stato"].value_counts()
            st.bar_chart(stato_counts)

        with g_col2:
            st.write("**Top 5 Incassi per Modello Auto**")
            if "Modello" in df_valid.columns:
                incassi_modello = df_valid.groupby("Modello")["Costo Totale (€)"].sum().reset_index()
                incassi_modello = incassi_modello.sort_values(by="Costo Totale (€)", ascending=False).head(5)
                st.dataframe(incassi_modello, use_container_width=True, hide_index=True)
    else:
        st.info("Nessun dato disponibile per generare la dashboard.")

# --- TAB 2: Registro e Filtri ---
with tab_registro:
    st.subheader("📋 Registro Completo dei Noleggi")
    
    if not df.empty:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            search_query = st.text_input("🔍 Cerca per Targa, Cliente o Modello", "")
        with col_f2:
            stati = ["Tutti"] + [s for s in df["Stato"].dropna().unique()]
            filtro_stato = st.selectbox("Filtra per Stato Veicolo", stati)

        df_filtrato = df.copy()
        if search_query:
            df_filtrato = df_filtrato[
                df_filtrato.astype(str).apply(lambda row: row.str.contains(search_query, case=False).any(), axis=1)
            ]
        if filtro_stato != "Tutti":
            df_filtrato = df_filtrato[df_filtrato["Stato"] == filtro_stato]

        st.dataframe(df_filtrato, use_container_width=True, hide_index=True)
        st.caption(f"Record visualizzati: {len(df_filtrato)}")
    else:
        st.warning("Nessun dato trovato sul Foglio Google.")

# --- TAB 3: Nuovo Noleggio & Calcolo Costi ---
with tab_nuovo:
    st.subheader("➕ Inserisci Noleggio e Calcola Preventivo")
    
    with st.form("form_noleggio", clear_on_submit=False):
        c1, c2 = st.columns(2)
        
        with c1:
            targa = st.text_input("Targa *", placeholder="AA123BB").upper()
            modello = st.text_input("Modello Auto *", placeholder="es. Fiat Panda")
            cliente = st.text_input("Nome Cliente *", placeholder="Mario Rossi")
            stato = st.selectbox("Stato Veicolo", ["Noleggiata", "Disponibile", "In Manutenzione"])

        with c2:
            data_inizio = st.date_input("Data Inizio Noleggio", date.today())
            data_fine = st.date_input("Data Fine Noleggio", date.today())
            tariffa_giornaliera = st.number_input("Tariffa al Giorno (€) *", min_value=0.0, value=50.0, step=5.0)
            note = st.text_area("Note", placeholder="Opzionale...")

        # Calcolo dinamico dei giorni e del costo totale
        giorni_noleggio = (data_fine - data_inizio).days
        if giorni_noleggio < 1:
            giorni_noleggio = 1  # Minimo 1 giorno di addebito
            
        costo_totale = giorni_noleggio * tariffa_giornaliera

        # Box informativo preventivo
        st.info(f"📐 **Riepilogo Calcolo:** {giorni_noleggio} giorno/i × €{tariffa_giornaliera:.2f}/giorno = **Costo Totale: €{costo_totale:.2f}**")

        submit = st.form_submit_button("💾 Salva Registrazione su Google Sheets")

        if submit:
            if not targa or not modello or not cliente:
                st.error("I campi Targa, Modello e Cliente sono obbligatori.")
            elif data_fine < data_inizio:
                st.error("La data di fine noleggio non può essere precedente alla data di inizio.")
            else:
                # Creazione nuovo record
                nuovo_record = pd.DataFrame([{
                    "Targa": targa,
                    "Modello": modello,
                    "Cliente": cliente,
                    "Stato": stato,
                    "Data Inizio": str(data_inizio),
                    "Data Fine": str(data_fine),
                    "Giorni": giorni_noleggio,
                    "Tariffa al Giorno (€)": tariffa_giornaliera,
                    "Costo Totale (€)": costo_totale,
                    "Note": note
                }])

                # Unione e salvataggio su Google Sheets
                df_aggiornato = pd.concat([df, nuovo_record], ignore_index=True)
                
                try:
                    conn.update(data=df_aggiornato)
                    st.success(f"Noleggio registrato con successo! Totale: €{costo_totale:.2f}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore nel salvataggio dei dati: {e}")
