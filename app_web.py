import datetime
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# ==========================================
# CONFIGURAZIONE PAGINA
# ==========================================
st.set_page_config(
    page_title="Autonoleggio Pro (Excel Cloud)", page_icon="🚗", layout="wide"
)

# ==========================================
# CONNESSIONE A GOOGLE SHEETS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)


def leggi_foglio(sheet_name):
    try:
        # ttl=0 evita che Streamlit salvi dati vecchi in memoria
        return conn.read(worksheet=sheet_name, ttl=0)
    except Exception as e:
        st.error(f"Errore lettura foglio {sheet_name}: {e}")
        return pd.DataFrame()


def salva_dati(sheet_name, df_aggiornato):
    conn.update(worksheet=sheet_name, data=df_aggiornato)
    st.cache_data.clear()


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
                        nuova_riga = pd.DataFrame(
                            [
                                {
                                    "targa": targa,
                                    "marca": marca,
                                    "modello": modello,
                                    "categoria": categoria,
                                    "prezzo_giornaliero": prezzo,
                                    "anno": anno,
                                    "stato": "Disponibile",
                                }
                            ]
                        )
                        df_finale = pd.concat(
                            [df_v, nuova_riga], ignore_index=True
                        )
                        salva_dati("veicoli", df_finale)
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
                        df_nuovo = df_veicoli[
                            df_veicoli["targa"] != row["targa"]
                        ]
                        salva_dati("veicoli", df_nuovo)
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

                    nuovo_nol = pd.DataFrame(
                        [
                            {
                                "id": nuovo_id,
                                "targa": auto["targa"],
                                "cliente_nome": cliente,
                                "cliente_documento": doc,
                                "data_inizio": str(d_inizio),
                                "data_fine": str(d_fine),
                                "giorni": giorni,
                                "costo_totale": totale,
                                "stato": "Attivo",
                            }
                        ]
                    )

                    df_noleggi_fin = pd.concat(
                        [df_noleggi, nuovo_nol], ignore_index=True
                    )
                    salva_dati("noleggi", df_noleggi_fin)

                    # Aggiorna lo stato dell'auto
                    df_veicoli.loc[
                        df_veicoli["targa"] == auto["targa"], "stato"
                    ] = "Noleggiato"
                    salva_dati("veicoli", df_veicoli)

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
            # Chiudi Noleggio
            df_noleggi.loc[df_noleggi["id"] == noleggio["id"], "stato"] = (
                "Completato"
            )
            salva_dati("noleggi", df_noleggi)

            # Rendi auto disponibile
            df_veicoli = leggi_foglio("veicoli")
            df_veicoli.loc[
                df_veicoli["targa"] == noleggio["targa"], "stato"
            ] = "Disponibile"
            salva_dati("veicoli", df_veicoli)

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
