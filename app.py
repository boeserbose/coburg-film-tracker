import streamlit as st
import pandas as pd
import re
import os
import sqlite3
from pathlib import Path
from datetime import datetime
import io

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
                "Magazine": "",
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
    # Short Ends aus Testdreh (17.-18.12.25) — benutze die von dir gelieferten Namen (Parent + 'a')
    short_ends = [
        {"Roll_ID": "A00T01a", "Emulsion": "5207 (250D)", "Length_ft": 375, "Status": "Short End", "Location": "Set (Praxis)", "Magazine": "", "Notes": "Rest Test (A00T01)", "Exposed_Date": None},
        {"Roll_ID": "TX004a",  "Emulsion": "5219 (500T)", "Length_ft": 300, "Status": "Short End", "Location": "Set (Praxis)", "Magazine": "", "Notes": "Rest Test (TX004) | Hinweis: Push +1", "Exposed_Date": None},
        {"Roll_ID": "A00T002a","Emulsion": "5207 (250D)", "Length_ft": 350, "Status": "Short End", "Location": "Set (Praxis)", "Magazine": "", "Notes": "Rest Test (A00T002)", "Exposed_Date": None},
        {"Roll_ID": "T01Aa",   "Emulsion": "5207 (250D)", "Length_ft": 70,  "Status": "Short End", "Location": "Set (Praxis)", "Magazine": "", "Notes": "Rest Test (T01A) — Sehr kurz!", "Exposed_Date": None},
        {"Roll_ID": "TA009a",  "Emulsion": "5219 (500T)", "Length_ft": 280, "Status": "Short End", "Location": "Set (Praxis)", "Magazine": "", "Notes": "Rest Test (TA009)", "Exposed_Date": None},
        {"Roll_ID": "T002a",   "Emulsion": "5207 (250D)", "Length_ft": 50,  "Status": "Short End", "Location": "Set (Praxis)", "Magazine": "", "Notes": "Labor-Anweisung: Kopierung + Entwicklung (+1 Push)", "Exposed_Date": None},
    ]
    
    return pd.concat([pd.DataFrame(data), pd.DataFrame(short_ends)], ignore_index=True)

# --- APP START ---
def make_empty_inventory():
    cols = ["Roll_ID", "Emulsion", "Length_ft", "Status", "Location", "Magazine", "Notes", "Exposed_Date"]
    return pd.DataFrame(columns=cols)
DB_PATH = Path("data/db.sqlite")
IMG_DIR = Path("data/images")


def db_init():
    os.makedirs(IMG_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        name TEXT PRIMARY KEY,
        created TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project TEXT,
        Roll_ID TEXT,
        Emulsion TEXT,
        Length_ft REAL,
        Status TEXT,
        Location TEXT,
        Magazine TEXT,
        Notes TEXT,
        Exposed_Date TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project TEXT,
        filename TEXT,
        path TEXT
    )
    """)
    conn.commit()
    conn.close()


def load_projects_from_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name, created FROM projects")
    rows = cur.fetchall()
    projects = {}
    if not rows:
        # seed Coburg
        created = datetime.now().strftime('%Y-%m-%d')
        cur.execute("INSERT INTO projects (name, created) VALUES (?,?)", ('Coburg', created))
        conn.commit()
        df = load_initial_data()
        save_inventory_df('Coburg', df, conn=conn)
        projects['Coburg'] = {'inventory': df, 'created': created}
    else:
        for name, created in rows:
            df = pd.read_sql_query("SELECT Roll_ID, Emulsion, Length_ft, Status, Location, Magazine, Notes, Exposed_Date FROM inventory WHERE project = ?", conn, params=(name,))
            projects[name] = {'inventory': df, 'created': created}
    conn.close()
    return projects


def save_inventory_df(project, df, conn=None):
    close_conn = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        close_conn = True
    cur = conn.cursor()
    cur.execute("DELETE FROM inventory WHERE project = ?", (project,))
    conn.commit()
    # Ensure required columns exist
    df2 = df.copy()
    df2['project'] = project
    # Write rows
    df2.to_sql('inventory', conn, if_exists='append', index=False)
    if close_conn:
        conn.close()


def save_image_file(project, filename, data_bytes):
    project_dir = IMG_DIR / project
    project_dir.mkdir(parents=True, exist_ok=True)
    path = project_dir / filename
    with open(path, 'wb') as f:
        f.write(data_bytes)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO images (project, filename, path) VALUES (?,?,?)", (project, filename, str(path)))
    conn.commit()
    conn.close()


# Projekt-Management: Mehrere Projekte unterstützen
db_init()
if 'projects' not in st.session_state:
    st.session_state.projects = load_projects_from_db()

if 'current_project' not in st.session_state:
    st.session_state.current_project = 'Coburg'

# Arbeits-Kopie des aktuellen Inventars
st.session_state.inventory = st.session_state.projects[st.session_state.current_project]['inventory'].copy()


def sync_to_project():
    st.session_state.projects[st.session_state.current_project]['inventory'] = st.session_state.inventory.copy()
    # persist to sqlite
    save_inventory_df(st.session_state.current_project, st.session_state.inventory)

# --- HELPER FUNKTIONEN ---
def get_next_se_name(inventory_df, roll_id):
    # Bestimme Basis (wenn sel_roll wie 'A01a' ist, dann Basis 'A01')
    if roll_id and len(roll_id) > 0 and roll_id[-1].isalpha():
        base = roll_id[:-1]
    else:
        base = roll_id

    # Suche alle existierenden IDs, die mit base beginnen und danach nur Buchstaben haben
    pattern = re.compile(rf"^{re.escape(base)}([A-Za-z]+)$")
    used_suffixes = set()
    for rid in inventory_df['Roll_ID'].astype(str).tolist():
        m = pattern.match(rid)
        if m:
            used_suffixes.add(m.group(1).lower())

    # Finde erstes freies ein-buchstabiges Suffix a, b, c ...
    for i in range(26):
        candidate = chr(ord('a') + i)
        if candidate not in used_suffixes:
            return f"{base}{candidate}"

    # Fallback: falls mehr als 26 short-ends, erweitere mit number
    return f"{base}x{len(used_suffixes)+1}"

# --- UI HEADER ---
st.title("🎥 Projekt Coburg: Material Tracker")

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Admin")
    # Projektwahl / Neues Projekt
    st.markdown("#### Projekt")
    proj_opts = list(st.session_state.projects.keys())
    sel_proj = st.selectbox("Aktuelles Projekt", proj_opts, index=proj_opts.index(st.session_state.current_project))
    if sel_proj != st.session_state.current_project:
        # Speichere aktuellen Stand und wechsle
        sync_to_project()
        st.session_state.current_project = sel_proj
        st.session_state.inventory = st.session_state.projects[sel_proj]['inventory'].copy()

    with st.expander("Neues Projekt anlegen"):
        new_name = st.text_input("Projektname")
        if st.button("Erstellen und wechseln") and new_name:
            if new_name in st.session_state.projects:
                st.warning("Projekt existiert bereits.")
            else:
                st.session_state.projects[new_name] = {'inventory': make_empty_inventory(), 'created': datetime.now().strftime('%Y-%m-%d')}
                sync_to_project()
                st.session_state.current_project = new_name
                st.session_state.inventory = st.session_state.projects[new_name]['inventory'].copy()
                st.success(f"Projekt '{new_name}' erstellt und aktiviert.")

    if st.button("⚠️ PROJEKT RESET (Alles auf Anfang)"):
        # Reset nur für aktuelles Projekt
        if st.session_state.current_project == 'Coburg':
            st.session_state.inventory = load_initial_data()
            st.session_state.projects['Coburg']['inventory'] = st.session_state.inventory.copy()
            st.success("Projekt 'Coburg' zurückgesetzt!")
        else:
            st.session_state.inventory = make_empty_inventory()
            st.session_state.projects[st.session_state.current_project]['inventory'] = st.session_state.inventory.copy()
            st.success(f"Projekt '{st.session_state.current_project}' geleert.")
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
    st.dataframe(active_stock[['Roll_ID', 'Emulsion', 'Length_ft', 'Status', 'Magazine', 'Notes']], use_container_width=True)

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
                # Validierung
                if exp < 0 or waste < 0:
                    st.error("'Belichtet' und 'Waste' müssen >= 0 sein.")
                    st.stop()
                if exp + waste > curr['Length_ft']:
                    st.error("Summe aus 'Belichtet' und 'Waste' darf die Startlänge nicht überschreiten.")
                    st.stop()
                today_str = datetime.now().strftime("%Y-%m-%d")
                
                # 1. Update Ursprungsrolle -> Wird zu "Exposed" (fürs Labor)
                st.session_state.inventory.at[idx, 'Status'] = 'Exposed'
                st.session_state.inventory.at[idx, 'Length_ft'] = exp # Wichtig: hier wird die belichtete Länge gespeichert
                st.session_state.inventory.at[idx, 'Magazine'] = mag
                st.session_state.inventory.at[idx, 'Notes'] = f"Mag: {mag} | {note}"
                st.session_state.inventory.at[idx, 'Exposed_Date'] = today_str
                
                msg = f"✅ Rolle {sel_roll} gespeichert: {exp} ft belichtet."
                
                # 2. Short End erstellen (wenn genug übrig)
                if rest > 40:
                    se_name = get_next_se_name(st.session_state.inventory, sel_roll)
                    new_se = {
                        "Roll_ID": se_name, "Emulsion": curr['Emulsion'],
                        "Length_ft": rest, "Status": "Short End",
                        "Location": "Set (Praxis)", "Magazine": "", "Notes": f"Rest von {sel_roll}", "Exposed_Date": None
                    }
                    st.session_state.inventory = pd.concat([st.session_state.inventory, pd.DataFrame([new_se])], ignore_index=True)
                    msg += f"\n✂️ Short End erstellt: {se_name} ({rest} ft / {ft_to_time(rest)})"

                # Sync in Projekt speichern
                sync_to_project()

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
        st.dataframe(exposed_list[['Roll_ID', 'Emulsion', 'Length_ft', 'Magazine', 'Exposed_Date', 'Notes']], use_container_width=True)
        
        # Summary
        total_exp = exposed_list['Length_ft'].sum()
        st.markdown(f"**Gesamtmenge im Ausgang:** {total_exp} ft ({ft_to_time(total_exp)})")
        
        col_act1, col_act2 = st.columns([1, 3])
        with col_act1:
            if st.button("📦 Als 'Verschickt' markieren"):
                    # Status ändern auf "Sent"
                    for i in exposed_list.index:
                        st.session_state.inventory.at[i, 'Status'] = 'Sent to Lab'
                    sync_to_project()
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
    # --- Foto-Upload & Manuelle Korrektur ---
    st.divider()
    st.markdown("### 📸 Fotos hochladen & manuelle Korrekturen")
    if 'images' not in st.session_state:
        st.session_state['images'] = {}

    uploaded = st.file_uploader("Fotos (mehrere möglich)", type=['png','jpg','jpeg'], accept_multiple_files=True)
    if uploaded:
        for f in uploaded:
            st.session_state['images'][f.name] = f.getvalue()
    if st.session_state['images']:
        st.markdown("**Hochgeladene Bilder**")
        cols = st.columns(3)
        i = 0
        for name, data in st.session_state['images'].items():
            with cols[i % 3]:
                st.image(data, caption=name, use_column_width=True)
            i += 1

    st.markdown("#### Neuen Eintrag aus Bild / manuell anlegen")
    with st.form("create_from_image"):
        img_choice = st.selectbox("Bild (optional)", [""] + list(st.session_state['images'].keys()))
        new_id = st.text_input("Roll_ID")
        new_emu = st.selectbox("Emulsion", ["5219 (500T)", "5207 (250D)"], index=0)
        new_len = st.number_input("Length (ft)", min_value=1, value=100)
        new_status = st.selectbox("Status", ["Fresh", "Short End", "Exposed"] , index=1)
        new_loc = st.selectbox("Location", ["Set (Praxis)", "Cineplus (Lager)", "Schweizsprinter"], index=0)
        new_mag = st.selectbox("Magazine (optional)", ["", "G1 (6887)", "G2 (7115)", "G4 (6795)", "G5 (6223)", "K1 (2413)", "K2 (2279)"])
        new_notes = st.text_input("Notes / Lab-Info")
        if st.form_submit_button("Eintrag erstellen"):
            if not new_id:
                st.error("Bitte `Roll_ID` angeben.")
            else:
                entry = {
                    "Roll_ID": new_id,
                    "Emulsion": new_emu,
                    "Length_ft": new_len,
                    "Status": new_status,
                    "Location": new_loc,
                    "Magazine": new_mag,
                    "Notes": new_notes,
                    "Exposed_Date": None
                }
                st.session_state.inventory = pd.concat([st.session_state.inventory, pd.DataFrame([entry])], ignore_index=True)
                sync_to_project()
                st.success(f"Eintrag {new_id} erstellt.")

    st.markdown("#### Bestehenden Eintrag bearbeiten")
    roll_list = st.session_state.inventory['Roll_ID'].astype(str).tolist()
    if roll_list:
        edit_sel = st.selectbox("Wähle Rolle zum Bearbeiten", [""] + roll_list)
        if edit_sel:
            row = st.session_state.inventory[st.session_state.inventory['Roll_ID'] == edit_sel].iloc[0]
            with st.form("edit_entry"):
                e_emu = st.selectbox("Emulsion", ["5219 (500T)", "5207 (250D)"], index=0 if "500T" in row['Emulsion'] else 1)
                e_len = st.number_input("Length (ft)", min_value=0, value=int(row['Length_ft']))
                e_status = st.selectbox("Status", ["Fresh", "Short End", "Exposed", "Sent to Lab"], index=["Fresh","Short End","Exposed","Sent to Lab"].index(row['Status']) if row['Status'] in ["Fresh","Short End","Exposed","Sent to Lab"] else 0)
                e_loc = st.text_input("Location", value=row['Location'])
                e_mag = st.text_input("Magazine", value=row.get('Magazine', ""))
                e_notes = st.text_input("Notes", value=row.get('Notes', ""))
                if st.form_submit_button("Speichern"):
                    idx = st.session_state.inventory[st.session_state.inventory['Roll_ID'] == edit_sel].index[0]
                    st.session_state.inventory.at[idx, 'Emulsion'] = e_emu
                    st.session_state.inventory.at[idx, 'Length_ft'] = e_len
                    st.session_state.inventory.at[idx, 'Status'] = e_status
                    st.session_state.inventory.at[idx, 'Location'] = e_loc
                    st.session_state.inventory.at[idx, 'Magazine'] = e_mag
                    st.session_state.inventory.at[idx, 'Notes'] = e_notes
                    sync_to_project()
                    st.success(f"{edit_sel} gespeichert.")
    else:
        st.info("Keine Einträge zum Bearbeiten vorhanden.")
        storage_inv = st.session_state.inventory[~st.session_state.inventory['Location'].str.contains("Set")]
        st.dataframe(storage_inv, use_container_width=True)