PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS operateurs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    droit_acces TEXT NOT NULL,
    actif INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions_operateur (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operateur_id INTEGER NOT NULL,
    vendeur_nom TEXT NOT NULL,
    opened_at TEXT NOT NULL DEFAULT (datetime('now')),
    closed_at TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (operateur_id) REFERENCES operateurs(id)
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    parent_id INTEGER,
    FOREIGN KEY (parent_id) REFERENCES categories(id)
);

-- Catégories principales (hiérarchie)
INSERT INTO categories (nom) VALUES ('Catégorie 1 - OW (Owners)') ON CONFLICT(nom) DO NOTHING;
INSERT INTO categories (nom) VALUES ('Catégorie 2 - NOW (Not owners)') ON CONFLICT(nom) DO NOTHING;
INSERT INTO categories (nom) VALUES ('Catégorie 3 - NONE') ON CONFLICT(nom) DO NOTHING;

-- Sous-catégories Catégorie 1 - OW (Owners): BA, BSA, PF, GL, Confi, EPI, Tabac, HS, Baz, TelC
INSERT INTO categories (nom, parent_id) VALUES ('BA', (SELECT id FROM categories WHERE nom = 'Catégorie 1 - OW (Owners)')) ON CONFLICT(nom) DO NOTHING;
INSERT INTO categories (nom, parent_id) VALUES ('BSA', (SELECT id FROM categories WHERE nom = 'Catégorie 1 - OW (Owners)')) ON CONFLICT(nom) DO NOTHING;
INSERT INTO categories (nom, parent_id) VALUES ('PF', (SELECT id FROM categories WHERE nom = 'Catégorie 1 - OW (Owners)')) ON CONFLICT(nom) DO NOTHING;
INSERT INTO categories (nom, parent_id) VALUES ('GL', (SELECT id FROM categories WHERE nom = 'Catégorie 1 - OW (Owners)')) ON CONFLICT(nom) DO NOTHING;
INSERT INTO categories (nom, parent_id) VALUES ('Confi', (SELECT id FROM categories WHERE nom = 'Catégorie 1 - OW (Owners)')) ON CONFLICT(nom) DO NOTHING;
INSERT INTO categories (nom, parent_id) VALUES ('EPI', (SELECT id FROM categories WHERE nom = 'Catégorie 1 - OW (Owners)')) ON CONFLICT(nom) DO NOTHING;
INSERT INTO categories (nom, parent_id) VALUES ('Tabac', (SELECT id FROM categories WHERE nom = 'Catégorie 1 - OW (Owners)')) ON CONFLICT(nom) DO NOTHING;
INSERT INTO categories (nom, parent_id) VALUES ('HS', (SELECT id FROM categories WHERE nom = 'Catégorie 1 - OW (Owners)')) ON CONFLICT(nom) DO NOTHING;
INSERT INTO categories (nom, parent_id) VALUES ('Baz', (SELECT id FROM categories WHERE nom = 'Catégorie 1 - OW (Owners)')) ON CONFLICT(nom) DO NOTHING;
INSERT INTO categories (nom, parent_id) VALUES ('TelC', (SELECT id FROM categories WHERE nom = 'Catégorie 1 - OW (Owners)')) ON CONFLICT(nom) DO NOTHING;

-- Sous-catégories Catégorie 2 - NOW (Not owners): Lub, Pea, Solaires
INSERT INTO categories (nom, parent_id) VALUES ('Lub', (SELECT id FROM categories WHERE nom = 'Catégorie 2 - NOW (Not owners)')) ON CONFLICT(nom) DO NOTHING;
INSERT INTO categories (nom, parent_id) VALUES ('Pea', (SELECT id FROM categories WHERE nom = 'Catégorie 2 - NOW (Not owners)')) ON CONFLICT(nom) DO NOTHING;
INSERT INTO categories (nom, parent_id) VALUES ('Solaires', (SELECT id FROM categories WHERE nom = 'Catégorie 2 - NOW (Not owners)')) ON CONFLICT(nom) DO NOTHING;

-- Sous-catégories Catégorie 3 - NONE: Zoth, Gaz
INSERT INTO categories (nom, parent_id) VALUES ('Zoth', (SELECT id FROM categories WHERE nom = 'Catégorie 3 - NONE')) ON CONFLICT(nom) DO NOTHING;
INSERT INTO categories (nom, parent_id) VALUES ('Gaz', (SELECT id FROM categories WHERE nom = 'Catégorie 3 - NONE')) ON CONFLICT(nom) DO NOTHING;

CREATE TABLE IF NOT EXISTS fournisseurs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    code TEXT UNIQUE,
    nif TEXT,
    stat TEXT,
    contact TEXT,
    telephone TEXT,
    adresse TEXT,
    note TEXT,
    actif INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS parametres (
    cle TEXT PRIMARY KEY,
    valeur TEXT NOT NULL,
    description TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS produits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    categorie_id INTEGER,
    pv INTEGER NOT NULL DEFAULT 0,
    pa INTEGER NOT NULL DEFAULT 0,
    stock_boutique INTEGER NOT NULL DEFAULT 0,
    stock_reserve INTEGER NOT NULL DEFAULT 0,
    dlv_dlc TEXT,
    description TEXT,
    sku TEXT,
    en_promo INTEGER NOT NULL DEFAULT 0,
    prix_promo INTEGER DEFAULT 0,
    derniere_verification TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (categorie_id) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS depenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_depense TEXT NOT NULL DEFAULT (datetime('now')),
    designation TEXT NOT NULL,
    valeur INTEGER NOT NULL CHECK (valeur >= 0),
    remarque TEXT
);

CREATE TABLE IF NOT EXISTS ventes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jour TEXT NOT NULL,
    heure TEXT NOT NULL,
    produit_id INTEGER NOT NULL,
    produit_nom TEXT NOT NULL,
    quantite INTEGER NOT NULL CHECK (quantite > 0),
    prix_unitaire INTEGER NOT NULL CHECK (prix_unitaire >= 0),
    prix_total INTEGER NOT NULL CHECK (prix_total >= 0),
    session_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted INTEGER NOT NULL DEFAULT 0,
    deleted_by INTEGER NULL,
    deleted_at TEXT NULL,
    deleted_reason TEXT NULL,
    FOREIGN KEY (produit_id) REFERENCES produits(id),
    FOREIGN KEY (session_id) REFERENCES sessions_operateur(id),
    FOREIGN KEY (deleted_by) REFERENCES operateurs(id)
);

CREATE TABLE IF NOT EXISTS mouvements_stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jour TEXT NOT NULL DEFAULT (datetime('now')),
    produit_id INTEGER NOT NULL,
    type_mouvement TEXT NOT NULL CHECK (type_mouvement IN ('RB', 'BR', 'EB', 'ER', 'ENV')),
    quantite INTEGER NOT NULL CHECK (quantite > 0),
    raison TEXT CHECK (raison IN ('abime', 'perime') OR raison IS NULL),
    valeur INTEGER NOT NULL DEFAULT 0,
    stock_boutique_avant INTEGER NOT NULL,
    stock_boutique_apres INTEGER NOT NULL,
    stock_reserve_avant INTEGER NOT NULL,
    stock_reserve_apres INTEGER NOT NULL,
    operateur_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    vendeur_nom TEXT NOT NULL,
    FOREIGN KEY (produit_id) REFERENCES produits(id),
    FOREIGN KEY (operateur_id) REFERENCES operateurs(id),
    FOREIGN KEY (session_id) REFERENCES sessions_operateur(id)
);

CREATE TABLE IF NOT EXISTS historique_produits_enleves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jour TEXT NOT NULL DEFAULT (datetime('now')),
    nom TEXT NOT NULL,
    categorie TEXT NOT NULL,
    quantite INTEGER NOT NULL CHECK (quantite > 0),
    valeur INTEGER NOT NULL,
    raison TEXT NOT NULL CHECK (raison IN ('abime', 'perime')),
    operateur_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    vendeur_nom TEXT NOT NULL,
    FOREIGN KEY (operateur_id) REFERENCES operateurs(id),
    FOREIGN KEY (session_id) REFERENCES sessions_operateur(id)
);

CREATE TABLE IF NOT EXISTS clotures_caisse (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jour TEXT NOT NULL UNIQUE,
    ca_ttc_final INTEGER NOT NULL CHECK (ca_ttc_final >= 0),
    note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS clotures_caisse_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jour TEXT NOT NULL,
    categorie TEXT NOT NULL,
    ca_ttc_final INTEGER NOT NULL CHECK (ca_ttc_final >= 0),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(jour, categorie)
);

CREATE TABLE IF NOT EXISTS analyse_journaliere_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jour TEXT NOT NULL,
    categorie_id INTEGER NOT NULL,
    si INTEGER NOT NULL DEFAULT 0,
    achats INTEGER NOT NULL DEFAULT 0,
    ca INTEGER NOT NULL DEFAULT 0,
    sf INTEGER NOT NULL DEFAULT 0,
    env INTEGER NOT NULL DEFAULT 0,
    vente_theorique INTEGER NOT NULL DEFAULT 0,
    marge INTEGER NOT NULL DEFAULT 0,
    cloturee INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(jour, categorie_id),
    FOREIGN KEY (categorie_id) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS achats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jour TEXT NOT NULL DEFAULT (date('now')),
    fournisseur_id INTEGER NOT NULL,
    numero_facture TEXT,
    total_ttc INTEGER NOT NULL DEFAULT 0,
    cloturee INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id)
);

CREATE TABLE IF NOT EXISTS achats_lignes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    achat_id INTEGER NOT NULL,
    produit_id INTEGER NOT NULL,
    quantite INTEGER NOT NULL CHECK (quantite >= 0),
    pa_unitaire INTEGER NOT NULL CHECK (pa_unitaire >= 0),
    prc_unitaire INTEGER NOT NULL CHECK (prc_unitaire >= 0),
    pv_unitaire INTEGER NOT NULL CHECK (pv_unitaire >= 0),
    total_ttc INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (achat_id) REFERENCES achats(id),
    FOREIGN KEY (produit_id) REFERENCES produits(id)
);

CREATE TABLE IF NOT EXISTS audit_admin_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    jour TEXT,
    categorie_id INTEGER,
    old_value TEXT,
    new_value TEXT,
    actor TEXT NOT NULL DEFAULT 'admin',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (categorie_id) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS suivi_journalier_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jour TEXT NOT NULL,
    categorie TEXT NOT NULL,
    si INTEGER NOT NULL DEFAULT 0,
    achats INTEGER NOT NULL DEFAULT 0,
    vente_ca INTEGER NOT NULL DEFAULT 0,
    sf INTEGER NOT NULL DEFAULT 0,
    vente_theorique INTEGER NOT NULL DEFAULT 0,
    marge INTEGER NOT NULL DEFAULT 0,
    marge_percent REAL,
    cloturee INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(jour, categorie)
);

CREATE TABLE IF NOT EXISTS suivi_formulaire_journalier (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jour TEXT NOT NULL,
    categorie TEXT NOT NULL,
    achats_ttc INTEGER NOT NULL DEFAULT 0,
    ca_final INTEGER NOT NULL DEFAULT 0,
    cloturee INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(jour, categorie)
);

CREATE INDEX IF NOT EXISTS idx_mouvements_stock_jour ON mouvements_stock(jour);
CREATE INDEX IF NOT EXISTS idx_mouvements_stock_produit ON mouvements_stock(produit_id);
CREATE INDEX IF NOT EXISTS idx_mouvements_stock_jour_produit ON mouvements_stock(jour, produit_id);
CREATE INDEX IF NOT EXISTS idx_historique_enleves_jour ON historique_produits_enleves(jour);
CREATE INDEX IF NOT EXISTS idx_depenses_date ON depenses(date_depense);
CREATE INDEX IF NOT EXISTS idx_ventes_jour ON ventes(jour);
CREATE INDEX IF NOT EXISTS idx_ventes_session ON ventes(session_id);
CREATE INDEX IF NOT EXISTS idx_clotures_caisse_jour ON clotures_caisse(jour);
CREATE INDEX IF NOT EXISTS idx_clotures_caisse_categories_jour ON clotures_caisse_categories(jour);
CREATE INDEX IF NOT EXISTS idx_fournisseurs_nom ON fournisseurs(nom);
CREATE INDEX IF NOT EXISTS idx_suivi_journalier_categories_jour ON suivi_journalier_categories(jour);
CREATE INDEX IF NOT EXISTS idx_suivi_formulaire_journalier_jour ON suivi_formulaire_journalier(jour);
CREATE INDEX IF NOT EXISTS idx_analyse_journaliere_categories_jour ON analyse_journaliere_categories(jour);
CREATE INDEX IF NOT EXISTS idx_analyse_journaliere_categories_cat ON analyse_journaliere_categories(categorie_id);
CREATE INDEX IF NOT EXISTS idx_achats_jour ON achats(jour);
CREATE INDEX IF NOT EXISTS idx_achats_jour_fournisseur_facture ON achats(jour, fournisseur_id, numero_facture);
CREATE INDEX IF NOT EXISTS idx_achats_lignes_achat ON achats_lignes(achat_id);
CREATE INDEX IF NOT EXISTS idx_audit_admin_actions_jour ON audit_admin_actions(jour);
CREATE INDEX IF NOT EXISTS idx_ventes_jour_heure ON ventes(jour, heure);
CREATE INDEX IF NOT EXISTS idx_depenses_date_id ON depenses(date_depense, id);
CREATE INDEX IF NOT EXISTS idx_produits_categorie ON produits(categorie_id);

INSERT INTO parametres (cle, valeur, description)
VALUES ('TVA_TAUX', '20.00', 'Taux de TVA en pourcentage')
ON CONFLICT(cle) DO NOTHING;
