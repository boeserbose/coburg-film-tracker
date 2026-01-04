import streamlit as st
import pandas as pd
from datetime import datetime

# --- KONFIGURATION ---
st.set_page_config(page_title="Film Tracker (2-Perf)", page_icon="🎬", layout="wide")

# --- HELPER: ZEIT UMRECHNUNG (2-PERF @ 24fps) ---
def ft_to_time(ft):
    if pd.isna(ft) or ft == 0:
        return "00:00"
    total_seconds = int((ft / 45) * 60)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d} min"

# --- INITIAL DATEN (PROJEKT COBURG) ---
def load_initial_data():
    data = []
    
    # Batch-Funktion (generiert einzelne Dosen-IDs)
    def add_batch(prefix, count, emu, length, loc, note_batch):
        for i in range(1, count + 1):
            data.append({
                "Roll_ID": f"{prefix}_{i:02d}",
                "Emulsion": emu,
                "Length_ft": length,
                "Status": "Fresh",
                "Location": loc,
                "Notes": note_batch,
                "Exposed_Date": None # Neu für Lab-Tracking
            })

    # --- LAGER BESTAND (Reserve) ---
    add_batch("CP_500T_400", 19, "5219 (500T)", 400, "Cineplus (Lager)", "Batch 19x")
    add_batch("CP_500T_1000", 8, "5219 (500T)", 1000, "Cineplus (Lager)", "Batch 8x")
    add_batch("CH_500T_400", 2, "5219 (500T)", 400, "Schweizsprinter", "Batch 2x")
    add_batch("CH_250D_400", 13, "5207 (250D)", 400, "Schweizsprinter", "Batch 13x")
    add_batch("CH_250D_1000", 5, "5207 (250D)", 1000, "Schweizsprinter", "Batch 5x")
    
    # --- AKTIVES SET MATERIAL ---
    add_batch("SET_500T_400", 8, "5219 (500T)", 400, "Set (Praxis)", "Startbestand")
    add_batch("SET_500T_1000", 4, "5219 (500T)", 1000, "Set (Praxis)", "Startbestand")
    add_batch("SET_250D_400", 1, "5207 (250D)", 400, "Set (Praxis)", "Startbestand")
    add_batch("SET_250D_1000", 1, "5207 (250D)", 1000, "Set (Praxis)", "Startbestand")

    # --- SHORT ENDS (Bereits vorhanden) ---
    short_ends = [
        {"Roll_ID": "A00T01A", "Emulsion": "5207 (250D)", "Length_ft": 375, "Status": "Short End", "Location": "Set (Praxis)", "Notes": "Rest Test", "Exposed_Date": None},
        {"Roll_ID": "TX004a",  "Emulsion": "5219 (500T)", "Length_ft": 300, "Status": "Short End", "Location": "Set (Praxis)", "Notes": "Rest Test", "Exposed_Date": None},
        {"Roll_ID": "A00T002a","Emulsion": "5207 (250D)", "Length_ft": 350, "Status": "Short End", "Location": "Set (Praxis)", "Notes": "Rest Test", "Exposed_Date": None},
        {"Roll_ID": "T01Aa",   "Emulsion": "5207 (250D)", "Length_ft": 70,  "Status": "Short End", "Location": "Set (Praxis)", "Notes": "Rest Test (kurz)", "Exposed_Date": None},
        {"Roll_ID": "TA009a",  "Emulsion": "5219 (500T)", "Length_ft": 280, "Status": "Short End", "Location": "Set (Praxis)", "Notes": "Rest Test", "Exposed_Date": None},
    ]
    
    return pd.concat([pd.DataFrame(data), pd.DataFrame(short_ends)], ignore_index=True)

# --- APP START ---
if 'inventory' not in st.session_state:
    st.session_state.inventory = load_initial_data()

# --- HELPER FUNKTIONEN ---
def get_next_se_name(roll_id):
    if roll_id and roll_id[-1].isalpha() and roll_id[-1].islower():
        return roll_id[:-1] + chr(ord(roll_id[-1]) + 1)
    else:
        return str(roll_id) + "a"

# --- UI HEADER ---
st.title("🎥 Projekt Coburg: Material Tracker")

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Admin")
    if st.button("⚠️ PROJEKT RESET (Alles auf Anfang)"):
        st.session_state.inventory = load_initial_data()
        st.success("Datenbank zurückgesetzt!")
    st.info("Das Kopierwerk heißt offiziell 'Lab' oder 'Kopierwerk'.")

# TABS
tab_dash, tab_work, tab_lab, tab_list = st.tabs(["📊 Set-Dashboard", "🎬 Magazin Unload", "🚚 Versand / Labor", "📦 Alle Listen"])

# --- TAB 1: DASHBOARD (NUR SET MATERIAL) ---
with tab_dash:
    # Filter: Nur Material, das wirklich am Set ist
    set_inv = st.session_state.inventory[st.session_state.inventory['Location'].str.contains("Set", case=False)]
    
    # Berechnungen (Nur Fresh & Short Ends)
    active_stock = set_inv[set_inv['Status'].isin(['Fresh', 'Short End'])]
    
    ft_500T = active_stock[active_stock['Emulsion'].str.contains("500T")]['Length_ft'].sum()
    ft_250D = active_stock[active_stock['Emulsion'].str.contains("250D")]['Length_ft'].sum()
    
    # Visualisierung
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🌙 500T (Tungsten)")
        st.metric("Verfügbar am Set", f"{ft_to_time(ft_500T)}", delta=f"{ft_500T} ft")
    with col2:
        st.markdown("### ☀️ 250D (Daylight)")
        st.metric("Verfügbar am Set", f"{ft_to_time(ft_250D)}", delta=f"{ft_250D} ft")

    st.divider()
    st.markdown("##### Schnell-Übersicht (Set)")
    st.dataframe(active_stock[['Roll_ID', 'Emulsion', 'Length_ft', 'Status', 'Notes']], use_container_width=True)

# --- TAB 2: ARBEIT (UNLOAD) ---
with tab_work:
    st.subheader("Kamerabericht: Rolle entladen")
    
    # Nur verfügbare Rollen am Set laden
    available = st.session_state.inventory[
        (st.session_state.inventory['Location'].str.contains("Set")) & 
        (st.session_state.inventory['Status'].isin(['Fresh', 'Short End']))
    ]
    
    roll_opts = available['Roll_ID'].tolist()
    
    if roll_opts:
        sel_roll = st.selectbox("Welche Rolle kommt raus?", roll_opts)
        curr = st.session_state.inventory[st.session_state.inventory['Roll_ID'] == sel_roll].iloc[0]
        
        st.info(f"Gewählt: **{curr['Emulsion']}** | Start: {curr['Length_ft']} ft")
        
        with st.form("unload"):
            c1, c2 = st.columns(2)
            with c1:
                mag = st.selectbox("Magazin", ["G1 (6887)", "G2 (7115)", "G4 (6795)", "G5 (6223)", "K1 (2413)", "K2 (2279)"])
                exp = st.number_input("Belichtet (Exposed)", min_value=0, max_value=int(curr['Length_ft']))
            with c2:
                waste = st.number_input("Waste (Müll)", value=15)
                note = st.text_input("Notiz (Push/Pull/Kratzer)")
            
            if st.form_submit_button("Speichern & Berechnen"):
                # Mathe
                rest = curr['Length_ft'] - exp - waste
                idx = available[available['Roll_ID'] == sel_roll].index[0]
                today_str = datetime.now().strftime("%Y-%m-%d")
                
                # 1. Update Ursprungsrolle -> Wird zu "Exposed" (fürs Labor)
                st.session_state.inventory.at[idx, 'Status'] = 'Exposed'
                st.session_state.inventory.at[idx, 'Length_ft'] = exp # Wichtig: Hier steht jetzt die belichtete Länge drin!
                st.session_state.inventory.at[idx, 'Notes'] = f"Mag: {mag} | {note}"
                st.session_state.inventory.at[idx, 'Exposed_Date'] = today_str
                
                msg = f"✅ Rolle {sel_roll} gespeichert: {exp} ft belichtet."
                
                # 2. Short End erstellen (wenn genug übrig)
                if rest > 40:
                    se_name = get_next_se_name(sel_roll)
                    new_se = {
                        "Roll_ID": se_name, "Emulsion": curr['Emulsion'],
                        "Length_ft": rest, "Status": "Short End",
                        "Location": "Set (Praxis)", "Notes": f"Rest von {sel_roll}", "Exposed_Date": None
                    }
                    st.session_state.inventory = pd.concat([st.session_state.inventory, pd.DataFrame([new_se])], ignore_index=True)
                    msg += f"\n✂️ Short End erstellt: {se_name} ({rest} ft / {ft_to_time(rest)})"
                
                st.success(msg)
                st.rerun()
    else:
        st.warning("Kein Material am Set verfügbar! (Ggfs. aus dem Lager holen?)")

# --- TAB 3: LABOR / KOPIERWERK ---
with tab_lab:
    st.subheader("🚚 Versand ans Kopierwerk")
    st.caption("Hier siehst du alle Rollen, die belichtet wurden, aber noch nicht 'verschickt' sind.")
    
    # Zeige alles was "Exposed" ist
    exposed_list = st.session_state.inventory[st.session_state.inventory['Status'] == 'Exposed']
    
    if not exposed_list.empty:
        # Zeige Tabelle
        st.dataframe(exposed_list[['Roll_ID', 'Emulsion', 'Length_ft', 'Exposed_Date', 'Notes']], use_container_width=True)
        
        # Summary
        total_exp = exposed_list['Length_ft'].sum()
        st.markdown(f"**Gesamtmenge im Ausgang:** {total_exp} ft ({ft_to_time(total_exp)})")
        
        col_act1, col_act2 = st.columns([1, 3])
        with col_act1:
            if st.button("📦 Als 'Verschickt' markieren"):
                # Status ändern auf "Sent"
                for i in exposed_list.index:
                    st.session_state.inventory.at[i, 'Status'] = 'Sent to Lab'
                st.success("Status aktualisiert! Liste ist jetzt leer.")
                st.rerun()
        with col_act2:
            st.caption("⚠️ Klick hier erst, wenn der Fahrer die Dosen abgeholt hat. Sie verschwinden dann aus dieser Ansicht.")
            
    else:
        st.info("Aktuell keine offenen belichteten Rollen. Alles sauber!")
        
    st.divider()
    with st.expander("Historie (Bereits verschickt)"):
        sent_list = st.session_state.inventory[st.session_state.inventory['Status'] == 'Sent to Lab']
        st.dataframe(sent_list, use_container_width=True)

# --- TAB 4: ALLE LISTEN (LAGER) ---
with tab_list:
    st.subheader("Gesamtbestand (Lager & Set)")
    
    tab_a, tab_b = st.tabs(["Set (Aktuell)", "Lager (Reserve)"])
    
    with tab_a:
        st.dataframe(st.session_state.inventory[st.session_state.inventory['Location'].str.contains("Set")], use_container_width=True)
        
    with tab_b:
        st.warning("Hier ist das Material, das noch bei Cineplus oder im Sprinter liegt.")
        storage_inv = st.session_state.inventory[~st.session_state.inventory['Location'].str.contains("Set")]
        st.dataframe(storage_inv, use_container_width=True)
