# Coburg Film Tracker

Kleine Streamlit-App zum Tracken von 35mm (2-Perf) Filmrollen, Short-Ends und Versandlisten.

Kurz: App speichert Projekte persistent in `data/db.sqlite` und Bilder unter `data/images/<Projekt>/`.

Voraussetzungen
- Python 3.10+ (virtuelle Umgebung empfohlen)
- Abhängigkeiten: in `requirements.txt`

Installation
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Starten
```bash
streamlit run app.py
```

Wichtig
- Das Verzeichnis `data/` enthält die SQLite-DB und Bilder; es ist in `.gitignore` ausgenommen.
- Regelmäßig Backups der DB anlegen:
```bash
bash scripts/backup_db.sh
```

Benutzung (Kurz)
- Projekt wählen oder neues Projekt anlegen in der Sidebar.
- Im Dashboard: nur Set-Material wird angezeigt (Minuten & ft).
- "Magazin Unload": Rolle entladen, `Belichtet` + `Waste` eintragen; Short-End wird automatisch angelegt wenn Rest > 40 ft.
- "Versand / Labor": Exposed-Rollen als 'Verschickt' markieren.
- "Alle Listen": Manuelles Anlegen / Bearbeiten von Einträgen und Bild-Upload (Bilder werden im Projektordner gespeichert).

Persistenz & Backup
- Die App benutzt SQLite (`data/db.sqlite`). Vor dem Teilen oder Deploy: DB-Backups erstellen und Bilder extern sichern (S3/Nextcloud o.ä.).

Weiterentwicklung
- Empfohlen: später Images in externen Storage auslagern (S3) und Benutzerverwaltung hinzufügen.

Dateien
- `app.py` — Hauptanwendung
- `requirements.txt` — Abhängigkeiten
- `scripts/backup_db.sh` — einfaches Backup-Skript

Bei Fragen schreibe kurz — ich kann noch Beispiel-Deploy-Skripte oder Dockerfile hinzufügen.
# coburg-film-tracker