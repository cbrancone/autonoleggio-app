import streamlit as st
import pandas as pd
import requests
from datetime import date
import time

# =========================================================
# CONFIGURAZIONE PAGINA & COSTANTI
# =========================================================
st.set_page_config(page_title="Gestione Autonoleggio", layout="wide")

# INSERISCI QUI IL TUO URL DI GOOGLE APPS SCRIPT
APPS_SCRIPT_URL = "INSERISCI_QUI_IL_TUO_URL_DI_APPS_SCRIPT"

# Nomi standard delle colonne (devono corrispondere alle intestazioni del tuo Google Sheet)
COL_TARGA = "Targa"
COL_MARCA = "Marca"
COL_MODELLO = "Modello"
COL_CATEGORIA = "Categoria"
COL_PREZZO = "Prezzo"
COL_ANNO = "Anno"
COL_CLIENTE = "Cliente"
COL_STATO = "Stato"
COL_DATA_INI = "Data Inizio"
COL_DATA_FIN = "Data Fine"
COL_NOTE = "Note"
COL_COSTO = "Costo Totale"
COL_NOTE1 = "Note1"
COL_NOTE_CHECKIN = "Note Check-in"

# =========================================================
# FUNZIONE DI CARICAMENTO DATI DA GOOGLE SHEETS
# =========================================================
@st.cache_data(ttl=10)
py_cache_dummy = None # Forza la freschezza dei dati se necessario
def carica_dati():
    try:
        response = requests.get(APPS_SCRIPT_URL, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if len(data) > 1:
                headers = data[0]
                rows = data[1:]
                df = pd.DataFrame(rows, columns=headers)
                return df
    except Exception as e:
        st.error(f"Errore di connessione a Google Sheets: {e}")
    return pd.DataFrame()

def formatta_date_df(df_input):
    df_f = df_input.copy()
    for col in [COL_DATA_INI, COL_DATA_FIN]:
        if col in df_f.columns:
            df_f[col] = pd.to_datetime(df_f[col], errors='coerce').dt.strftime('%Y-%m-%d').fillna('')
    return df_f

# Caricamento del DataFrame globale
df = carica_dati()

st.title("🚗 Gestionale Flotta Autonoleggio")

# ---------------------------------------------------------
# DEFINIZIONE DEI TAB
# ---------------------------------------------------------
tab_dash, tab_rientro, tab_storico, tab_registro, tab_nuovo_veicolo, tab_nuovo_cliente = st.tabs([
    "📊 Dashboard",
    "🔑 Rientro Veicolo",
    "📜 Storico & Ricerca",
    "📋 Registro Flotta",
    "🚗 Nuovo veicolo da aggiungere",
    "👤 Inserisci Nuovo Cliente",
])

# =========================================================
# TAB 1: DASHBOARD
# =========================================================
with tab_dash:
    st.subheader("📊 Panoramica Generale della Flotta")
    if not df.empty and COL_STATO in df.columns:
        tot_veicoli = len(df)
        df['stato_p'] = df[COL_STATO].astype(str).str.strip().str.capitalize()
        disponibili = len(df[df['stato_p'] == "Disponibile"])
        noleggiate = len(df[df['stato_p'] == "Noleggiata"])
        manutenzione = len(df[df['stato_p'] == "In Manutenzione"])

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Totale Veicoli", tot_veicoli)
        col2.metric("Disponibili", disponibili)
        col3.metric("Noleggiate", noleggiate)
        col4.metric("In Manutenzione", manutenzione)
    else:
        st.info("Nessun dato statistico disponibile.")

# =========================================================
# TAB 2: RIENTRO VEICOLO
# =========================================================
with tab_rientro:
    st.subheader("🔑 Gestione Rientro Veicolo")
    if not df.empty and COL_STATO in df.columns:
        df_noleggiate = df[df[COL_STATO].astype(str).str.strip().str.capitalize() == "Noleggiata"]
        if df_noleggiate.empty:
            st.info("Nessun veicolo attualmente noleggiato.")
        else:
            opzioni_rientro = df_noleggiate.apply(
                lambda r: f"{r.get(COL_TARGA, '')} - {r.get(COL_MARCA, '')} {r.get(COL_MODELLO, '')} (Cliente: {r.get(COL_CLIENTE, 'N/D')})",
                axis=1
            ).tolist()
            
            with st.form("form_rientro"):
                auto_sel = st.selectbox("Seleziona Veicolo in Rientro", opzioni_rientro)
                nota_checkin = st.text_area("Note Check-in / Condizioni Veicolo")
                submit_rientro = st.form_submit_button("🔄 Conferma Rientro Veicolo", type="primary")

                if submit_rientro:
                    targa_r = auto_sel.split(" - ")[0]
                    try:
                        df_agg = formatta_date_df(df)
                        idx = df_agg[df_agg[COL_TARGA] == targa_r].index
                        if len(idx) > 0:
                            i = idx[0]
                            df_agg.loc[i, COL_STATO] = "Disponibile"
                            df_agg.loc[i, COL_CLIENTE] = "N/D"
                            df_agg.loc[i, COL_DATA_INI] = ""
                            df_agg.loc[i, COL_DATA_FIN] = ""
                            df_agg.loc[i, COL_COSTO] = "0.0"
                            if nota_checkin.strip() and COL_NOTE_CHECKIN in df_agg.columns:
                                df_agg.loc[i, COL_NOTE_CHECKIN] = nota_checkin.strip()

                            payload = {"action": "update_all", "rows": df_agg.fillna("").astype(str).to_dict(orient="records")}
                            res = requests.post(APPS_SCRIPT_URL, json=payload, timeout=15)
                            if res.status_code == 200 and res.json().get("status") == "success":
                                st.success(f"✅ Veicolo {targa_r} rientrato con successo ed è ora Disponibile!")
                                st.cache_data.clear()
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"Errore server: {res.text}")
                    except Exception as e:
                        st.error(f"Errore durante il rientro: {e}")

# =========================================================
# TAB 3: STORICO & RICERCA
# =========================================================
with tab_storico:
    st.subheader("📜 Storico e Ricerca Veicoli / Clienti")
    if not df.empty:
        search_query = st.text_input("Cerca per Targa, Cliente, Marca o Modello").lower()
        if search_query:
            df_filtered = df[df.astype(str).apply(lambda row: row.str.lower().str.contains(search_query).any(), axis=1)]
        else:
            df_filtered = df
        st.dataframe(df_filtered, use_container_width=True)
    else:
        st.info("Nessun dato nel registro.")

# =========================================================
# TAB 4: REGISTRO FLOTTA
# =========================================================
with tab_registro:
    st.subheader("📋 Registro Completo della Flotta")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nessun dato disponibile.")

# =========================================================
# TAB 5: NUOVO VEICOLO DA AGGIUNGERE
# =========================================================
with tab_nuovo_veicolo:
    st.subheader("🚗 Aggiungi un Nuovo Veicolo alla Flotta")

    with st.form("form_nuovo_veicolo", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            targa = st.text_input(f"{COL_TARGA} *").upper()
            marca = st.text_input(f"{COL_MARCA} *")
            modello = st.text_input(f"{COL_MODELLO} *")
            categoria = st.selectbox(COL_CATEGORIA, ["Utilitaria", "Berlina", "SUV", "Station Wagon", "Furgone"])
        with c2:
            prezzo_giornaliero = st.number_input(f"{COL_PREZZO} *", min_value=0.0, value=50.0)
            anno_imm = st.number_input(COL_ANNO, min_value=1990, max_value=2030, value=2023)
            stato = st.selectbox(f"{COL_STATO} *", ["Disponibile", "In Manutenzione"])
            note1 = st.text_input(COL_NOTE1, placeholder="Eventuali annotazioni sul veicolo...")

        submit_veicolo = st.form_submit_button("💾 Salva Nuovo Veicolo nel Foglio", type="primary")

        if submit_veicolo:
            if not targa or not marca or not modello:
                st.error("Compila i campi obbligatori: Targa, Marca e Modello.")
            else:
                payload = {
                    "action": "append",
                    COL_TARGA: str(targa),
                    COL_MARCA: str(marca),
                    COL_MODELLO: str(modello),
                    COL_CATEGORIA: str(categoria),
                    COL_PREZZO: str(prezzo_giornaliero),
                    COL_ANNO: str(int(anno_imm)),
                    COL_CLIENTE: "N/D",
                    COL_STATO: str(stato),
                    COL_DATA_INI: "",
                    COL_DATA_FIN: "",
                    COL_NOTE: "",
                    COL_COSTO: "0.0",
                    COL_NOTE1: str(note1),
                    COL_NOTE_CHECKIN: "",
                }
                try:
                    res = requests.post(APPS_SCRIPT_URL, json=payload, timeout=15)
                    res_json = res.json() if res.status_code == 200 else {}
                    if res.status_code == 200 and res_json.get("status") in ["ok", "success"]:
                        st.success(f"✅ Veicolo {targa} aggiunto con successo!")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Errore server: {res.text}")
                except Exception as e:
                    st.error(f"Errore di connessione: {e}")

# =========================================================
# TAB 6: INSERISCI NUOVO CLIENTE & ASSEGNAZIONE VEICOLO
# =========================================================
with tab_nuovo_cliente:
    st.subheader("👤 Registrazione Nuovo Cliente e Assegnazione Veicolo")

    if not df.empty:
        df_temp = df.copy()
        if COL_STATO in df_temp.columns:
            df_temp['stato_pulito'] = df_temp[COL_STATO].astype(str).str.strip().str.capitalize()
            df_disponibili = df_temp[df_temp['stato_pulito'] == "Disponibile"]
        else:
            df_disponibili = pd.DataFrame()

        if df_disponibili.empty:
            st.warning("⚠️ Al momento non ci sono veicoli con stato 'Disponibile' nel registro flotta.")
        else:
            opzioni_auto = []
            mappa_auto = {}
            for idx, r in df_disponibili.iterrows():
                t = str(r.get(COL_TARGA, ''))
                m = str(r.get(COL_MARCA, ''))
                mod = str(r.get(COL_MODELLO, ''))
                p = r.get(COL_PREZZO, 0.0)
                
                label = f"{t} - {m} {mod} (Prezzo base: €{p}/giorno)"
                opzioni_auto.append(label)
                try:
                    p_val = float(p) if pd.notna(p) and str(p) != '' else 50.0
                except:
                    p_val = 50.0
                mappa_auto[label] = (t, p_val)

            with st.form("form_nuovo_cliente", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    nome_cliente = st.text_input("Nome e Cognome Cliente *", placeholder="es. Mario Rossi")
                    auto_scelta_label = st.selectbox("Seleziona Veicolo Disponibile *", opzioni_auto)
                    prezzo_default = mappa_auto[auto_scelta_label][1] if auto_scelta_label in mappa_auto else 50.0
                    prezzo_personalizzato = st.number_input("Prezzo Giornaliero Applicato (€) *", min_value=0.0, value=float(prezzo_default))
                with c2:
                    data_inizio_cli = st.date_input("Data Inizio Noleggio *", date.today())
                    data_fine_cli = st.date_input("Data Fine Noleggio *", date.today())
                    stato_nuovo = st.selectbox("Stato Veicolo *", ["Noleggiata", "In Manutenzione", "Disponibile"], index=0)
                    note_cli = st.text_area("Note / Dettagli Cliente", placeholder="Eventuali annotazioni...")

                submit_cliente = st.form_submit_button("💾 Salva Cliente e Avvia Noleggio", type="primary")

                if submit_cliente:
                    if not nome_cliente.strip():
                        st.error("Inserisci il nome e cognome del cliente.")
                    elif not auto_scelta_label:
                        st.error("Seleziona un veicolo valido.")
                    else:
                        targa_selezionata = mappa_auto.get(auto_scelta_label)[0]
                        try:
                            df_agg = formatta_date_df(df)
                            idx_matches = df_agg[df_agg[COL_TARGA] == targa_selezionata].index

                            if len(idx_matches) > 0:
                                i = idx_matches[0]
                                giorni = (data_fine_cli - data_inizio_cli).days
                                giorni = 1 if giorni < 1 else giorni
                                costo_totale = giorni * prezzo_personalizzato

                                df_agg.loc[i, COL_STATO] = str(stato_nuovo)
                                df_agg.loc[i, COL_CLIENTE] = nome_cliente.strip()
                                df_agg.loc[i, COL_DATA_INI] = str(data_inizio_cli)
                                df_agg.loc[i, COL_DATA_FIN] = str(data_fine_cli)
                                df_agg.loc[i, COL_PREZZO] = float(prezzo_personalizzato)
                                df_agg.loc[i, COL_COSTO] = float(costo_totale)
                                if note_cli.strip() and COL_NOTE in df_agg.columns:
                                    df_agg.loc[i, COL_NOTE] = note_cli.strip()

                                rows_payload = df_agg.fillna("").astype(str).to_dict(orient="records")
                                payload = {
                                    "action": "update_all",
                                    "rows": rows_payload,
                                }

                                res = requests.post(APPS_SCRIPT_URL, json=payload, timeout=20)
                                if res.status_code == 200:
                                    res_json = res.json()
                                    if res_json.get("status") in ["ok", "success"]:
                                        st.success(f"✅ Cliente {nome_cliente} registrato e veicolo {targa_selezionata} aggiornato con successo!")
                                        st.cache_data.clear()
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error(f"Errore dal server: {res_json.get('message', 'Sconosciuto')}")
                                else:
                                    st.error(f"Errore HTTP {res.status_code}: {res.text}")
                            else:
                                st.error(f"Impossibile trovare la targa {targa_selezionata} nel database.")
                        except Exception as e:
                            st.error(f"Errore imprevisto: {e}")
    else:
        st.info("Nessun dato disponibile nel sistema.")
