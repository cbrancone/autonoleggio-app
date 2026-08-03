import datetime
import pandas as pd
import streamlit as st
from supabase import create_client, Client

# ==========================================
# 1. CONFIGURAZIONE PAGINA
# ==========================================
st.set_page_config(
    page_title="Autonoleggio Pro",
    page_icon="🚗",
    layout="wide"
)

# ==========================================
# 2. CONNESSIONE A SUPABASE
# ==========================================
@st.cache_resource
def init_supabase() -> Client:
    """Inizializza il client Supabase recuperando i secret"""
    try:
        url = st.secrets["supabase"]["SUPABASE_URL"]
        key = st.secrets["supabase"]["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("Errore di connessione a Supabase. Controlla la configurazione dei Secrets.")
        st.stop()

supabase = init_supabase()

# ==========================================
# 3. FUNZIONI DATABASE (SUPABASE)
# ==========================================
def leggi_tabella(nome_tabella):
    """Legge tutti i record da una tabella Supabase"""
    try:
        response = supabase.table(nome_tabella).select("*").execute()
        data = response.data
        return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception as e:
        st.error(f"Errore nella lettura della tabella {nome_tabella}: {e}")
        return pd.DataFrame()

def salva_veicolo(targa, marca, modello, categoria, prezzo, anno):
    """Inserisce un nuovo veicolo su Supabase"""
    data = {
        "targa": targa,
        "marca": marca,
        "modello": modello,
        "categoria": categoria,
        "prezzo_giornaliero": prezzo,
        "anno": anno,
        "stato": "Disponibile"
    }
    supabase.table("veicoli").insert(data).execute()

def elimina_veicolo(targa):
    """Elimina un veicolo da Supabase"""
    supabase.table("veicoli").delete().eq("targa", targa).execute()

def registra_noleggio(targa, cliente, doc, d_inizio, d_fine, giorni, totale):
    """Registra un nuovo noleggio e aggiorna lo stato dell'auto"""
    data_noleggio = {
        "targa": targa,
        "cliente_nome": cliente,
        "cliente_documento": doc,
        "data_inizio": str(d_inizio),
        "data_fine": str(d_fine),
        "giorni": giorni,
        "costo_totale": totale,
        "stato": "Attivo"
    }
    # Inserisce la prenotazione
    supabase.table("noleggi").insert(data_noleggio).execute()
    # Cambia lo stato dell'auto a 'Noleggiato'
    supabase.table("veicoli").update({"stato": "Noleggiato"}).eq("targa", targa).execute()

def chiudi_noleggio(id_noleggio, targa):
    """Chiude un noleggio attivo e ripristina l'auto a 'Disponibile'"""
    supabase.table("noleggi").update({"stato": "Completato"}).eq("id", id_noleggio).execute()
    supabase.table("veicoli").update({"stato": "Disponibile"}).eq("targa", targa).execute()

# ==========================================
# 4. INTERFACCIA UTENTE (STREAMLIT)
# ==========================================
st.sidebar.title("🚘 Autonoleggio Pro")
st.sidebar.caption("Sincronizzato con Supabase Cloud")

menu = st.sidebar.radio(
    "Navigazione Menu:",
    [
        "📊 Dashboard",
        "🚙 Gestione Flotta",
        "🔑 Nuovo Noleggio",
        "🔄 Restituzione",
        "📜 Storico Noleggi"
    ]
)

# ------------------------------------------
# A. DASHBOARD
# ------------------------------------------
if menu == "📊 Dashboard":
    st.title("📊 Dashboard Panoramica")
    
    df_veicoli = leggi_tabella("veicoli")
    df_noleggi = leggi_tabella("noleggi")
    
    df_attivi = df_noleggi[df_noleggi["stato"] == "Attivo"] if not df_noleggi.empty and "stato" in df_noleggi.columns else pd.DataFrame()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Totale Flotta", len(df_veicoli) if not df_veicoli.empty else 0)
    col2.metric("Disponibili", len(df_veicoli[df_veicoli['stato'] == 'Disponibile']) if not df_veicoli.empty and 'stato' in df_veicoli.columns else 0)
    col3.metric("Noleggi Attivi", len(df_attivi))
    
    fatturato = pd.to_numeric(df_noleggi['costo_totale'], errors='coerce').sum() if not df_noleggi.empty and 'costo_totale' in df_noleggi.columns else 0.0
    col4.metric("Fatturato Totale", f"{fatturato:.2f} €")
    
    st.markdown("---")
    st.subheader("📌 Stato Flotta Veicoli")
    if not df_veicoli.empty and all(k in df_veicoli.columns for k in ['targa', 'marca', 'modello', 'categoria', 'prezzo_giornaliero', 'stato']):
        st.dataframe(df_veicoli[['targa', 'marca', 'modello', 'categoria', 'prezzo_giornaliero', 'stato']], use_container_width=True, hide_index=True)
    else:
        st.info("Nessun veicolo registrato nel database Supabase.")

# ------------------------------------------
# B. GESTIONE FLOTTA
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
            categoria = col2.selectbox("Categoria", ["Utilitaria", "Berlina", "SUV", "Furgone"])
            prezzo = col1.number_input("Prezzo Giornaliero (€)", min_value=10.0, value=50.0)
            anno = col2.number_input("Anno", min_value=2000, value=2024)
            
            if st.form_submit_button("Salva Veicolo"):
                if targa and marca and modello:
                    df_v = leggi_tabella("veicoli")
                    if not df_v.empty and targa in df_v['targa'].astype(str).values:
                        st.error(f"La targa {targa} esiste già nel database.")
                    else:
                        salva_veicolo(targa, marca, modello, categoria, prezzo, anno)
                        st.success(f"Veicolo {targa} salvato su Supabase!")
                        st.rerun()
                else:
                    st.warning("Compila tutti i campi obbligatori.")
                    
    with tab2:
        df_veicoli = leggi_tabella("veicoli")
        if not df_veicoli.empty:
            for _, row in df_veicoli.iterrows():
                col_info, col_btn = st.columns([4, 1])
                col_info.write(f"**{row['targa']}** - {row['marca']} {row['modello']} (`{row['stato']}`)")
                if row['stato'] == 'Disponibile':
                    if col_btn.button("🗑️ Elimina", key=f"del_{row['targa']}"):
                        elimina_veicolo(row['targa'])
                        st.success(f"Veicolo {row['targa']} rimosso.")
                        st.rerun()
                st.divider()
        else:
            st.info("Nessun veicolo presente.")

# ------------------------------------------
# C. NUOVO NOLEGGIO
# ------------------------------------------
elif menu == "🔑 Nuovo Noleggio":
    st.title("🔑 Registra Noleggio")
    
    df_veicoli = leggi_tabella("veicoli")
    df_disp = df_veicoli[df_veicoli['stato'] == 'Disponibile'] if not df_veicoli.empty and 'stato' in df_veicoli.columns else pd.DataFrame()
    
    if df_disp.empty:
        st.warning("Nessun veicolo disponibile al momento per il noleggio.")
    else:
        opzioni = {f"{r['targa']} - {r['marca']} {r['modello']} ({r['prezzo_giornaliero']}€/gg)": r for _, r in df_disp.iterrows()}
        scelta = st.selectbox("Seleziona Auto:", list(opzioni.keys()))
        auto = opzioni[scelta]
        
        with st.form("form_noleggio"):
            cliente = st.text_input("Nome Cliente")
            doc = st.text_input("Documento (Patente/CF)")
            d_inizio = st.date_input("Inizio", datetime.date.today())
            d_fine = st.date_input("Fine", datetime.date.today() + datetime.timedelta(days=3))
            
            giorni = (d_fine - d_inizio).days
            totale = giorni * float(auto['prezzo_giornaliero'])
            
            if giorni > 0:
                st.info(f"Costo Totale Previsto: **{totale:.2f} €** ({giorni} giorni)")
            
            if st.form_submit_button("Conferma e Salva Noleggio"):
                if giorni > 0 and cliente and doc:
                    registra_noleggio(auto['targa'], cliente, doc, d_inizio, d_fine, giorni, totale)
                    st.success("Noleggio registrato con successo!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Inserisci date valide e compila i dati del cliente.")

# ------------------------------------------
# D. RESTITUZIONE
# ------------------------------------------
elif menu == "🔄 Restituzione":
    st.title("🔄 Rientro Veicolo")
    
    df_noleggi = leggi_tabella("noleggi")
    df_attivi = df_noleggi[df_noleggi["stato"] == "Attivo"] if not df_noleggi.empty and 'stato' in df_noleggi.columns else pd.DataFrame()
    
    if df_attivi.empty:
        st.info("Nessun noleggio attualmente in corso.")
    else:
        opzioni = {f"ID: {r['id']} | Targa: {r['targa']} | Cliente: {r['cliente_nome']}": r for _, r in df_attivi.iterrows()}
        scelta = st.selectbox("Seleziona Noleggio da chiudere:", list(opzioni.keys()))
        noleggio = opzioni[scelta]
        
        if st.button("✅ Registra Rientro", type="primary"):
            chiudi_noleggio(noleggio['id'], noleggio['targa'])
            st.success("Veicolo rientrato con successo! Stato aggiornato a 'Disponibile'.")
            st.rerun()

# ------------------------------------------
# E. STORICO NOLEGGI
# ------------------------------------------
elif menu == "📜 Storico Noleggi":
    st.title("📜 Storico Noleggi Registrati")
    df_storico = leggi_tabella("noleggi")
    
    if not df_storico.empty:
        st.dataframe(df_storico, use_container_width=True, hide_index=True)
    else:
        st.info("Nessun noleggio salvato nel database.")
