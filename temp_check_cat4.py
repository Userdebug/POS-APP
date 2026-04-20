import sqlite3
from pathlib import Path
import os

os.chdir(Path(__file__).resolve().parent)
db_path = Path("database") / "app.db"
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Vérifier d'abord les catégories existantes
print("=== Catégories dans la base ===")
cursor.execute("SELECT id, nom, parent_id FROM categories ORDER BY id")
cats = cursor.fetchall()
for c in cats:
    print(f"ID={c['id']}, Nom='{c['nom']}', Parent={c['parent_id']}")

# Trouver la catégorie 4 (OW) si elle existe
cursor.execute("""
    SELECT id, nom FROM categories
    WHERE parent_id = (SELECT id FROM categories WHERE nom LIKE '%OW%' OR nom LIKE '%Owners%')
""")
ow_parents = cursor.fetchall()
if ow_parents:
    print(f"\nCatégories OW trouvées: {[dict(r) for r in ow_parents]}")
else:
    print("\nAucune catégorie parent 'OW' trouvée")

# Afficher toutes les catégories pour voir
cursor.execute("SELECT id, nom FROM categories ORDER BY id")
all_cats = cursor.fetchall()
print("\nToutes les catégories:")
for c in all_cats:
    print(f"  {c['id']}: {c['nom']}")

# Essayer de trouver une catégorie dont le nom contient "4" ou "Catégorie 4"
cursor.execute("SELECT id, nom FROM categories WHERE nom LIKE '%4%' OR nom LIKE '%quatrième%'")
cat4_candidates = cursor.fetchall()
if cat4_candidates:
    print("\nCandidats catégorie 4:")
    for c in cat4_candidates:
        print(f"  {c['id']}: {c['nom']}")
else:
    print("\nAucune catégorie contenant '4' trouvée")

conn.close()
