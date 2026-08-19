from datetime import date
import time
import pandas as pd
import requests
import streamlit as st

# ---------------------------------------------------------
# CONFIGURAZIONE URL E NOMI COLONNE
# ---------------------------------------------------------
# Gestione sicura dell'ID: estrae il codice ID anche se viene incollato l'URL intero
RAW_SPREADSHEET_ID = st.secrets.get(
    "SPREADSHEET_ID",
    "1-XQnKHP1vWFNcvjCdG631FrqIST4PmJ-MtIGdvFesEE/edit?usp=sharing",
)
if "/d/" in RAW_SPREADSHEET_ID:
    SPREADSHEET_ID = RAW_SPREADSHEET_ID.split("/d/")[1].split("/")[0]
else:
    SPREADSHEET_ID = RAW_SPREADSHEET_ID.split("/")[0]

APPS_SCRIPT_URL = st.secrets.get(
    "APPS_SCRIPT_URL",
    "https://script.google.com/macros/s/AKfycbycKrCl2BqKioOSTasMXTItOSJyUOxYx30qDe1SiedNqBQZNHRk6mBbslKU8zU0voyJ/exec",
)

# Nomi colonne esatti dal Foglio Google
COL_TARGA = "Targa Auto"
COL_MARCA = "Marca"
COL_MODELLO = "Modello"
COL_CATEGORIA = "Categoria"
COL_PREZZO = "Prezzo Giornaliero (€)"
COL_ANNO = "Anno Immatricolazione"
COL_CLIENTE = "Cliente"
COL_STATO = "Stato Veicolo"
COL_DATA_INI = "Data Inizio Noleggio"
COL_DATA_FIN = "Data Fine Noleggio"
COL_NOTE = "Note"
COL_COSTO = "Costo Totale (€)"
COL_NOTE1 = "Note1"
COL_NOTE_CHECKIN = "Note Check In"

st.set_page_config(
    page_title="Gestione Autonoleggio", page_icon="🚗", layout="wide"
)
st.title("🚗 Sistema Gestione Autonoleggio")


# ---------------------------------------------------------
# CARICAMENTO E PULIZIA DATI
# ---------------------------------------------------------
def pulisci_valore_numerico(valore):
    if pd.isna(valore):
        return 0.0
    val_str = (
        str(valore)
        .replace("€", "")
        .replace(" ", "")
        .replace(",", ".")
        .strip()
    )
    try:
        return float(val_str)
    except ValueError:
        return 0.0


def formatta_date_df(dataframe):
    df_out = dataframe.copy()
    for col in [COL_DATA_INI, COL_DATA_FIN]:
        if col in df_out.columns:
            df_out[col] = pd.to_datetime(df_out[col], errors="coerce")
            df_out[col] = df_out[col].dt.strftime("%Y-%m-%d").fillna("")
    return df_out


@st.cache_data(ttl=60)
def carica_dati():
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&nocache={int(time.time())}"
        data = pd.read_csv(url)
        data.columns = data.columns.str.strip()

        if COL_PREZZO in data.columns:
            data[COL_PREZZO] = data[COL_PREZZO].apply(pulisci_valore_numerico)

        if COL_COSTO in data.columns:
            data[COL_COSTO] = data[COL_COSTO].apply(pulisci_valore_numerico)

        for col_date in [COL_DATA_INI, COL_DATA_FIN]:
            if col_date in data.columns:
                data[col_date] = pd.to_datetime(
                    data[col_date], errors="coerce"
                )

        return data
    except Exception as e:
        st.error(f"Errore nella lettura del Foglio Google: {e}")
        return pd.DataFrame()


df = carica_dati()

# ---------------------------------------------------------
# TAB
# ---------------------------------------------------------
tab_dash, tab_rientro, tab_storico, tab_registro, tab_nuovo_noleggio, tab_nuovo_veicolo = st.tabs([
    "📊 Dashboard",
    "🔑 Rientro Veicolo",
    "📜 Storico & Ricerca",
    "📋 Registro Flotta",
    "➕ Nuovo Noleggio",
    "🚗 Inserisci Nuovo Veicolo",
])
])

# =========================================================
# TAB 1: DASHBOARD
# =========================================================
with tab_dash:
    st.subheader("📊 Panoramica & Statistiche Flotta")

    if not df.empty:
        tot_veicoli = len(df)
        noleggiati = (
            len(df[df[COL_STATO] == "Noleggiata"])
            if COL_STATO in df.columns
            else 0
        )
        disponibili = (
            len(df[df[COL_STATO] == "Disponibile"])
            if COL_STATO in df.columns
            else 0
        )
        manutenzione = (
            len(df[df[COL_STATO] == "In Manutenzione"])
            if COL_STATO in df.columns
            else 0
        )

        tasso_occ = (noleggiati / tot_veicoli * 100) if tot_veicoli > 0 else 0
        incasso_tot = df[COL_COSTO].sum() if COL_COSTO in df.columns else 0.0
        prezzo_medio = (
            df[COL_PREZZO].mean() if COL_PREZZO in df.columns else 0.0
        )

        noleggi_attivi = (
            df[df[COL_STATO] == "Noleggiata"].copy()
            if COL_STATO in df.columns
            else pd.DataFrame()
        )
        scaduti = 0
        if not noleggi_attivi.empty and COL_DATA_FIN in noleggi_attivi.columns:
            oggi = pd.to_datetime(date.today())
            noleggi_attivi["_df_fine"] = pd.to_datetime(
                noleggi_attivi[COL_DATA_FIN], errors="coerce"
            )
            scaduti = len(noleggi_attivi[noleggi_attivi["_df_fine"] < oggi])

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Totale Flotta", tot_veicoli)
        k2.metric("🟢 Disponibili", disponibili)
        k3.metric("🔴 In Noleggio", noleggiati)
        k4.metric("🟠 In Manutenzione", manutenzione)

        f1, f2, f3, f4 = st.columns(4)
        f1.metric("Incasso Totale Registrato", f"€ {incasso_tot:,.2f}")
        f2.metric("Prezzo Medio Giornaliero", f"€ {prezzo_medio:,.2f}")
        f3.metric("Tasso di Occupazione", f"{tasso_occ:.1f}%")
        f4.metric(
            "⚠️ Noleggi Scaduti",
            scaduti,
            delta="- Attenzione" if scaduti > 0 else "Tutto OK",
            delta_color="inverse" if scaduti > 0 else "normal",
        )

        st.divider()

        cg1, cg2 = st.columns(2)
        with cg1:
            st.markdown("### 📊 Ripartizione Stato Veicoli")
            if COL_STATO in df.columns:
                st.bar_chart(df[COL_STATO].value_counts())

        with cg2:
            st.markdown("### 🚗 Veicoli per Categoria")
            if COL_CATEGORIA in df.columns:
                st.bar_chart(df[COL_CATEGORIA].value_counts())

        st.divider()

        cg3, cg4 = st.columns(2)
        with cg3:
            st.markdown("### 💰 Incassi per Categoria (€)")
            if COL_CATEGORIA in df.columns and COL_COSTO in df.columns:
                st.bar_chart(df.groupby(COL_CATEGORIA)[COL_COSTO].sum())

        with cg4:
            st.markdown("### 🔑 Noleggi Attivi in Corso")
            if not noleggi_attivi.empty:
                cols_view = [
                    c
                    for c in [
                        COL_TARGA,
                        COL_MARCA,
                        COL_MODELLO,
                        COL_CLIENTE,
                        COL_DATA_FIN,
                    ]
                    if c in noleggi_attivi.columns
                ]
                st.dataframe(
                    noleggi_attivi[cols_view],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Nessun noleggio attualmente in corso.")
    else:
        st.info("Nessun dato caricato dal Foglio Google.")

# =========================================================
# TAB 2: RIENTRO VEICOLO
# =========================================================
with tab_rientro:
    st.subheader("🔑 Check-in e Registrazione Rientro Veicolo")

    if not df.empty and COL_STATO in df.columns:
        df_noleggiate = df[df[COL_STATO] == "Noleggiata"]

        if df_noleggiate.empty:
            st.success(
                "Tutti i veicoli risultano attualmente disponibili o in"
                " manutenzione."
            )
        else:
            opzioni = df_noleggiate.apply(
                lambda r: (
                    f"{r.get(COL_TARGA, '')} - {r.get(COL_MARCA, '')}"
                    f" {r.get(COL_MODELLO, '')} (Cliente:"
                    f" {r.get(COL_CLIENTE, 'N/D')})"
                ),
                axis=1,
            ).tolist()

            veicolo_sel = st.selectbox(
                "Seleziona il veicolo da far rientrare *", opzioni
            )

            if veicolo_sel:
                targa_selezionata = veicolo_sel.split(" - ")[0]
                row_veicolo = df_noleggiate[
                    df_noleggiate[COL_TARGA] == targa_selezionata
                ].iloc[0]

                d_ini = row_veicolo.get(COL_DATA_INI)
                d_ini_str = (
                    d_ini.strftime("%Y-%m-%d") if pd.notna(d_ini) else "N/D"
                )
                prezzo_giornaliero = float(
                    row_veicolo.get(COL_PREZZO, 0.0) or 0.0
                )

                st.divider()
                st.markdown("### 📄 Dettagli Noleggio Attivo")
                c1, c2 = st.columns(2)
                c1.markdown(
                    f"**Targa:** `{targa_selezionata}` | **Veicolo:**"
                    f" {row_veicolo.get(COL_MARCA, '')}"
                    f" {row_veicolo.get(COL_MODELLO, '')}"
                )
                c1.markdown(
                    f"**Cliente:** {row_veicolo.get(COL_CLIENTE, 'N/D')}"
                )
                c2.markdown(f"**Data Inizio Noleggio:** {d_ini_str}")
                c2.markdown(
                    f"**Prezzo Giornaliero:** € {prezzo_giornaliero:.2f}"
                )

                st.divider()
                st.markdown("### 📋 Form Check-in Rientro")
                r_col1, r_col2 = st.columns(2)

                with r_col1:
                    data_rientro = st.date_input(
                        "Data Rientro Effettiva *", date.today()
                    )
                    nuovo_stato = st.selectbox(
                        "Nuovo Stato Veicolo *",
                        ["Disponibile", "In Manutenzione"],
                    )
                    km_rientro = st.text_input(
                        "Chilometri al rientro", placeholder="es. 45.200 km"
                    )

                with r_col2:
                    carburante = st.selectbox(
                        "Livello Carburante/Ricarica",
                        ["Pieno", "3/4", "1/2", "1/4", "Riserva"],
                    )
                    note_danni = st.text_area(
                        "Note Check In / Eventuali Danni",
                        placeholder=(
                            "Indicare eventuali graffi, stato di pulizia o"
                            " note sul veicolo..."
                        ),
                    )

                if pd.notna(d_ini):
                    d_ini_date = (
                        d_ini.date()
                        if isinstance(d_ini, pd.Timestamp)
                        else d_ini
                    )
                    giorni_effettivi = (data_rientro - d_ini_date).days
                    giorni_effettivi = (
                        1 if giorni_effettivi < 1 else giorni_effettivi
                    )
                else:
                    giorni_effettivi = 1

                costo_ricalcolato = giorni_effettivi * prezzo_giornaliero
                st.info(
                    f"📐 **Riepilogo Conteggio:** {giorni_effettivi} giorni di"
                    f" noleggio × €{prezzo_giornaliero:.2f}/gg = **Costo"
                    f" Totale: € {costo_ricalcolato:.2f}**"
                )

                if st.button(
                    "➕ Registra Rientro e Aggiorna Foglio Google",
                    type="primary",
                ):
                    try:
                        df_agg = formatta_date_df(df)

                        idx = df_agg[
                            (df_agg[COL_TARGA] == targa_selezionata)
                            & (df_agg[COL_STATO] == "Noleggiata")
                        ].index

                        if len(idx) > 0:
                            i = idx[0]
                            dettagli_checkin = (
                                f"Rientro il {data_rientro} | Carb:"
                                f" {carburante}"
                            )
                            if km_rientro:
                                dettagli_checkin += f" | Km: {km_rientro}"
                            if note_danni.strip():
                                dettagli_checkin += (
                                    f" | Note: {note_danni.strip()}"
                                )

                            df_agg[COL_NOTE_CHECKIN] = df_agg[COL_NOTE_CHECKIN].astype(str)

                            df_agg.loc[i, COL_STATO] = nuovo_stato
                            df_agg.loc[i, COL_DATA_FIN] = str(data_rientro)
                            df_agg.loc[i, COL_COSTO] = float(costo_ricalcolato)
                            df_agg.loc[i, COL_NOTE_CHECKIN] = dettagli_checkin
                            

                            rows_payload = (
                                df_agg.fillna("")
                                .astype(str)
                                .to_dict(orient="records")
                            )

                            payload = {
                                "action": "update_all",
                                "rows": rows_payload,
                            }

                            res = requests.post(
                                APPS_SCRIPT_URL, json=payload, timeout=15
                            )
                            res_json = (
                                res.json() if res.status_code == 200 else {}
                            )

                            if res.status_code == 200 and res_json.get(
                                "status"
                            ) in ["ok", "success"]:
                                st.success(
                                    "✅ Rientro per la targa"
                                    f" {targa_selezionata} registrato con"
                                    " successo!"
                                )
                                st.cache_data.clear()
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(
                                    f"Errore risposta server: {res.text}"
                                )
                    except Exception as e:
                        st.error(
                            f"Errore durante l'operazione di rientro: {e}"
                        )

# =========================================================
# TAB 3: STORICO & RICERCA
# =========================================================
with tab_storico:
    st.subheader("📜 Ricerca & Storico Noleggi")

    if not df.empty:
        f1, f2 = st.columns(2)
        with f1:
            ricerca = st.text_input("🔍 Cerca per Targa o Cliente", "")
        with f2:
            stati = (
                ["Tutti"] + list(df[COL_STATO].dropna().unique())
                if COL_STATO in df.columns
                else ["Tutti"]
            )
            stato_f = st.selectbox("Filtra Stato", stati)

        df_f = df.copy()

        if ricerca:
            mask_t = (
                df_f[COL_TARGA]
                .astype(str)
                .str.contains(ricerca, case=False, na=False)
                if COL_TARGA in df_f.columns
                else False
            )
            mask_c = (
                df_f[COL_CLIENTE]
                .astype(str)
                .str.contains(ricerca, case=False, na=False)
                if COL_CLIENTE in df_f.columns
                else False
            )
            df_f = df_f[mask_t | mask_c]

        if stato_f != "Tutti" and COL_STATO in df_f.columns:
            df_f = df_f[df_f[COL_STATO] == stato_f]

        df_display = formatta_date_df(df_f)
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        csv = df_display.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Scarica Dati (CSV)",
            csv,
            "storico_autonoleggio.csv",
            "text/csv",
        )

# =========================================================
# TAB 4: REGISTRO FLOTTA (EDITABILE E SOVRASCRIVIBILE)
# =========================================================
with tab_registro:
    st.subheader("📋 Registro Completo Flotta")

    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = False

    if not df.empty:
        df_formattato = formatta_date_df(df)

        if not st.session_state.edit_mode:
            # Vista standard (Sola lettura)
            if st.button("✏️ Abilita Modifica Tabella"):
                st.session_state.edit_mode = True
                st.rerun()

            st.dataframe(
                df_formattato,
                use_container_width=True,
                hide_index=True,
            )

        else:
            # Vista Modifica
            st.info(
                "💡 **Modalità Modifica Attiva:** Modifica i dati nelle celle"
                " oppure seleziona le righe da eliminare e usa il tasto"
                " **Canc/Backspace** (o l'icona cestino in alto a destra"
                " dell'editor). Al termine fai clic su **💾 Salva Modifiche su"
                " Google Sheets**."
            )

            edited_df = st.data_editor(
                df_formattato,
                use_container_width=True,
                hide_index=True,
                key="editor_parco_auto",
                num_rows="dynamic",
            )

            st.divider()
            b1, b2 = st.columns([4, 6])

            # Bottone Salva Modifiche
            if b1.button(
                "💾 Salva Modifiche su Google Sheets", type="primary"
            ):
                try:
                    df_salva = edited_df.fillna("").astype(str)

                    payload = {
                        "action": "update_all",
                        "rows": df_salva.to_dict(orient="records"),
                    }

                    res = requests.post(
                        APPS_SCRIPT_URL, json=payload, timeout=20
                    )
                    res_json = res.json() if res.status_code == 200 else {}

                    if res.status_code == 200 and res_json.get("status") in [
                        "ok",
                        "success",
                    ]:
                        st.success("✅ Foglio Google aggiornato con successo!")
                        st.session_state.edit_mode = False
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Errore durante il salvataggio: {res.text}")
                except Exception as e:
                    st.error(f"Errore di connessione con Apps Script: {e}")

            # Bottone Annulla
            if b2.button("❌ Annulla"):
                st.session_state.edit_mode = False
                st.rerun()
    else:
        st.warning("Nessun dato disponibile nel Registro.")

# =========================================================
# TAB 5: INSERISCI REGISTRAZIONE
# =========================================================
# =========================================================
# TAB 5: NUOVO NOLEGGIO (SELEZIONE AUTO DISPONIBILE)
# =========================================================
with tab_nuovo:
    st.subheader("➕ Registra Nuovo Veicolo / Noleggio")

    with st.form("form_nuovo", clear_on_submit=True):
        c1, c2 = st.columns(2)

        with c1:
            targa = st.text_input(f"{COL_TARGA} *").upper()
            marca = st.text_input(f"{COL_MARCA} *")
            modello = st.text_input(f"{COL_MODELLO} *")
            categoria = st.selectbox(
                COL_CATEGORIA,
                ["Utilitaria", "Berlina", "SUV", "Station Wagon", "Furgone"],
            )
            prezzo_giornaliero = st.number_input(
                f"{COL_PREZZO} *", min_value=0.0, value=50.0
            )
            anno_imm = st.number_input(
                COL_ANNO, min_value=1990, max_value=2030, value=2023
            )

        with c2:
            cliente = st.text_input(COL_CLIENTE)
            stato = st.selectbox(
                f"{COL_STATO} *",
                ["Disponibile", "Noleggiata", "In Manutenzione"],
            )
            data_inizio = st.date_input(COL_DATA_INI, date.today())
            data_fine = st.date_input(COL_DATA_FIN, date.today())
            note = st.text_area(COL_NOTE)
            note1 = st.text_input(COL_NOTE1)
            note_checkin = st.text_input(COL_NOTE_CHECKIN)

        giorni = (data_fine - data_inizio).days
        giorni = 1 if giorni < 1 else giorni
        costo_totale = (
            giorni * prezzo_giornaliero if stato == "Noleggiata" else 0.0
        )

        if stato == "Noleggiata":
            st.info(f"📐 **Costo Totale Calcolato:** € {costo_totale:.2f}")

        submit = st.form_submit_button("💾 Salva nel Foglio Google")

        if submit:
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
                    COL_CLIENTE: str(cliente) if cliente else "N/D",
                    COL_STATO: str(stato),
                    COL_DATA_INI: (
                        str(data_inizio) if stato == "Noleggiata" else ""
                    ),
                    COL_DATA_FIN: (
                        str(data_fine) if stato == "Noleggiata" else ""
                    ),
                    COL_NOTE: str(note),
                    COL_COSTO: str(costo_totale),
                    COL_NOTE1: str(note1),
                    COL_NOTE_CHECKIN: str(note_checkin),
                }

                try:
                    res = requests.post(
                        APPS_SCRIPT_URL, json=payload, timeout=15
                    )
                    res_json = res.json() if res.status_code == 200 else {}

                    if res.status_code == 200 and res_json.get("status") in [
                        "ok",
                        "success",
                    ]:
                        st.success(
                            f"✅ Registrazione per {targa} salvata"
                            " correttamente!"
                        )
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Errore risposta server: {res.text}")
                except Exception as e:
                    st.error(f"Errore di connessione: {e}")

# =========================================================
# TAB 6: INSERISCI NUOVO VEICOLO IN FLOTTA
# =========================================================
with tab_nuovo_veicolo:
    st.subheader("🚗 Aggiungi un Nuovo Veicolo al Parco Auto")

    with st.form("form_nuovo_veicolo", clear_on_submit=True):
        c1, c2 = st.columns(2)

        with c1:
            targa = st.text_input(f"{COL_TARGA} *").upper()
            marca = st.text_input(f"{COL_MARCA} *")
            modello = st.text_input(f"{COL_MODELLO} *")
            categoria = st.selectbox(
                COL_CATEGORIA,
                ["Utilitaria", "Berlina", "SUV", "Station Wagon", "Furgone"],
            )
            prezzo_giornaliero = st.number_input(
                f"{COL_PREZZO} *", min_value=0.0, value=50.0
            )
            anno_imm = st.number_input(
                COL_ANNO, min_value=1990, max_value=2030, value=2023
            )

        with c2:
            cliente = st.text_input(COL_CLIENTE, placeholder="Se noleggiato subito, inserisci cliente")
            stato = st.selectbox(
                f"{COL_STATO} *",
                ["Disponibile", "Noleggiata", "In Manutenzione"],
            )
            data_inizio = st.date_input(COL_DATA_INI, date.today())
            data_fine = st.date_input(COL_DATA_FIN, date.today())
            note = st.text_area(COL_NOTE)
            note1 = st.text_input(COL_NOTE1)
            note_checkin = st.text_input(COL_NOTE_CHECKIN)

        giorni = (data_fine - data_inizio).days
        giorni = 1 if giorni < 1 else giorni
        costo_totale = (
            giorni * prezzo_giornaliero if stato == "Noleggiata" else 0.0
        )

        if stato == "Noleggiata":
            st.info(f"📐 **Costo Totale Calcolato:** € {costo_totale:.2f}")

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
                    COL_CLIENTE: str(cliente) if cliente else "N/D",
                    COL_STATO: str(stato),
                    COL_DATA_INI: str(data_inizio) if stato == "Noleggiata" else "",
                    COL_DATA_FIN: str(data_fine) if stato == "Noleggiata" else "",
                    COL_NOTE: str(note),
                    COL_COSTO: str(costo_totale),
                    COL_NOTE1: str(note1),
                    COL_NOTE_CHECKIN: str(note_checkin),
                }

                try:
                    res = requests.post(APPS_SCRIPT_URL, json=payload, timeout=15)
                    res_json = res.json() if res.status_code == 200 else {}

                    if res.status_code == 200 and res_json.get("status") in ["ok", "success"]:
                        st.success(f"✅ Veicolo con targa {targa} aggiunto con successo alla flotta!")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Errore risposta server: {res.text}")
                except Exception as e:
                    st.error(f"Errore di connessione: {e}")

