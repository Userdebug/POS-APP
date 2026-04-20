import sqlite3
from pathlib import Path
import os

os.chdir(Path(__file__).resolve().parent)
db_path = Path("database") / "app.db"
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 1. Ventes par catégorie pour le 2026-04-19 (jour avec ventes mais VenteThéo=0)
print("=== Détail des ventes du 2026-04-19 par catégorie ===")
cursor.execute("""
    SELECT p.nom as produit, v.produit_id, c.nom as categorie, v.quantite, v.prix_total
    FROM ventes v
    JOIN produits p ON v.produit_id = p.id
    JOIN categories c ON p.categorie_id = c.id
    WHERE v.jour = '2026-04-19' AND v.deleted = 0
    ORDER BY c.nom, p.nom
    LIMIT 50
""")
ventes = cursor.fetchall()
for v in ventes:
    print(
        f"Catégorie: {v['categorie']}, Produit: {v['produit']}, Qte: {v['quantite']}, Total: {v['prix_total']}"
    )

print("\n=== Vérification: table mouvements_stock entière (tous types) ===")
cursor.execute("""
    SELECT jour, type_mouvement, COUNT(*) as nb, SUM(quantite) as total_qte
    FROM mouvements_stock
    GROUP BY jour, type_mouvement
    ORDER BY jour DESC, type_mouvement
""")
rows = cursor.fetchall()
for row in rows:
    print(
        f"Jour={row['jour']}, Type={row['type_mouvement']}, Nb={row['nb']}, QteTot={row['total_qte']}"
    )

print("\n=== Y a-t-il des mouvements de type 'RB', 'BR', 'EB', 'ER', 'ENV' ? ===")
cursor.execute("SELECT DISTINCT type_mouvement FROM mouvements_stock")
types = cursor.fetchall()
print("Types de mouvements présents:", [t["type_mouvement"] for t in types])

conn.close()
