"""Audit Tcollecte data quality before migration."""

import sys
from pathlib import Path

# Ensure project root is on sys.path (needed for direct script execution)
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.database import DatabaseManager


def main():
    base = Path(__file__).resolve().parent
    db = DatabaseManager()

    print("=" * 60)
    print("TCOLLECTE DATA AUDIT")
    print("=" * 60)

    with db._connect() as conn:
        # Total rows
        total = conn.execute("SELECT COUNT(*) as cnt FROM Tcollecte").fetchone()["cnt"]
        print(f"Total Tcollecte rows: {total}")

        # Distinct days
        days = [
            r["jour"]
            for r in conn.execute(
                "SELECT DISTINCT jour FROM Tcollecte ORDER BY jour DESC"
            ).fetchall()
        ]
        print(f"Distinct days: {len(days)}")
        print(f"  Earliest: {days[-1] if days else 'N/A'}")
        print(f"  Latest:   {days[0] if days else 'N/A'}")

        # Days with zero values across board
        empty = conn.execute("""
            SELECT COUNT(*) as cnt FROM Tcollecte
            WHERE si = 0 AND achats = 0 AND ca = 0 AND sf = 0 AND env = 0
        """).fetchone()["cnt"]
        print(f"Empty rows (all zeros): {empty}")

        # Days marked closed with ca=0
        closed_no_ca = conn.execute("""
            SELECT COUNT(*) as cnt FROM Tcollecte
            WHERE cloturee = 1 AND ca = 0
        """).fetchone()["cnt"]
        print(f"Closed days with CA=0: {closed_no_ca}")

        # Rows with ca_temporaire > 0 but ca = 0 (open days with sales)
        temp_ca = conn.execute("""
            SELECT COUNT(*) as cnt FROM Tcollecte
            WHERE ca = 0 AND ca_temporaire > 0
        """).fetchone()["cnt"]
        print(f"Open days with live CA (ca_temporaire>0, ca=0): {temp_ca}")

        # Duplicate (jour, categorie_id) pairs?
        dupes = conn.execute("""
            SELECT jour, categorie_id, COUNT(*) as cnt FROM Tcollecte
            GROUP BY jour, categorie_id HAVING cnt > 1
        """).fetchall()
        print(f"Duplicate rows: {len(dupes)}")
        if dupes:
            for d in dupes[:5]:
                print(f"  {d['jour']} cat_id={d['categorie_id']} count={d['cnt']}")

        # Missing category rows: for each day, count expected OW categories
        ow_cats = [
            r["nom"]
            for r in conn.execute("""
            SELECT c.nom FROM categories c
            JOIN categories parent ON c.parent_id = parent.id
            WHERE parent.nom = 'Catégorie 1 - OW (Owners)'
        """).fetchall()
        ]
        print(f"OW categories expected: {len(ow_cats)}")

        # Sample row for most recent day
        if days:
            latest = days[0]
            print(f"\nSample for latest day '{latest}':")
            sample = conn.execute(
                """
                SELECT c.nom, t.si, t.achats, t.ca, t.ca_temporaire, t.sf, t.env, t.vente_theorique, t.marge, t.cloturee
                FROM Tcollecte t
                JOIN categories c ON t.categorie_id = c.id
                WHERE t.jour = ?
                ORDER BY c.nom
            """,
                (latest,),
            ).fetchall()
            print(f"  Categories: {len(sample)}")
            for s in sample[:3]:
                print(
                    f"    {s['nom']}: si={s['si']}, achats={s['achats']}, ca={s['ca']}, sf={s['sf']}, env={s['env']}, vt={s['vente_theorique']}, marge={s['marge']}, closed={s['cloturee']}"
                )
            if len(sample) > 3:
                print(f"    ... and {len(sample) - 3} more")


if __name__ == "__main__":
    main()
