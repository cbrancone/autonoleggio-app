import streamlit as st
import pandas as pd
import requests
from datetime import date, datetime
import time

# =========================================================
# CONFIGURAZIONE
# =========================================================
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyKMhlDddoULMNfyx_1sdV_63rEofWq-U2hyzIfVs1yao-Gy5NFuH5f41WWKbJoHitT/exec"

# Colonne esistenti
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
COL_NOTE1 = "Note1"
COL_NOTE_CHECKIN = "Note Check In"
COL_KM_INIZIALI = "KM_INIZIALI"
COL_KM_FINALI = "KM_FINALI"
COL_PAGAMENTO = "PAGAMENTO"
COL_CAUZIONE = "CAUZIONE"
COL_ENTRATE_USCITE = "ENTRATE/USCITE"
COL_MANUTENZIONE = "MANUTENZIONE"

# Fatturazione
COL_FATTURA = "FATTURA"
COL_NUMERO_FATTURA = "NUMERO FATTURA"
COL_DATA_FATTURA = "DATA FATTURA"
COL_STATO_FATTURA = "STATO FATTURA"

# Nuove colonne
COL_COSTO = "Costo Totale"
COL_TIPO_RECORD = "TIPO RECORD"

TIPO_VEICOLO = "VEICOLO"
TIPO_NOLEGGIO = "NOLEGGIO"
TIPO_CONTABILITA = "CONTABILITA"

COLONNE_ATTESE = [
    COL_TARGA, COL_MARCA, COL_MODELLO, COL_CATEGORIA, COL_PREZZO, COL_ANNO,
    COL_CLIENTE, COL_STATO, COL_DATA_INI, COL_DATA_FIN, COL_NOTE, COL_NOTE1,
    COL_NOTE_CHECKIN, COL_KM_INIZIALI, COL_KM_FINALI, COL_PAGAMENTO,
    COL_CAUZIONE, COL_ENTRATE_USCITE, COL_MANUTENZIONE, COL_COSTO,
    COL_FATTURA, COL_NUMERO_FATTURA, COL_DATA_FATTURA, COL_STATO_FATTURA,
    COL_TIPO_RECORD
]

# =========================================================
# AUTENTICAZIONE
# =========================================================
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    st.markdown("## 🔐 Accesso Riservato - Gestionale Flotta")
    username_input = st.text_input("Username", key="login_user")
    password_input = st.text_input("Password", type="password", key="login_pass")

    if st.button("Accedi", type="primary"):
        if username_input == "flotta" and password_input == "Pa$$Admin12345":
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("😕 Username o password errati. Riprova.")
    st.stop()

# =========================================================
# FUNZIONI UTILI
# =========================================================
def trova_col(df, keywords):
    for col in df.columns:
        col_lower = str(col).strip().lower()
        for kw in keywords:
            if kw.lower() in col_lower:
                return col
    return None


def valore_numero(value, default=0.0):
    if value is None:
        return default
    if isinstance(value, (int, float)):
        try:
            return float(value)
        except Exception:
            return default

    testo = str(value).strip()
    if not testo:
        return default

    testo = testo.replace("€", "").replace(" ", "")
    if "," in testo and "." in testo:
        testo = testo.replace(".", "").replace(",", ".")
    elif "," in testo:
        testo = testo.replace(",", ".")

    try:
        return float(testo)
    except Exception:
        return default


def giorni_noleggio(data_ini, data_fin):
    try:
        di = pd.to_datetime(data_ini, errors="coerce")
        df = pd.to_datetime(data_fin, errors="coerce")
        if pd.isna(di) or pd.isna(df):
            return 0
        return max(1, (df.date() - di.date()).days)
    except Exception:
        return 0


def costo_riga_noleggio(row):
    costo = valore_numero(row.get(COL_COSTO, 0), 0)
    if costo > 0:
        return costo

    prezzo = valore_numero(row.get(COL_PREZZO, 0), 0)
    giorni = giorni_noleggio(row.get(COL_DATA_INI, ""), row.get(COL_DATA_FIN, ""))
    return prezzo * giorni


def normalizza_tipo_record(row):
    tipo = str(row.get(COL_TIPO_RECORD, "")).strip().upper()
    if tipo in [TIPO_VEICOLO, TIPO_NOLEGGIO, TIPO_CONTABILITA]:
        return tipo

    categoria = str(row.get(COL_CATEGORIA, "")).strip().lower()
    cliente = str(row.get(COL_CLIENTE, "")).strip().upper()
    data_ini = str(row.get(COL_DATA_INI, "")).strip()
    data_fin = str(row.get(COL_DATA_FIN, "")).strip()

    if "contabilità" in categoria or "contabilita" in categoria:
        return TIPO_CONTABILITA

    if cliente not in ["", "N/D", "NONE", "NAN"] and (data_ini or data_fin):
        return TIPO_NOLEGGIO

    return TIPO_VEICOLO


def prepara_dataframe(df_input):
    """
    Prepara il DataFrame senza MAI spostare i dati tra colonne.

    Regola fondamentale per la contabilità:
    - MARCA resta vuota
    - MODELLO resta vuoto
    - CATEGORIA = Contabilità
    - NOTE = descrizione della spesa/entrata
    - NOTE1 = tipo movimento (Spesa (Uscita) / Entrata Extra)
    - ENTRATE/USCITE = importo positivo o negativo
    """
    df_out = df_input.copy()

    for col in COLONNE_ATTESE:
        if col not in df_out.columns:
            df_out[col] = ""

    # Determina il tipo per i dati vecchi che non avevano la colonna.
    df_out[COL_TIPO_RECORD] = df_out.apply(normalizza_tipo_record, axis=1)

    # Ripara automaticamente i vecchi record CONTABILITA che avevano
    # erroneamente il tipo movimento dentro MARCA.
    tipi_contabilita = {
        "spesa (uscita)",
        "entrata extra",
        "spesa",
        "uscita",
        "entrata"
    }

    for idx in df_out.index:
        if df_out.loc[idx, COL_TIPO_RECORD] == TIPO_CONTABILITA:
            marca = str(df_out.loc[idx, COL_MARCA]).strip()
            note1 = str(df_out.loc[idx, COL_NOTE1]).strip()

            # Se il vecchio codice aveva messo il tipo movimento in MARCA,
            # lo spostiamo nella colonna corretta NOTE1.
            if marca.lower() in tipi_contabilita:
                if not note1:
                    df_out.loc[idx, COL_NOTE1] = marca
                df_out.loc[idx, COL_MARCA] = ""

            # Una riga contabile non deve avere dati di marca/modello.
            df_out.loc[idx, COL_MARCA] = ""
            df_out.loc[idx, COL_MODELLO] = ""
            df_out.loc[idx, COL_CATEGORIA] = "Contabilità"

            # Se manca Note1, ricaviamo il tipo dal segno dell'importo.
            if not str(df_out.loc[idx, COL_NOTE1]).strip():
                movimento = valore_numero(df_out.loc[idx, COL_ENTRATE_USCITE], 0)
                if movimento < 0:
                    df_out.loc[idx, COL_NOTE1] = "Spesa (Uscita)"
                elif movimento > 0:
                    df_out.loc[idx, COL_NOTE1] = "Entrata Extra"

        # Per i vecchi noleggi calcola il costo se manca.
        if df_out.loc[idx, COL_TIPO_RECORD] == TIPO_NOLEGGIO:
            costo = valore_numero(df_out.loc[idx, COL_COSTO], 0)
            if costo <= 0:
                calcolato = costo_riga_noleggio(df_out.loc[idx])
                if calcolato > 0:
                    df_out.loc[idx, COL_COSTO] = calcolato

    return df_out


def formatta_date_df(df_input):
    df_f = df_input.copy()
    for col in [COL_DATA_INI, COL_DATA_FIN, COL_DATA_FATTURA]:
        if col in df_f.columns:
            date_convertite = pd.to_datetime(df_f[col], errors="coerce")
            df_f[col] = date_convertite.dt.strftime("%Y-%m-%d").fillna("")
    return df_f


def payload_dataframe(df_input):
    df_out = prepara_dataframe(df_input)
    df_out = formatta_date_df(df_out)

    colonne_extra = [c for c in df_out.columns if c not in COLONNE_ATTESE]
    df_out = df_out[COLONNE_ATTESE + colonne_extra]

    return df_out.fillna("").astype(str).to_dict(orient="records")


def invia_payload(payload, timeout=20):
    try:
        res = requests.post(APPS_SCRIPT_URL, json=payload, timeout=timeout)
        try:
            risposta = res.json()
        except Exception:
            risposta = {"message": res.text}

        if res.status_code == 200 and risposta.get("status") in ["ok", "success"]:
            return True, risposta

        return False, risposta
    except Exception as e:
        return False, {"message": str(e)}


def numero_fattura_suggerito(df):
    anno_corrente = date.today().year
    if COL_NUMERO_FATTURA not in df.columns:
        return f"1/{anno_corrente}"

    numeri = []
    for valore in df[COL_NUMERO_FATTURA].dropna().astype(str):
        valore = valore.strip()
        if not valore:
            continue
        try:
            numeri.append(int(valore.split("/")[0].strip()))
        except Exception:
            pass

    return f"{max(numeri, default=0) + 1}/{anno_corrente}"


def stato_normalizzato(value):
    return str(value).strip().lower()


def righe_veicoli(df):
    return df[df[COL_TIPO_RECORD] == TIPO_VEICOLO].copy()


def righe_noleggi(df):
    return df[df[COL_TIPO_RECORD] == TIPO_NOLEGGIO].copy()


def righe_contabilita(df):
    return df[df[COL_TIPO_RECORD] == TIPO_CONTABILITA].copy()


# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown("### 👤 Area Utente")
    st.write("Accesso effettuato come: **Admin**")

    if st.button("🚪 Logout", type="secondary"):
        st.session_state["password_correct"] = False
        st.rerun()

    st.markdown("---")
    st.caption("Gestionale Flotta")

# =========================================================
# CARICAMENTO DATI
# =========================================================
@st.cache_data(ttl=10)
def carica_dati():
    try:
        response = requests.get(APPS_SCRIPT_URL, timeout=15)
        if response.status_code == 200:
            data = response.json()

            if isinstance(data, list) and len(data) > 0:
                headers = data[0]
                rows = data[1:]
                df = pd.DataFrame(rows, columns=headers).astype(object)
                return prepara_dataframe(df)

    except Exception as e:
        st.error(f"Errore di connessione a Google Sheets: {e}")

    return pd.DataFrame(columns=COLONNE_ATTESE)


df = carica_dati()

# =========================================================
# AVVISO COLONNE
# =========================================================
colonne_mancanti = [c for c in COLONNE_ATTESE if c not in df.columns]
if colonne_mancanti:
    st.warning(
        "⚠️ Nel Google Sheet mancano queste colonne: "
        + ", ".join(colonne_mancanti)
        + ". Aggiungile nella prima riga del foglio."
    )

# =========================================================
# TABS
# =========================================================
(
    tab_dash,
    tab_rientro,
    tab_storico,
    tab_registro,
    tab_nuovo_veicolo,
    tab_nuovo_cliente,
    tab_fatturazione,
    tab_contabilita
) = st.tabs([
    "📊 Dashboard",
    "🔑 Rientro Veicolo",
    "📜 Storico & Ricerca",
    "📋 Registro Flotta",
    "🚗 Nuovo veicolo",
    "👤 Nuovo Cliente / Noleggio",
    "🧾 Fatturazione",
    "💰 Contabilità & Spese"
])

# =========================================================
# TAB 1 - DASHBOARD
# =========================================================
with tab_dash:
    st.subheader("📊 Panoramica Generale")

    if df.empty:
        st.info("Nessun dato disponibile nel sistema.")
    else:
        df_veicoli = righe_veicoli(df)
        df_noleggi = righe_noleggi(df)
        df_contab = righe_contabilita(df)

        # Stato veicoli
        stato = df_veicoli[COL_STATO].astype(str).str.strip().str.lower() if not df_veicoli.empty else pd.Series(dtype=str)

        tot_veicoli = len(df_veicoli)
        disponibili = int((stato == "disponibile").sum()) if not df_veicoli.empty else 0
        noleggiate = int(stato.isin(["noleggiata", "noleggiato", "in uso"]).sum()) if not df_veicoli.empty else 0
        manutenzione = int(stato.str.contains("manutenzione", na=False).sum()) if not df_veicoli.empty else 0

        # Entrate da noleggi
        entrate_noleggi = sum(costo_riga_noleggio(r) for _, r in df_noleggi.iterrows())

        # Entrate extra e spese
        entrate_extra = 0.0
        spese = 0.0

        if not df_contab.empty:
            for _, r in df_contab.iterrows():
                valore = valore_numero(r.get(COL_ENTRATE_USCITE, 0))
                if valore > 0:
                    entrate_extra += valore
                elif valore < 0:
                    spese += abs(valore)

        totale_entrate = entrate_noleggi + entrate_extra
        saldo = totale_entrate - spese

        # Fatturato
        fatture_emesse = 0
        fatture_da_emettere = 0
        totale_fatturato = 0.0

        if not df_noleggi.empty:
            stati_fatt = df_noleggi[COL_STATO_FATTURA].astype(str).str.strip().str.lower()
            fatture_emesse = int(stati_fatt.isin(["emessa", "pagata"]).sum())
            fatture_da_emettere = int(stati_fatt.eq("da emettere").sum())

            for _, r in df_noleggi.iterrows():
                if stato_normalizzato(r.get(COL_STATO_FATTURA, "")) in ["emessa", "pagata"]:
                    totale_fatturato += costo_riga_noleggio(r)

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("🚗 Totale Veicoli", tot_veicoli)
        c2.metric("🟢 Disponibili", disponibili)
        c3.metric("🔵 Noleggiate", noleggiate)
        c4.metric("🟠 Manutenzione", manutenzione)
        c5.metric("🚙 Noleggi registrati", len(df_noleggi))

        st.markdown("---")

        e1, e2, e3, e4 = st.columns(4)
        e1.metric("🚗 Entrate Noleggi", f"€ {entrate_noleggi:,.2f}")
        e2.metric("➕ Entrate Extra", f"€ {entrate_extra:,.2f}")
        e3.metric("💸 Spese / Uscite", f"€ {spese:,.2f}")
        e4.metric("💰 Saldo Netto", f"€ {saldo:,.2f}")

        st.markdown("---")

        f1, f2, f3 = st.columns(3)
        f1.metric("🧾 Fatture emesse/pagate", fatture_emesse)
        f2.metric("⏳ Fatture da emettere", fatture_da_emettere)
        f3.metric("💰 Totale fatturato", f"€ {totale_fatturato:,.2f}")

        st.markdown("---")

        g1, g2 = st.columns(2)

        with g1:
            st.markdown("### 📊 Stato dei Veicoli")
            if not df_veicoli.empty:
                df_stati = (
                    df_veicoli[COL_STATO]
                    .astype(str)
                    .str.strip()
                    .str.capitalize()
                    .value_counts()
                    .reset_index()
                )
                df_stati.columns = ["Stato", "Quantità"]
                st.bar_chart(df_stati.set_index("Stato"))

        with g2:
            st.markdown("### 💶 Entrate e Uscite")
            df_movimenti = pd.DataFrame({
                "Tipo": ["Entrate Noleggi", "Entrate Extra", "Spese"],
                "Importo": [entrate_noleggi, entrate_extra, spese]
            })
            st.bar_chart(df_movimenti.set_index("Tipo"))

        st.markdown("### 📌 Ultimi Noleggi")
        if not df_noleggi.empty:
            vista = df_noleggi.sort_values(COL_DATA_INI, ascending=False)
            colonne = [
                COL_TARGA, COL_CLIENTE, COL_DATA_INI, COL_DATA_FIN,
                COL_COSTO, COL_PAGAMENTO, COL_FATTURA,
                COL_NUMERO_FATTURA, COL_STATO_FATTURA
            ]
            colonne = [c for c in colonne if c in vista.columns]
            st.dataframe(vista[colonne].head(10), use_container_width=True, hide_index=True)

# =========================================================
# TAB 2 - RIENTRO VEICOLO
# =========================================================
with tab_rientro:
    st.subheader("🔑 Gestione Rientro Veicolo")

    df_veicoli = righe_veicoli(df)
    if df_veicoli.empty:
        st.info("Nessun veicolo presente.")
    else:
        stato_clean = df_veicoli[COL_STATO].astype(str).str.strip().str.lower()
        df_noleggiate = df_veicoli[
            stato_clean.isin(["noleggiata", "noleggiato", "in uso"])
        ]

        if df_noleggiate.empty:
            st.info("ℹ️ Al momento non risulta alcun veicolo in noleggio.")
        else:
            opzioni = []
            mappa = {}

            for idx, r in df_noleggiate.iterrows():
                label = (
                    f"{r.get(COL_TARGA, '')} - "
                    f"{r.get(COL_MARCA, '')} {r.get(COL_MODELLO, '')} "
                    f"(Cliente: {r.get(COL_CLIENTE, 'N/D')})"
                )
                opzioni.append(label)
                mappa[label] = idx

            with st.form("form_rientro"):
                auto_sel = st.selectbox("Seleziona Veicolo in Rientro *", opzioni)
                km_finali = st.number_input("Km Finali alla Consegna *", min_value=0, value=0, step=100)
                nota = st.text_area("Note Check-in / Condizioni Veicolo")
                submit = st.form_submit_button("🔄 Conferma Rientro Veicolo", type="primary")

            if submit:
                idx = mappa[auto_sel]
                df_mod = df.copy()

                df_mod.loc[idx, COL_STATO] = "Disponibile"
                df_mod.loc[idx, COL_CLIENTE] = "N/D"
                df_mod.loc[idx, COL_DATA_INI] = ""
                df_mod.loc[idx, COL_DATA_FIN] = ""
                df_mod.loc[idx, COL_KM_FINALI] = km_finali
                if nota.strip():
                    df_mod.loc[idx, COL_NOTE_CHECKIN] = nota.strip()

                ok, risposta = invia_payload({
                    "action": "update_all",
                    "rows": payload_dataframe(df_mod)
                })

                if ok:
                    st.success("✅ Veicolo rientrato correttamente. Lo storico del noleggio è rimasto salvato.")
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Errore dal server: {risposta.get('message', 'Sconosciuto')}")

# =========================================================
# TAB 3 - STORICO & RICERCA
# =========================================================
with tab_storico:
    st.subheader("📜 Storico Noleggi, Flotta e Contabilità")

    if df.empty:
        st.info("Nessun dato nel registro.")
    else:
        ricerca = st.text_input(
            "Cerca per Targa, Cliente, Marca, Modello, Fattura o Descrizione"
        ).strip().lower()

        df_view = df.copy()

        if ricerca:
            mask = df_view.astype(str).apply(
                lambda row: row.str.lower().str.contains(
                    ricerca, na=False, regex=False
                ).any(),
                axis=1
            )
            df_view = df_view[mask]

        filtro = st.selectbox(
            "Tipo di record",
            ["Tutti", "Veicoli", "Noleggi", "Contabilità"]
        )

        if filtro == "Veicoli":
            df_view = df_view[df_view[COL_TIPO_RECORD] == TIPO_VEICOLO]
        elif filtro == "Noleggi":
            df_view = df_view[df_view[COL_TIPO_RECORD] == TIPO_NOLEGGIO]
        elif filtro == "Contabilità":
            df_view = df_view[df_view[COL_TIPO_RECORD] == TIPO_CONTABILITA]

        st.dataframe(df_view, use_container_width=True, hide_index=True)

# =========================================================
# TAB 4 - REGISTRO FLOTTA
# =========================================================
with tab_registro:
    st.subheader("📋 Registro Flotta")

    df_veicoli = righe_veicoli(df)

    if df_veicoli.empty:
        st.info("Nessun veicolo disponibile.")
    else:
        filtro = st.radio(
            "Mostra:",
            [
                "Tutti i veicoli",
                "🟢 Solo Disponibili",
                "🔵 Solo Noleggiate",
                "🟠 Solo in Manutenzione"
            ],
            horizontal=True
        )

        view = df_veicoli.copy()
        stato = view[COL_STATO].astype(str).str.strip().str.lower()

        if filtro == "🟢 Solo Disponibili":
            view = view[stato == "disponibile"]
        elif filtro == "🔵 Solo Noleggiate":
            view = view[stato.isin(["noleggiata", "noleggiato", "in uso"])]
        elif filtro == "🟠 Solo in Manutenzione":
            view = view[stato.str.contains("manutenzione", na=False)]

        colonne = [
            COL_TARGA, COL_MARCA, COL_MODELLO, COL_CATEGORIA,
            COL_PREZZO, COL_ANNO, COL_CLIENTE, COL_STATO,
            COL_KM_INIZIALI, COL_KM_FINALI, COL_NOTE1
        ]
        colonne = [c for c in colonne if c in view.columns]
        st.dataframe(view[colonne], use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("⚙️ Gestione Veicolo")

        targhe = view[COL_TARGA].astype(str).tolist()
        if targhe:
            targa = st.selectbox("Seleziona la Targa", targhe, key="sel_ges_veicolo")
            righe = df_veicoli[df_veicoli[COL_TARGA].astype(str) == targa]

            if not righe.empty:
                idx = righe.index[0]
                dati = righe.iloc[0]

                with st.form("form_modifica_veicolo"):
                    a, b = st.columns(2)

                    with a:
                        marca = st.text_input("Marca", str(dati.get(COL_MARCA, "")))
                        modello = st.text_input("Modello", str(dati.get(COL_MODELLO, "")))
                        categoria = st.text_input("Categoria", str(dati.get(COL_CATEGORIA, "")))
                        prezzo = st.number_input(
                            "Prezzo Giornaliero (€)",
                            min_value=0.0,
                            value=valore_numero(dati.get(COL_PREZZO, 50), 50)
                        )

                    with b:
                        anno = int(valore_numero(dati.get(COL_ANNO, 2023), 2023))
                        anno = st.number_input("Anno", min_value=1990, max_value=2030, value=anno)
                        stati = ["Disponibile", "Noleggiata", "In Manutenzione"]
                        stato_attuale = str(dati.get(COL_STATO, "Disponibile"))

                        try:
                            stato_index = [x.lower() for x in stati].index(stato_attuale.lower())
                        except ValueError:
                            stato_index = 0

                        stato_nuovo = st.selectbox("Stato", stati, index=stato_index)
                        cliente = st.text_input("Cliente", str(dati.get(COL_CLIENTE, "N/D")))
                        note = st.text_input("Note", str(dati.get(COL_NOTE, "")))

                    salva = st.form_submit_button("✏️ Salva Modifiche", type="primary")

                if salva:
                    df_mod = df.copy()
                    df_mod.loc[idx, COL_MARCA] = marca
                    df_mod.loc[idx, COL_MODELLO] = modello
                    df_mod.loc[idx, COL_CATEGORIA] = categoria
                    df_mod.loc[idx, COL_PREZZO] = float(prezzo)
                    df_mod.loc[idx, COL_ANNO] = int(anno)
                    df_mod.loc[idx, COL_STATO] = stato_nuovo
                    df_mod.loc[idx, COL_CLIENTE] = cliente
                    df_mod.loc[idx, COL_NOTE] = note

                    ok, risposta = invia_payload({
                        "action": "update_all",
                        "rows": payload_dataframe(df_mod)
                    })

                    if ok:
                        st.success("✅ Veicolo modificato con successo.")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Errore: {risposta.get('message', '')}")

# =========================================================
# TAB 5 - NUOVO VEICOLO
# =========================================================
with tab_nuovo_veicolo:
    st.subheader("🚗 Aggiungi un Nuovo Veicolo alla Flotta")

    with st.form("form_nuovo_veicolo", clear_on_submit=True):
        c1, c2 = st.columns(2)

        with c1:
            targa = st.text_input("TARGA *").strip().upper()
            marca = st.text_input("MARCA *").strip()
            modello = st.text_input("MODELLO *").strip()
            categoria = st.selectbox(
                "CATEGORIA",
                ["Utilitaria", "Berlina", "SUV", "Station Wagon", "Furgone"]
            )

        with c2:
            km_iniziali = st.number_input("Km Iniziali *", min_value=0, value=0, step=100)
            prezzo = st.number_input("Prezzo Giornaliero (€) *", min_value=0.0, value=50.0)
            anno = st.number_input("Anno Immatricolazione", min_value=1990, max_value=2030, value=2023)
            stato = st.selectbox("Stato Veicolo *", ["Disponibile", "In Manutenzione"])
            note1 = st.text_input("Note1")

        submit = st.form_submit_button("💾 Salva Nuovo Veicolo", type="primary")

    if submit:
        if not targa or not marca or not modello:
            st.error("Compila Targa, Marca e Modello.")
        else:
            # Evita di creare una seconda macchina con la stessa targa.
            esiste = (
                not df.empty
                and (df[COL_TIPO_RECORD] == TIPO_VEICOLO)
                and (df[COL_TARGA].astype(str).str.upper() == targa)
            ).any()

            if esiste:
                st.error(f"⚠️ La targa {targa} esiste già nella flotta.")
            else:
                payload = {
                    "action": "append",
                    COL_TARGA: targa,
                    COL_MARCA: marca,
                    COL_MODELLO: modello,
                    COL_CATEGORIA: categoria,
                    COL_PREZZO: str(prezzo),
                    COL_ANNO: str(int(anno)),
                    COL_CLIENTE: "N/D",
                    COL_STATO: stato,
                    COL_DATA_INI: "",
                    COL_DATA_FIN: "",
                    COL_NOTE: "",
                    COL_NOTE1: note1,
                    COL_NOTE_CHECKIN: "",
                    COL_KM_INIZIALI: str(km_iniziali),
                    COL_KM_FINALI: "",
                    COL_PAGAMENTO: "",
                    COL_CAUZIONE: "0.0",
                    COL_ENTRATE_USCITE: "",
                    COL_MANUTENZIONE: "",
                    COL_COSTO: "0.0",
                    COL_FATTURA: "No",
                    COL_NUMERO_FATTURA: "",
                    COL_DATA_FATTURA: "",
                    COL_STATO_FATTURA: "",
                    COL_TIPO_RECORD: TIPO_VEICOLO
                }

                ok, risposta = invia_payload(payload, timeout=15)

                if ok:
                    st.success(f"✅ Veicolo {targa} aggiunto.")
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Errore server: {risposta.get('message', 'Sconosciuto')}")

# =========================================================
# TAB 6 - NUOVO CLIENTE / NOLEGGIO
# =========================================================
with tab_nuovo_cliente:
    st.subheader("👤 Nuovo Cliente / Nuovo Noleggio")

    df_veicoli = righe_veicoli(df)
    stato_veicoli = df_veicoli[COL_STATO].astype(str).str.strip().str.lower() if not df_veicoli.empty else pd.Series(dtype=str)

    df_disponibili = df_veicoli[
        stato_veicoli.isin(["disponibile", "disponibili", "libera", "libero", ""])
    ] if not df_veicoli.empty else pd.DataFrame()

    if df_disponibili.empty:
        st.warning("⚠️ Al momento non ci sono veicoli disponibili.")
    else:
        opzioni = []
        mappa = {}

        for idx, r in df_disponibili.iterrows():
            targa = str(r.get(COL_TARGA, ""))
            marca = str(r.get(COL_MARCA, ""))
            modello = str(r.get(COL_MODELLO, ""))
            prezzo_base = valore_numero(r.get(COL_PREZZO, 50), 50)

            label = f"{targa} - {marca} {modello} (€{prezzo_base:.2f}/giorno)"
            opzioni.append(label)
            mappa[label] = (idx, targa, prezzo_base)

        with st.form("form_nuovo_cliente", clear_on_submit=True):
            c1, c2 = st.columns(2)

            with c1:
                nome_cliente = st.text_input("Nome e Cognome Cliente *")
                auto_label = st.selectbox("Seleziona Veicolo Disponibile *", opzioni)

                prezzo_default = mappa[auto_label][2]
                prezzo_applicato = st.number_input(
                    "Prezzo Giornaliero Applicato (€) *",
                    min_value=0.0,
                    value=float(prezzo_default)
                )

            with c2:
                data_inizio = st.date_input("Data Inizio Noleggio *", date.today())
                data_fine = st.date_input("Data Fine Noleggio *", date.today())
                pagamento = st.selectbox(
                    "Metodo di Pagamento",
                    ["Contanti", "Carta di Credito", "Bonifico", "Altro"]
                )
                cauzione = st.number_input(
                    "Cauzione / Deposito (€)",
                    min_value=0.0,
                    value=0.0,
                    step=50.0
                )

            note = st.text_area("Note / Dettagli Cliente")

            st.markdown("### 🧾 Fatturazione")
            f1, f2 = st.columns(2)

            with f1:
                fattura = st.selectbox("Fattura", ["No", "Sì"], index=1)
                stato_fattura = st.selectbox(
                    "Stato Fattura",
                    ["Da emettere", "Emessa", "Pagata", "Annullata"]
                )

            with f2:
                numero_fattura = st.text_input(
                    "Numero Fattura",
                    value=numero_fattura_suggerito(df)
                )
                data_fattura = st.date_input("Data Fattura", date.today())

            submit = st.form_submit_button(
                "💾 Salva Cliente e Avvia Noleggio",
                type="primary"
            )

        if submit:
            if not nome_cliente.strip():
                st.error("Inserisci il nome del cliente.")
            elif data_fine < data_inizio:
                st.error("La data di fine non può essere precedente alla data di inizio.")
            else:
                idx_veicolo, targa, _ = mappa[auto_label]
                giorni = max(1, (data_fine - data_inizio).days)
                costo_totale = giorni * float(prezzo_applicato)

                df_mod = df.copy()

                # 1) AGGIORNA SOLO LA RIGA DEL VEICOLO
                #    La macchina resta una sola.
                df_mod.loc[idx_veicolo, COL_STATO] = "Noleggiata"
                df_mod.loc[idx_veicolo, COL_CLIENTE] = nome_cliente.strip()

                # 2) CREA UNA NUOVA RIGA SOLO PER IL NOLEGGIO/STORICO
                nuova_riga = {c: "" for c in COLONNE_ATTESE}
                nuova_riga.update({
                    COL_TARGA: targa,
                    COL_MARCA: df.loc[idx_veicolo, COL_MARCA],
                    COL_MODELLO: df.loc[idx_veicolo, COL_MODELLO],
                    COL_CATEGORIA: "Noleggio",
                    COL_PREZZO: float(prezzo_applicato),
                    COL_ANNO: df.loc[idx_veicolo, COL_ANNO],
                    COL_CLIENTE: nome_cliente.strip(),
                    COL_STATO: "Noleggiata",
                    COL_DATA_INI: str(data_inizio),
                    COL_DATA_FIN: str(data_fine),
                    COL_NOTE: note.strip(),
                    COL_KM_INIZIALI: df.loc[idx_veicolo, COL_KM_INIZIALI],
                    COL_KM_FINALI: "",
                    COL_PAGAMENTO: pagamento,
                    COL_CAUZIONE: float(cauzione),
                    # IL NOLEGGIO È UNA ENTRATA
                    COL_ENTRATE_USCITE: float(costo_totale),
                    COL_MANUTENZIONE: "",
                    COL_COSTO: float(costo_totale),
                    COL_FATTURA: fattura,
                    COL_NUMERO_FATTURA: numero_fattura.strip() if fattura == "Sì" else "",
                    COL_DATA_FATTURA: str(data_fattura) if fattura == "Sì" else "",
                    COL_STATO_FATTURA: stato_fattura if fattura == "Sì" else "Da emettere",
                    COL_TIPO_RECORD: TIPO_NOLEGGIO
                })

                df_mod = pd.concat(
                    [df_mod, pd.DataFrame([nuova_riga])],
                    ignore_index=True
                )

                ok, risposta = invia_payload({
                    "action": "update_all",
                    "rows": payload_dataframe(df_mod)
                })

                if ok:
                    st.success(
                        f"✅ Noleggio registrato per {nome_cliente} - {targa}. "
                        f"Totale: € {costo_totale:,.2f}. "
                        "La macchina non è stata duplicata."
                    )
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Errore server: {risposta.get('message', 'Sconosciuto')}")

# =========================================================
# TAB 7 - FATTURAZIONE
# =========================================================
with tab_fatturazione:
    st.subheader("🧾 Gestione Fatturazione")

    df_fatt = righe_noleggi(df)

    if df_fatt.empty:
        st.info("Nessun noleggio disponibile per la fatturazione.")
    else:
        colonne = [
            COL_TARGA, COL_CLIENTE, COL_DATA_INI, COL_DATA_FIN,
            COL_COSTO, COL_FATTURA, COL_NUMERO_FATTURA,
            COL_DATA_FATTURA, COL_STATO_FATTURA
        ]
        colonne = [c for c in colonne if c in df_fatt.columns]
        st.dataframe(df_fatt[colonne], use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### ✏️ Inserisci / Modifica Dati Fattura")

        opzioni = {}
        for idx, r in df_fatt.iterrows():
            label = (
                f"{r.get(COL_TARGA, '')} - "
                f"{r.get(COL_CLIENTE, '')} - "
                f"€ {costo_riga_noleggio(r):,.2f}"
            )
            opzioni[label] = idx

        selezione = st.selectbox("Seleziona il noleggio", list(opzioni.keys()))
        idx_fattura = opzioni[selezione]
        dati = df.loc[idx_fattura]

        with st.form("form_fattura"):
            a, b = st.columns(2)

            with a:
                fattura_edit = st.selectbox(
                    "Fattura",
                    ["No", "Sì"],
                    index=1 if str(dati.get(COL_FATTURA, "")).strip().lower() == "sì" else 0
                )
                numero_edit = st.text_input(
                    "Numero Fattura",
                    str(dati.get(COL_NUMERO_FATTURA, ""))
                )

            with b:
                data_val = pd.to_datetime(
                    dati.get(COL_DATA_FATTURA, ""),
                    errors="coerce"
                )
                data_default = date.today() if pd.isna(data_val) else data_val.date()
                data_edit = st.date_input("Data Fattura", data_default)

                stati = ["Da emettere", "Emessa", "Pagata", "Annullata"]
                stato_attuale = str(dati.get(COL_STATO_FATTURA, "Da emettere"))
                try:
                    stato_index = [x.lower() for x in stati].index(stato_attuale.lower())
                except ValueError:
                    stato_index = 0

                stato_edit = st.selectbox("Stato Fattura", stati, index=stato_index)

            salva = st.form_submit_button("💾 Salva Dati Fattura", type="primary")

        if salva:
            df_mod = df.copy()
            df_mod.loc[idx_fattura, COL_FATTURA] = fattura_edit
            df_mod.loc[idx_fattura, COL_NUMERO_FATTURA] = numero_edit.strip()
            df_mod.loc[idx_fattura, COL_DATA_FATTURA] = str(data_edit) if fattura_edit == "Sì" else ""
            df_mod.loc[idx_fattura, COL_STATO_FATTURA] = stato_edit if fattura_edit == "Sì" else "Da emettere"

            ok, risposta = invia_payload({
                "action": "update_all",
                "rows": payload_dataframe(df_mod)
            })

            if ok:
                st.success("✅ Dati della fattura aggiornati.")
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"Errore: {risposta.get('message', 'Sconosciuto')}")

# =========================================================
# TAB 8 - CONTABILITÀ & SPESE
# =========================================================
with tab_contabilita:
    st.subheader("💰 Gestione Spese e Ricavi Extra")

    with st.form("form_contabilita", clear_on_submit=True):
        c1, c2 = st.columns(2)

        with c1:
            tipo = st.selectbox(
                "Tipo di Movimento *",
                ["Spesa (Uscita)", "Entrata Extra"]
            )
            categoria = st.selectbox(
                "Categoria",
                [
                    "Manutenzione Straordinaria",
                    "Assicurazione / Bollo",
                    "Riparazione Meccanica",
                    "Spese Amministrative / Gestione",
                    "Carburante / Spese Varie",
                    "Altro"
                ]
            )
            importo = st.number_input(
                "Importo (€) *",
                min_value=0.0,
                value=0.0,
                step=10.0
            )

        with c2:
            data_mov = st.date_input("Data Movimento *", date.today())
            targa = st.text_input("Targa Veicolo (Opzionale)")
            descrizione = st.text_area("Descrizione / Note *")

        submit = st.form_submit_button("💾 Salva Movimento Contabile", type="primary")

    if submit:
        if not descrizione.strip() or importo <= 0:
            st.error("Inserisci una descrizione e un importo superiore a zero.")
        else:
            valore = -abs(importo) if tipo == "Spesa (Uscita)" else abs(importo)
            manutenzione = categoria if tipo == "Spesa (Uscita)" else ""

            # MAPPATURA ESPLICITA: ogni dato va nella sua colonna.
            # In particolare il tipo di movimento NON va in MARCA: va in NOTE1.
            payload = {
                "action": "append",
                COL_TARGA: targa.upper().strip() if targa.strip() else "EXTRA",
                COL_MARCA: "",
                COL_MODELLO: "",
                COL_CATEGORIA: "Contabilità",
                COL_PREZZO: str(importo),
                COL_ANNO: str(data_mov.year),
                COL_CLIENTE: "",
                COL_STATO: "Registrato",
                COL_DATA_INI: str(data_mov),
                COL_DATA_FIN: str(data_mov),
                COL_NOTE: descrizione.strip(),
                COL_NOTE1: tipo,
                COL_NOTE_CHECKIN: "",
                COL_KM_INIZIALI: "0",
                COL_KM_FINALI: "0",
                COL_PAGAMENTO: "N/D",
                COL_CAUZIONE: "0.0",
                COL_ENTRATE_USCITE: str(valore),
                COL_MANUTENZIONE: manutenzione,
                COL_COSTO: "0.0",
                COL_FATTURA: "No",
                COL_NUMERO_FATTURA: "",
                COL_DATA_FATTURA: "",
                COL_STATO_FATTURA: "",
                COL_TIPO_RECORD: TIPO_CONTABILITA
            }

            ok, risposta = invia_payload(payload, timeout=15)

            if ok:
                st.success("✅ Movimento contabile registrato.")
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"Errore server: {risposta.get('message', 'Sconosciuto')}")

    st.markdown("---")
    st.subheader("📊 Storico Movimenti Contabili")

    df_contab = righe_contabilita(df)

    if df_contab.empty:
        st.info("Nessun movimento contabile registrato.")
    else:
        colonne = [
            COL_TARGA, COL_DATA_INI, COL_MARCA, COL_CATEGORIA,
            COL_NOTE, COL_ENTRATE_USCITE, COL_MANUTENZIONE
        ]
        colonne = [c for c in colonne if c in df_contab.columns]
        st.dataframe(df_contab[colonne], use_container_width=True, hide_index=True)

        entrate = df_contab[COL_ENTRATE_USCITE].apply(valore_numero)
        totale_extra = entrate[entrate > 0].sum()
        totale_spese = abs(entrate[entrate < 0].sum())

        a, b = st.columns(2)
        a.metric("➕ Entrate Extra", f"€ {totale_extra:,.2f}")
        b.metric("💸 Spese", f"€ {totale_spese:,.2f}")
