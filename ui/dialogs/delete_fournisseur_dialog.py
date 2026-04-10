from PyQt6.QtWidgets import QMessageBox, QWidget

from styles.design_tokens import TOKENS


class DeleteFournisseurDialog:
    """Helper class to show confirmation dialog for supplier deactivation."""

    @staticmethod
    def confirm_delete(parent: QWidget | None, fournisseur_nom: str) -> bool:
        """Show a confirmation dialog for deactivating a supplier.

        Args:
            parent: Parent widget for the dialog
            fournisseur_nom: Name of the supplier to deactivate

        Returns:
            True if user confirms deactivation, False otherwise
        """
        msg_box = QMessageBox(parent)
        msg_box.setWindowTitle("Confirmer la désactivation")
        msg_box.setText(
            f"Êtes-vous sûr de vouloir désactiver le fournisseur « {fournisseur_nom} » ?\n\n"
            "Le fournisseur ne sera plus visible dans la liste mais les données seront conservées."
        )
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        msg_box.setStyleSheet(
            f"QDialog {{ background-color: {TOKENS['bg_sidebar']}; }}"
            f"QLabel {{ color: {TOKENS['text_default']}; font-size: 13px; }}"
            f"QPushButton {{"
            f"  background-color: {TOKENS['bg_button']};"
            f"  color: {TOKENS['text_primary']};"
            f"  border: 1px solid {TOKENS['border_button']};"
            f"  border-radius: 6px;"
            f"  padding: 8px 16px;"
            f"  font-weight: 600;"
            f"  min-width: 80px;"
            f"}}"
            f"QPushButton:hover {{ background-color: {TOKENS['bg_button_hover']}; }}"
        )
        reply = msg_box.exec()
        return reply == QMessageBox.StandardButton.Yes
