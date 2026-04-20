import sqlite3
from pathlib import Path
import os

os.chdir(Path(__file__).resolve().parent)
db_path = Path("database") / "app.db"
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT * FROM Tcollecte LIMIT 1")
row = cursor.fetchone()
if row:
    print("Keys disponibles:", list(row.keys()))
    print("First row:", dict(row))
else:
    print("Table vide")

conn.close()
