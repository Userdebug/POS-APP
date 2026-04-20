import sqlite3
from pathlib import Path
import os
from datetime import datetime

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
    f"{'Jour':<12} {'Catégorie':<20} {'SI':>12} {'Achats':>10} {'CA':>12} {'SF':>12} {'ENV':>8} {'VenteThéo':>12} {'Marge':>12} {'Clot':>4}"
)
print("-" * 120)

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
        print(
            f"{row['jour']:<12} {row['categorie']:<20} {row['si']:>12,} {row['achats']:>10,} {row['ca']:>12,} {row['sf']:>12,} {row['env']:>8,} {row['vente_theorique']:>12,} {row['marge']:>12,} {row['cloturee']:>4}"
        )
    print("-" * 120)

conn.close()
