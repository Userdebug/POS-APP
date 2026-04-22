#!/usr/bin/env python3
"""Check category structure."""

import sys

sys.path.insert(0, "C:\\Users\\nak\\Documents\\Projet\\POS-APP")

from core.database import DatabaseManager

db = DatabaseManager("database/app.db")
with db._connect() as conn:
    print("=== Category hierarchy ===")
    rows = conn.execute("""
        SELECT p.nom as parent, c.nom as child, c.id
        FROM categories c
        LEFT JOIN categories p ON c.parent_id = p.id
        ORDER BY p.nom, c.nom
    """).fetchall()
    for row in rows:
        print(f"  {row['parent'] or 'ROOT'} > {row['child']} (id={row['id']})")
