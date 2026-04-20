from core.database import DatabaseManager

db = DatabaseManager()
with db._connect() as conn:
    print("=== Tcollecte structure ===")
    cols = conn.execute("PRAGMA table_info(Tcollecte)").fetchall()
    for c in cols:
        print(f"  {c[1]}: {c[2]}")

    print("\n=== Tcollecte unique dates ===")
    dates = conn.execute("SELECT DISTINCT jour FROM Tcollecte ORDER BY jour").fetchall()
    for d in dates:
        print(f"  {d[0]}")

    print("\n=== Tcollecte categories (should be OW subcategories) ===")
    cats = conn.execute("""
        SELECT DISTINCT t.categorie_id, c.nom, parent.nom as parent
        FROM Tcollecte t 
        JOIN categories c ON t.categorie_id = c.id
        JOIN categories parent ON c.parent_id = parent.id
        WHERE parent.nom = 'Catégorie 1 - OW (Owners)'
        ORDER BY c.nom
    """).fetchall()
    print(f"  Found {len(cats)} OW categories:")
    for c in cats:
        print(f"    id={c[0]}, nom={c[1]}, parent={c[2]}")

    print("\n=== Tcollecte ALL categories (no filter) ===")
    all_cats = conn.execute("""
        SELECT DISTINCT t.categorie_id, c.nom
        FROM Tcollecte t 
        JOIN categories c ON t.categorie_id = c.id
        ORDER BY c.nom
    """).fetchall()
    print(f"  Found {len(all_cats)} categories:")
    for c in all_cats:
        print(f"    id={c[0]}, nom={c[1]}")

    print("\n=== What OW categories exist in DB ===")
    ow_cats = conn.execute("""
        SELECT c.id, c.nom, parent.nom as parent
        FROM categories c
        JOIN categories parent ON c.parent_id = parent.id
        WHERE parent.nom = 'Catégorie 1 - OW (Owners)'
    """).fetchall()
    for c in ow_cats:
        print(f"  id={c[0]}, nom={c[1]}, parent={c[2]}")
