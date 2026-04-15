"""Ecran qui assemble les composants de mouvements."""

import os
import sys

# Ajoute le répertoire de l'application au path pour rendre les imports absolus robustes
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from services.mouvements_service import MOUVEMENT_LABELS, apply_movement
from ui.components.mouvements_actions_panel import MouvementsActionsPanel
from ui.components.mouvements_history_panel import MouvementsHistoryPanel
from ui.components.product_info_panel import ProduitInfoPanel
from ui.components.products_table import ProduitsTable
from ui.dialogs.env_confirmation_dialog import EnvConfirmationDialog


class EcranMouvements(QWidget):
    """Assemble les 4 composants de l'ecran mouvements."""

    retour_demande = pyqtSignal()
    produit_modifie = pyqtSignal(dict)  # Re-emit for external listeners

    def __init__(
        self,
        db_manager=None,
        vendeur_nom: str = "",
        operateur_id: int | None = None,
        session_id: int | None = None,
    ) -> None:
        super().__init__()
        self.produit_info_panel = ProduitInfoPanel()
        self.mouvements_history_panel = MouvementsHistoryPanel()
        self.mouvements_actions_panel = MouvementsActionsPanel()
        self.produits_table = ProduitsTable(db_manager)

        self.db_manager = db_manager
        self.vendeur_nom = vendeur_nom
        self.operateur_id = operateur_id
        self.session_id = session_id
        self._produit_actif_id = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        self.btn_retour = QPushButton("Retour")
        self.btn_retour.setMinimumHeight(34)
        title = QLabel("Produits et Mouvements")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #e2e8f0;")
        toolbar.addWidget(self.btn_retour)
        toolbar.addWidget(title)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        # Partie 1: informations produit + historique
        part1 = QHBoxLayout()
        part1.setSpacing(10)
        part1.addWidget(self.produit_info_panel, 2)
        part1.addWidget(self.mouvements_history_panel, 2)
        layout.addLayout(part1, 1)

        # Partie 2: zone des boutons groupes horizontalement
        layout.addWidget(self.mouvements_actions_panel, 0)

        # Partie 3: liste des produits
        layout.addWidget(self.produits_table, 2)
        self.setLayout(layout)

    def _connect_signals(self) -> None:
        self.btn_retour.clicked.connect(self.retour_demande.emit)
        self.produits_table.produit_selectionne.connect(self._on_produit_selectionne)
        self.produit_info_panel.produit_modifie.connect(self._on_produit_modifie)
        self.mouvements_actions_panel.action_declenchee.connect(self._on_action_declenchee)

    def _on_produit_selectionne(self, produit: dict) -> None:
        self._produit_actif_id = produit.get("id")
        self.produit_info_panel.update_info(produit)
        self.mouvements_actions_panel.set_actions_enabled(True)

    def _on_produit_modifie(self, produit: dict) -> None:
        target_id = produit.get("id")
        if target_id is None:
            return
        produits = self.produits_table.get_produits()
        for i, row in enumerate(produits):
            if row.get("id") == target_id:
                produits[i] = dict(produit)
                self.produits_table.set_produits(produits)
                self._produit_actif_id = target_id
                self.produit_info_panel.update_info(produit)
                self._save_product(produit)
                # Defer signal emission to prevent UI freeze during cascading updates
                QTimer.singleShot(0, lambda p=dict(produit): self.produit_modifie.emit(p))
                return

    def _on_action_declenchee(self, data: tuple) -> None:
        action, qte_text = data
        produit = self._get_produit_actif()
        if not produit:
            return

        try:
            qte = int(qte_text) if qte_text else 1
        except ValueError:
            qte = 1

        raison = None
        action_db = action

        if action in ("ENV_DLV", "ENV_ABIME"):
            env_type = "DLV" if action == "ENV_DLV" else "Abime"
            dialog = EnvConfirmationDialog(
                self,
                produit_nom=str(produit.get("nom", "-")),
                quantite=qte,
                stock_b=int(produit.get("b", 0)),
                stock_r=int(produit.get("r", 0)),
                env_type=env_type,
            )
            if dialog.exec() != dialog.DialogCode.Accepted:
                return

            location = dialog.location()
            if location == "B":
                action_db = "ENV_B"
            elif location == "R":
                action_db = "ENV_R"
            else:
                return

            raison = "perime" if action == "ENV_DLV" else "abime"

        avant_b = int(produit.get("b", 0))
        avant_r = int(produit.get("r", 0))
        quantite_effective = apply_movement(produit, action_db, qte)

        # Detect if movement was rejected or partial due to insufficient stock
        if quantite_effective < qte:
            self._afficher_erreur_mouvement(produit, action, qte, quantite_effective)

        apres_b = int(produit.get("b", 0))
        apres_r = int(produit.get("r", 0))
        if quantite_effective == 0:
            # Stock is zero - product was removed
            # Update table and emit signal so main_window updates zone_produits
            self.produits_table.refresh()
            self.produit_info_panel.update_info(produit)
            # Emit modification so main_window can update zone_produits
            self.produit_modifie.emit(dict(produit))
            return

        # Update only the specific product row without full refresh
        self.produits_table.update_produit(produit)
        self.produit_info_panel.update_info(produit)
        self.mouvements_history_panel.add_movement(
            str(produit.get("nom", "-")), MOUVEMENT_LABELS.get(action, action), quantite_effective
        )
        self._persist_mouvement(
            produit=produit,
            action=action_db,
            qte=quantite_effective,
            raison=raison,
            avant_b=avant_b,
            avant_r=avant_r,
            apres_b=apres_b,
            apres_r=apres_r,
        )
        self._save_product(produit)
        # Emit modification so main_window can update zone_produits
        self.produit_modifie.emit(dict(produit))

    def _get_produit_actif(self) -> dict | None:
        for produit in self.produits_table.get_produits():
            if produit.get("id") == self._produit_actif_id:
                return produit
        return None

    def _save_product(self, produit: dict) -> None:
        if self.db_manager is None:
            return
        self.db_manager.upsert_products([produit])

    def _afficher_erreur_mouvement(
        self,
        produit: dict,
        action: str,
        qte_demandee: int,
        qte_effective: int,
    ) -> None:
        """Show error when stock movement is rejected or partial due to insufficient stock."""
        nom = produit.get("nom", "-")
        stock_b = int(produit.get("b", 0))
        stock_r = int(produit.get("r", 0))
        action_label = MOUVEMENT_LABELS.get(action, action)

        if qte_effective == 0:
            message = (
                f"Mouvement impossible pour '{nom}'!\n\n"
                f"Action: {action_label}\n"
                f"Demandée: {qte_demandee}\n"
                f"Stock boutique: {stock_b}\n"
                f"Stock réserve: {stock_r}"
            )
        else:
            message = (
                f"Attention: mouvement partiel pour '{nom}'\n\n"
                f"Action: {action_label}\n"
                f"Demandée: {qte_demandee}\n"
                f"Effectuée: {qte_effective}\n"
                f"Manquant: {qte_demandee - qte_effective}"
            )

        QMessageBox.warning(self, "Mouvement de stock", message)

    def _persist_mouvement(
        self,
        *,
        produit: dict,
        action: str,
        qte: int,
        raison: str | None,
        avant_b: int,
        avant_r: int,
        apres_b: int,
        apres_r: int,
    ) -> None:
        if self.db_manager is None or self.operateur_id is None or self.session_id is None:
            return

        pa_unitaire = int(produit.get("pa", produit.get("prc", 0)))
        self.db_manager.log_movement(
            produit_id=int(produit.get("id")),
            type_mouvement=action,
            quantite=int(qte),
            raison=raison,
            pa_unitaire=pa_unitaire,
            stock_b_avant=avant_b,
            stock_b_apres=apres_b,
            stock_r_avant=avant_r,
            stock_r_apres=apres_r,
            operateur_id=int(self.operateur_id),
            session_id=int(self.session_id),
            vendeur_nom=self.vendeur_nom,
        )

        if action == "ENV":
            self.db_manager.log_removed_product(
                nom=str(produit.get("nom", "")),
                categorie=str(produit.get("categorie", "Sans categorie")),
                quantite=int(qte),
                pa_unitaire=pa_unitaire,
                raison=str(raison or ""),
                operateur_id=int(self.operateur_id),
                session_id=int(self.session_id),
                vendeur_nom=self.vendeur_nom,
            )
