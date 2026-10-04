import streamlit as st
import pandas as pd
import requests
from datetime import date
import time

# =========================================================
# CONFIGURAZIONE
# =========================================================
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyKMhlDddoULMNfyx_1sdV_63rEofWq-U2hyzIfVs1yao-Gy5NFuH5f41WWKbJoHitT/exec"

# Colonne principali del Google Sheet / Excel
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

# Aggiunte per gestione economica/fatturazione
COL_COSTO = "Costo Totale"
COL_FATTURA = "FATTURA"
COL_NUMERO_FATTURA = "NUMERO FATTURA"
COL_DATA_FATTURA = "DATA FATTURA"
COL_STATO_FATTURA = "STATO FATTURA"

# Ordine completo previsto nel foglio
COLONNE_ATTESE = [
    COL_TARGA,
    COL_MARCA,
    COL_MODELLO,
    COL_CATEGORIA,
    COL_PREZZO,
    COL_ANNO,
    COL_CLIENTE,
    COL_STATO,
    COL_DATA_INI,
    COL_DATA_FIN,
    COL_NOTE,
    COL_NOTE1,
    COL_NOTE_CHECKIN,
    COL_KM_INIZIALI,
    COL_KM_FINALI,
    COL_PAGAMENTO,
    COL_CAUZIONE,
    COL_ENTRATE_USCITE,
    COL_MANUTENZIONE,
    COL_COSTO,
    COL_FATTURA,
    COL_NUMERO_FATTURA,
    COL_DATA_FATTURA,
    COL_STATO_FATTURA,
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
    """Trova una colonna anche se il nome non coincide perfettamente."""
    for col in df.columns:
        col_lower = str(col).strip().lower()
        for kw in keywords:
            if kw.lower() in col_lower:
                return col
    return None


def valore_numero(value, default=0.0):
    """Converte in numero gestendo valori vuoti e formati italiani."""
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

    # Gestione 1.234,56 e 1234,56
    if "," in testo and "." in testo:
        testo = testo.replace(".", "").replace(",", ".")
    elif "," in testo:
        testo = testo.replace(",", ".")

    try:
        return float(testo)
    except Exception:
        return default


def formatta_date_df(df_input):
    df_f = df_input.copy()

    for col in [COL_DATA_INI, COL_DATA_FIN, COL_DATA_FATTURA]:
        if col in df_f.columns:
            df_f[col] = (
                pd.to_datetime(df_f[col], errors="coerce")
                .dt.strftime("%Y-%m-%d")
                .fillna("")
            )

    return df_f


def prepara_dataframe(df_input):
    """
    Garantisce che il DataFrame abbia tutte le colonne previste.
    Le colonne mancanti vengono aggiunte vuote senza spostare quelle esistenti.
    """
    df_out = df_input.copy()

    for col in COLONNE_ATTESE:
        if col not in df_out.columns:
            df_out[col] = ""

    return df_out


def payload_dataframe(df_input):
    """Prepara tutte le righe per update_all."""
    df_out = prepara_dataframe(df_input)
    df_out = formatta_date_df(df_out)

    # Ordina le colonne secondo la struttura prevista.
    # Eventuali colonne extra vengono mantenute in fondo.
    colonne_extra = [c for c in df_out.columns if c not in COLONNE_ATTESE]
    ordine = COLONNE_ATTESE + colonne_extra
    df_out = df_out[ordine]

    return df_out.fillna("").astype(str).to_dict(orient="records")


def invia_payload(payload, timeout=20):
    """Invia i dati all'Apps Script e restituisce (successo, risposta)."""
    try:
        res = requests.post(
            APPS_SCRIPT_URL,
            json=payload,
            timeout=timeout
        )

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
    """
    Calcola il prossimo numero fattura nel formato N/ANNO.
    Esempio: 1/2026, 2/2026...
    """
    anno_corrente = date.today().year

    if COL_NUMERO_FATTURA not in df.columns:
        return f"1/{anno_corrente}"

    numeri = []

    for valore in df[COL_NUMERO_FATTURA].dropna().astype(str):
        valore = valore.strip()
        if not valore:
            continue

        try:
            parte_numero = valore.split("/")[0].strip()
            numeri.append(int(parte_numero))
        except Exception:
            continue

    prossimo = max(numeri, default=0) + 1
    return f"{prossimo}/{anno_corrente}"


def stato_normalizzato(value):
    return str(value).strip().lower()


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
# CARICAMENTO GOOGLE SHEETS
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
# AVVISO STRUTTURA FOGLIO
# =========================================================
colonne_mancanti = [c for c in COLONNE_ATTESE if c not in df.columns]

if colonne_mancanti:
    st.warning(
        "⚠️ Nel foglio mancano alcune colonne. "
        "Il gestionale le creerà nel DataFrame, ma per salvarle correttamente "
        "devi aggiungerle anche nel Google Sheet: "
        + ", ".join(colonne_mancanti)
    )


# =========================================================
# TAB
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
    st.subheader("📊 Panoramica Generale della Flotta")

    if not df.empty:
        df_dash = df.copy()

        c_stato = COL_STATO if COL_STATO in df_dash.columns else trova_col(df_dash, ["stato"])
        c_categoria = (
            COL_CATEGORIA
            if COL_CATEGORIA in df_dash.columns
            else trova_col(df_dash, ["categoria"])
        )

        if c_stato:
            df_dash["stato_clean"] = (
                df_dash[c_stato].astype(str).str.strip().str.lower()
            )

            tot_veicoli = len(df_dash)

            disponibili = len(
                df_dash[df_dash["stato_clean"] == "disponibile"]
            )

            noleggiate = len(
                df_dash[
                    df_dash["stato_clean"].isin(
                        ["noleggiata", "noleggiato", "in uso"]
                    )
                ]
            )

            manutenzione = len(
                df_dash[
                    df_dash["stato_clean"].str.contains(
                        "manutenzione",
                        na=False
                    )
                ]
            )
        else:
            tot_veicoli = len(df_dash)
            disponibili = 0
            noleggiate = 0
            manutenzione = 0

        fatturato_totale = 0.0

        if COL_COSTO in df_dash.columns:
            fatturato_totale = sum(
                valore_numero(x)
                for x in df_dash[COL_COSTO]
            )

        fatture_emesse = 0
        fatture_da_emettere = 0
        totale_fatturato = 0.0

        if COL_STATO_FATTURA in df_dash.columns:
            stato_fatt = (
                df_dash[COL_STATO_FATTURA]
                .astype(str)
                .str.strip()
                .str.lower()
            )

            fatture_emesse = int(
                stato_fatt.isin(["emessa", "pagata"]).sum()
            )

            fatture_da_emettere = int(
                stato_fatt.eq("da emettere").sum()
            )

        if COL_COSTO in df_dash.columns:
            for idx, row in df_dash.iterrows():
                stato_fattura = stato_normalizzato(
                    row.get(COL_STATO_FATTURA, "")
                )

                if stato_fattura in ["emessa", "pagata"]:
                    totale_fatturato += valore_numero(
                        row.get(COL_COSTO, 0)
                    )

        col1, col2, col3, col4, col5 = st.columns(5)

        col1.metric("🚗 Totale Veicoli", tot_veicoli)
        col2.metric("🟢 Disponibili", disponibili)
        col3.metric("🔵 Noleggiate", noleggiate)
        col4.metric("🟠 In Manutenzione", manutenzione)
        col5.metric("💶 Totale Noleggi", f"€ {fatturato_totale:,.2f}")

        st.markdown("---")

        f1, f2, f3 = st.columns(3)
        f1.metric("🧾 Fatture emesse/pagate", fatture_emesse)
        f2.metric("⏳ Fatture da emettere", fatture_da_emettere)
        f3.metric("💰 Totale fatturato", f"€ {totale_fatturato:,.2f}")

        st.markdown("---")

        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.markdown("### 📊 Stato dei Veicoli")

            if c_stato:
                df_stati = (
                    df_dash[c_stato]
                    .astype(str)
                    .str.strip()
                    .str.capitalize()
                    .value_counts()
                    .reset_index()
                )

                df_stati.columns = ["Stato", "Quantità"]
                st.bar_chart(df_stati.set_index("Stato"))

        with col_g2:
            st.markdown("### 🚙 Distribuzione per Categoria")

            if c_categoria:
                df_cat = (
                    df_dash[c_categoria]
                    .astype(str)
                    .str.strip()
                    .value_counts()
                    .reset_index()
                )

                df_cat.columns = ["Categoria", "Quantità"]
                st.bar_chart(df_cat.set_index("Categoria"))

    else:
        st.info("Nessun dato disponibile nel sistema.")


# =========================================================
# TAB 2 - RIENTRO VEICOLO
# =========================================================
with tab_rientro:
    st.subheader("🔑 Gestione Rientro Veicolo")

    if not df.empty:
        c_stato = COL_STATO if COL_STATO in df.columns else trova_col(df, ["stato"])
        c_targa = COL_TARGA if COL_TARGA in df.columns else trova_col(df, ["targa"])
        c_marca = COL_MARCA if COL_MARCA in df.columns else trova_col(df, ["marca"])
        c_modello = COL_MODELLO if COL_MODELLO in df.columns else trova_col(df, ["modello"])
        c_cliente = COL_CLIENTE if COL_CLIENTE in df.columns else trova_col(df, ["cliente"])

        if c_stato:
            df_temp = df.copy()
            df_temp["stato_pulito"] = (
                df_temp[c_stato].astype(str).str.strip().str.lower()
            )

            df_noleggiate = df_temp[
                df_temp["stato_pulito"].isin(
                    ["noleggiata", "noleggiato", "affittata", "in uso"]
                )
            ]
        else:
            df_noleggiate = pd.DataFrame()

        if df_noleggiate.empty:
            st.info("ℹ️ Al momento non risulta alcun veicolo in noleggio.")
        else:
            opzioni_rientro = []
            mappa_rientro = {}

            for idx, r in df_noleggiate.iterrows():
                t = str(r.get(c_targa, ""))
                m = str(r.get(c_marca, ""))
                mod = str(r.get(c_modello, ""))
                cli = str(r.get(c_cliente, "N/D"))

                label = f"{t} - {m} {mod} (Cliente: {cli})"
                opzioni_rientro.append(label)
                mappa_rientro[label] = idx

            with st.form("form_rientro"):
                auto_sel = st.selectbox(
                    "Seleziona Veicolo in Rientro *",
                    opzioni_rientro
                )

                km_finali_inseriti = st.number_input(
                    "Km Finali alla Consegna *",
                    min_value=0,
                    value=0,
                    step=100
                )

                nota_checkin = st.text_area(
                    "Note Check-in / Condizioni Veicolo",
                    placeholder="es. Condizioni ottime..."
                )

                submit_rientro = st.form_submit_button(
                    "🔄 Conferma Rientro Veicolo",
                    type="primary"
                )

            if submit_rientro:
                idx = mappa_rientro[auto_sel]
                df_agg = df.copy()

                try:
                    df_agg.loc[idx, COL_STATO] = "Disponibile"
                    df_agg.loc[idx, COL_CLIENTE] = "N/D"
                    df_agg.loc[idx, COL_DATA_INI] = ""
                    df_agg.loc[idx, COL_DATA_FIN] = ""

                    # Il costo rimane nello storico del noleggio.
                    # Non viene cancellato.

                    df_agg.loc[idx, COL_KM_FINALI] = km_finali_inseriti

                    if nota_checkin.strip():
                        df_agg.loc[idx, COL_NOTE_CHECKIN] = nota_checkin.strip()

                    rows_payload = payload_dataframe(df_agg)

                    ok, risposta = invia_payload({
                        "action": "update_all",
                        "rows": rows_payload
                    })

                    if ok:
                        st.success(
                            f"✅ Veicolo rientrato correttamente "
                            f"con {km_finali_inseriti} Km registrati!"
                        )
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(
                            f"Errore dal server: "
                            f"{risposta.get('message', 'Sconosciuto')}"
                        )

                except Exception as e:
                    st.error(f"Errore durante il rientro: {e}")

    else:
        st.info("Nessun dato disponibile nel sistema.")


# =========================================================
# TAB 3 - STORICO & RICERCA
# =========================================================
with tab_storico:
    st.subheader("📜 Storico e Ricerca Veicoli / Clienti")

    if not df.empty:
        search_query = st.text_input(
            "Cerca per Targa, Cliente, Marca, Modello o Fattura"
        ).strip().lower()

        if search_query:
            mask = df.astype(str).apply(
                lambda row: row.str.lower().str.contains(
                    search_query,
                    na=False,
                    regex=False
                ).any(),
                axis=1
            )

            df_filtered = df[mask]
        else:
            df_filtered = df

        st.dataframe(
            df_filtered,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Nessun dato nel registro.")


# =========================================================
# TAB 4 - REGISTRO FLOTTA
# =========================================================
with tab_registro:
    st.subheader("📋 Registro Completo della Flotta & Gestione")

    if not df.empty:
        c_stato_reg = (
            COL_STATO
            if COL_STATO in df.columns
            else trova_col(df, ["stato"])
        )

        if c_stato_reg:
            st.markdown("### 🔍 Filtra Flotta per Stato")

            filtro_stato = st.radio(
                "Mostra:",
                [
                    "Tutti i veicoli",
                    "🟢 Solo Disponibili",
                    "🔵 Solo Noleggiate",
                    "🟠 Solo in Manutenzione"
                ],
                horizontal=True
            )

            df_reg_view = df.copy()
            df_reg_view["stato_c"] = (
                df_reg_view[c_stato_reg]
                .astype(str)
                .str.strip()
                .str.lower()
            )

            if filtro_stato == "🟢 Solo Disponibili":
                df_reg_view = df_reg_view[
                    df_reg_view["stato_c"] == "disponibile"
                ]

            elif filtro_stato == "🔵 Solo Noleggiate":
                df_reg_view = df_reg_view[
                    df_reg_view["stato_c"].isin(
                        ["noleggiata", "noleggiato", "in uso"]
                    )
                ]

            elif filtro_stato == "🟠 Solo in Manutenzione":
                df_reg_view = df_reg_view[
                    df_reg_view["stato_c"].str.contains(
                        "manutenzione",
                        na=False
                    )
                ]

            df_reg_view = df_reg_view.drop(columns=["stato_c"])

            st.dataframe(
                df_reg_view,
                use_container_width=True,
                hide_index=True
            )

        else:
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

        st.markdown("---")
        st.subheader("⚙️ Gestione Veicolo")

        c_targa = COL_TARGA
        targhe_disponibili = (
            df[c_targa].astype(str).tolist()
            if c_targa in df.columns
            else []
        )

        if targhe_disponibili:
            targa_selezionata_ges = st.selectbox(
                "Seleziona la Targa",
                targhe_disponibili,
                key="sel_ges_veicolo"
            )

            riga_veicolo = df[
                df[c_targa].astype(str) == targa_selezionata_ges
            ]

            if not riga_veicolo.empty:
                idx_orig = riga_veicolo.index[0]
                dati_v = riga_veicolo.iloc[0]

                with st.form("form_modifica_elimina"):
                    col_m1, col_m2 = st.columns(2)

                    with col_m1:
                        mod_marca = st.text_input(
                            "Marca",
                            value=str(dati_v.get(COL_MARCA, ""))
                        )

                        mod_modello = st.text_input(
                            "Modello",
                            value=str(dati_v.get(COL_MODELLO, ""))
                        )

                        mod_categoria = st.text_input(
                            "Categoria",
                            value=str(dati_v.get(COL_CATEGORIA, ""))
                        )

                        mod_prezzo = st.number_input(
                            "Prezzo Giornaliero (€)",
                            min_value=0.0,
                            value=valore_numero(
                                dati_v.get(COL_PREZZO, 50),
                                50
                            )
                        )

                    with col_m2:
                        try:
                            anno_default = int(
                                valore_numero(
                                    dati_v.get(COL_ANNO, 2023),
                                    2023
                                )
                            )
                        except Exception:
                            anno_default = 2023

                        mod_anno = st.number_input(
                            "Anno",
                            min_value=1990,
                            max_value=2030,
                            value=anno_default
                        )

                        stati = [
                            "Disponibile",
                            "Noleggiata",
                            "In Manutenzione"
                        ]

                        stato_attuale = str(
                            dati_v.get(COL_STATO, "Disponibile")
                        )

                        try:
                            stato_index = [
                                x.lower() for x in stati
                            ].index(stato_attuale.lower())
                        except ValueError:
                            stato_index = 0

                        mod_stato = st.selectbox(
                            "Stato",
                            stati,
                            index=stato_index
                        )

                        mod_cliente = st.text_input(
                            "Cliente",
                            value=str(
                                dati_v.get(COL_CLIENTE, "N/D")
                            )
                        )

                        mod_note = st.text_input(
                            "Note",
                            value=str(
                                dati_v.get(COL_NOTE, "")
                            )
                        )

                    col_btn1, col_btn2 = st.columns(2)

                    btn_modifica = col_btn1.form_submit_button(
                        "✏️ Salva Modifiche",
                        type="primary"
                    )

                    btn_elimina = col_btn2.form_submit_button(
                        "🗑️ Elimina Veicolo",
                        type="secondary"
                    )

                    if btn_modifica:
                        try:
                            df_mod = df.copy()

                            df_mod.loc[idx_orig, COL_MARCA] = str(mod_marca)
                            df_mod.loc[idx_orig, COL_MODELLO] = str(mod_modello)
                            df_mod.loc[idx_orig, COL_CATEGORIA] = str(mod_categoria)
                            df_mod.loc[idx_orig, COL_PREZZO] = float(mod_prezzo)
                            df_mod.loc[idx_orig, COL_ANNO] = int(mod_anno)
                            df_mod.loc[idx_orig, COL_STATO] = str(mod_stato)
                            df_mod.loc[idx_orig, COL_CLIENTE] = str(mod_cliente)
                            df_mod.loc[idx_orig, COL_NOTE] = str(mod_note)

                            ok, risposta = invia_payload({
                                "action": "update_all",
                                "rows": payload_dataframe(df_mod)
                            })

                            if ok:
                                st.success(
                                    f"✅ Veicolo {targa_selezionata_ges} "
                                    "modificato con successo!"
                                )
                                st.cache_data.clear()
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(
                                    f"Errore durante il salvataggio: "
                                    f"{risposta.get('message', '')}"
                                )

                        except Exception as e:
                            st.error(f"Errore: {e}")

                    if btn_elimina:
                        try:
                            df_del = df.drop(
                                idx_orig
                            ).reset_index(drop=True)

                            ok, risposta = invia_payload({
                                "action": "update_all",
                                "rows": payload_dataframe(df_del)
                            })

                            if ok:
                                st.success(
                                    f"🗑️ Veicolo {targa_selezionata_ges} "
                                    "eliminato con successo!"
                                )
                                st.cache_data.clear()
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(
                                    f"Errore durante l'eliminazione: "
                                    f"{risposta.get('message', '')}"
                                )

                        except Exception as e:
                            st.error(f"Errore: {e}")

        else:
            st.info("Nessuna targa disponibile per la gestione.")

    else:
        st.info("Nessun dato disponibile nel registro.")


# =========================================================
# TAB 5 - NUOVO VEICOLO
# =========================================================
with tab_nuovo_veicolo:
    st.subheader("🚗 Aggiungi un Nuovo Veicolo alla Flotta")

    with st.form("form_nuovo_veicolo", clear_on_submit=True):
        c1, c2 = st.columns(2)

        with c1:
            targa = st.text_input(f"{COL_TARGA} *").strip().upper()
            marca = st.text_input(f"{COL_MARCA} *").strip()
            modello = st.text_input(f"{COL_MODELLO} *").strip()

            categoria = st.selectbox(
                COL_CATEGORIA,
                [
                    "Utilitaria",
                    "Berlina",
                    "SUV",
                    "Station Wagon",
                    "Furgone"
                ]
            )

        with c2:
            km_iniziali = st.number_input(
                "Km Iniziali *",
                min_value=0,
                value=0,
                step=100
            )

            prezzo_giornaliero = st.number_input(
                f"{COL_PREZZO} *",
                min_value=0.0,
                value=50.0
            )

            anno_imm = st.number_input(
                COL_ANNO,
                min_value=1990,
                max_value=2030,
                value=2023
            )

            stato = st.selectbox(
                f"{COL_STATO} *",
                ["Disponibile", "In Manutenzione"]
            )

            note1 = st.text_input(
                COL_NOTE1,
                placeholder="Eventuali annotazioni sul veicolo..."
            )

        submit_veicolo = st.form_submit_button(
            "💾 Salva Nuovo Veicolo",
            type="primary"
        )

    if submit_veicolo:
        if not targa or not marca or not modello:
            st.error(
                "Compila i campi obbligatori: Targa, Marca e Modello."
            )
        else:
            payload = {
                "action": "append",

                COL_TARGA: targa,
                COL_MARCA: marca,
                COL_MODELLO: modello,
                COL_CATEGORIA: categoria,
                COL_PREZZO: str(prezzo_giornaliero),
                COL_ANNO: str(int(anno_imm)),
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
                COL_STATO_FATTURA: "Da emettere"
            }

            ok, risposta = invia_payload(payload, timeout=15)

            if ok:
                st.success(
                    f"✅ Veicolo {targa} aggiunto con successo!"
                )
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()
            else:
                st.error(
                    f"Errore server: "
                    f"{risposta.get('message', 'Sconosciuto')}"
                )


# =========================================================
# TAB 6 - NUOVO CLIENTE / NOLEGGIO
# =========================================================
with tab_nuovo_cliente:
    st.subheader("👤 Registrazione Nuovo Cliente e Noleggio")

    if not df.empty:
        c_stato = COL_STATO if COL_STATO in df.columns else trova_col(df, ["stato"])
        c_targa = COL_TARGA if COL_TARGA in df.columns else trova_col(df, ["targa"])
        c_marca = COL_MARCA if COL_MARCA in df.columns else trova_col(df, ["marca"])
        c_modello = COL_MODELLO if COL_MODELLO in df.columns else trova_col(df, ["modello"])
        c_prezzo = COL_PREZZO if COL_PREZZO in df.columns else trova_col(df, ["prezzo"])

        df_temp = df.copy()

        if c_stato:
            df_temp["stato_pulito"] = (
                df_temp[c_stato].astype(str).str.strip().str.lower()
            )

            df_disponibili = df_temp[
                df_temp["stato_pulito"].isin(
                    ["disponibile", "disponibili", "libera", "libero", ""]
                )
            ]
        else:
            df_disponibili = pd.DataFrame()

        if df_disponibili.empty:
            st.warning(
                "⚠️ Al momento non ci sono veicoli disponibili."
            )
        else:
            opzioni_auto = []
            mappa_auto = {}

            for idx, r in df_disponibili.iterrows():
                t = str(r.get(c_targa, ""))
                m = str(r.get(c_marca, ""))
                mod = str(r.get(c_modello, ""))
                p = r.get(c_prezzo, 0.0)

                p_val = valore_numero(p, 50.0)

                label = (
                    f"{t} - {m} {mod} "
                    f"(Prezzo base: €{p_val:.2f}/giorno)"
                )

                opzioni_auto.append(label)
                mappa_auto[label] = (idx, t, p_val)

            with st.form("form_nuovo_cliente", clear_on_submit=True):
                c1, c2 = st.columns(2)

                with c1:
                    nome_cliente = st.text_input(
                        "Nome e Cognome Cliente *",
                        placeholder="es. Mario Rossi"
                    )

                    auto_scelta_label = st.selectbox(
                        "Seleziona Veicolo Disponibile *",
                        opzioni_auto
                    )

                    prezzo_default = (
                        mappa_auto[auto_scelta_label][2]
                        if auto_scelta_label in mappa_auto
                        else 50.0
                    )

                    prezzo_personalizzato = st.number_input(
                        "Prezzo Giornaliero Applicato (€) *",
                        min_value=0.0,
                        value=float(prezzo_default)
                    )

                with c2:
                    data_inizio_cli = st.date_input(
                        "Data Inizio Noleggio *",
                        date.today()
                    )

                    data_fine_cli = st.date_input(
                        "Data Fine Noleggio *",
                        date.today()
                    )

                    metodo_pagamento = st.selectbox(
                        "Metodo di Pagamento",
                        [
                            "Contanti",
                            "Carta di Credito",
                            "Bonifico",
                            "Altro"
                        ]
                    )

                    cauzione_importo = st.number_input(
                        "Cauzione / Deposito (€)",
                        min_value=0.0,
                        value=0.0,
                        step=50.0
                    )

                    note_cli = st.text_area(
                        "Note / Dettagli Cliente",
                        placeholder="Eventuali annotazioni..."
                    )

                st.markdown("### 🧾 Fatturazione")

                f1, f2 = st.columns(2)

                with f1:
                    fattura = st.selectbox(
                        "Fattura",
                        ["No", "Sì"],
                        index=1
                    )

                    stato_fattura = st.selectbox(
                        "Stato Fattura",
                        [
                            "Da emettere",
                            "Emessa",
                            "Pagata",
                            "Annullata"
                        ]
                    )

                with f2:
                    numero_fattura = st.text_input(
                        "Numero Fattura",
                        placeholder="es. 1/2026"
                    )

                    data_fattura = st.date_input(
                        "Data Fattura",
                        date.today()
                    )

                submit_cliente = st.form_submit_button(
                    "💾 Salva Cliente e Avvia Noleggio",
                    type="primary"
                )

            if submit_cliente:
                if not nome_cliente.strip():
                    st.error("Inserisci il nome e cognome del cliente.")

                elif data_fine_cli < data_inizio_cli:
                    st.error(
                        "La data di fine noleggio non può essere precedente "
                        "alla data di inizio."
                    )

                elif not auto_scelta_label:
                    st.error("Seleziona un veicolo valido.")

                else:
                    idx_veicolo = mappa_auto[auto_scelta_label][0]
                    targa_selezionata = mappa_auto[auto_scelta_label][1]

                    try:
                        dati_base = df.loc[idx_veicolo]

                        giorni = (
                            data_fine_cli - data_inizio_cli
                        ).days

                        # Un noleggio con stessa data di inizio/fine
                        # viene considerato di almeno 1 giorno.
                        giorni = max(1, giorni)

                        costo_totale = (
                            giorni * prezzo_personalizzato
                        )

                        # IMPORTANTE:
                        # aggiorniamo la riga del veicolo esistente
                        # invece di creare un duplicato.
                        df_mod = df.copy()

                        df_mod.loc[idx_veicolo, COL_CLIENTE] = (
                            nome_cliente.strip()
                        )

                        df_mod.loc[idx_veicolo, COL_STATO] = (
                            "Noleggiata"
                        )

                        df_mod.loc[idx_veicolo, COL_PREZZO] = (
                            float(prezzo_personalizzato)
                        )

                        df_mod.loc[idx_veicolo, COL_DATA_INI] = (
                            str(data_inizio_cli)
                        )

                        df_mod.loc[idx_veicolo, COL_DATA_FIN] = (
                            str(data_fine_cli)
                        )

                        df_mod.loc[idx_veicolo, COL_COSTO] = (
                            float(costo_totale)
                        )

                        df_mod.loc[idx_veicolo, COL_PAGAMENTO] = (
                            metodo_pagamento
                        )

                        df_mod.loc[idx_veicolo, COL_CAUZIONE] = (
                            float(cauzione_importo)
                        )

                        df_mod.loc[idx_veicolo, COL_NOTE] = (
                            note_cli.strip()
                        )

                        df_mod.loc[idx_veicolo, COL_FATTURA] = (
                            fattura
                        )

                        df_mod.loc[idx_veicolo, COL_NUMERO_FATTURA] = (
                            numero_fattura.strip()
                        )

                        df_mod.loc[idx_veicolo, COL_DATA_FATTURA] = (
                            str(data_fattura)
                            if fattura == "Sì"
                            else ""
                        )

                        df_mod.loc[idx_veicolo, COL_STATO_FATTURA] = (
                            stato_fattura
                            if fattura == "Sì"
                            else "Da emettere"
                        )

                        ok, risposta = invia_payload({
                            "action": "update_all",
                            "rows": payload_dataframe(df_mod)
                        })

                        if ok:
                            st.success(
                                f"✅ Noleggio registrato per "
                                f"{nome_cliente} - Veicolo "
                                f"{targa_selezionata}. "
                                f"Totale: € {costo_totale:,.2f}"
                            )

                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()

                        else:
                            st.error(
                                f"Errore dal server: "
                                f"{risposta.get('message', 'Sconosciuto')}"
                            )

                    except Exception as e:
                        st.error(f"Errore imprevisto: {e}")

    else:
        st.info("Nessun dato disponibile nel sistema.")


# =========================================================
# TAB 7 - FATTURAZIONE
# =========================================================
with tab_fatturazione:
    st.subheader("🧾 Gestione Fatturazione")

    if not df.empty:
        df_fatt = df.copy()

        # Mostriamo solo righe che rappresentano un noleggio/cliente.
        if COL_CLIENTE in df_fatt.columns:
            clienti_validi = (
                df_fatt[COL_CLIENTE]
                .astype(str)
                .str.strip()
                .ne("")
                &
                ~df_fatt[COL_CLIENTE]
                .astype(str)
                .str.upper()
                .eq("N/D")
            )

            df_fatt = df_fatt[clienti_validi]

        if df_fatt.empty:
            st.info("Nessun noleggio disponibile per la fatturazione.")
        else:
            st.markdown("### 📋 Elenco Noleggi / Fatture")

            colonne_visualizzazione = [
                COL_TARGA,
                COL_CLIENTE,
                COL_DATA_INI,
                COL_DATA_FIN,
                COL_COSTO,
                COL_FATTURA,
                COL_NUMERO_FATTURA,
                COL_DATA_FATTURA,
                COL_STATO_FATTURA,
            ]

            colonne_visualizzazione = [
                c for c in colonne_visualizzazione
                if c in df_fatt.columns
            ]

            st.dataframe(
                df_fatt[colonne_visualizzazione],
                use_container_width=True,
                hide_index=True
            )

            st.markdown("---")
            st.markdown("### ✏️ Inserisci / Modifica Dati Fattura")

            indici = df_fatt.index.tolist()
            opzioni_fattura = {}

            for idx in indici:
                r = df_fatt.loc[idx]

                label = (
                    f"{r.get(COL_TARGA, '')} - "
                    f"{r.get(COL_CLIENTE, '')} - "
                    f"€ {valore_numero(r.get(COL_COSTO, 0)):,.2f}"
                )

                opzioni_fattura[label] = idx

            selezione = st.selectbox(
                "Seleziona il noleggio",
                list(opzioni_fattura.keys())
            )

            idx_fattura = opzioni_fattura[selezione]
            dati_fattura = df.loc[idx_fattura]

            with st.form("form_fattura"):
                col1, col2 = st.columns(2)

                with col1:
                    fattura_edit = st.selectbox(
                        "Fattura",
                        ["No", "Sì"],
                        index=(
                            1
                            if str(
                                dati_fattura.get(
                                    COL_FATTURA,
                                    "No"
                                )
                            ).strip().lower() == "sì"
                            else 0
                        )
                    )

                    numero_fattura_edit = st.text_input(
                        "Numero Fattura",
                        value=str(
                            dati_fattura.get(
                                COL_NUMERO_FATTURA,
                                ""
                            )
                        )
                    )

                with col2:
                    data_fattura_val = (
                        pd.to_datetime(
                            dati_fattura.get(
                                COL_DATA_FATTURA,
                                ""
                            ),
                            errors="coerce"
                        )
                    )

                    if pd.isna(data_fattura_val):
                        data_fattura_default = date.today()
                    else:
                        data_fattura_default = data_fattura_val.date()

                    data_fattura_edit = st.date_input(
                        "Data Fattura",
                        data_fattura_default
                    )

                    stati_fattura = [
                        "Da emettere",
                        "Emessa",
                        "Pagata",
                        "Annullata"
                    ]

                    stato_attuale = str(
                        dati_fattura.get(
                            COL_STATO_FATTURA,
                            "Da emettere"
                        )
                    )

                    try:
                        stato_index = [
                            x.lower() for x in stati_fattura
                        ].index(stato_attuale.lower())
                    except ValueError:
                        stato_index = 0

                    stato_fattura_edit = st.selectbox(
                        "Stato Fattura",
                        stati_fattura,
                        index=stato_index
                    )

                salva_fattura = st.form_submit_button(
                    "💾 Salva Dati Fattura",
                    type="primary"
                )

            if salva_fattura:
                df_mod = df.copy()

                df_mod.loc[idx_fattura, COL_FATTURA] = (
                    fattura_edit
                )

                df_mod.loc[idx_fattura, COL_NUMERO_FATTURA] = (
                    numero_fattura_edit.strip()
                )

                df_mod.loc[idx_fattura, COL_DATA_FATTURA] = (
                    str(data_fattura_edit)
                    if fattura_edit == "Sì"
                    else ""
                )

                df_mod.loc[idx_fattura, COL_STATO_FATTURA] = (
                    stato_fattura_edit
                    if fattura_edit == "Sì"
                    else "Da emettere"
                )

                ok, risposta = invia_payload({
                    "action": "update_all",
                    "rows": payload_dataframe(df_mod)
                })

                if ok:
                    st.success("✅ Dati della fattura aggiornati correttamente.")
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(
                        f"Errore durante il salvataggio: "
                        f"{risposta.get('message', 'Sconosciuto')}"
                    )

    else:
        st.info("Nessun dato disponibile per la fatturazione.")


# =========================================================
# TAB 8 - CONTABILITÀ & SPESE EXTRA
# =========================================================
with tab_contabilita:
    st.subheader("💰 Gestione Spese e Ricavi Extra")

    with st.form("form_contabilita", clear_on_submit=True):
        col_c1, col_c2 = st.columns(2)

        with col_c1:
            tipo_movimento = st.selectbox(
                "Tipo di Movimento *",
                [
                    "Spesa (Uscita)",
                    "Entrata Extra"
                ]
            )

            categoria_mov = st.selectbox(
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

            importo_mov = st.number_input(
                "Importo (€) *",
                min_value=0.0,
                value=0.0,
                step=10.0
            )

        with col_c2:
            data_mov = st.date_input(
                "Data Movimento *",
                date.today()
            )

            riferimento_targa = st.text_input(
                "Targa Veicolo (Opzionale)",
                placeholder="es. AB123CD"
            )

            descrizione_mov = st.text_area(
                "Descrizione / Note *",
                placeholder="es. Sostituzione pastiglie freni..."
            )

        submit_mov = st.form_submit_button(
            "💾 Salva Movimento Contabile",
            type="primary"
        )

    if submit_mov:
        if not descrizione_mov.strip() or importo_mov <= 0:
            st.error(
                "Inserisci una descrizione valida e un importo "
                "superiore a zero."
            )
        else:
            if tipo_movimento == "Spesa (Uscita)":
                valore_entrate_uscite = -abs(importo_mov)
                valore_manutenzione = categoria_mov
            else:
                valore_entrate_uscite = abs(importo_mov)
                valore_manutenzione = ""

            payload = {
                "action": "append",

                COL_TARGA: (
                    riferimento_targa.upper()
                    if riferimento_targa
                    else "EXTRA"
                ),

                COL_MARCA: tipo_movimento,
                COL_MODELLO: "",
                COL_CATEGORIA: "Contabilità",
                COL_PREZZO: str(importo_mov),
                COL_ANNO: str(data_mov.year),
                COL_CLIENTE: "",
                COL_STATO: "Registrato",
                COL_DATA_INI: str(data_mov),
                COL_DATA_FIN: str(data_mov),
                COL_NOTE: descrizione_mov.strip(),
                COL_NOTE1: "",
                COL_NOTE_CHECKIN: "",
                COL_KM_INIZIALI: "0",
                COL_KM_FINALI: "0",
                COL_PAGAMENTO: "N/D",
                COL_CAUZIONE: "0.0",
                COL_ENTRATE_USCITE: str(
                    valore_entrate_uscite
                ),
                COL_MANUTENZIONE: valore_manutenzione,

                COL_COSTO: "0.0",
                COL_FATTURA: "No",
                COL_NUMERO_FATTURA: "",
                COL_DATA_FATTURA: "",
                COL_STATO_FATTURA: ""
            }

            ok, risposta = invia_payload(
                payload,
                timeout=15
            )

            if ok:
                st.success(
                    "✅ Movimento contabile registrato con successo!"
                )

                st.cache_data.clear()
                time.sleep(1)
                st.rerun()

            else:
                st.error(
                    f"Errore dal server: "
                    f"{risposta.get('message', 'Sconosciuto')}"
                )

    st.markdown("---")
    st.subheader("📊 Storico Movimenti Contabili Extra")

    if not df.empty:
        df_contab = df[
            df[COL_CATEGORIA]
            .astype(str)
            .str.contains(
                "Contabilità",
                case=False,
                na=False
            )
        ]

        if not df_contab.empty:
            st.dataframe(
                df_contab,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Nessun movimento contabile registrato.")
