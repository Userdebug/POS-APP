import sqlite3
from pathlib import Path
import os

os.chdir(Path(__file__).resolve().parent)
db_path = Path("database") / "app.db"
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Récupérer tous les jours
cursor.execute("SELECT DISTINCT jour FROM Tcollecte ORDER BY jour DESC")
days = [r["jour"] for r in cursor.fetchall()]

print("=== Tableau Tcollecte complet (toutes catégories) ===\n")
print(
    f"{'Jour':<12} {'Categorie':<20} {'SI':>12} {'Achats':>10} {'CA':>12} {'SF':>12} {'ENV':>8} {'VenteThéo':>12} {'Marge':>12} {'Clot':>4}"
)
print("-" * 118)

for day in days:
    cursor.execute(
        """
        SELECT c.nom as categorie, t.si, t.achats, t.ca, t.sf, t.env, t.vente_theorique, t.marge, t.cloturee
        FROM Tcollecte t
        JOIN categories c ON t.categorie_id = c.id
        WHERE t.jour = ?
        ORDER BY c.nom
    """,
        (day,),
    )
    rows = cursor.fetchall()
    for row in rows:
        # Convert Row to dict safely
        r = dict(row)
        print(
            f"{r.get('jour', ''):<12} {r.get('categorie', ''):<20} {r.get('si', 0):>12,} {r.get('achats', 0):>10,} {r.get('ca', 0):>12,} {r.get('sf', 0):>12,} {r.get('env', 0):>8,} {r.get('vente_theorique', 0):>12,} {r.get('marge', 0):>12,} {r.get('cloturee', 0):>4}"
        )
    print("-" * 118)

conn.close()
