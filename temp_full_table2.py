import sqlite3
from pathlib import Path
import os

os.chdir(Path(__file__).resolve().parent)
db_path = Path("database") / "app.db"
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Récupérer tous les jours avec données
cursor.execute("SELECT DISTINCT jour FROM Tcollecte ORDER BY jour DESC")
days = [r["jour"] for r in cursor.fetchall()]

print("=== Tableau Tcollecte complet (toutes catégories) ===\n")
print(
    f"{'Jour':<12} {'Categorie':<20} {'SI':>12} {'Achats':>10} {'CA':>12} {'SF':>12} {'ENV':>8} {'VenteTheo':>12} {'Marge':>12} {'Clot':>4}"
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
        r = dict(row)
        print(
            f"{r['jour']:<12} {r['categorie']:<20} {r['si']:>12,} {r['achats']:>10,} {r['ca']:>12,} {r['sf']:>12,} {r['env']:>8,} {r['vente_theorique']:>12,} {r['marge']:>12,} {r['cloturee']:>4}"
        )
    print("-" * 118)

conn.close()
