import datetime
import pandas as pd
import streamlit as st
from supabase import create_client, Client

# ==========================================
# CONFIGURAZIONE PAGINA
# ==========================================
st.set_page_config(
    page_title="Autonoleggio Pro",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# INIZIALIZZAZIONE SUPABASE (CLOUD DATABASE)
# ==========================================
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["https://autonoleggio-app-kujmsvy8gen5we7emmqxnv.streamlit.app/"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(https://autonoleggio-app-kujmsvy8gen5we7emmqxnv.streamlit.app/, key)

supabase = init_supabase()

# ==========================================
# FUNZIONI HELPER DB (SUPABASE)
# ==========================================
def get_veicoli(solo_disponibili=False):
    query = supabase.table("veicoli").select("*")
    if solo_disponibili:
        query = query.eq("stato", "Disponibile")
    data = query.execute().data
    return pd.DataFrame(data)

def inserisci_veicolo(targa, marca, modello, categoria, prezzo, anno):
    targa_formatted = targa.upper()
    
    # Controlla se la targa esiste già
    check = supabase.table("veicoli").select("targa").eq("targa", targa_formatted).execute().data
    if check:
        return False, f"Targa {targa_formatted} già presente nel sistema."
        
    data = {
        "targa": targa_formatted,
        "marca": marca,
        "modello": modello,
        "categoria": categoria,
        "prezzo_giornaliero": prezzo,
        "anno": anno,
        "stato": "Disponibile"
    }
    supabase.table("veicoli").insert(data).execute()
    return True, "Veicolo aggiunto con successo!"

def elimina_veicolo(targa):
    """Elimina un singolo veicolo tramite targa"""
    supabase.table("veicoli").delete().eq("targa", targa).execute()

def reset_parco_veicoli():
    """Elimina TUTTI i veicoli dal parco auto"""
    supabase.table("veicoli").delete().neq("targa", "").execute()

def crea_noleggio(targa, cliente, doc, data_inz, data_fn, giorni, totale):
    data_noleggio = {
        "targa": targa,
        "cliente_nome": cliente,
        "cliente_documento": doc,
        "data_inizio": str(data_inz),
        "data_fine": str(data_fn),
        "giorni": giorni,
        "costo_totale": totale,
        "stato": "Attivo"
    }
    supabase.table("noleggi").insert(data_noleggio).execute()
    supabase.table("veicoli").update({"stato": "Noleggiato"}).eq("targa", targa).execute()

def chiudi_noleggio(noleggio_id, targa):
    supabase.table("noleggi").update({"stato": "Completato"}).eq("id", noleggio_id).execute()
    supabase.table("veicoli").update({"stato": "Disponibile"}).eq("targa", targa).execute()

def get_noleggi(stato="Attivo"):
    data = supabase.table("noleggi").select("*").eq("stato", stato).execute().data
    return pd.DataFrame(data)

def get_tutti_noleggi():
    data = supabase.table("noleggi").select("*").order("id", desc=True).execute().data
    return pd.DataFrame(data)

# ==========================================
# INTERFACCIA UTENTE (STREAMLIT)
# ==========================================

st.sidebar.title("🚘 Autonoleggio Pro")
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Navigazione Menu:",
    ["📊 Dashboard", "🚙 Gestione Flotta", "🔑 Nuovo Noleggio", "🔄 Restituzione Veicolo", "📜 Storico & Report"]
)

st.sidebar.markdown("---")
st.sidebar.caption("Software di Gestione Autonoleggio")

# ------------------------------------------
# 1. DASHBOARD
# ------------------------------------------
if menu == "📊 Dashboard":
    st.title("📊 Dashboard Panoramica")
    st.markdown("Monitora in tempo reale lo stato della flotta e i ricavi.")
    
    df_veicoli = get_veicoli()
    df_noleggi_attivi = get_noleggi("Attivo")
    df_tutti_noleggi = get_tutti_noleggi()
    
    totale_veicoli = len(df_veicoli)
    disponibili = len(df_veicoli[df_veicoli["stato"] == "Disponibile"]) if not df_veicoli.empty else 0
    noleggiati = len(df_veicoli[df_veicoli["stato"] == "Noleggiato"]) if not df_veicoli.empty else 0
    incasso_totale = df_tutti_noleggi["costo_totale"].sum() if not df_tutti_noleggi.empty else 0.0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Totale Flotta", f"{totale_veicoli} auto")
    col2.metric("Disponibili", f"{disponibili} auto")
    col3.metric("Noleggi Attivi", f"{noleggiati} auto")
    col4.metric("Fatturato Totale", f"{incasso_totale:.2f} €")
    
    st.markdown("---")
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📌 Stato Flotta attuale")
        if not df_veicoli.empty:
            st.dataframe(df_veicoli[["targa", "marca", "modello", "categoria", "stato"]], use_container_width=True, hide_index=True)
        else:
            st.info("Nessun veicolo registrato nel sistema.")
    
    with col_right:
        st.subheader("🔑 Ultimi Noleggi Attivi")
        if not df_noleggi_attivi.empty:
            st.dataframe(df_noleggi_attivi[["targa", "cliente_nome", "data_fine", "costo_totale"]], use_container_width=True, hide_index=True)
        else:
            st.info("Nessun noleggio attivo al momento.")

# ------------------------------------------
# 2. GESTIONE FLOTTA
# ------------------------------------------
elif menu == "🚙 Gestione Flotta":
    st.title("🚙 Gestione Flotta Veicoli")
    
    tab1, tab2, tab3 = st.tabs(["📋 Lista Veicoli", "➕ Aggiungi Veicolo", "⚠️ Reset Flotta"])
    
    with tab1:
        st.subheader("Parco Veicoli Registrati")
        df_veicoli = get_veicoli()
        
        if df_veicoli.empty:
            st.info("Nessun veicolo presente nel parco auto.")
        else:
            for idx, row in df_veicoli.iterrows():
                col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 2, 2])
                col1.write(f"**{row['targa']}**")
                col2.write(f"{row['marca']} {row['modello']}")
                col3.write(f"{row['prezzo_giornaliero']:.2f} €/gg")
                col4.write(f"Stato: `{row['stato']}`")
                
                if row['stato'] == 'Disponibile':
                    if col5.button("🗑️ Elimina", key=f"del_{row['targa']}"):
                        elimina_veicolo(row['targa'])
                        st.success(f"Veicolo {row['targa']} eliminato!")
                        st.rerun()
                else:
                    col5.caption("In Noleggio")
                st.divider()

    with tab2:
        st.subheader("Aggiungi un Nuovo Veicolo alla Flotta")
        with st.form("form_nuovo_veicolo", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            targa = col_a.text_input("Targa Auto (es. AB123CD)").strip()
            marca = col_b.text_input("Marca (es. Audi)")
            modello = col_a.text_input("Modello (es. A4)")
            categoria = col_b.selectbox("Categoria", ["Utilitaria", "Berlina", "Station Wagon", "SUV", "Sportiva", "Furgone"])
            prezzo = col_a.number_input("Prezzo Giornaliero (€)", min_value=10.0, value=50.0, step=5.0)
            anno = col_b.number_input("Anno di Immatricolazione", min_value=2000, max_value=2026, value=2023)
            
            submit = st.form_submit_button("Aggiungi Veicolo")
            
            if submit:
                if targa and marca and modello:
                    esito, messaggio = inserisci_veicolo(targa, marca, modello, categoria, prezzo, anno)
                    if esito:
                        st.success(messaggio)
                        st.rerun()
                    else:
                        st.error(messaggio)
                else:
                    st.warning("Per favore compila tutti i campi obbligatori.")

    with tab3:
        st.subheader("⚠️ Zona di Pericolo: Svuotamento Flotta")
        st.warning("Attenzione: questa operazione eliminerà TUTTI i veicoli dal database.")
        
        conferma = st.checkbox("Confermo di voler cancellare l'intero parco veicoli")
        if st.button("🚨 Svuota Intero Parco Veicoli", type="primary", disabled=not conferma):
            reset_parco_veicoli()
            st.success("Tutti i veicoli sono stati eliminati con successo.")
            st.rerun()

# ------------------------------------------
# 3. NUOVO NOLEGGIO
# ------------------------------------------
elif menu == "🔑 Nuovo Noleggio":
    st.title("🔑 Registra Nuovo Noleggio")
    
    df_disponibili = get_veicoli(solo_disponibili=True)
    
    if df_disponibili.empty:
        st.warning("Nessun veicolo disponibile per il noleggio al momento.")
    else:
        opzioni_auto = {
            f"{row['targa']} - {row['marca']} {row['modello']} ({row['prezzo_giornaliero']}€/gg)": row
            for _, row in df_disponibili.iterrows()
        }
        
        scelta_auto_str = st.selectbox("Seleziona Veicolo Disponibile:", list(opzioni_auto.keys()))
        auto_selezionata = opzioni_auto[scelta_auto_str]
        
        st.markdown("---")
        st.subheader("Dati Noleggio e Cliente")
        
        with st.form("form_noleggio"):
            col1, col2 = st.columns(2)
            cliente_nome = col1.text_input("Nome e Cognome Cliente")
            cliente_doc = col2.text_input("Codice Fiscale / N. Patente")
            
            data_inizio = col1.date_input("Data Inizio Noleggio", datetime.date.today())
            data_fine = col2.date_input("Data Fine Noleggio", datetime.date.today() + datetime.timedelta(days=3))
            
            giorni = (data_fine - data_inizio).days
            prezzo_unitario = float(auto_selezionata["prezzo_giornaliero"])
            
            if giorni <= 0:
                st.error("⚠️ La data di fine noleggio deve essere successiva alla data di inizio.")
                totale_preventivo = 0.0
            else:
                totale_preventivo = giorni * prezzo_unitario
                st.info(f"📊 **Riepilogo Costi:** {giorni} giorno/i x {prezzo_unitario:.2f} € = **{totale_preventivo:.2f} €**")
            
            btn_conferma = st.form_submit_button("Conferma e Noleggia")
            
            if btn_conferma:
                if giorni <= 0:
                    st.error("Correggi le date inserite prima di procedere.")
                elif cliente_nome and cliente_doc:
                    crea_noleggio(
                        auto_selezionata["targa"],
                        cliente_nome,
                        cliente_doc,
                        data_inizio,
                        data_fine,
                        giorni,
                        totale_preventivo
                    )
                    st.success(f"🎉 Noleggio registrato con successo per {cliente_nome}!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Inserire tutti i dati del cliente prima di confermare.")

# ------------------------------------------
# 4. RESTITUZIONE VEICOLO
# ------------------------------------------
elif menu == "🔄 Restituzione Veicolo":
    st.title("🔄 Restituzione Veicolo")
    st.markdown("Chiudi un noleggio attivo e ripristina la disponibilità del veicolo.")
    
    df_attivi = get_noleggi("Attivo")
    
    if df_attivi.empty:
        st.info("Nessun noleggio attualmente in corso.")
    else:
        opzioni_rientro = {
            f"ID #{row['id']} | Targa: {row['targa']} | Cliente: {row['cliente_nome']} (Rientro: {row['data_fine']})": row
            for _, row in df_attivi.iterrows()
        }
        
        scelta_rientro = st.selectbox("Seleziona Noleggio da Chiudere:", list(opzioni_rientro.keys()))
        noleggio_sel = opzioni_rientro[scelta_rientro]
        
        st.write("---")
        col_det1, col_det2 = st.columns(2)
        col_det1.write(f"**Cliente:** {noleggio_sel['cliente_nome']}")
        col_det1.write(f"**Documento:** {noleggio_sel['cliente_documento']}")
        col_det2.write(f"**Periodo:** dal {noleggio_sel['data_inizio']} al {noleggio_sel['data_fine']}")
        col_det2.write(f"**Totale Noleggio:** {float(noleggio_sel['costo_totale']):.2f} €")
        
        if st.button("✅ Registra Rientro Veicolo", type="primary"):
            chiudi_noleggio(noleggio_sel["id"], noleggio_sel["targa"])
            st.success(f"Auto targa {noleggio_sel['targa']} restituita con successo ed è ora nuovamente disponibile.")
            st.rerun()

# ------------------------------------------
# 5. STORICO & REPORT
# ------------------------------------------
elif menu == "📜 Storico & Report":
    st.title("📜 Storico Noleggi & Analytics")
    
    df_storico = get_tutti_noleggi()
    
    if df_storico.empty:
        st.info("Nessuno storico noleggi presente.")
    else:
        st.subheader("Registro Completo Transazioni")
        st.dataframe(
            df_storico,
            column_config={
                "id": "ID",
                "targa": "Targa Auto",
                "cliente_nome": "Cliente",
                "cliente_documento": "Documento",
                "data_inizio": "Inizio",
                "data_fine": "Fine",
                "giorni": "Giorni",
                "costo_totale": st.column_config.NumberColumn("Totale Incassato", format="%.2f €"),
                "stato": "Stato Noleggio"
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Download Report CSV
        csv_data = df_storico.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Scarica Report CSV",
            data=csv_data,
            file_name=f"report_noleggi_{datetime.date.today()}.csv",
            mime="text/csv"
        )
        
        st.markdown("---")
        st.subheader("📈 Analisi Categorie Flotta")
        
        df_flotta = get_veicoli()
        if not df_flotta.empty:
            cat_counts = df_flotta["categoria"].value_counts()
            st.bar_chart(cat_counts)
