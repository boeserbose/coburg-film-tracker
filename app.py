import streamlit as st
import pandas as pd
from datetime import datetime

# --- KONFIGURATION ---
st.set_page_config(page_title="Film Tracker (2-Perf)", page_icon="🎥", layout="wide")

# --- HELPER: ZEIT UMRECHNUNG (2-PERF @ 24fps) ---
def ft_to_time(ft):
    if pd.isna(ft) or ft == 0:
        return "00:00"
    # Regel: 45 ft = 1 Minute (bei 24fps 2-Perf)
    total_seconds = int((ft / 45) * 60)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d} min"

# --- INITIAL DATEN (LADEN BEIM ERSTEN START) ---
def load_initial_data():
    data = []
    
    # Batch-Generator Funktion
    def add_batch(prefix, count, emu, length, loc, note_batch):
        for i in range(1, count + 1):
            data.append({
                "Roll_ID": f"{prefix}_{i:02d}",
                "Emulsion": emu,
                "Length_ft": length,
                "Status": "Fresh",
                "Location": loc,
                "Notes": note_batch
            })

    # --- BESTAND COBURG ---
    # CINEPLUS LAGER
    add_batch("CP_500T_400", 19, "5219 (500T)", 400, "Cineplus", "Batch 19x")
    add_batch("CP_500T_1000", 8, "5219 (500T)", 1000, "Cineplus", "Batch 8x")
    
    # SCHWEIZSPRINTER
    add_batch("CH_500T_400", 2, "5219 (500T)", 400, "Schweizsprinter", "Batch 2x")
    add_batch("CH_250D_400", 13, "5207 (250D)", 400, "Schweizsprinter", "Batch 13x")
    add_batch("CH_250D_1000", 5, "5207 (250D)", 1000, "Schweizsprinter", "Batch 5x")
    
    # PRAXISZIMMER (SET - Startbestand 1. Drehtage)
    add_batch("SET_500T_400", 8, "5219 (500T)", 400, "Set (Praxis)", "Startbestand")
    add_batch("SET_500T_1000", 4, "5219 (500T)", 1000, "Set (Praxis)", "Startbestand")
    add_batch("SET_250D_400", 1, "5207 (250D)", 400, "Set (Praxis)", "Startbestand")
    add_batch("SET_250D_1000", 1, "5207 (250D)", 1000, "Set (Praxis)", "Startbestand")

    # --- SHORT ENDS VOM TEST (Manuell) ---
    short_ends = [
        {"Roll_ID": "A00T01A", "Emulsion": "5207 (250D)", "Length_ft": 375, "Status": "Short End", "Location": "Set (Praxis)", "Notes": "Rest Test"},
        {"Roll_ID": "TX004a",  "Emulsion": "5219 (500T)", "Length_ft": 300, "Status": "Short End", "Location": "Set (Praxis)", "Notes": "Rest Test (Push?)"},
        {"Roll_ID": "A00T002a","Emulsion": "5207 (250D)", "Length_ft": 350, "Status": "Short End", "Location": "Set (Praxis)", "Notes": "Rest Test"},
        {"Roll_ID": "T01Aa",   "Emulsion": "5207 (250D)", "Length_ft": 70,  "Status": "Short End", "Location": "Set (Praxis)", "Notes": "Rest Test (kurz)"},
        {"Roll_ID": "TA009a",  "Emulsion": "5219 (500T)", "Length_ft": 280, "Status": "Short End", "Location": "Set (Praxis)", "Notes": "Rest Test"},
    ]
    
    return pd.concat([pd.DataFrame(data), pd.DataFrame(short_ends)], ignore_index=True)

# --- APP START ---
if 'inventory' not in st.session_state:
    st.session_state.inventory = load_initial_data()

if 'logs' not in st.session_state:
    st.session_state.logs = pd.DataFrame(columns=["Zeit", "Aktion", "Rolle", "Info"])

# --- HELPERS ---
def get_next_se_name(roll_id):
    if roll_id and roll_id[-1].isalpha() and roll_id[-1].islower():
        return roll_id[:-1] + chr(ord(roll_id[-1]) + 1)
    else:
        return str(roll_id) + "a"

# --- UI ---
st.title("⏱️ Film Tracker (2-Perf)")

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Admin")
    st.info("2-Perf Modus (45 ft = 1 min)")
    if st.button("⚠️ RESET (Coburg Start)"):
        st.session_state.inventory = load_initial_data()
        st.session_state.logs = pd.DataFrame(columns=["Zeit", "Aktion", "Rolle", "Info"])
        st.success("Reset auf Startbestand!")

tab_dash, tab_work, tab_list = st.tabs(["📊 Set-Dashboard", "🎬 Magazin Unload", "📝 Listen"])

# --- DASHBOARD ---
with tab_dash:
    set_inv = st.session_state.inventory[st.session_state.inventory['Location'].str.contains("Set", case=False)]
    
    # Berechnungen
    fresh_500T = set_inv[(set_inv['Status'].isin(['Fresh'])) & (set_inv['Emulsion'].str.contains("500T"))]['Length_ft'].sum()
    fresh_250D = set_inv[(set_inv['Status'].isin(['Fresh'])) & (set_inv['Emulsion'].str.contains("250D"))]['Length_ft'].sum()
    
    se_inv = set_inv[set_inv['Status'] == 'Short End']
    se_500T = se_inv[se_inv['Emulsion'].str.contains("500T")]['Length_ft'].sum()
    se_250D = se_inv[se_inv['Emulsion'].str.contains("250D")]['Length_ft'].sum()
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🌙 500T (Tungsten)")
        st.metric("Frisch (OVP)", f"{ft_to_time(fresh_500T)}", delta=f"{fresh_500T} ft")
        st.metric("Short Ends", f"{ft_to_time(se_500T)}", delta=f"{se_500T} ft")
        
    with col2:
        st.markdown("### ☀️ 250D (Daylight)")
        st.metric("Frisch (OVP)", f"{ft_to_time(fresh_250D)}", delta=f"{fresh_250D} ft")
        st.metric("Short Ends", f"{ft_to_time(se_250D)}", delta=f"{se_250D} ft")
        
    st.info(f"Gesamtzeit am Set verfügbar: {ft_to_time(fresh_500T + fresh_250D + se_500T + se_250D)}")

# --- WORK AREA ---
with tab_work:
    st.subheader("Rolle kommt aus der Kamera")
    
    # Nur Set-Rollen anzeigen
    available = st.session_state.inventory[
        (st.session_state.inventory['Location'].str.contains("Set")) & 
        (st.session_state.inventory['Status'].isin(['Fresh', 'Short End']))
    ]
    
    roll_opts = available['Roll_ID'].tolist()
    
    if roll_opts:
        sel_roll = st.selectbox("Welche Rolle?", roll_opts)
        curr = st.session_state.inventory[st.session_state.inventory['Roll_ID'] == sel_roll].iloc[0]
        
        st.markdown(f"**{curr['Emulsion']}** | Start: `{curr['Length_ft']} ft` ({ft_to_time(curr['Length_ft'])})")
        
        with st.form("unload"):
            c1, c2 = st.columns(2)
            with c1:
                mag = st.selectbox("Magazin", ["G1 (6887)", "G2 (7115)", "G4 (6795)", "G5 (6223)", "K1 (2413)", "K2 (2279)"])
                exp = st.number_input("Belichtet (ft)", min_value=0, max_value=int(curr['Length_ft']))
            with c2:
                waste = st.number_input("Waste (ft)", value=15)
                note = st.text_input("Notiz (Kratzer/Push/etc)")
            
            if st.form_submit_button("Speichern"):
                # Logic
                rest = curr['Length_ft'] - exp - waste
                idx = available[available['Roll_ID'] == sel_roll].index[0]
                
                # Update Alt
                st.session_state.inventory.at[idx, 'Status'] = 'Exposed'
                st.session_state.inventory.at[idx, 'Length_ft'] = exp
                st.session_state.inventory.at[idx, 'Notes'] = f"Mag: {mag} | {note}"
                
                msg = f"Rolle {sel_roll} -> {ft_to_time(exp)} belichtet."
                
                # Create SE
                if rest > 40:
                    se_name = get_next_se_name(sel_roll)
                    new_se = {
                        "Roll_ID": se_name, "Emulsion": curr['Emulsion'],
                        "Length_ft": rest, "Status": "Short End",
                        "Location": "Set (Praxis)", "Notes": f"Rest von {sel_roll}"
                    }
                    st.session_state.inventory = pd.concat([st.session_state.inventory, pd.DataFrame([new_se])], ignore_index=True)
                    msg += f" Neuer Short End: {se_name} ({ft_to_time(rest)})"
                
                st.success(msg)
                st.rerun()
    else:
        st.error("Kein Material im Set-Inventar!")

# --- LISTS ---
with tab_list:
    st.subheader("Inventar Liste")
    # Zeige Zeitspalte
    df_show = st.session_state.inventory.copy()
    df_show['Laufzeit'] = df_show['Length_ft'].apply(ft_to_time)
    
    filter_stat = st.multiselect("Status", ["Fresh", "Short End", "Exposed"], default=["Fresh", "Short End"])
    st.dataframe(df_show[df_show['Status'].isin(filter_stat)][['Roll_ID', 'Emulsion', 'Length_ft', 'Laufzeit', 'Status', 'Location', 'Notes']], use_container_width=True)
