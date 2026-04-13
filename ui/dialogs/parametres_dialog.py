"""Settings dialog with category-based panels."""

from __future__ import annotations

import hashlib
from datetime import datetime

from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from styles.dialog_styles import (
    DIALOG_BASE,
    ERROR_LABEL,
    INPUT_FIELD,
    INPUT_MIN_HEIGHT,
    PRIMARY_BUTTON,
    SECONDARY_BUTTON,
    SEPARATOR,
)


class BilletageEditor(QWidget):
    """Widget for editing bill denominations."""

    def __init__(
        self,
        denominations: list[int],
        financial_service,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._denominations = list(denominations)
        self._financial = financial_service
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel("Coupures de billets")
        header.setStyleSheet("font-weight: 700;")
        layout.addWidget(header)

        # Denominations grid layout - 2 per row
        self._denom_grid = QGridLayout()
        self._denom_grid.setSpacing(8)
        self._denom_inputs: list[tuple[QLineEdit, QPushButton]] = []

        for i, denom in enumerate(self._denominations):
            row = i // 2
            col = i % 2
            row_layout = self._create_denom_row(denom)
            self._denom_grid.addLayout(row_layout, row, col)

        # Add button
        btn_add = QPushButton("+ Ajouter une coupure")
        btn_add.setStyleSheet(SECONDARY_BUTTON)
        btn_add.clicked.connect(self._add_denomination)
        layout.addWidget(btn_add)

        layout.addLayout(self._denom_grid)

        # Total display
        self._total_label = QLabel()
        self._total_label.setStyleSheet("font-weight: 700; color: #2c3e50;")
        layout.addWidget(self._total_label)
        self._update_total()

    def _create_denom_row(self, denom: int) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(4)

        input_val = QLineEdit()
        input_val.setText(str(denom))
        input_val.setPlaceholderText("Valeur")
        input_val.setMinimumHeight(INPUT_MIN_HEIGHT)
        input_val.setFixedWidth(80)
        input_val.textChanged.connect(self._on_value_changed)
        row.addWidget(input_val)

        btn_remove = QPushButton("×")
        btn_remove.setFixedSize(24, 28)
        btn_remove.clicked.connect(lambda: self._remove_row(input_val))
        row.addWidget(btn_remove)

        row.addStretch()

        self._denom_inputs.append((input_val, btn_remove))
        return row

    def _add_denomination(self) -> None:
        # Find next empty slot in grid
        current_count = len(self._denom_inputs)
        row = current_count // 2
        col = current_count % 2

        row_layout = self._create_denom_row(0)
        self._denom_grid.addLayout(row_layout, row, col)

    def _remove_row(self, input_widget: QLineEdit) -> None:
        for i, (inp, btn) in enumerate(self._denom_inputs):
            if inp == input_widget:
                inp.deleteLater()
                btn.deleteLater()
                self._denom_inputs.pop(i)
                break
        self._update_total()

    def _on_value_changed(self) -> None:
        self._update_total()

    def _update_total(self) -> None:
        total = sum(int(inp.text() or "0") for inp, _ in self._denom_inputs)
        self._total_label.setText(f"Total: {total:,} Ar")

    def get_denominations(self) -> list[int]:
        """Return the list of denominations."""
        denoms = []
        for inp, _ in self._denom_inputs:
            try:
                val = int(inp.text())
                if val > 0:
                    denoms.append(val)
            except ValueError:
                pass
        return sorted(denoms, reverse=True)

    def validate(self) -> bool:
        """Validate denominations."""
        denoms = self.get_denominations()
        return self._financial.validate_denominations(denoms)


class ParametresDialog(QDialog):
    """Settings dialog with category-based navigation."""

    def __init__(
        self,
        parent: QWidget | None,
        db_manager,
        settings_service=None,
        financial_service=None,
    ):
        super().__init__(parent)
        self.db_manager = db_manager
        self.settings_service = settings_service or db_manager.settings
        self.financial_service = financial_service or db_manager.financial
        self.setWindowTitle("Paramètres")
        self.resize(480, 420)

        self.setStyleSheet(DIALOG_BASE + INPUT_FIELD)

        self._init_ui()
        self._load_settings()

    def _init_ui(self) -> None:
        # Root layout (horizontal)
        root = QHBoxLayout()
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        # Left sidebar - category list
        self._category_list = QListWidget()
        self._category_list.setFixedWidth(120)
        self._category_list.currentRowChanged.connect(self._on_category_changed)

        categories = [
            ("Général", "general"),
            ("Financial", "financial"),
            ("Affichage", "display"),
            ("Catégories", "categories"),
            ("Base de données", "database"),
            ("Utilisateurs", "users"),
        ]

        for label, key in categories:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self._category_list.addItem(item)

        root.addWidget(self._category_list)

        # Right panel - stacked pages
        self._stacked = QStackedWidget()

        # General page
        self._general_page = self._create_general_page()
        self._stacked.addWidget(self._general_page)

        # Financial page
        self._financial_page = self._create_financial_page()
        self._stacked.addWidget(self._financial_page)

        # Display page
        self._display_page = self._create_display_page()
        self._stacked.addWidget(self._display_page)

        # Categories page
        self._categories_page = self._create_categories_page()
        self._stacked.addWidget(self._categories_page)

        # Database page
        self._database_page = self._create_database_page()
        self._stacked.addWidget(self._database_page)

        # Users page
        self._users_page = self._create_users_page()
        self._stacked.addWidget(self._users_page)

        root.addWidget(self._stacked)

        # Bottom buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        save_btn = buttons.button(QDialogButtonBox.StandardButton.Save)
        if save_btn is not None:
            save_btn.setText("Enregistrer")
            save_btn.setStyleSheet(PRIMARY_BUTTON)
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn is not None:
            cancel_btn.setText("Annuler")
            cancel_btn.setStyleSheet(SECONDARY_BUTTON)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)

        # Add buttons at bottom
        bottom = QVBoxLayout()
        bottom.addLayout(root)
        bottom.addWidget(buttons)
        self.setLayout(bottom)

    def _create_general_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Error label
        self._error_label = QLabel()
        self._error_label.setStyleSheet(ERROR_LABEL)
        self._error_label.setVisible(False)
        self._error_label.setWordWrap(True)
        layout.addWidget(self._error_label)

        # Auto-save settings
        autosave_label = QLabel("Sauvegarde automatique")
        autosave_label.setStyleSheet("font-weight: 700;")
        layout.addWidget(autosave_label)

        form = QFormLayout()
        form.setSpacing(12)

        self._check_autosave = QCheckBox()
        self._check_autosave.setText("Activer la sauvegarde automatique après clôture")
        form.addRow("", self._check_autosave)

        self._input_backup_dir = QLineEdit()
        self._input_backup_dir.setPlaceholderText("backups/")
        self._input_backup_dir.setMinimumHeight(INPUT_MIN_HEIGHT)
        form.addRow("Dossier:", self._input_backup_dir)

        self._input_retention = QSpinBox()
        self._input_retention.setMinimum(1)
        self._input_retention.setMaximum(100)
        self._input_retention.setValue(10)
        self._input_retention.setSuffix(" fichiers")
        form.addRow("Conservation:", self._input_retention)

        layout.addLayout(form)
        layout.addStretch()

        return widget

    def _create_financial_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # TVA settings
        tva_label = QLabel("Taxe sur la valeur ajoutée (TVA)")
        tva_label.setStyleSheet("font-weight: 700;")
        layout.addWidget(tva_label)

        form = QFormLayout()
        form.setSpacing(12)

        self._input_tva = QLineEdit()
        self._input_tva.setPlaceholderText("20.00")
        self._input_tva.setMinimumHeight(INPUT_MIN_HEIGHT)
        form.addRow("Taux TVA (%)", self._input_tva)

        layout.addLayout(form)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(SEPARATOR)
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        # Display mode (read-only from new system)
        display_label = QLabel("Coffre")
        display_label.setStyleSheet("font-weight: 700;")
        layout.addWidget(display_label)

        coff_form = QFormLayout()
        self._coffre_label = QLabel("0")
        self._coffre_label.setStyleSheet("font-weight: 700; color: #27ae60;")
        coff_form.addRow("Montant actuel:", self._coffre_label)
        layout.addLayout(coff_form)

        layout.addStretch()

        return widget

    def _create_display_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Currency settings
        currency_label = QLabel("Devise")
        currency_label.setStyleSheet("font-weight: 700;")
        layout.addWidget(currency_label)

        form = QFormLayout()
        form.setSpacing(12)

        self._input_currency = QLineEdit()
        self._input_currency.setPlaceholderText("Ar")
        self._input_currency.setMinimumHeight(INPUT_MIN_HEIGHT)
        form.addRow("Symbole:", self._input_currency)

        self._input_precision = QSpinBox()
        self._input_precision.setMinimum(0)
        self._input_precision.setMaximum(3)
        self._input_precision.setValue(0)
        form.addRow("Décimales:", self._input_precision)

        layout.addLayout(form)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(SEPARATOR)
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        # Billetage editor
        denoms = self.financial_service.get_billetage_denominations()
        self._billetage_editor = BilletageEditor(list(denoms), self.financial_service)
        layout.addWidget(self._billetage_editor)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(SEPARATOR)
        sep2.setFixedHeight(1)
        layout.addWidget(sep2)

        # Admin PIN
        pin_label = QLabel("Sécurité")
        pin_label.setStyleSheet("font-weight: 700;")
        layout.addWidget(pin_label)

        pin_form = QFormLayout()
        self._input_pin = QLineEdit()
        self._input_pin.setEchoMode(QLineEdit.EchoMode.Password)
        self._input_pin.setPlaceholderText("Nouveau code admin (laisser vide pour conserver)")
        self._input_pin.setMinimumHeight(INPUT_MIN_HEIGHT)
        pin_form.addRow("Code admin:", self._input_pin)
        layout.addLayout(pin_form)

        # Separator
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.HLine)
        sep3.setStyleSheet(SEPARATOR)
        sep3.setFixedHeight(1)
        layout.addWidget(sep3)

        layout.addStretch()

        return widget

    def _create_categories_page(self) -> QWidget:
        """Create the categories management page."""

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Info text
        info = QLabel(
            "Gestion des catégories de produits. "
            "Cliquez sur 'Ouvrir' pour modifier les catégories."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # Open categories button
        btn_open = QPushButton("Ouvrir la gestion des catégories")
        btn_open.setStyleSheet(PRIMARY_BUTTON)
        btn_open.clicked.connect(self._open_categories_dialog)
        layout.addWidget(btn_open)

        layout.addStretch()

        return widget

    def _open_categories_dialog(self) -> None:
        """Open the categories management dialog."""
        from ui.dialogs.categories_dialog import CategoriesDialog

        dialog = CategoriesDialog(self, category_service=self.db_manager.categories)
        dialog.exec()

    def _create_database_page(self) -> QWidget:
        """Create the database management page."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Info text
        info = QLabel("Gestion de la base de données. " "Cliquez sur une action pour continuer.")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(SEPARATOR)
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        # Buttons section
        buttons_label = QLabel("Opérations")
        buttons_label.setStyleSheet("font-weight: 700;")
        layout.addWidget(buttons_label)

        # Database operations buttons
        db_buttons = QVBoxLayout()
        db_buttons.setSpacing(12)

        # Import button
        btn_import = QPushButton("Importer la base de données...")
        btn_import.setStyleSheet(SECONDARY_BUTTON)
        btn_import.clicked.connect(self._import_database)
        db_buttons.addWidget(btn_import)

        # Export button
        btn_export = QPushButton("Exporter la base de données...")
        btn_export.setStyleSheet(SECONDARY_BUTTON)
        btn_export.clicked.connect(self._export_database)
        db_buttons.addWidget(btn_export)

        # Restore button
        btn_restore = QPushButton("Restaurer une sauvegarde...")
        btn_restore.setStyleSheet(SECONDARY_BUTTON)
        btn_restore.clicked.connect(self._restore_database)
        db_buttons.addWidget(btn_restore)

        layout.addLayout(db_buttons)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(SEPARATOR)
        sep2.setFixedHeight(1)
        layout.addWidget(sep2)

        # Warning label
        warning = QLabel(
            "⚠️ Attention: L'import et la restauration écrasent " "les données actuelles."
        )
        warning.setStyleSheet("color: #e74c3c; font-weight: 600;")
        warning.setWordWrap(True)
        layout.addWidget(warning)

        layout.addStretch()

        return widget

    def _create_users_page(self) -> QWidget:
        """Create the users management page."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Info text
        info = QLabel("Gestion des utilisateurs du système.")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(SEPARATOR)
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        # Users list
        self._users_list = QListWidget()
        layout.addWidget(self._users_list)

        # Buttons
        buttons_layout = QHBoxLayout()
        btn_add = QPushButton("Ajouter utilisateur")
        btn_add.setStyleSheet(SECONDARY_BUTTON)
        btn_add.clicked.connect(self._add_user)
        buttons_layout.addWidget(btn_add)

        btn_edit = QPushButton("Modifier utilisateur")
        btn_edit.setStyleSheet(SECONDARY_BUTTON)
        btn_edit.clicked.connect(self._edit_user)
        buttons_layout.addWidget(btn_edit)

        btn_delete = QPushButton("Supprimer utilisateur")
        btn_delete.setStyleSheet(SECONDARY_BUTTON)
        btn_delete.clicked.connect(self._delete_user)
        buttons_layout.addWidget(btn_delete)

        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        layout.addStretch()

        return widget

    def _import_database(self) -> None:
        """Handle database import action."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Importer une base de données",
            "",
            "Fichiers SQLite (*.db *.sqlite *.sqlite3);;Tous les fichiers (*)",
        )

        if not file_path:
            return

        # Confirm destructive action
        confirm = QMessageBox.question(
            self,
            "Confirmer l'import",
            "Cette action va remplacer la base de données actuelle. " "Voulez-vous continuer?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        # Show progress dialog
        progress = QProgressDialog("Import en cours...", "Annuler", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(10)
        QCoreApplication.processEvents()

        try:
            result = self.db_manager.import_database(file_path)
            progress.setValue(100)

            QMessageBox.information(
                self,
                "Succès",
                f"Base de données importée avec succès.\n" f"Fichier: {result.get('path', '')}",
            )

        except FileNotFoundError as e:
            progress.setValue(0)
            QMessageBox.warning(
                self,
                "Erreur",
                f"Fichier non trouvé: {e}",
            )
        except (OSError, ValueError) as e:
            progress.setValue(0)
            QMessageBox.critical(
                self,
                "Erreur",
                f"Import échoué: {e}",
            )
        except Exception as e:
            progress.setValue(0)
            QMessageBox.critical(
                self,
                "Erreur",
                f"Erreur inattendue: {e}",
            )

    def _export_database(self) -> None:
        """Handle database export action."""
        default_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter la base de données",
            default_name,
            "Fichiers SQLite (*.db *.sqlite *.sqlite3);;Tous les fichiers (*)",
        )

        if not file_path:
            return

        # Show progress dialog
        progress = QProgressDialog("Export en cours...", "Annuler", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(10)
        QCoreApplication.processEvents()

        try:
            result = self.db_manager.export_database(file_path)
            progress.setValue(100)

            QMessageBox.information(
                self,
                "Succès",
                f"Base de données exportée avec succès.\n" f"Fichier: {result.get('path', '')}",
            )

        except OSError as e:
            progress.setValue(0)
            QMessageBox.critical(
                self,
                "Erreur",
                f"Export échoué: {e}",
            )
        except Exception as e:
            progress.setValue(0)
            QMessageBox.critical(
                self,
                "Erreur",
                f"Erreur inattendue: {e}",
            )

    def _restore_database(self) -> None:
        """Handle database restore action."""
        # First try to find existing backups
        backups = self.db_manager.list_database_backups()

        if backups:
            # Offer choice: select existing or choose file
            reply = QMessageBox.question(
                self,
                "Restaurer une sauvegarde",
                "Voulez-vous sélectionner une sauvegarde existante " "ou choisir un fichier?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self._restore_from_existing(backups)
                return

        # Choose file directly
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner une sauvegarde",
            "",
            "Fichiers SQLite (*.db *.sqlite *.sqlite3);;Tous les fichiers (*)",
        )

        if not file_path:
            return

        self._perform_restore(file_path)

    def _restore_from_existing(self, backups: list) -> None:
        """Restore from existing backup selection."""
        if not backups:
            QMessageBox.information(
                self,
                "Aucune sauvegarde",
                "Aucune sauvegarde trouvée.",
            )
            return

        # Show simple selection via message
        backup_options = [b["filename"] for b in backups]
        backup_options.append("Annuler")

        # For simplicity, use first backup - could be enhanced with custom dialog
        file_path = backups[0].get("path", "")

        if file_path:
            self._perform_restore(file_path)

    def _perform_restore(self, file_path: str) -> None:
        """Perform the actual restore operation."""
        # Confirm destructive action
        confirm = QMessageBox.question(
            self,
            "Confirmer la restauration",
            "Cette action va remplacer la base de données actuelle "
            "par la sauvegarde. Voulez-vous continuer?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        # Show progress dialog
        progress = QProgressDialog("Restauration en cours...", "Annuler", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(10)
        QCoreApplication.processEvents()

        try:
            result = self.db_manager.restore_database(file_path)
            progress.setValue(100)

            QMessageBox.information(
                self,
                "Succès",
                f"Base de données restaurée avec succès.\n" f"Sauvegarde: {result.get('path', '')}",
            )

        except FileNotFoundError as e:
            progress.setValue(0)
            QMessageBox.warning(
                self,
                "Erreur",
                f"Sauvegarde non trouvée: {e}",
            )
        except (OSError, ValueError) as e:
            progress.setValue(0)
            QMessageBox.critical(
                self,
                "Erreur",
                f"Restauration échouée: {e}",
            )
        except Exception as e:
            progress.setValue(0)
            QMessageBox.critical(
                self,
                "Erreur",
                f"Erreur inattendue: {e}",
            )

    def _on_category_changed(self, index: int) -> None:
        self._stacked.setCurrentIndex(index)

    def _add_user(self) -> None:
        """Add a new user."""
        dialog = UserDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            username = dialog.get_username()
            password = dialog.get_password()

            # Validate username
            if len(username) < 3 or not all(c.isalnum() or c in "-_" for c in username):
                QMessageBox.warning(
                    self,
                    "Erreur",
                    "Nom d'utilisateur invalide (min 3 caractères, lettres/chiffres/-/_).",
                )
                return
            if self.db_manager.user_exists(username):
                QMessageBox.warning(self, "Erreur", "Nom d'utilisateur existe déjà.")
                return

            # Validate password
            if not password.isdigit() or len(password) != 4:
                QMessageBox.warning(self, "Erreur", "Mot de passe doit être exactement 4 chiffres.")
                return

            # Hash password
            hashed = hashlib.sha256(password.encode()).hexdigest()

            try:
                self.db_manager.add_user(username, hashed)
                self._load_users()
                QMessageBox.information(self, "Succès", "Utilisateur ajouté avec succès.")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de l'ajout: {e}")

    def _edit_user(self) -> None:
        """Edit selected user."""
        current_item = self._users_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self,
                "Aucun utilisateur sélectionné",
                "Veuillez sélectionner un utilisateur à modifier.",
            )
            return

        user_id = current_item.data(Qt.ItemDataRole.UserRole)
        username = current_item.text()

        dialog = UserDialog(self, username=username)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_username = dialog.get_username()
            new_password = dialog.get_password()

            # Validate username
            if (
                len(new_username) < 3
                or not new_username.replace("_", "").replace("-", "").isalnum()
            ):
                QMessageBox.warning(
                    self,
                    "Erreur",
                    "Nom d'utilisateur invalide (min 3 caractères, lettres/chiffres/-/_).",
                )
                return
            if new_username != username and self.db_manager.user_exists(new_username):
                QMessageBox.warning(self, "Erreur", "Nom d'utilisateur existe déjà.")
                return

            # Validate password if provided
            if new_password:
                if not new_password.isdigit() or len(new_password) != 4:
                    QMessageBox.warning(
                        self, "Erreur", "Mot de passe doit être exactement 4 chiffres."
                    )
                    return
                hashed = hashlib.sha256(new_password.encode()).hexdigest()
            else:
                hashed = None  # Keep old password

            try:
                self.db_manager.update_user(user_id, new_username, hashed)
                self._load_users()
                QMessageBox.information(self, "Succès", "Utilisateur modifié avec succès.")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de la modification: {e}")

    def _delete_user(self) -> None:
        """Delete selected user."""
        current_item = self._users_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self,
                "Aucun utilisateur sélectionné",
                "Veuillez sélectionner un utilisateur à supprimer.",
            )
            return

        user_id = current_item.data(Qt.ItemDataRole.UserRole)
        username = current_item.text()

        # Confirm deletion
        confirm = QMessageBox.question(
            self,
            "Confirmer la suppression",
            f"Êtes-vous sûr de vouloir supprimer l'utilisateur '{username}' ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            self.db_manager.delete_user(user_id)
            self._load_users()
            QMessageBox.information(self, "Succès", "Utilisateur supprimé avec succès.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la suppression: {e}")

    def _load_settings(self) -> None:
        """Load current settings from database."""
        if self.db_manager is None:
            return

        # General settings
        autosave = self.settings_service.get_item_value("autosave_enabled", True, "boolean")
        self._check_autosave.setChecked(autosave)

        backup_dir = self.settings_service.get_item_value("backup_dir", "backups/", "string")
        self._input_backup_dir.setText(backup_dir)

        retention = self.settings_service.get_item_value("backup_retention", 10, "int")
        self._input_retention.setValue(retention)

        # Financial settings
        tva = self.financial_service.get_tva_rate(20.0)
        self._input_tva.setText(f"{tva:.2f}")

        raw_coffre = self.db_manager.get_parameter("COFFRE_TOTAL", "0")
        try:
            coffre = int(raw_coffre) if raw_coffre else 0
        except ValueError:
            coffre = 0
        self._coffre_label.setText(f"{coffre:,} Ar".replace(",", " "))

        # Display settings
        currency = self.financial_service.get_currency_label()
        self._input_currency.setText(currency)

        precision = self.financial_service.get_currency_precision()
        self._input_precision.setValue(precision)

        # Load users
        self._load_users()

    def _load_users(self) -> None:
        """Load users into the list."""
        users = self.db_manager.get_users()
        self._users_list.clear()
        for user in users:
            item = QListWidgetItem(user["username"])
            item.setData(Qt.ItemDataRole.UserRole, user["id"])
            self._users_list.addItem(item)

    def save(self) -> None:
        """Save all settings."""
        self._error_label.setVisible(False)

        if self.db_manager is None:
            self.accept()
            return

        # Validate financial settings
        tva_text = self._input_tva.text().strip().replace(",", ".")
        try:
            tva = float(tva_text)
        except ValueError:
            self._error_label.setText("Le taux TVA est invalide.")
            self._error_label.setVisible(True)
            return
        if tva < 0:
            self._error_label.setText("Le taux TVA doit être positif.")
            self._error_label.setVisible(True)
            return

        # Validate billetage
        if not self._billetage_editor.validate():
            self._error_label.setText("Les coupures sont invalides.")
            self._error_label.setVisible(True)
            return

        # Save financial settings
        self.financial_service.set_tva_rate(tva)

        # Save general settings
        autosave_enabled = self._check_autosave.isChecked()
        self.settings_service.set_item(
            key="autosave_enabled",
            value=autosave_enabled,
            value_type="boolean",
            category_key="general",
        )

        backup_dir = self._input_backup_dir.text().strip() or "backups/"
        self.settings_service.set_item(
            key="backup_dir",
            value=backup_dir,
            value_type="string",
            category_key="general",
        )

        retention = self._input_retention.value()
        self.settings_service.set_item(
            key="backup_retention",
            value=retention,
            value_type="int",
            category_key="general",
        )

        # Save display settings
        currency = self._input_currency.text().strip() or "Ar"
        self.financial_service.set_currency_label(currency)

        precision = self._input_precision.value()
        self.financial_service.set_currency_precision(precision)

        # Save billetage
        denoms = self._billetage_editor.get_denominations()
        self.financial_service.set_billetage_denominations(denoms)

        # Save PIN if provided
        pin = self._input_pin.text().strip()
        if pin:
            try:
                self.db_manager.set_admin_pin(pin)
            except ValueError as exc:
                self._error_label.setText(str(exc))
                self._error_label.setVisible(True)
                return

        self.accept()

    def _open_export(self) -> None:
        """Open export dialog."""
        from ui.dialogs.export_dialog import ExportDialog

        dialog = ExportDialog(self, self.db_manager)
        dialog.exec()

    def _open_import(self) -> None:
        """Open import dialog."""
        from ui.dialogs.import_dialog import ImportDialog

        dialog = ImportDialog(self, self.db_manager)
        dialog.exec()


class UserDialog(QDialog):
    """Dialog for adding/editing users."""

    def __init__(self, parent: QWidget | None = None, username: str = "", password: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Utilisateur")
        self.resize(300, 150)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        form = QFormLayout()
        form.setSpacing(12)

        self._input_username = QLineEdit(username)
        self._input_username.setPlaceholderText("Nom d'utilisateur")
        self._input_username.setMinimumHeight(INPUT_MIN_HEIGHT)
        form.addRow("Nom d'utilisateur:", self._input_username)

        self._input_password = QLineEdit(password)
        self._input_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._input_password.setPlaceholderText("4 chiffres (laisser vide pour conserver)")
        self._input_password.setMinimumHeight(INPUT_MIN_HEIGHT)
        form.addRow("Mot de passe:", self._input_password)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_username(self) -> str:
        """Get entered username."""
        return self._input_username.text().strip()

    def get_password(self) -> str:
        """Get entered password."""
        return self._input_password.text().strip()
