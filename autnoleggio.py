import streamlit as st
import pandas as pd
import requests
from datetime import date
import time

# =========================================================
# CONFIGURAZIONE COSTANTI (Allineate esattamente al foglio)
# =========================================================
# Inserisci qui l'URL della tua Web App di Google Apps Script
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyKMhlDddoULMNfyx_1sdV_63rEofWq-U2hyzIfVs1yao-Gy5NFuH5f41WWKbJoHitT/exec"

COL_TARGA = "TARGA"
COL_MARCA = "MARCA"
COL_MODELLO = "MODELLO"
COL_CATEGORIA = "CATEGORIA"
COL_PREZZO = "PREZZO GIORNALIERO (€)"
COL_ANNO = "Anno Immatricolazione"
COL_CLIENTE = "Cliente"
COL_STATO = "Stato Veicolo"
COL_DATA_INI = "Data Inizio Noleggio"
COL_DATA_FIN = "Data Fine Noleggio"
COL_NOTE = "Note"
COL_COSTO = "Costo Totale"
COL_NOTE1 = "Note1"
COL_NOTE_CHECKIN = "Note Check In"
COL_KM_INIZIALI = "KM_INIZIALI"
COL_KM_FINALI = "KM_FINALI"
COL_PAGAMENTO = "PAGAMENTO"
COL_CAUZIONE = "CAUZIONE"
# =========================================================
# FUNZIONE DI CARICAMENTO DATI DA GOOGLE SHEETS
# =========================================================
@st.cache_data(ttl=10)
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
    
    if not df.empty:
        # Pulizia dello stato per i calcoli
        df_dash = df.copy()
        c_stato = COL_STATO if COL_STATO in df_dash.columns else "Stato"
        c_categoria = COL_CATEGORIA if COL_CATEGORIA in df_dash.columns else "Categoria"
        c_costo = COL_COSTO if COL_COSTO in df_dash.columns else "Costo Totale"
        
        if c_stato in df_dash.columns:
            df_dash['stato_p'] = df_dash[c_stato].astype(str).str.strip().str.capitalize()
            tot_veicoli = len(df_dash)
            disponibili = len(df_dash[df_dash['stato_p'] == "Disponibile"])
            noleggiate = len(df_dash[df_dash['stato_p'].isin(["Noleggiata", "Noleggiato", "In Uso"])])
            manutenzione = len(df_dash[df_dash['stato_p'].isin(["In Manutenzione", "Manutenzione"])])
        else:
            tot_veicoli = len(df_dash)
            disponibili = noleggiate = manutenzione = 0

        # Calcolo del fatturato totale stimato dai noleggi attivi
        fatturato_totale = 0.0
        if c_costo in df_dash.columns:
            try:
                fatturato_totale = pd.to_numeric(df_dash[c_costo], errors='coerce').sum()
            except:
                fatturato_totale = 0.0

        # Mostra le metriche principali in alto
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("🚗 Totale Veicoli", tot_veicoli)
        col2.metric("🟢 Disponibili", disponibili)
        col3.metric("🔵 Noleggiate", noleggiate)
        col4.metric("🟠 In Manutenzione", manutenzione)
        col5.metric("💶 Fatturato Attivo", f"€ {fatturato_totale:,.2f}")

        st.markdown("---")

        # Visualizzazioni grafiche dettagliate con Streamlit
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.markdown("### 📊 Stato dei Veicoli in Flotta")
            if c_stato in df_dash.columns:
                df_stati = df_dash['stato_p'].value_counts().reset_index()
                df_stati.columns = ['Stato', 'Quantità']
                st.bar_chart(df_stati.set_index('Stato'))
            else:
                st.info("Colonna stato non disponibile per il grafico.")

        with col_g2:
            st.markdown("### 🚙 Distribuzione per Categoria")
            if c_categoria in df_dash.columns:
                df_cat = df_dash[c_categoria].astype(str).str.strip().value_counts().reset_index()
                df_cat.columns = ['Categoria', 'Quantità']
                st.bar_chart(df_cat.set_index('Categoria'))
            else:
                st.info("Colonna categoria non disponibile per il grafico.")
    else:
        st.info("Nessun dato statistico disponibile nel sistema.")

# =========================================================
# TAB 2: RIENTRO VEICOLO (Aggiornato con Km Finali)
# =========================================================
with tab_rientro:
    st.subheader("🔑 Gestione Rientro Veicolo")
    
    if not df.empty:
        def trova_col(keywords):
            for col in df.columns:
                for kw in keywords:
                    if kw.lower() in str(col).lower():
                        return col
            return None

        c_stato = COL_STATO if COL_STATO in df.columns else trova_col(["stato"])
        c_targa = COL_TARGA if COL_TARGA in df.columns else trova_col(["targa"])
        c_marca = COL_MARCA if COL_MARCA in df.columns else trova_col(["marca"])
        c_modello = COL_MODELLO if COL_MODELLO in df.columns else trova_col(["modello"])
        c_cliente = COL_CLIENTE if COL_CLIENTE in df.columns else trova_col(["cliente"])

        if c_stato and c_stato in df.columns:
            df_temp = df.copy()
            df_temp['stato_pulito'] = df_temp[c_stato].astype(str).str.strip().str.lower()
            df_noleggiate = df_temp[df_temp['stato_pulito'].isin(["noleggiata", "noleggiato", "affittata", "in uso"])]
        else:
            df_noleggiate = pd.DataFrame()

        if df_noleggiate.empty:
            st.info("ℹ️ Al momento non ci risulta alcun veicolo con stato 'Noleggiata'.")
        else:
            opzioni_rientro = []
            mappa_rientro = {}
            
            for idx, r in df_noleggiate.iterrows():
                t = str(r.get(c_targa, ''))
                m = str(r.get(c_marca, ''))
                mod = str(r.get(c_modello, ''))
                cli = str(r.get(c_cliente, 'N/D'))
                
                label = f"{t} - {m} {mod} (Cliente: {cli})"
                opzioni_rientro.append(label)
                mappa_rientro[label] = t

            with st.form("form_rientro"):
                auto_sel = st.selectbox("Seleziona Veicolo in Rientro *", opzioni_rientro)
                
                # ---> NUOVO CAMPO: Km Finali nel form di rientro
                km_finali_inseriti = st.number_input("Km Finali alla Consegna *", min_value=0, value=0, step=100)
                
                nota_checkin = st.text_area("Note Check-in / Condizioni Veicolo", placeholder="es. Condizioni ottime...")
                submit_rientro = st.form_submit_button("🔄 Conferma Rientro Veicolo", type="primary")

                if submit_rientro:
                    if not auto_sel:
                        st.error("Seleziona un veicolo da rientrare.")
                    else:
                        targa_r = mappa_rientro.get(auto_sel)
                        try:
                            df_agg = formatta_date_df(df)
                            idx_matches = df_agg[df_agg[c_targa] == targa_r].index

                            if len(idx_matches) > 0:
                                i = idx_matches[0]
                                
                                # Aggiornamento dei campi nel DataFrame
                                if c_stato: df_agg.loc[i, c_stato] = "Disponibile"
                                if c_cliente: df_agg.loc[i, c_cliente] = "N/D"
                                if COL_DATA_INI in df_agg.columns: df_agg.loc[i, COL_DATA_INI] = ""
                                if COL_DATA_FIN in df_agg.columns: df_agg.loc[i, COL_DATA_FIN] = ""
                                if COL_COSTO in df_agg.columns: df_agg.loc[i, COL_COSTO] = "0.0"
                                
                                # ---> SALVATAGGIO KM FINALI NEL DATAFRAME
                                if COL_KM_FINALI in df_agg.columns: 
                                    df_agg.loc[i, COL_KM_FINALI] = str(km_finali_inseriti)
                                    
                                if nota_checkin.strip() and COL_NOTE_CHECKIN in df_agg.columns:
                                    df_agg.loc[i, COL_NOTE_CHECKIN] = nota_checkin.strip()

                                rows_payload = df_agg.fillna("").astype(str).to_dict(orient="records")
                                payload = {
                                    "action": "update_all",
                                    "rows": rows_payload,
                                }

                                res = requests.post(APPS_SCRIPT_URL, json=payload, timeout=20)
                                if res.status_code == 200:
                                    res_json = res.json()
                                    if res_json.get("status") in ["ok", "success"]:
                                        st.success(f"✅ Veicolo {targa_r} rientrato correttamente con {km_finali_inseriti} Km registrati!")
                                        st.cache_data.clear()
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error(f"Errore dal server: {res_json.get('message', 'Sconosciuto')}")
                                else:
                                    st.error(f"Errore HTTP {res.status_code}: {res.text}")
                            else:
                                st.error(f"Impossibile trovare la targa {targa_r} nel registro.")
                        except Exception as e:
                            st.error(f"Errore durante il rientro del veicolo: {e}")
    else:
        st.info("Nessun dato disponibile nel sistema.")
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
            km_iniziali = st.number_input("Km Iniziali *", min_value=0, value=0, step=100)
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
                    COL_KM_INIZIALI: str(km_iniziali),
                    COL_KM_FINALI: "",
                    COL_PAGAMENTO: "",
                    COL_CAUZIONE: "0.0",
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
        def trova_col(keywords):
            for col in df.columns:
                for kw in keywords:
                    if kw.lower() in str(col).lower():
                        return col
            return None

        c_stato = COL_STATO if COL_STATO in df.columns else trova_col(["stato"])
        c_targa = COL_TARGA if COL_TARGA in df.columns else trova_col(["targa"])
        c_marca = COL_MARCA if COL_MARCA in df.columns else trova_col(["marca"])
        c_modello = COL_MODELLO if COL_MODELLO in df.columns else trova_col(["modello"])
        c_prezzo = COL_PREZZO if COL_PREZZO in df.columns else trova_col(["prezzo"])

        df_temp = df.copy()
        if c_stato and c_stato in df_temp.columns:
            df_temp['stato_pulito'] = df_temp[c_stato].astype(str).str.strip().str.lower()
            df_disponibili = df_temp[df_temp['stato_pulito'].isin(["disponibile", "disponibili", "libera", "libero", ""])]
        else:
            df_disponibili = pd.DataFrame()

        if df_disponibili.empty:
            st.warning("⚠️ Al momento non ci sono veicoli con stato 'Disponibile' nel registro flotta.")
        else:
            opzioni_auto = []
            mappa_auto = {}
            for idx, r in df_disponibili.iterrows():
                t = str(r.get(c_targa, ''))
                m = str(r.get(c_marca, ''))
                mod = str(r.get(c_modello, ''))
                p = r.get(c_prezzo, 0.0)
                
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
                    
                    # Nuovi campi integrati correttamente
                    metodo_pagamento = st.selectbox("Metodo di Pagamento", ["Contanti", "Carta di Credito", "Bonifico", "Altro"])
                    cauzione_importo = st.number_input("Cauzione / Deposito (€)", min_value=0.0, value=0.0, step=50.0)
                    
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
                            idx_matches = df_agg[df_agg[c_targa] == targa_selezionata].index

                            if len(idx_matches) > 0:
                                i = idx_matches[0]
                                giorni = (data_fine_cli - data_inizio_cli).days
                                giorni = 1 if giorni < 1 else giorni
                                costo_totale = giorni * prezzo_personalizzato

                                if c_stato: df_agg.loc[i, c_stato] = str(stato_nuovo)
                                if COL_CLIENTE in df_agg.columns: df_agg.loc[i, COL_CLIENTE] = nome_cliente.strip()
                                if COL_DATA_INI in df_agg.columns: df_agg.loc[i, COL_DATA_INI] = str(data_inizio_cli)
                                if COL_DATA_FIN in df_agg.columns: df_agg.loc[i, COL_DATA_FIN] = str(data_fine_cli)
                                if c_prezzo in df_agg.columns: df_agg.loc[i, c_prezzo] = float(prezzo_personalizzato)
                                if COL_COSTO in df_agg.columns: df_agg.loc[i, COL_COSTO] = float(costo_totale)
                                
                                # Salvataggio dei campi aggiuntivi nel DataFrame
                                if COL_PAGAMENTO in df_agg.columns: df_agg.loc[i, COL_PAGAMENTO] = str(metodo_pagamento)
                                if COL_CAUZIONE in df_agg.columns: df_agg.loc[i, COL_CAUZIONE] = float(cauzione_importo)
                                
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
