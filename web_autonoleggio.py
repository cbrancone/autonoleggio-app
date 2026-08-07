from datetime import date
import time
import pandas as pd
import requests
import streamlit as st

# ---------------------------------------------------------
# CONFIGURAZIONE URL
# ---------------------------------------------------------
SPREADSHEET_ID = "1-XQnKHP1vWFNcvjCdG631FrqIST4PmJ-MtIGdvFesEE"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzIMY05XhfUpztNADq1KlBC3vJxxdOGWisOdJDyrDXR2c6ZWiAiphJkL3aNvjAoBhS0-Q/exec"

# ---------------------------------------------------------
# 1. Setup Pagina
# ---------------------------------------------------------
st.set_page_config(
    page_title="Gestione Autonoleggio", page_icon="🚗", layout="wide"
)
st.title("🚗 Sistema Gestione Autonoleggio")


# ---------------------------------------------------------
# 2. Lettura e Pre-processing Dati
# ---------------------------------------------------------
@st.cache_data(ttl=300)
def carica_dati():
    try:
        timestamp_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&nocache={int(time.time())}"
        data = pd.read_csv(timestamp_url)

        # Pulizia nomi colonne
        data.columns = data.columns.str.strip()

        # Conversione e pulizia 'Costo Totale (€)'
        col_costo = "Costo Totale (€)"
        if col_costo in data.columns:
            valori_puliti = (
                data[col_costo]
                .astype(str)
                .str.replace("€", "", regex=False)
                .str.replace(" ", "", regex=False)
                .str.replace(",", ".", regex=False)
            )
            data[col_costo] = pd.to_numeric(valori_puliti, errors="coerce").fillna(
                0.0
            )

        # Conversione Date
        for col_date in ["Data Inizio", "Data Fine"]:
            if col_date in data.columns:
                data[col_date] = pd.to_datetime(data[col_date], errors="coerce")

        # Conversione 'Giorni'
        if "Giorni" in data.columns:
            data["Giorni"] = pd.to_numeric(
                data["Giorni"], errors="coerce"
            ).fillna(0)

        return data
    except Exception as e:
        st.error(f"Impossibile leggere il Foglio Google: {e}")
        return pd.DataFrame()


df = carica_dati()

# ---------------------------------------------------------
# 3. Layout a Schede (Tab)
# ---------------------------------------------------------
tab_dash, tab_rientro, tab_storico, tab_registro, tab_nuovo = st.tabs([
    "📊 Dashboard & Analytics",
    "🔑 Rientro Veicolo",
    "📜 Storico & Ricerca",
    "📋 Registro Parco Auto",
    "➕ Inserisci Veicolo / Noleggio",
])

# =========================================================
# TAB 1: DASHBOARD & STATISTICHE
# =========================================================
with tab_dash:
    st.subheader("📊 Panoramica & Statistiche Avanzate")

    if not df.empty:
        tot_veicoli = len(df)
        noleggiati = (
            len(df[df["Stato"] == "Noleggiata"]) if "Stato" in df.columns else 0
        )
        tasso_occupazione = (
            (noleggiati / tot_veicoli * 100) if tot_veicoli > 0 else 0
        )

        incasso_totale = (
            df["Costo Totale (€)"].sum()
            if "Costo Totale (€)" in df.columns
            else 0
        )
        durata_media = (
            df[df["Giorni"] > 0]["Giorni"].mean()
            if "Giorni" in df.columns
            else 0
        )
        incasso_medio = (
            df[df["Costo Totale (€)"] > 0]["Costo Totale (€)"].mean()
            if "Costo Totale (€)" in df.columns
            else 0
        )

        # Metric Cards - KPI Primari
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Incasso Totale", f"€ {incasso_totale:,.2f}")
        kpi2.metric("Tasso Occupazione", f"{tasso_occupazione:.1f}%")
        kpi3.metric(
            "Incasso Medio / Noleggio",
            f"€ {incasso_medio:.2f}" if not pd.isna(incasso_medio) else "€ 0.00",
        )
        kpi4.metric(
            "Durata Media Noleggio",
            f"{durata_media:.1f} gg" if not pd.isna(durata_media) else "0 gg",
        )

        st.divider()

        # Grafici Analitici
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.write("📈 **Trend Incassi nel Tempo**")
            if (
                "Data Inizio" in df.columns
                and "Costo Totale (€)" in df.columns
            ):
                df_trend = (
                    df.dropna(subset=["Data Inizio"])
                    .set_index("Data Inizio")
                    .resample("M")["Costo Totale (€)"]
                    .sum()
                    .reset_index()
                )
                if not df_trend.empty:
                    df_trend["Data Inizio"] = df_trend["Data Inizio"].dt.strftime(
                        "%Y-%m"
                    )
                    st.line_chart(
                        df_trend.set_index("Data Inizio")["Costo Totale (€)"]
                    )
                else:
                    st.caption("Dati temporali insufficienti per il grafico.")

        with col_g2:
            st.write("🏷️ **Ricavi Totali per Categoria**")
            if (
                "Categoria" in df.columns
                and "Costo Totale (€)" in df.columns
            ):
                cat_chart = df.groupby("Categoria")["Costo Totale (€)"].sum()
                st.bar_chart(cat_chart)

        col_g3, col_g4 = st.columns(2)
        with col_g3:
            st.write("🚘 **Top 5 Veicoli per Incasso Generato**")
            if (
                "Targa Auto" in df.columns
                and "Costo Totale (€)" in df.columns
            ):
                top_veicoli = (
                    df.groupby(["Targa Auto", "Marca", "Modello"])[
                        "Costo Totale (€)"
                    ]
                    .sum()
                    .reset_index()
                    .sort_values(by="Costo Totale (€)", ascending=False)
                    .head(5)
                )
                st.dataframe(
                    top_veicoli, use_container_width=True, hide_index=True
                )

        with col_g4:
            st.write("📊 **Ripartizione Stato Parco Auto**")
            if "Stato" in df.columns:
                st.bar_chart(df["Stato"].value_counts())

    else:
        st.info("Nessun dato disponibile nel Foglio Google.")

# =========================================================
# TAB 2: RIENTRO VEICOLO (CHECK-IN)
# =========================================================
with tab_rientro:
    st.subheader("🔑 Check-in e Rientro Veicolo")

    if not df.empty and "Stato" in df.columns:
        # Filtra solo le auto in stato 'Noleggiata'
        df_noleggiate = df[df["Stato"] == "Noleggiata"]

        if df_noleggiate.empty:
            st.success(
                "🎉 Nessun veicolo attualmente in noleggio! Tutto il parco auto è"
                " disponibile o in manutenzione."
            )
        else:
            # Lista per la selectbox
            auto_opzioni = df_noleggiate.apply(
                lambda r: (
                    f"{r.get('Targa Auto', '')} - {r.get('Marca', '')}"
                    f" {r.get('Modello', '')} (Cliente:"
                    f" {r.get('Cliente', 'N/D')})"
                ),
                axis=1,
            ).tolist()

            auto_scelta = st.selectbox(
                "Seleziona il veicolo da far rientrare:", auto_opzioni
            )

            if auto_scelta:
                targa_selezionata = auto_scelta.split(" - ")[0]
                veicolo = df_noleggiate[
                    df_noleggiate["Targa Auto"] == targa_selezionata
                ].iloc[0]

                st.divider()

                # Card Informativa Noleggio
                st.markdown("### 📄 Dettagli Noleggio Attivo")
                c1, c2, c3 = st.columns(3)

                c1.markdown(f"**Targa:** `{veicolo.get('Targa Auto', '')}`")
                c1.markdown(
                    "**Veicolo:**"
                    f" {veicolo.get('Marca', '')} {veicolo.get('Modello', '')}"
                )

                d_ini = (
                    veicolo["Data Inizio"].strftime("%Y-%m-%d")
                    if pd.notna(veicolo.get("Data Inizio"))
                    else "N/D"
                )
                d_fin = (
                    veicolo["Data Fine"].strftime("%Y-%m-%d")
                    if pd.notna(veicolo.get("Data Fine"))
                    else "N/D"
                )

                c2.markdown(f"**Cliente:** {veicolo.get('Cliente', 'N/D')}")
                c2.markdown(f"**Data Inizio Prevista:** {d_ini}")

                c3.markdown(
                    "**Costo Totale:** €"
                    f" {veicolo.get('Costo Totale (€)', 0):.2f}"
                )
                c3.markdown(f"**Data Fine Prevista:** {d_fin}")

                st.divider()

                # Form per il Rientro
                with st.form("form_rientro"):
                    st.markdown("### 📝 Registra Rientro")

                    r_col1, r_col2 = st.columns(2)
                    with r_col1:
                        nuovo_stato = st.selectbox(
                            "Nuovo Stato del Veicolo *",
                            ["Disponibile", "In Manutenzione"],
                            help=(
                                "Seleziona 'In Manutenzione' se il veicolo"
                                " necessita di pulizia straordinaria o"
                                " riparazioni."
                            ),
                        )
                        data_rientro = st.date_input(
                            "Data Rientro Effettiva", date.today()
                        )

                    with r_col2:
                        note_rientro = st.text_area(
                            "Note Check-in (Carburante, Danni, Pulizia)",
                            help=(
                                "Le note verranno salvate ed allegate al"
                                " registro dello storico."
                            ),
                        )

                    btn_rientro = st.form_submit_button(
                        "✅ Conferma Rientro Veicolo", type="primary"
                    )

                    if btn_rientro:
                        try:
                            df_aggiornato = df.copy()

                            # Formattazione stringa date per l'export JSON
                            for c in ["Data Inizio", "Data Fine"]:
                                if c in df_aggiornato.columns:
                                    df_aggiornato[c] = (
                                        df_aggiornato[c]
                                        .dt.strftime("%Y-%m-%d")
                                        .fillna("")
                                    )

                            idx = df_aggiornato[
                                df_aggiornato["Targa Auto"] == targa_selezionata
                            ].index

                            if len(idx) > 0:
                                i = idx[0]
                                df_aggiornato.loc[i, "Stato"] = nuovo_stato

                                # Append delle note di rientro
                                note_esistenti = (
                                    str(df_aggiornato.loc[i, "Note"])
                                    if "Note" in df_aggiornato.columns
                                    and pd.notna(df_aggiornato.loc[i, "Note"])
                                    else ""
                                )
                                tag_rientro = (
                                    f"[Rientro {data_rientro}: {note_rientro}]"
                                    if note_rientro
                                    else f"[Rientro {data_rientro}]"
                                )
                                df_aggiornato.loc[i, "Note"] = (
                                    f"{note_esistenti} {tag_rientro}".strip()
                                )

                                payload = {
                                    "action": "update_all",
                                    "rows": df_aggiornato.fillna("").to_dict(
                                        orient="records"
                                    ),
                                }

                                response = requests.post(
                                    APPS_SCRIPT_URL, json=payload
                                )
                                if response.status_code == 200:
                                    st.success(
                                        f"🔑 Veicolo {targa_selezionata}"
                                        " rientrato con successo! Stato"
                                        f" aggiornato a '{nuovo_stato}'."
                                    )
                                    st.cache_data.clear()
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(
                                        "Errore durante il salvataggio:"
                                        f" {response.status_code}"
                                    )
                        except Exception as e:
                            st.error(f"Errore durante l'operazione: {e}")
    else:
        st.info("Nessun dato disponibile.")

# =========================================================
# TAB 3: STORICO & RICERCA FILTRATA
# =========================================================
with tab_storico:
    st.subheader("📜 Storico Noleggi e Filtri Avanzati")

    if not df.empty:
        f1, f2, f3 = st.columns(3)

        with f1:
            testo_ricerca = st.text_input("🔍 Cerca Targa o Cliente", "")

        with f2:
            stati_disponibili = (
                ["Tutti"] + list(df["Stato"].unique())
                if "Stato" in df.columns
                else ["Tutti"]
            )
            stato_selezionato = st.selectbox("Filtra per Stato", stati_disponibili)

        with f3:
            range_date = st.date_input(
                "Intervallo Data Inizio",
                value=(),
                help="Seleziona la data di inizio e di fine per filtrare lo storico",
            )

        df_filtrato = df.copy()

        if testo_ricerca:
            mask_targa = df_filtrato["Targa Auto"].astype(str).str.contains(
                testo_ricerca, case=False, na=False
            ) if "Targa Auto" in df_filtrato.columns else False
            mask_cliente = df_filtrato["Cliente"].astype(str).str.contains(
                testo_ricerca, case=False, na=False
            ) if "Cliente" in df_filtrato.columns else False
            df_filtrato = df_filtrato[mask_targa | mask_cliente]

        if stato_selezionato != "Tutti" and "Stato" in df_filtrato.columns:
            df_filtrato = df_filtrato[
                df_filtrato["Stato"] == stato_selezionato
            ]

        if len(range_date) == 2 and "Data Inizio" in df_filtrato.columns:
            d_inizio, d_fine = pd.to_datetime(range_date[0]), pd.to_datetime(
                range_date[1]
            )
            df_filtrato = df_filtrato[
                (df_filtrato["Data Inizio"] >= d_inizio)
                & (df_filtrato["Data Inizio"] <= d_fine)
            ]

        st.markdown(f"**Risultati trovati:** {len(df_filtrato)}")
        c_incasso = (
            df_filtrato["Costo Totale (€)"].sum()
            if "Costo Totale (€)" in df_filtrato.columns
            else 0
        )
        c_giorni = (
            df_filtrato["Giorni"].sum()
            if "Giorni" in df_filtrato.columns
            else 0
        )

        rf1, rf2 = st.columns(2)
        rf1.info(f"💰 **Incasso Totale Filtrato:** € {c_incasso:,.2f}")
        rf2.info(f"📅 **Giorni Noleggio Totali Filtrati:** {int(c_giorni)} giorni")

        df_display = df_filtrato.copy()
        for c in ["Data Inizio", "Data Fine"]:
            if c in df_display.columns:
                df_display[c] = df_display[c].dt.strftime("%Y-%m-%d").fillna("")

        st.dataframe(df_display, use_container_width=True, hide_index=True)

        csv_data = df_display.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Scarica Storico Filtrato (CSV)",
            data=csv_data,
            file_name="storico_noleggi.csv",
            mime="text/csv",
        )
    else:
        st.warning("Nessun dato disponibile.")

# =========================================================
# TAB 4: REGISTRO PARCO AUTO (EDITABILE)
# =========================================================
with tab_registro:
    st.subheader("📋 Registro Completo (Modifica e Salvataggio)")

    if "modalita_modifica" not in st.session_state:
        st.session_state.modalita_modifica = False

    if not df.empty:
        search_query = st.text_input(
            "🔍 Cerca nel registro",
            "",
            disabled=st.session_state.modalita_modifica,
            help=(
                "Disabilitato in modalità modifica per prevenire perdite di"
                " dati."
                if st.session_state.modalita_modifica
                else ""
            ),
        )

        if search_query and not st.session_state.modalita_modifica:
            df_reg = df[
                df.astype(str).apply(
                    lambda r: r.str.contains(search_query, case=False).any(),
                    axis=1,
                )
            ]
        else:
            df_reg = df.copy()

        st.divider()

        if not st.session_state.modalita_modifica:
            col_a, _ = st.columns([2, 5])
            with col_a:
                if st.button("✏️ Abilita Modifica", type="secondary"):
                    st.session_state.modalita_modifica = True
                    st.rerun()

            st.caption(
                "🔒 **Modalità Lettura**: Clicca su *✏️ Abilita Modifica* per"
                " apportare cambiamenti alla tabella."
            )

            df_reg_disp = df_reg.copy()
            for c in ["Data Inizio", "Data Fine"]:
                if c in df_reg_disp.columns:
                    df_reg_disp[c] = (
                        df_reg_disp[c].dt.strftime("%Y-%m-%d").fillna("")
                    )

            st.dataframe(df_reg_disp, use_container_width=True, hide_index=True)

        else:
            col_btn1, col_btn2, _ = st.columns([2, 2, 4])
            with col_btn1:
                tasto_salva = st.button(
                    "💾 Salva Modifiche su Google Sheets", type="primary"
                )
            with col_btn2:
                if st.button("❌ Annulla Modifiche"):
                    st.session_state.modalita_modifica = False
                    st.rerun()

            st.caption(
                "💡 Spunta la casella 'Elimina' sulle righe da rimuovere o"
                " modifica i dati direttamente nella tabella."
            )

            df_editabile = df.copy()
            for c in ["Data Inizio", "Data Fine"]:
                if c in df_editabile.columns:
                    df_editabile[c] = (
                        df_editabile[c].dt.strftime("%Y-%m-%d").fillna("")
                    )

            if "Elimina" not in df_editabile.columns:
                df_editabile.insert(0, "Elimina", False)

            edited_df = st.data_editor(
                df_editabile,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Elimina": st.column_config.CheckboxColumn(
                        "🗑️ Elimina?",
                        help="Spunta per rimuovere la riga",
                        default=False,
                    )
                },
            )

            if tasto_salva:
                try:
                    df_final = edited_df[edited_df["Elimina"] == False].drop(
                        columns=["Elimina"]
                    )
                    df_pulito = df_final.fillna("")

                    payload = {
                        "action": "update_all",
                        "rows": df_pulito.to_dict(orient="records"),
                    }

                    response = requests.post(APPS_SCRIPT_URL, json=payload)
                    if response.status_code == 200:
                        st.success("✅ Salvataggio completato!")
                        st.session_state.modalita_modifica = False
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(
                            "Errore durante il salvataggio:"
                            f" {response.status_code}"
                        )
                except Exception as e:
                    st.error(f"Errore di connessione: {e}")
    else:
        st.warning("Nessun dato trovato.")

# =========================================================
# TAB 5: NUOVO INSERIMENTO
# =========================================================
with tab_nuovo:
    st.subheader("➕ Inserisci Registrazione")

    with st.form("form_noleggio", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            targa = st.text_input("Targa Auto *").upper()
            marca = st.text_input("Marca *")
            modello = st.text_input("Modello *")
            categoria = st.selectbox(
                "Categoria",
                ["Utilitaria", "Berlina", "SUV", "Station Wagon", "Furgone"],
            )
            anno_imm = st.number_input(
                "Anno immatricolazione",
                min_value=1990,
                max_value=2030,
                value=2023,
            )

        with col2:
            prezzo_giornaliero = st.number_input(
                "Prezzo Giornaliero (€) *", min_value=0.0, value=50.0
            )
            cliente = st.text_input("Cliente")
            stato = st.selectbox(
                "Stato Veicolo",
                ["Disponibile", "Noleggiata", "In Manutenzione"],
            )

            data_inizio = st.date_input("Data Inizio Noleggio", date.today())
            data_fine = st.date_input("Data Fine Noleggio", date.today())
            note = st.text_area("Note")

        giorni = (data_fine - data_inizio).days
        giorni = 1 if giorni < 1 else giorni
        costo_totale = (
            giorni * prezzo_giornaliero if stato == "Noleggiata" else 0.0
        )

        if stato == "Noleggiata":
            st.info(
                "📐 **Costo Calcolato:**"
                f" {giorni} giorni × €{prezzo_giornaliero:.2f} ="
                f" **€{costo_totale:.2f}**"
            )

        submit = st.form_submit_button("💾 Aggiungi Nuovo Veicolo")

        if submit:
            if not targa or not marca or not modello:
                st.error("Compila i campi obbligatori: Targa, Marca e Modello.")
            else:
                payload = {
                    "action": "append",
                    "Targa Auto": targa,
                    "Marca": marca,
                    "Modello": modello,
                    "Categoria": categoria,
                    "Prezzo Giornaliero": prezzo_giornaliero,
                    "Anno immatricolazione": int(anno_imm),
                    "Cliente": cliente if cliente else "N/D",
                    "Stato": stato,
                    "Data Inizio": (
                        str(data_inizio) if stato == "Noleggiata" else ""
                    ),
                    "Data Fine": str(data_fine) if stato == "Noleggiata" else "",
                    "Giorni": giorni if stato == "Noleggiata" else 0,
                    "Costo Totale (€)": costo_totale,
                    "Note": note,
                }

                try:
                    response = requests.post(APPS_SCRIPT_URL, json=payload)
                    if response.status_code == 200:
                        st.success(f"Veicolo {targa} salvato correttamente!")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(
                            "Errore nella risposta dello script:"
                            f" {response.status_code}"
                        )
                except Exception as e:
                    st.error(f"Errore di connessione: {e}")
