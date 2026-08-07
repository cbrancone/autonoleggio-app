import uuid
import time
from datetime import date
import pandas as pd
import requests
import streamlit as st

# ---------------------------------------------------------
# CONFIGURAZIONE (Usa st.secrets oppure inserisci qui i tuoi link)
# ---------------------------------------------------------
SPREADSHEET_ID = st.secrets.get("SPREADSHEET_ID", "IL_TUO_SPREADSHEET_ID")
APPS_SCRIPT_URL = st.secrets.get("APPS_SCRIPT_URL", "IL_TUO_APPS_SCRIPT_URL")

st.set_page_config(page_title="Gestione Autonoleggio", page_icon="🚗", layout="wide")
st.title("🚗 Sistema Gestione Autonoleggio")

# ---------------------------------------------------------
# HELPER E CARICAMENTO DATI
# ---------------------------------------------------------
def formatta_date(df):
    df_out = df.copy()
    colonne_date = ["Data Inizio", "Data Fine", "Data Inizio Noleggio"]
    for col in colonne_date:
        if col in df_out.columns:
            df_out[col] = pd.to_datetime(df_out[col], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    return df_out

@st.cache_data(ttl=60)
def carica_dati_fogli():
    try:
        # Usa URL encoding per gli spazi nei nomi dei fogli
        url_parco = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=Parco%20Auto"
        url_storico = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=Storico%20Noleggi"
        
        df_parco = pd.read_csv(url_parco)
        df_storico = pd.read_csv(url_storico)
        
        # Pulisci e converti i costi nello storico se esistono
        if "Costo Totale (€)" in df_storico.columns:
            valori_puliti = df_storico["Costo Totale (€)"].astype(str).str.replace("€", "").str.replace(",", ".")
            df_storico["Costo Totale (€)"] = pd.to_numeric(valori_puliti, errors="coerce").fillna(0.0)
            
        return df_parco, df_storico
    except Exception as e:
        st.warning("Impossibile caricare i dati. Assicurati che il Foglio Google abbia due schede nominate esattamente 'Parco Auto' e 'Storico Noleggi'.")
        return pd.DataFrame(), pd.DataFrame()

df_parco, df_storico = carica_dati_fogli()

# ---------------------------------------------------------
# LAYOUT A TAB
# ---------------------------------------------------------
tab_dash, tab_rientro, tab_storico, tab_registro, tab_nuovo = st.tabs([
    "📊 Dashboard", "🔑 Rientro", "📜 Storico Noleggi", "📋 Parco Auto", "➕ Nuovo"
])

# =========================================================
# TAB 1: DASHBOARD
# =========================================================
with tab_dash:
    st.subheader("📊 Panoramica & Statistiche")
    if not df_parco.empty:
        tot_veicoli = len(df_parco)
        noleggiati = len(df_parco[df_parco.get("Stato", "") == "Noleggiata"])
        tasso = (noleggiati / tot_veicoli * 100) if tot_veicoli > 0 else 0
        
        incasso_totale = df_storico["Costo Totale (€)"].sum() if not df_storico.empty else 0.0
        noleggi_totali = len(df_storico) if not df_storico.empty else 0
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Veicoli Totali", tot_veicoli)
        k2.metric("In Noleggio", noleggiati)
        k3.metric("Tasso Occupazione", f"{tasso:.1f}%")
        k4.metric("Incasso Storico", f"€ {incasso_totale:,.2f}")
        
        st.divider()
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.write("📊 **Stato Flotta Attuale**")
            if "Stato" in df_parco.columns:
                st.bar_chart(df_parco["Stato"].value_counts())
        with col_g2:
            st.write("📈 **Noleggi Conclusi per Targa**")
            if not df_storico.empty and "Targa Auto" in df_storico.columns:
                st.bar_chart(df_storico["Targa Auto"].value_counts())

# =========================================================
# TAB 2: RIENTRO VEICOLO
# =========================================================
with tab_rientro:
    st.subheader("🔑 Check-in e Rientro Veicolo")
    
    if not df_parco.empty and "Stato" in df_parco.columns:
        df_noleggiate = df_parco[df_parco["Stato"] == "Noleggiata"]
        
        if df_noleggiate.empty:
            st.success("Tutto il parco auto è attualmente disponibile o in manutenzione.")
        else:
            opzioni = df_noleggiate.apply(lambda r: f"{r.get('Targa Auto', '')} - {r.get('Marca', '')} ({r.get('Cliente Attuale', 'N/D')})", axis=1).tolist()
            scelta = st.selectbox("Seleziona il veicolo da far rientrare:", opzioni)
            
            if scelta:
                targa_sel = scelta.split(" - ")[0]
                v = df_noleggiate[df_noleggiate["Targa Auto"] == targa_sel].iloc[0]
                
                c1, c2 = st.columns(2)
                c1.markdown(f"**Targa:** {v.get('Targa Auto', '')} | **Cliente:** {v.get('Cliente Attuale', '')}")
                
                data_inizio_str = v.get("Data Inizio Noleggio", "")
                data_inizio_dt = pd.to_datetime(data_inizio_str, errors="coerce")
                
                c2.markdown(f"**Data Uscita:** {data_inizio_str}")
                prezzo = float(v.get("Prezzo Giornaliero", 0.0))
                
                st.divider()
                r1, r2 = st.columns(2)
                with r1:
                    nuovo_stato = st.selectbox("Nuovo Stato Veicolo", ["Disponibile", "In Manutenzione"])
                    data_rientro = st.date_input("Data Rientro Effettiva", date.today())
                with r2:
                    note_rientro = st.text_area("Note Check-in (Danni, Km, ecc.)")
                
                # Calcolo Dinamico
                if pd.notna(data_inizio_dt):
                    giorni = (data_rientro - data_inizio_dt.date()).days
                    giorni = 1 if giorni < 1 else giorni
                else:
                    giorni = 1
                    
                costo_totale = giorni * prezzo
                st.info(f"📐 **Calcolo:** {giorni} gg × €{prezzo:.2f} = **€ {costo_totale:.2f}**")
                
                if st.button("➕ Registra Rientro nello Storico", type="primary"):
                    record_storico = {
                        "id_noleggio": str(uuid.uuid4())[:8].upper(),
                        "targa": targa_sel,
                        "cliente": v.get("Cliente Attuale", "N/D"),
                        "data_inizio": str(data_inizio_dt.date()) if pd.notna(data_inizio_dt) else "",
                        "data_fine": str(data_rientro),
                        "giorni": int(giorni),
                        "costo_totale": float(costo_totale),
                        "note": note_rientro.strip()
                    }
                    
                    payload = {
                        "action": "registra_rientro",
                        "noleggio": record_storico,
                        "nuovo_stato": nuovo_stato
                    }
                    
                    try:
                        res = requests.post(APPS_SCRIPT_URL, json=payload)
                        if res.status_code == 200:
                            st.success(f"✅ Rientro salvato! Auto {targa_sel} ora {nuovo_stato}.")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Errore Server: {res.status_code}")
                    except Exception as e:
                        st.error(f"Errore Connessione: {e}")

# =========================================================
# TAB 3: STORICO NOLEGGI
# =========================================================
with tab_storico:
    st.subheader("📜 Archivio Storico Noleggi")
    if not df_storico.empty:
        cerca = st.text_input("🔍 Cerca Targa o Cliente nello storico")
        df_s = df_storico.copy()
        
        if cerca:
            mask = df_s.astype(str).apply(lambda r: r.str.contains(cerca, case=False).any(), axis=1)
            df_s = df_s[mask]
            
        df_disp = formatta_date(df_s)
        st.dataframe(df_disp, use_container_width=True, hide_index=True)
    else:
        st.info("Nessun dato nello Storico Noleggi. Registra il primo rientro per popolarlo!")

# =========================================================
# TAB 4: REGISTRO PARCO AUTO
# =========================================================
with tab_registro:
    st.subheader("📋 Gestione Flotta Attiva")
    
    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = False
        
    if not df_parco.empty:
        if not st.session_state.edit_mode:
            if st.button("✏️ Abilita Modifica Tabella"):
                st.session_state.edit_mode = True
                st.rerun()
            st.dataframe(formatta_date(df_parco), use_container_width=True, hide_index=True)
        else:
            c1, c2 = st.columns([2, 8])
            if c1.button("💾 Salva Modifiche", type="primary"):
                # Salva i dati
                df_clean = st.session_state.edited_data.fillna("")
                payload = {"action": "update_parco", "rows": df_clean.to_dict(orient="records")}
                try:
                    r = requests.post(APPS_SCRIPT_URL, json=payload)
                    if r.status_code == 200:
                        st.success("Salvataggio completato!")
                        st.session_state.edit_mode = False
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")
            if c2.button("❌ Annulla"):
                st.session_state.edit_mode = False
                st.rerun()
                
            st.session_state.edited_data = st.data_editor(formatta_date(df_parco), use_container_width=True, hide_index=True)
    else:
        st.warning("Parco Auto vuoto.")

# =========================================================
# TAB 5: NUOVO VEICOLO
# =========================================================
with tab_nuovo:
    st.subheader("➕ Inserisci Nuovo Veicolo in Flotta")
    
    with st.form("form_nuovo_veicolo", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            targa = st.text_input("Targa Auto *").upper()
            marca = st.text_input("Marca *")
            modello = st.text_input("Modello *")
            cat = st.selectbox("Categoria", ["Utilitaria", "Berlina", "SUV", "Furgone"])
            anno = st.number_input("Anno", 1990, 2030, 2024)
        with c2:
            prezzo = st.number_input("Prezzo Giornaliero Base (€) *", min_value=0.0, value=50.0)
            stato = st.selectbox("Stato Iniziale", ["Disponibile", "In Manutenzione"])
            note = st.text_area("Note aggiuntive")
            
        submitted = st.form_submit_button("💾 Aggiungi alla Flotta")
        
        if submitted:
            if not targa or not marca or not modello:
                st.error("Compila Targa, Marca e Modello.")
            else:
                row_data = {
                    "Targa Auto": targa, "Marca": marca, "Modello": modello,
                    "Categoria": cat, "Anno": int(anno), "Prezzo Giornaliero": float(prezzo),
                    "Stato": stato, "Cliente Attuale": "N/D", "Data Inizio Noleggio": "", "Note": note
                }
                
                payload = {"action": "append_parco", "row": row_data}
                try:
                    req = requests.post(APPS_SCRIPT_URL, json=payload)
                    if req.status_code == 200:
                        st.success("Veicolo aggiunto con successo!")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")
