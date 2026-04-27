import sqlite3
import os

# Connect to the database
db_path = os.path.join(os.path.dirname(__file__), "data", "pos.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get the schema for categories table
cursor.execute("SELECT sql FROM sqlite_master WHERE name='categories'")
schema = cursor.fetchone()
print("Categories table schema:")
print(schema[0] if schema else "Not found")
print()

# Get column info
cursor.execute("PRAGMA table_info(categories)")
columns = cursor.fetchall()
print("Columns in categories table:")
for col in columns:
    print(
        f"  {col[1]} {col[2]} {'NULL' if col[3] == 0 else 'NOT NULL'} {'DEFAULT ' + str(col[4]) if col[4] is not None else ''} {'PK' if col[5] == 1 else ''}"
    )
print()

# Find the NOW category
cursor.execute("SELECT id, nom, parent_id FROM categories WHERE nom LIKE '%NOW%'")
now_category = cursor.fetchone()
print("NOW category:", now_category)

if now_category:
    # Find subcategories of NOW
    cursor.execute("SELECT id, nom FROM categories WHERE parent_id=?", (now_category[0],))
    subcategories = cursor.fetchall()
    print("Subcategories of NOW:")
    for subcat in subcategories:
        print(f"  ID: {subcat[0]}, Name: {subcat[1]}")

conn.close()
