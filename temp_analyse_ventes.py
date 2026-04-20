import sqlite3
from pathlib import Path
import os

os.chdir(Path(__file__).resolve().parent)
db_path = Path("database") / "app.db"
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=== VENTES PAR JOUR ET PAR CATÉGORIE (comparaison avec Tcollecte) ===")
cursor.execute("""
    SELECT v.jour, c.nom as categorie, COUNT(*) as nb_ventes, SUM(v.prix_total) as ca_ventes
    FROM ventes v
    JOIN produits p ON v.produit_id = p.id
    JOIN categories c ON p.categorie_id = c.id
    WHERE v.deleted = 0
    GROUP BY v.jour, c.nom
    ORDER BY v.jour DESC, c.nom
""")
ventes_par_cat = cursor.fetchall()
for v in ventes_par_cat:
    print(f"{v['jour']} {v['categorie']}: {v['nb_ventes']} ventes, CA={v['ca_ventes']}")

print("\n=== COMPARAISON: Ventes (table ventes) vs CA dans Tcollecte ===")
cursor.execute("""
    SELECT 
        t.jour,
        c.nom as categorie,
        t.ca as ca_tcollecte,
        (SELECT COALESCE(SUM(v.prix_total),0)
         FROM ventes v
         JOIN produits p ON v.produit_id = p.id
         WHERE v.jour = t.jour AND p.categorie_id = t.categorie_id AND v.deleted=0) as ca_ventes
    FROM Tcollecte t
    JOIN categories c ON t.categorie_id = c.id
    WHERE t.jour >= '2026-04-16'
    ORDER BY t.jour DESC, c.nom
""")
rows = cursor.fetchall()
for row in rows:
    match = (
        "OK"
        if row["ca_tcollecte"] == row["ca_ventes"]
        else f"DIFF ({row['ca_tcollecte'] - row['ca_ventes']})"
    )
    print(
        f"{row['jour']} {row['categorie']}: CA_Tcollecte={row['ca_tcollecte']}, CA_Ventes={row['ca_ventes']} -> {match}"
    )

print("\n=== Vérification presence de mouvements_stock pour les jours avec ventes ===")
cursor.execute("SELECT DISTINCT jour FROM mouvements_stock ORDER BY jour DESC")
days_with_moves = [r["jour"] for r in cursor.fetchall()]
print("Jours avec mouvements_stock:", days_with_moves)

cursor.execute("SELECT DISTINCT jour FROM ventes WHERE deleted=0 ORDER BY jour DESC")
days_with_sales = [r["jour"] for r in cursor.fetchall()]
print("Jours avec ventes:", days_with_sales)

print(
    "Jours avec ventes mais sans mouvements_stock:",
    [d for d in days_with_sales if d not in days_with_moves],
)

conn.close()
