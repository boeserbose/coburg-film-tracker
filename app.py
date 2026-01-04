import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- KONFIGURATION ---
st.set_page_config(page_title="Film Tracker (Mobile)", page_icon="🎬", layout="wide")

# --- GOOGLE SHEETS VERBINDUNG ---
def get_db_connection():
    if 'gcn' not in st.session_state:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = json.loads(st.secrets["gcp_service_account"]["info"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        try:
            sheet = client.open("Coburg_Film_DB").sheet1
            st.session_state.gcn = sheet
        except gspread.exceptions.SpreadsheetNotFound:
            st.error("Fehler: Tabelle 'Coburg_Film_DB' nicht gefunden. Hast du sie erstellt und den Bot eingeladen?")
            st.stop()
    return st.session_state.gcn


def load_data():
    sheet = get_db_connection()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if df.empty:
        return pd.DataFrame(columns=["Roll_ID", "Emulsion", "Length_ft", "Status", "Location", "Magazine", "Notes", "Exposed_Date"])
    if 'Length_ft' in df.columns:
        df['Length_ft'] = pd.to_numeric(df['Length_ft'], errors='coerce').fillna(0)
    return df


def save_data(df):
    sheet = get_db_connection()
    df_clean = df.fillna("")
    sheet.clear()
    sheet.append_row(df_clean.columns.tolist())
    sheet.append_rows(df_clean.values.tolist())
    try:
        st.cache_data.clear()
    except Exception:
        pass


def seed_initial_data():
    data = []
    def add_batch(prefix, count, emu, length, loc, note_batch):
        for i in range(1, count + 1):
            data.append({
                "Roll_ID": f"{prefix}_{i:02d}", "Emulsion": emu, "Length_ft": length,
                "Status": "Fresh", "Location": loc, "Magazine": "", "Notes": note_batch, "Exposed_Date": ""
            })
    add_batch("CP_500T_400", 19, "5219 (500T)", 400, "Cineplus (Lager)", "Batch 19x")
    add_batch("CP_500T_1000", 8, "5219 (500T)", 1000, "Cineplus (Lager)", "Batch 8x")
    add_batch("CH_500T_400", 2, "5219 (500T)", 400, "Schweizsprinter", "Batch 2x")
    add_batch("CH_250D_400", 13, "5207 (250D)", 400, "Schweizsprinter", "Batch 13x")
    add_batch("CH_250D_1000", 5, "5207 (250D)", 1000, "Schweizsprinter", "Batch 5x")
    add_batch("SET_500T_400", 8, "5219 (500T)", 400, "Set (Praxis)", "Startbestand")
    add_batch("SET_500T_1000", 4, "5219 (500T)", 1000, "Set (Praxis)", "Startbestand")
    add_batch("SET_250D_400", 1, "5207 (250D)", 400, "Set (Praxis)", "Startbestand")
    add_batch("SET_250D_1000", 1, "5207 (250D)", 1000, "Set (Praxis)", "Startbestand")
    short_ends = [
        {"Roll_ID": "A00T01a", "Emulsion": "5207 (250D)", "Length_ft": 375, "Status": "Short End", "Location": "Set (Praxis)", "Magazine": "", "Notes": "Rest Test (A00T01)", "Exposed_Date": ""},
        {"Roll_ID": "TX004a",  "Emulsion": "5219 (500T)", "Length_ft": 300, "Status": "Short End", "Location": "Set (Praxis)", "Magazine": "", "Notes": "Rest Test (TX004) | Push +1", "Exposed_Date": ""},
        {"Roll_ID": "A00T002a","Emulsion": "5207 (250D)", "Length_ft": 350, "Status": "Short End", "Location": "Set (Praxis)", "Magazine": "", "Notes": "Rest Test (A00T002)", "Exposed_Date": ""},
        {"Roll_ID": "T01Aa",   "Emulsion": "5207 (250D)", "Length_ft": 70,  "Status": "Short End", "Location": "Set (Praxis)", "Magazine": "", "Notes": "Rest Test (T01A) short", "Exposed_Date": ""},
        {"Roll_ID": "TA009a",  "Emulsion": "5219 (500T)", "Length_ft": 280, "Status": "Short End", "Location": "Set (Praxis)", "Magazine": "", "Notes": "Rest Test (TA009)", "Exposed_Date": ""},
        {"Roll_ID": "T002a",   "Emulsion": "5207 (250D)", "Length_ft": 50,  "Status": "Short End", "Location": "Set (Praxis)", "Magazine": "", "Notes": "Kopierung + Entw. (+1 Push)", "Exposed_Date": ""},
    ]
    df = pd.concat([pd.DataFrame(data), pd.DataFrame(short_ends)], ignore_index=True)
    save_data(df)
    return df


def ft_to_time(ft):
    if pd.isna(ft) or ft == 0: return "00:00"
    total_seconds = int((ft / 45) * 60)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d} min"


def get_next_se_name(inventory_df, roll_id):
    if roll_id and roll_id[-1].isalpha(): base = roll_id[:-1]
    else: base = roll_id
    inventory_df['Roll_ID'] = inventory_df['Roll_ID'].astype(str)
    used_suffixes = [r[-1].lower() for r in inventory_df['ROLL_ID'].tolist() if r.startswith(base) and r[-1].isalpha()]
    for i in range(26):
        char = chr(ord('a') + i)
        if char not in used_suffixes: return f"{base}{char}"
    return f"{base}x"


try:
    if 'inventory' not in st.session_state:
        st.session_state.inventory = load_data()
except Exception as e:
    st.error(f"Verbindungsfehler zu Google Sheets: {e}")
    st.stop()

st.title("🎬 Coburg Film Tracker (Cloud Sync)")

with st.sidebar:
    st.markdown("### ☁️ Google Cloud Status")
    if st.button("⚠️ RESET DB (Startbestand laden)"):
        with st.spinner("Setze Google Sheet zurück..."):
            st.session_state.inventory = seed_initial_data()
            st.success("Datenbank auf Startzustand gesetzt!")
            st.rerun()
    if st.button("🔄 Sync erzwingen (Neu laden)"):
        st.session_state.inventory = load_data()
        st.success("Daten neu aus Cloud geladen!")
        st.rerun()

tab_dash, tab_work, tab_lab, tab_list = st.tabs(["📊 Dashboard", "🎬 Unload", "🚚 Labor", "📦 Listen"])

with tab_dash:
    set_inv = st.session_state.inventory[st.session_state.inventory['Location'].str.contains("Set", case=False)]
    active = set_inv[set_inv['Status'].isin(['Fresh', 'Short End'])]
    ft_500T = active[active['Emulsion'].str.contains("500T")]['Length_ft'].sum()
    ft_250D = active[active['Emulsion'].str.contains("250D")]['Length_ft'].sum()
    c1, c2 = st.columns(2)
    c1.metric("🌙 500T (Set)", f"{ft_to_time(ft_500T)}", f"{ft_500T} ft")
    c2.metric("☀️ 250D (Set)", f"{ft_to_time(ft_250D)}", f"{ft_250D} ft")
    st.dataframe(active[['Roll_ID', 'Emulsion', 'Length_ft', 'Status', 'Notes']], use_container_width=True)

with tab_work:
    st.subheader("Rolle entladen")
    available = st.session_state.inventory[(st.session_state.inventory['Location'].str.contains("Set")) & (st.session_state.inventory['Status'].isin(['Fresh', 'Short End']))]
    roll_opts = available['Roll_ID'].tolist()
    if roll_opts:
        sel_roll = st.selectbox("Rolle", roll_opts)
        curr = st.session_state.inventory[st.session_state.inventory['ROLL_ID'] == sel_roll].iloc[0]
        st.info(f"Start: {curr['Length_ft']} ft ({curr['Emulsion']})")
        with st.form("unload"):
            c1, c2 = st.columns(2)
            mag = c1.selectbox("Mag", ["G1 (6887)", "G2 (7115)", "G4 (6795)", "G5 (6223)", "K1 (2413)", "K2 (2279)"])
            exp = c1.number_input("Belichtet (ft)", 0, int(curr['Length_ft']))
            waste = c2.number_input("Waste (ft)", value=15)
            note = c2.text_input("Notiz")
            if st.form_submit_button("Speichern"):
                rest = curr['Length_ft'] - exp - waste
                idx = st.session_state.inventory[st.session_state.inventory['ROLL_ID'] == sel_roll].index[0]
                st.session_state.inventory.at[idx, 'Status'] = 'Exposed'
                st.session_state.inventory.at[idx, 'Length_ft'] = exp
                st.session_state.inventory.at[idx, 'Magazine'] = mag
                st.session_state.inventory.at[idx, 'Notes'] = f"Mag: {mag} | {note}"
                st.session_state.inventory.at[idx, 'Exposed_Date'] = datetime.now().strftime("%Y-%m-%d")
                msg = f"Rolle {sel_roll} gespeichert."
                if rest > 40:
                    se_name = get_next_se_name(st.session_state.inventory, sel_roll)
                    new_se = {"Roll_ID": se_name, "Emulsion": curr['Emulsion'], "Length_ft": rest, "Status": "Short End", "Location": "Set (Praxis)", "Magazine": "", "Notes": f"Rest von {sel_roll}", "Exposed_Date": ""}
                    st.session_state.inventory = pd.concat([st.session_state.inventory, pd.DataFrame([new_se])], ignore_index=True)
                    msg += f" SE: {se_name}"
                save_data(st.session_state.inventory)
                st.success(msg)
                st.rerun()
    else:
        st.warning("Kein Material am Set verfügbar!")

with tab_lab:
    st.subheader("Versand")
    exposed = st.session_state.inventory[st.session_state.inventory['Status'] == 'Exposed']
    if not exposed.empty:
        st.dataframe(exposed[['Roll_ID', 'Length_ft', 'Notes']], use_container_width=True)
        if st.button("📦 Als VERSCHICKT markieren"):
            for i in exposed.index:
                st.session_state.inventory.at[i, 'Status'] = 'Sent to Lab'
            save_data(st.session_state.inventory)
            st.success("Liste geleert!")
            st.rerun()
    else:
        st.info("Nichts zu verschicken.")

with tab_list:
    st.subheader("Gesamtbestand")
    st.dataframe(st.session_state.inventory, use_container_width=True)
