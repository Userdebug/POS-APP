from core.database import DatabaseManager

db = DatabaseManager()
with db._connect() as conn:
    print("=== Rebuilding Tsf as period-based table ===")

    # Get all unique dates in Tcollecte
    dates = [
        r[0] for r in conn.execute("SELECT DISTINCT jour FROM Tcollecte ORDER BY jour").fetchall()
    ]
    if not dates:
        print("  No dates found in Tcollecte")
        exit()

    date_debut = dates[0]  # First date = start date for SI
    date_fin = dates[-1]  # Last date = end date for SF
    print(f"  Period: {date_debut} to {date_fin}")

    # Clear old Tsf data
    conn.execute("DELETE FROM Tsf")

    # Get SI for start date (dateDebut)
    si_rows = conn.execute(
        """
        SELECT c.nom, t.si
        FROM Tcollecte t
        JOIN categories c ON t.categorie_id = c.id
        WHERE t.jour = ?
    """,
        (date_debut,),
    ).fetchall()
    dict_si = {str(r[0]): int(r[1] or 0) for r in si_rows}

    # Get SF for end date (dateFin)
    sf_rows = conn.execute(
        """
        SELECT c.nom, t.sf
        FROM Tcollecte t
        JOIN categories c ON t.categorie_id = c.id
        WHERE t.jour = ?
    """,
        (date_fin,),
    ).fetchall()
    dict_sf = {str(r[0]): int(r[1] or 0) for r in sf_rows}

    # Aggregate Achats and CA for the period
    agg_rows = conn.execute(
        """
        SELECT c.nom, 
               SUM(t.achats) as total_achats, 
               SUM(t.ca) as total_ca,
               SUM(t.env) as total_env
        FROM Tcollecte t
        JOIN categories c ON t.categorie_id = c.id
        WHERE t.jour BETWEEN ? AND ?
        GROUP BY c.nom
    """,
        (date_debut, date_fin),
    ).fetchall()

    inserts = []
    for r in agg_rows:
        cat_name = str(r[0])
        total_achats = int(r[1] or 0)
        total_ca = int(r[2] or 0)
        total_env = int(r[3] or 0)

        si_val = dict_si.get(cat_name, 0)
        sf_val = dict_sf.get(cat_name, 0)

        # Vente theorique: si + achats - sf - env
        vente_theo = max(0, si_val + total_achats - sf_val - total_env)
        marge = total_ca - vente_theo
        marge_pct = (marge / vente_theo * 100) if vente_theo > 0 else 0.0

        # Get categorie_id
        cat_row = conn.execute("SELECT id FROM categories WHERE nom = ?", (cat_name,)).fetchone()
        cat_id = cat_row[0] if cat_row else None

        if cat_id:
            # Insert: jour, categorie_id, si_ttc, achats_ttc, ca_ttc, env_ttc, sf_ttc, vente_theo, marge, marge_pct, is_closed
            inserts.append(
                (
                    date_fin,  # jour = period end
                    cat_id,
                    si_val,
                    total_achats,
                    total_ca,
                    total_env,
                    sf_val,
                    vente_theo,
                    marge,
                    marge_pct,
                    0,  # is_closed
                )
            )
            print(
                f"  {cat_name}: si={si_val} ach={total_achats} ca={total_ca} env={total_env} sf={sf_val} vt={vente_theo} marge={marge}"
            )

    # Insert new Tsf data with 11 columns
    conn.executemany(
        """
        INSERT INTO Tsf (
            jour, categorie_id, si_ttc, achats_ttc, ca_ttc, env_ttc, sf_ttc,
            vente_theorique_ttc, marge_ttc, marge_percent, is_closed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        inserts,
    )

    conn.commit()
    print(f"\n=== Tsf rebuilt: {len(inserts)} rows ===")

    # Show final Tsf
    print("\n=== Final Tsf data ===")
    final = conn.execute("""
        SELECT c.nom, t.si_ttc, t.achats_ttc, t.ca_ttc, t.env_ttc, t.sf_ttc, t.vente_theorique_ttc, t.marge_ttc, t.marge_percent
        FROM Tsf t
        JOIN categories c ON t.categorie_id = c.id
        ORDER BY c.nom
    """).fetchall()
    for r in final:
        print(
            f"  {r[0]}: si={r[1]} ach={r[2]} ca={r[3]} env={r[4]} sf={r[5]} vt={r[6]} marge={r[7]}"
        )
