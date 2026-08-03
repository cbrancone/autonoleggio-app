import datetime
import pandas as pd
import streamlit as st

# ==========================================
# CONFIGURAZIONE PAGINA
# ==========================================
st.set_page_config(
    page_title="Autonoleggio Pro (Excel Cloud)", page_icon="🚗", layout="wide"
)

# ==========================================
# GESTIONE SICURA GOOGLE SHEETS
# ==========================================
def get_gspread_client():
 import gspread
 from google.oauth2.service_account import Credentials

    
    scopes = [ 
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scopes
    )
    return gspread.authorize(credentials)


def leggi_foglio(sheet_name):
    # Struttura di ripiego per evitare il crash se Google Sheets fallisce
    empty_df = pd.DataFrame()

    # 1. Controlla se i Secrets di Google esistono su Streamlit Cloud
    if "gcp_service_account" not in st.secrets:
        st.error(
            "⚠️ Manca la configurazione 'gcp_service_account' nei Secrets di Streamlit!"
        )
        return empty_df

    # 2. Tenta la connessione al foglio
    try:
        client = get_gspread_client()
        sheet = client.open("Autonoleggio_DB")
        ws = sheet.worksheet(sheet_name)
        data = ws.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(
            f"⚠️ Errore durante la lettura del foglio '{sheet_name}': {e}"
        )
        return empty_df


def aggiungi_riga(sheet_name, riga_lista):
    ws = get_worksheet(sheet_name)
    ws.append_row(riga_lista)


def aggiorna_stato_veicolo(targa, nuovo_stato):
    ws = get_worksheet("veicoli")
    cell = ws.find(targa)
    if cell:
        # La colonna 'stato' è la 7a colonna
        ws.update_cell(cell.row, 7, nuovo_stato)


def elimina_riga_veicolo(targa):
    ws = get_worksheet("veicoli")
    cell = ws.find(targa)
    if cell:
        ws.delete_rows(cell.row)


def aggiorna_stato_noleggio(noleggio_id):
    ws = get_worksheet("noleggi")
    cell = ws.find(str(noleggio_id))
    if cell:
        # La colonna 'stato' è la 9a colonna
        ws.update_cell(cell.row, 9, "Completato")
# ==========================================
# INTERFACCIA UTENTE (STREAMLIT)
# ==========================================
st.sidebar.title("🚘 Autonoleggio Pro")
st.sidebar.caption("Sincronizzato su Google Sheets / Excel")

menu = st.sidebar.radio(
    "Navigazione Menu:",
    [
        "📊 Dashboard",
        "🚙 Gestione Flotta",
        "🔑 Nuovo Noleggio",
        "🔄 Restituzione",
        "📜 Storico Noleggi",
    ],
)

# ------------------------------------------
# 1. DASHBOARD
# ------------------------------------------
if menu == "📊 Dashboard":
    st.title("📊 Dashboard Panoramica")

    df_veicoli = leggi_foglio("veicoli")
    df_noleggi = leggi_foglio("noleggi")

    df_attivi = (
        df_noleggi[df_noleggi["stato"] == "Attivo"]
        if not df_noleggi.empty
        else pd.DataFrame()
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Totale Flotta", len(df_veicoli) if not df_veicoli.empty else 0)
    col2.metric(
        "Disponibili",
        (
            len(df_veicoli[df_veicoli["stato"] == "Disponibile"])
            if not df_veicoli.empty
            else 0
        ),
    )
    col3.metric("Noleggi Attivi", len(df_attivi))

    fatturato = (
        pd.to_numeric(df_noleggi["costo_totale"], errors="coerce").sum()
        if not df_noleggi.empty
        else 0.0
    )
    col4.metric("Fatturato Totale", f"{fatturato:.2f} €")

    st.markdown("---")
    st.subheader("📌 Stato Flotta su Foglio Condiviso")
    if not df_veicoli.empty:
        st.dataframe(
            df_veicoli[["targa", "marca", "modello", "categoria", "stato"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Nessun veicolo registrato nel foglio Excel.")

# ------------------------------------------
# 2. GESTIONE FLOTTA
# ------------------------------------------
elif menu == "🚙 Gestione Flotta":
    st.title("🚙 Gestione Flotta Veicoli")
    tab1, tab2 = st.tabs(["➕ Aggiungi Veicolo", "📋 Lista e Rimozione"])

    with tab1:
        with st.form("form_nuovo_veicolo", clear_on_submit=True):
            col1, col2 = st.columns(2)
            targa = col1.text_input("Targa (es. AB123CD)").upper().strip()
            marca = col2.text_input("Marca")
            modello = col1.text_input("Modello")
            categoria = col2.selectbox(
                "Categoria", ["Utilitaria", "Berlina", "SUV", "Furgone"]
            )
            prezzo = col1.number_input(
                "Prezzo Giornaliero (€)", min_value=10.0, value=50.0
            )
            anno = col2.number_input("Anno", min_value=2000, value=2023)

            if st.form_submit_button("Salva nel Foglio Excel"):
                if targa and marca and modello:
                    df_v = leggi_foglio("veicoli")
                    if (
                        not df_v.empty
                        and targa in df_v["targa"].astype(str).values
                    ):
                        st.error(f"La targa {targa} esiste già nel foglio.")
                    else:
                        aggiungi_riga(
                            "veicoli",
                            [
                                targa,
                                marca,
                                modello,
                                categoria,
                                prezzo,
                                anno,
                                "Disponibile",
                            ],
                        )
                        st.success(
                            f"Veicolo {targa} salvato sul foglio condiviso!"
                        )
                        st.rerun()
                else:
                    st.warning("Compila tutti i campi obbligatori.")

    with tab2:
        df_veicoli = leggi_foglio("veicoli")
        if not df_veicoli.empty:
            for _, row in df_veicoli.iterrows():
                col_info, col_btn = st.columns([4, 1])
                col_info.write(
                    f"**{row['targa']}** - {row['marca']} {row['modello']} (`{row['stato']}`)"
                )
                if row["stato"] == "Disponibile":
                    if col_btn.button("🗑️ Elimina", key=f"del_{row['targa']}"):
                        elimina_riga_veicolo(str(row["targa"]))
                        st.success(f"Veicolo {row['targa']} rimosso.")
                        st.rerun()
                st.divider()

# ------------------------------------------
# 3. NUOVO NOLEGGIO
# ------------------------------------------
elif menu == "🔑 Nuovo Noleggio":
    st.title("🔑 Registra Noleggio")

    df_veicoli = leggi_foglio("veicoli")
    df_disp = (
        df_veicoli[df_veicoli["stato"] == "Disponibile"]
        if not df_veicoli.empty
        else pd.DataFrame()
    )

    if df_disp.empty:
        st.warning("Nessun veicolo disponibile al momento.")
    else:
        opzioni = {
            f"{r['targa']} - {r['marca']} {r['modello']} ({r['prezzo_giornaliero']}€/gg)": r
            for _, r in df_disp.iterrows()
        }
        scelta = st.selectbox("Seleziona Auto:", list(opzioni.keys()))
        auto = opzioni[scelta]

        with st.form("form_noleggio"):
            cliente = st.text_input("Nome Cliente")
            doc = st.text_input("Documento (Patente/CF)")
            d_inizio = st.date_input("Inizio", datetime.date.today())
            d_fine = st.date_input(
                "Fine", datetime.date.today() + datetime.timedelta(days=3)
            )

            giorni = (d_fine - d_inizio).days
            totale = giorni * float(auto["prezzo_giornaliero"])

            if giorni > 0:
                st.info(f"Costo Totale Previsto: **{totale:.2f} €**")

            if st.form_submit_button("Conferma e Salva Noleggio"):
                if giorni > 0 and cliente and doc:
                    df_noleggi = leggi_foglio("noleggi")
                    nuovo_id = (
                        len(df_noleggi) + 1 if not df_noleggi.empty else 1
                    )

                    # Inserisci nel foglio 'noleggi'
                    aggiungi_riga(
                        "noleggi",
                        [
                            nuovo_id,
                            auto["targa"],
                            cliente,
                            doc,
                            str(d_inizio),
                            str(d_fine),
                            giorni,
                            totale,
                            "Attivo",
                        ],
                    )

                    # Aggiorna lo stato dell'auto nel foglio 'veicoli'
                    aggiorna_stato_veicolo(str(auto["targa"]), "Noleggiato")

                    st.success("Noleggio registrato sul foglio condiviso!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Dati incompleti o date non valide.")

# ------------------------------------------
# 4. RESTITUZIONE
# ------------------------------------------
elif menu == "🔄 Restituzione":
    st.title("🔄 Rientro Veicolo")

    df_noleggi = leggi_foglio("noleggi")
    df_attivi = (
        df_noleggi[df_noleggi["stato"] == "Attivo"]
        if not df_noleggi.empty
        else pd.DataFrame()
    )

    if df_attivi.empty:
        st.info("Nessun noleggio in corso.")
    else:
        opzioni = {
            f"ID: {r['id']} | Targa: {r['targa']} | Cliente: {r['cliente_nome']}": r
            for _, r in df_attivi.iterrows()
        }
        scelta = st.selectbox(
            "Seleziona Noleggio da chiudere:", list(opzioni.keys())
        )
        noleggio = opzioni[scelta]

        if st.button("✅ Registra Rientro", type="primary"):
            aggiorna_stato_noleggio(noleggio["id"])
            aggiorna_stato_veicolo(str(noleggio["targa"]), "Disponibile")
            st.success("Veicolo rientrato e foglio Excel aggiornato!")
            st.rerun()

# ------------------------------------------
# 5. STORICO NOLEGGI
# ------------------------------------------
elif menu == "📜 Storico Noleggi":
    st.title("📜 Storico Noleggi Registrati")
    df_storico = leggi_foglio("noleggi")

    if not df_storico.empty:
        st.dataframe(df_storico, use_container_width=True, hide_index=True)
    else:
        st.info("Nessun noleggio salvato nel foglio Excel.")
