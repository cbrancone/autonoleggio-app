from datetime import datetime
import pandas as pd
import streamlit as st

# Configurazione della pagina Streamlit
st.set_page_config(
    page_title="Gestionale Autonoleggio",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- CLASSI DI DOMINIO (OOP) ---
class Veicolo:

    def __init__(
        self,
        targa: str,
        marca: str,
        modello: str,
        categoria: str,
        prezzo_giornaliero: float,
    ):
        self.targa = targa.upper().strip()
        self.marca = marca.strip()
        self.modello = modello.strip()
        self.categoria = categoria.strip()
        self.prezzo_giornaliero = float(prezzo_giornaliero)
        self.disponibile = True

    def to_dict(self):
        return {
            "Targa": self.targa,
            "Marca": self.marca,
            "Modello": self.modello,
            "Categoria": self.categoria,
            "Prezzo / Giorno": f"€ {self.prezzo_giornaliero:.2f}",
            "Stato": "🟢 Disponibile" if self.disponibile else "🔴 Noleggiato",
        }


class Noleggio:

    def __init__(self, veicolo: Veicolo, nome_cliente: str, giorni: int):
        self.veicolo = veicolo
        self.nome_cliente = nome_cliente.strip()
        self.giorni = giorni
        self.data_inizio = datetime.now().strftime("%d/%m/%Y %H:%M")

        self.prezzo_base = veicolo.prezzo_giornaliero * giorni
        self.percentuale_sconto = self._calcola_sconto(giorni)
        self.sconto_applicato = self.prezzo_base * (
            self.percentuale_sconto / 100
        )
        self.costo_totale = self.prezzo_base - self.sconto_applicato

    def _calcola_sconto(self, giorni: int) -> int:
        if giorni >= 30:
            return 20  # 20% oltre un mese
        elif giorni >= 7:
            return 10  # 10% oltre una settimana
        elif giorni >= 3:
            return 5  # 5% oltre 3 giorni
        return 0


# --- INIZIALIZZAZIONE STATO DELLA SESSIONE STREAMLIT ---
if "parco_auto" not in st.session_state:
    # Popolamento iniziale di prova
    auto_iniziali = [
        Veicolo("AA123BB", "Fiat", "Panda", "Economica", 35.0),
        Veicolo("CC456DD", "Ford", "Focus", "Compatta", 50.0),
        Veicolo("EE789FF", "Audi", "Q5", "SUV", 95.0),
        Veicolo("GG012HH", "BMW", "Serie 3", "Lusso", 120.0),
    ]
    st.session_state.parco_auto = {v.targa: v for v in auto_iniziali}

if "noleggi_attivi" not in st.session_state:
    st.session_state.noleggi_attivi = {}

if "incassi_totali" not in st.session_state:
    st.session_state.incassi_totali = 0.0


# --- TITOLO & SIDEBAR METRICHE ---
st.title("🚗 Gestionale Autonoleggio")
st.caption("Piattaforma interattiva per la gestione flotta e prenotazioni")

# Sidebar con indicatori di prestazione (KPI)
st.sidebar.header("📊 Panoramica Flotta")
totale_veicoli = len(st.session_state.parco_auto)
disponibili = sum(
    1 for v in st.session_state.parco_auto.values() if v.disponibile
)
noleggiati = totale_veicoli - disponibili

st.sidebar.metric("Totale Veicoli", totale_veicoli)
st.sidebar.metric("Disponibili", disponibili)
st.sidebar.metric("In Noleggio", noleggiati)
st.sidebar.divider()
st.sidebar.metric(
    "Incasso Totale Generato", f"€ {st.session_state.incassi_totali:.2f}"
)


# --- NAVIGAZIONE SCHEDE (TABS) ---
tab_parco, tab_noleggio, tab_restituzione, tab_aggiungi = st.tabs([
    "📋 Parco Auto",
    "🔑 Nuovo Noleggio",
    "🔄 Restituzione Veicolo",
    "➕ Aggiungi Auto",
])


# --- TAB 1: PARCO AUTO ---
with tab_parco:
    st.subheader("Flotta Veicoli")

    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        filtro_stato = st.selectbox(
            "Filtra per stato:",
            ["Tutti", "Solo Disponibili", "Solo Noleggiati"],
        )
    with col_f2:
        ricerca = st.text_input("🔍 Cerca per Targa, Marca o Modello:").lower()

    # Filtraggio dinamico
    lista_veicoli = list(st.session_state.parco_auto.values())

    if filtro_stato == "Solo Disponibili":
        lista_veicoli = [v for v in lista_veicoli if v.disponibile]
    elif filtro_stato == "Solo Noleggiati":
        lista_veicoli = [v for v in lista_veicoli if not v.disponibile]

    if ricerca:
        lista_veicoli = [
            v
            for v in lista_veicoli
            if ricerca in v.targa.lower()
            or ricerca in v.marca.lower()
            or ricerca in v.modello.lower()
            or ricerca in v.categoria.lower()
        ]

    if lista_veicoli:
        df_veicoli = pd.DataFrame([v.to_dict() for v in lista_veicoli])
        st.dataframe(df_veicoli, use_container_width=True, hide_index=True)
    else:
        st.info("Nessun veicolo corrisponde ai criteri di ricerca.")


# --- TAB 2: NUOVO NOLEGGIO ---
with tab_noleggio:
    st.subheader("Registra un Nuovo Noleggio")

    veicoli_disponibili = {
        f"[{v.targa}] {v.marca} {v.modello} ({v.categoria}) - €{v.prezzo_giornaliero:.2f}/gg": v.targa
        for v in st.session_state.parco_auto.values()
        if v.disponibile
    }

    if not veicoli_disponibili:
        st.warning(
            "⚠️ Nessun veicolo attualmente disponibile per il noleggio."
        )
    else:
        with st.form("form_noleggio"):
            scelta_label = st.selectbox(
                "Seleziona Veicolo:", list(veicoli_disponibili.keys())
            )
            nome_cliente = st.text_input("Nome e Cognome Cliente:")
            giorni = st.number_input(
                "Durata noleggio (giorni):", min_value=1, value=1, step=1
            )

            # Calcolo preventivo dinamico
            targa_sel = veicoli_disponibili[scelta_label]
            veicolo_sel = st.session_state.parco_auto[targa_sel]

            prezzo_base = veicolo_sel.prezzo_giornaliero * giorni
            sconto_pct = (
                20
                if giorni >= 30
                else (10 if giorni >= 7 else (5 if giorni >= 3 else 0))
            )
            sconto_euro = prezzo_base * (sconto_pct / 100)
            costo_totale = prezzo_base - sconto_euro

            st.divider()
            st.markdown("### 🧾 Calcolo Preventivo")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Prezzo Base", f"€ {prezzo_base:.2f}")
            c2.metric("Sconto (%)", f"{sconto_pct}%")
            c3.metric("Risparmio", f"-€ {sconto_euro:.2f}")
            c4.metric("Totale da Pagare", f"€ {costo_totale:.2f}")

            submit_noleggio = st.form_submit_button(
                "Conferma Noleggio e Genera Ricevuta"
            )

            if submit_noleggio:
                if not nome_cliente.strip():
                    st.error("Attenzione: Inserisci il nome del cliente.")
                else:
                    veicolo_sel.disponibile = False
                    noleggio_obj = Noleggio(veicolo_sel, nome_cliente, giorni)
                    st.session_state.noleggi_attivi[targa_sel] = noleggio_obj
                    st.session_state.incassi_totali += (
                        noleggio_obj.costo_totale
                    )

                    st.success(
                        f"✅ Noleggio registrato per {nome_cliente}! Veicolo assegnato: [{targa_sel}]."
                    )
                    st.balloons()
                    st.rerun()


# --- TAB 3: RESTITUZIONE VEICOLO ---
with tab_restituzione:
    st.subheader("Restituzione Veicolo")

    noleggi_attivi = st.session_state.noleggi_attivi

    if not noleggi_attivi:
        st.info("Attualmente non ci sono noleggi in corso.")
    else:
        opzioni = {
            f"[{n.veicolo.targa}] {n.veicolo.marca} {n.veicolo.modello} - Cliente: {n.nome_cliente}": targa
            for targa, n in noleggi_attivi.items()
        }

        scelta_rest = st.selectbox(
            "Seleziona il noleggio da chiudere:", list(opzioni.keys())
        )
        targa_restituzione = opzioni[scelta_rest]
        info_noleggio = noleggi_attivi[targa_restituzione]

        st.write(f"**Cliente:** {info_noleggio.nome_cliente}")
        st.write(f"**Data inizio:** {info_noleggio.data_inizio}")
        st.write(f"**Durata:** {info_noleggio.giorni} giorni")
        st.write(
            f"**Totale Noleggio:** € {info_noleggio.costo_totale:.2f} (Sconto {info_noleggio.percentuale_sconto}%)"
        )

        if st.button("🔴 Conferma Restituzione Auto"):
            st.session_state.parco_auto[targa_restituzione].disponibile = True
            del st.session_state.noleggi_attivi[targa_restituzione]
            st.success(
                f"Veicolo [{targa_restituzione}] restituito correttamente ed è di nuovo disponibile."
            )
            st.rerun()


# --- TAB 4: AGGIUNGI AUTO ---
with tab_aggiungi:
    st.subheader("Aggiungi un nuovo veicolo al parco auto")

    with st.form("form_aggiungi_auto"):
        c_a, c_b = st.columns(2)
        with c_a:
            nuova_targa = st.text_input("Targa:").upper()
            nuova_marca = st.text_input("Marca (es. Fiat, Ford):")
            nuovo_modello = st.text_input("Modello (es. Panda, Golf):")
        with c_b:
            nuova_categoria = st.selectbox(
                "Categoria:",
                ["Economica", "Compatta", "Berlina", "SUV", "Lusso", "Furgone"],
            )
            nuovo_prezzo = st.number_input(
                "Prezzo Giornaliero (€):", min_value=1.0, value=40.0, step=5.0
            )

        submit_aggiungi = st.form_submit_button("Aggiungi alla Flotta")

        if submit_aggiungi:
            targa_clean = nuova_targa.strip()
            if not targa_clean:
                st.error("Inserisci una targa valida.")
            elif targa_clean in st.session_state.parco_auto:
                st.error("Un veicolo con questa targa è già registrato.")
            elif not nuova_marca or not nuovo_modello:
                st.error("Compila tutti i campi obbligatori.")
            else:
                nuovo_veicolo = Veicolo(
                    targa_clean,
                    nuova_marca,
                    nuovo_modello,
                    nuova_categoria,
                    nuovo_prezzo,
                )
                st.session_state.parco_auto[targa_clean] = nuovo_veicolo
                st.success(f"✅ Auto [{targa_clean}] aggiunta alla flotta!")
                st.rerun()
