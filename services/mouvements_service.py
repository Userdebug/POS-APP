MOUVEMENT_LABELS = {
    "RB": "Reserve vers Boutique",
    "BR": "Boutique vers Reserve",
    "EB": "Correction Boutique",
    "ER": "Correction Reserve",
    "ENV": "Enlever",
    "ENV_B": "Enlever Boutique",
    "ENV_R": "Enlever Reserve",
    "ENV_DLV": "Enlever DLV",
    "ENV_ABIME": "Enlever Abime",
}


def apply_movement(produit: dict, action: str, qte: int) -> int:
    b = int(produit.get("b", 0))
    r = int(produit.get("r", 0))
    effectif = int(qte)

    if action == "RB":
        transfert = min(r, qte)
        r -= transfert
        b += transfert
        effectif = transfert
    elif action == "BR":
        transfert = min(b, qte)
        b -= transfert
        r += transfert
        effectif = transfert
    elif action == "EB":
        b += qte
    elif action == "ER":
        r += qte
    elif action == "ENV":
        reste = qte
        retrait_b = min(b, reste)
        b -= retrait_b
        reste -= retrait_b
        retrait_r = min(r, reste)
        r -= retrait_r
        effectif = retrait_b + retrait_r
    elif action == "ENV_B":
        effectif = min(b, qte)
        b -= effectif
    elif action == "ENV_R":
        effectif = min(r, qte)
        r -= effectif

    produit["b"] = b
    produit["r"] = r
    return effectif
