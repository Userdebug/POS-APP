import sqlite3
from pathlib import Path
import os

os.chdir(Path(__file__).resolve().parent)
db_path = Path("database") / "app.db"
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 1. Vérifier les mouvements de stock pour la catégorie BA (ID=4) entre les jours
print("=== Mouvements de stock pour catégorie BA (ID=4) ===")
cursor.execute("""
    SELECT jour, type_mouvement, SUM(quantite) as total_qte
    FROM mouvements_stock
    WHERE produit_id IN (SELECT id FROM produits WHERE categorie_id = 4)
    GROUP BY jour, type_mouvement
    ORDER BY jour DESC, type_mouvement
""")
rows = cursor.fetchall()
for row in rows:
    print(f"Jour={row['jour']}, Type={row['type_mouvement']}, QteTot={row['total_qte']}")

print("\n=== Premiers/derniers mouvements par jour pour BA ===")
cursor.execute("""
    SELECT jour, type_mouvement, quantite, stock_boutique_avant, stock_reserve_avant,
           stock_boutique_apres, stock_reserve_apres
    FROM mouvements_stock
    WHERE produit_id IN (SELECT id FROM produits WHERE categorie_id = 4)
    ORDER BY jour DESC, id
    LIMIT 30
""")
rows = cursor.fetchall()
for row in rows:
    print(
        f"{row['jour']} {row['type_mouvement']} qte={row['quantite']}, "
        f"avant(B+R)={row['stock_boutique_avant']}+{row['stock_reserve_avant']}, "
        f"après(B+R)={row['stock_boutique_apres']}+{row['stock_reserve_apres']}"
    )

# 2. Vérifier si des ventes sont enregistrées dans la table ventes
print("\n=== Ventes enregistrées par jour (toutes catégories) ===")
cursor.execute("""
    SELECT jour, COUNT(*) as nb_ventes, SUM(prix_total) as total_ca
    FROM ventes
    WHERE deleted = 0
    GROUP BY jour
    ORDER BY jour DESC
""")
rows = cursor.fetchall()
for row in rows:
    print(f"Jour={row['jour']}, NbVentes={row['nb_ventes']}, TotalCA={row['total_ca']}")

# 3. Vérifier la table mouvements_stock pour les entrées/sorties du 17 et 20 avril
print("\n=== Activité mouvements_stock le 2026-04-17 ===")
cursor.execute("""
    SELECT jour, type_mouvement, quantite, produit_id
    FROM mouvements_stock
    WHERE jour = '2026-04-17'
    ORDER BY id
""")
rows = cursor.fetchall()
print(f"Nombre de mouvements le 17: {len(rows)}")
for row in rows[:10]:
    print(f"  {row['type_mouvement']} qte={row['quantite']} produit={row['produit_id']}")

print("\n=== Activité mouvements_stock le 2026-04-20 ===")
cursor.execute("""
    SELECT jour, type_mouvement, quantite, produit_id
    FROM mouvements_stock
    WHERE jour = '2026-04-20'
    ORDER BY id
""")
rows = cursor.fetchall()
print(f"Nombre de mouvements le 20: {len(rows)}")
for row in rows[:10]:
    print(f"  {row['type_mouvement']} qte={row['quantite']} produit={row['produit_id']}")

conn.close()
