import sqlite3
from pathlib import Path
import os

os.chdir(Path(__file__).resolve().parent)
db_path = Path("database") / "app.db"
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Vérifier les timestamps pour BA (catégorie_id=4)
print("=== Historique des modifications pour BA (categorie_id=4) ===")
cursor.execute("""
    SELECT jour, si, sf, created_at, updated_at, cloturee
    FROM Tcollecte
    WHERE categorie_id = 4
    ORDER BY jour
""")
rows = cursor.fetchall()
for row in rows:
    print(
        f"Jour={row['jour']}: SI={row['si']}, SF={row['sf']}, Created={row['created_at']}, Updated={row['updated_at']}, Clot={row['cloturee']}"
    )

print("\n=== Vérification: y a-t-il eu des entrées (EB/ER) dans mouvements_stock? ===")
cursor.execute(
    "SELECT type_mouvement, COUNT(*) as cnt FROM mouvements_stock GROUP BY type_mouvement"
)
for r in cursor.fetchall():
    print(f"Type={r['type_mouvement']}, Count={r['cnt']}")

print("\n=== Détail des mouvements_stock (s'il y en a) ===")
cursor.execute("SELECT * FROM mouvements_stock LIMIT 10")
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(dict(row))
else:
    print("Table mouvements_stock vide")

print("\n=== Vérifier produits catégorie BA (ID=4): stock total par produit ===")
cursor.execute("""
    SELECT id, nom, stock_boutique, stock_reserve, pa,
           (stock_boutique + stock_reserve) as total_q, 
           (stock_boutique + stock_reserve) * pa as total_valeur
    FROM produits
    WHERE categorie_id = 4
    ORDER BY nom
""")
rows = cursor.fetchall()
total_sf = 0
for row in rows:
    print(
        f"  {row['nom']}: B={row['stock_boutique']}, R={row['stock_reserve']}, PA={row['pa']}, TotalVal={row['total_valeur']}"
    )
    total_sf += row["total_valeur"] or 0
print(f"TOTAL SF calculé depuis produits: {total_sf:,}")

conn.close()
