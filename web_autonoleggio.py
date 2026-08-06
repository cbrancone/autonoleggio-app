import streamlit as st
import pandas as pd
from datetime import datetime, date
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
st.markdown("Monitoraggio parco auto, preventivi noleggio e sync con Google Sheets.")

# ---------------------------------------------------------
# 2. Connessione a Google Sheets
# ---------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def carica_dati():
    """Carica i dati dal foglio Google garantendo la presenza delle colonne corrette."""
    try:
        data = conn.read(ttl=0)
        # Nomi colonne esatti basati sul tuo foglio + colonne per la gestione noleggio
        colonne_richieste = [
            "Targa Auto", "Marca", "Modello", "Categoria", 
            "Prezzo Giornaliero", "Anno immatricolazione", 
            "Cliente", "Stato", "Data Inizio", "Data Fine", 
            "Giorni", "Costo Totale (€)", "Note"
        ]
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
    "📋 Registro Parco Auto", 
    "➕ Inserisci Veicolo / Noleggio"
])

# --- TAB 1: Dashboard Analitica ---
with tab_dash:
    st.subheader("📊 Panoramica Parco Auto e Incassi")
    
    if not df.empty:
        df_valid = df.copy()
        df_valid["Costo Totale (€)"] = pd.to_numeric(df_valid["Costo Totale (€)"], errors='coerce').fillna(0)
        df_valid["Prezzo Giornaliero"] = pd.to_numeric(df_valid["Prezzo Giornaliero"], errors='coerce').fillna(0)
        
        totale_veicoli = len(df_valid)
        noleggiate = len(df_valid[df_valid["Stato"] == "Noleggiata"]) if "Stato" in df_valid.columns else 0
        disponibili = len(df_valid[df_valid["Stato"] == "Disponibile"]) if "Stato" in df_valid.columns else 0
        in_manutenzione = len(df_valid[df_valid["Stato"] == "In Manutenzione"]) if "Stato" in df_valid.columns else 0
        incasso_totale = df_valid["Costo Totale (€)"].sum()

        # Indicatori principali (KPI)
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Totale Veicoli", totale_veicoli)
        col2.metric("In Noleggio", noleggiate)
        col3.metric("Disponibili", disponibili)
        col4.metric("In Manutenzione", in_manutenzione)
        col5.metric("Incasso Totale", f"€ {incasso_totale:,.2f}")

        st.divider()

        # Grafici
        g_col1, g_col2 = st.columns(2)
        
        with g_col1:
            st.write("**Distribuzione Veicoli per Categoria**")
            if "Categoria" in df_valid.columns and not df_valid["Categoria"].dropna().empty:
                cat_counts = df_valid["Categoria"].value_counts()
                st.bar_chart(cat_counts)
            else:
                st.info("Nessuna categoria registrata.")

        with g_col2:
            st.write("**Distribuzione per Stato Veicolo**")
            if "Stato" in df_valid.columns and not df_valid["Stato"].dropna().empty:
                stato_counts = df_valid["Stato"].value_counts()
                st.bar_chart(stato_counts)
            else:
                st.info("Nessun stato registrato.")
    else:
        st.info("Nessun dato disponibile per generare la dashboard.")

# --- TAB 2: Registro e Filtri ---
with tab_registro:
    st.subheader("📋 Registro Completo Veicoli e Noleggi")
    
    if not df.empty:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            search_query = st.text_input("🔍 Cerca per Targa Auto, Marca, Modello o Cliente", "")
        with col_f2:
            stati = ["Tutti"] + [s for s in df["Stato"].dropna().unique()] if "Stato" in df.columns else ["Tutti"]
            filtro_stato = st.selectbox("Filtra per Stato Veicolo", stati)

        df_filtrato = df.copy()
        if search_query:
            df_filtrato = df_filtrato[
                df_filtrato.astype(str).apply(lambda row: row.str.contains(search_query, case=False).any(), axis=1)
            ]
        if filtro_stato != "Tutti" and "Stato" in df_filtrato.columns:
            df_filtrato = df_filtrato[df_filtrato["Stato"] == filtro_stato]

        st.dataframe(df_filtrato, use_container_width=True, hide_index=True)
        st.caption(f"Totale elementi: {len(df_filtrato)}")
    else:
        st.warning("Nessun dato presente nel Foglio Google.")

# --- TAB 3: Inserimento Veicolo/Noleggio & Calcolo Costi ---
with tab_nuovo:
    st.subheader("➕ Registra Nuovo Veicolo o Noleggio")
    
    with st.form("form_noleggio", clear_on_submit=False):
        c1, c2 = st.columns(2)
        
        with c1:
            targa = st.text_input("Targa Auto *", placeholder="AA123BB").upper()
            marca = st.text_input("Marca *", placeholder="es. Fiat")
            modello = st.text_input("Modello *", placeholder="es. Panda")
            categoria = st.selectbox("Categoria", ["Utilitaria", "Berlina", "SUV", "Station Wagon", "Furgone", "Altro"])
            anno_imm = st.number_input("Anno immatricolazione", min_value=1990, max_value=2030, value=2023, step=1)

        with c2:
            prezzo_giornaliero = st.number_input("Prezzo Giornaliero (€) *", min_value=0.0, value=50.0, step=5.0)
            cliente = st.text_input("Cliente", placeholder="Mario Rossi (opzionale)")
            stato = st.selectbox("Stato Veicolo", ["Disponibile", "Noleggiata", "In Manutenzione"])
            
            data_inizio = st.date_input("Data Inizio Noleggio", date.today())
            data_fine = st.date_input("Data Fine Noleggio", date.today())
            note = st.text_area("Note", placeholder="Note opzionali...")

        # Calcolo dei giorni e del costo totale
        giorni_noleggio = (data_fine - data_inizio).days
        if giorni_noleggio < 1:
            giorni_noleggio = 1  # Minimo 1 giorno
            
        costo_totale = giorni_noleggio * prezzo_giornaliero if stato == "Noleggiata" else 0.0

        if stato == "Noleggiata":
            st.info(f"📐 **Riepilogo Costo:** {giorni_noleggio} giorno/i × €{prezzo_giornaliero:.2f}/giorno = **Costo Totale: €{costo_totale:.2f}**")

        submit = st.form_submit_button("💾 Salva su Google Sheets")

        if submit:
            if not targa or not marca or not modello:
                st.error("I campi Targa Auto, Marca e Modello sono obbligatori.")
            elif data_fine < data_inizio and stato == "Noleggiata":
                st.error("La data di fine noleggio non può essere precedente alla data di inizio.")
            else:
                # Mappatura dei dati corrispondente alle colonne del foglio
                nuovo_record = pd.DataFrame([{
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
                    "Giorni": giorni_noleggio if stato == "Noleggiata" else 0,
                    "Costo Totale (€)": costo_totale,
                    "Note": note
                }])

                # Unione e aggiornamento
                df_aggiornato = pd.concat([df, nuovo_record], ignore_index=True)
                
                try:
                    conn.update(data=df_aggiornato)
                    st.success(f"Veicolo {targa} salvato con successo!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore durante il salvataggio: {e}")
