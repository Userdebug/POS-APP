"""Categories management dialog for admin."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from styles.dialog_styles import (
    DIALOG_BASE,
    ERROR_LABEL,
    HEADER_LABEL,
    INPUT_FIELD,
    INPUT_MIN_HEIGHT,
    PRIMARY_BUTTON,
    SECONDARY_BUTTON,
    SEPARATOR,
)


class CategoriesDialog(QDialog):
    """Dialog for managing product categories with CRUD operations."""

    def __init__(self, parent: QWidget | None, category_service):
        super().__init__(parent)
        self.category_service = category_service
        self.setWindowTitle("Gestion des catégories")
        self.resize(600, 500)

        self.setStyleSheet(DIALOG_BASE + INPUT_FIELD)

        self._init_ui()
        self._load_categories()

    def _init_ui(self) -> None:
        """Initialize the UI components."""
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Header
        header = QLabel("Catégories de produits")
        header.setStyleSheet(HEADER_LABEL)
        root.addWidget(header)

        # Error message area
        self._error_label = QLabel()
        self._error_label.setStyleSheet(ERROR_LABEL)
        self._error_label.setVisible(False)
        self._error_label.setWordWrap(True)
        root.addWidget(self._error_label)

        # Main content: tree + controls
        content = QHBoxLayout()
        content.setSpacing(12)

        # Left: Category tree
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Nom", "Produits"])
        self._tree.setColumnWidth(0, 300)
        self._tree.setAlternatingRowColors(True)
        self._tree.itemDoubleClicked.connect(self._on_edit_category)
        content.addWidget(self._tree, 3)

        # Right: Controls
        controls = QVBoxLayout()
        controls.setSpacing(8)

        # Add parent button
        btn_add_parent = QPushButton("+ Ajouter catégorie parent")
        btn_add_parent.setStyleSheet(SECONDARY_BUTTON)
        btn_add_parent.clicked.connect(self._on_add_parent)
        controls.addWidget(btn_add_parent)

        # Add child button
        btn_add_child = QPushButton("+ Ajouter sous-catégorie")
        btn_add_child.setStyleSheet(SECONDARY_BUTTON)
        btn_add_child.clicked.connect(self._on_add_child)
        controls.addWidget(btn_add_child)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(SEPARATOR)
        sep.setFixedHeight(1)
        controls.addWidget(sep)

        # Edit button
        btn_edit = QPushButton("Modifier")
        btn_edit.setStyleSheet(SECONDARY_BUTTON)
        btn_edit.clicked.connect(self._on_edit_category)
        controls.addWidget(btn_edit)

        # Delete button
        btn_delete = QPushButton("Supprimer")
        btn_delete.setStyleSheet(SECONDARY_BUTTON)
        btn_delete.clicked.connect(self._on_delete_category)
        controls.addWidget(btn_delete)

        controls.addStretch()
        content.addLayout(controls, 1)

        root.addLayout(content)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_btn is not None:
            close_btn.setText("Fermer")
            close_btn.setStyleSheet(SECONDARY_BUTTON)
        buttons.rejected.connect(self.accept)
        root.addWidget(buttons)

    def _load_categories(self) -> None:
        """Load categories into the tree."""
        self._tree.clear()

        tree = self.category_service.get_category_tree()
        self._build_tree_items(tree, None)

    def _build_tree_items(self, categories: list, parent_item: QTreeWidgetItem | None) -> None:
        """Recursively build tree items."""
        for cat in categories:
            if parent_item:
                item = QTreeWidgetItem(parent_item)
            else:
                item = QTreeWidgetItem(self._tree)

            item.setText(0, cat.nom)

            # Get product count
            stats = self.category_service.get_category_stats(cat.id)
            item.setText(1, str(stats["product_count"]))

            # Store category ID
            item.setData(0, Qt.ItemDataRole.UserRole, cat.id)

            # Add children
            if cat.children:
                self._build_tree_items(cat.children, item)
                if parent_item:
                    parent_item.setExpanded(True)

    def _on_add_parent(self) -> None:
        """Add a new parent category."""
        self._show_category_dialog(None)

    def _on_add_child(self) -> None:
        """Add a new child category."""
        current = self._tree.currentItem()
        if not current:
            self._show_error("Veuillez sélectionner une catégorie parente")
            return

        parent_id = current.data(0, Qt.ItemDataRole.UserRole)
        if not parent_id:
            self._show_error("Veuillez sélectionner une catégorie parente valide")
            return

        self._show_category_dialog(None, parent_id)

    def _on_edit_category(self) -> None:
        """Edit the selected category."""
        current = self._tree.currentItem()
        if not current:
            self._show_error("Veuillez sélectionner une catégorie à modifier")
            return

        category_id = current.data(0, Qt.ItemDataRole.UserRole)
        if not category_id:
            return

        self._show_category_dialog(category_id)

    def _on_delete_category(self) -> None:
        """Delete the selected category."""
        current = self._tree.currentItem()
        if not current:
            self._show_error("Veuillez sélectionner une catégorie à supprimer")
            return

        category_id = current.data(0, Qt.ItemDataRole.UserRole)
        if not category_id:
            return

        category = self.category_service.get_category_by_id(category_id)
        if not category:
            return

        # Check if can delete
        can_delete, message = self.category_service.can_delete(category_id)
        if not can_delete:
            self._show_error(message)
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirmation de suppression",
            f'Voulez-vous vraiment supprimer la catégorie "{category.nom}" ?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            success, msg = self.category_service.delete_category(category_id)
            if success:
                self._load_categories()
            else:
                self._show_error(msg)

    def _show_category_dialog(
        self, category_id: int | None, default_parent_id: int | None = None
    ) -> None:
        """Show the category edit dialog."""
        dialog = CategoryEditDialog(
            self,
            category_service=self.category_service,
            category_id=category_id,
            default_parent_id=default_parent_id,
        )
        if dialog.exec():
            self._load_categories()

    def _show_error(self, message: str) -> None:
        """Show an error message."""
        self._error_label.setText(message)
        self._error_label.setVisible(True)


class CategoryEditDialog(QDialog):
    """Dialog for editing a category."""

    def __init__(
        self,
        parent: QWidget | None,
        category_service,
        category_id: int | None = None,
        default_parent_id: int | None = None,
    ):
        super().__init__(parent)
        self.category_service = category_service
        self.category_id = category_id
        self.default_parent_id = default_parent_id

        is_edit = category_id is not None
        self.setWindowTitle("Modifier la catégorie" if is_edit else "Nouvelle catégorie")
        self.resize(400, 200)

        self.setStyleSheet(DIALOG_BASE + INPUT_FIELD)

        self._init_ui()
        self._load_category()

    def _init_ui(self) -> None:
        """Initialize the UI components."""
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Form
        from PyQt6.QtWidgets import QFormLayout

        form = QFormLayout()
        form.setSpacing(10)

        # Name input
        self._name_input = QLineEdit()
        self._name_input.setMinimumHeight(INPUT_MIN_HEIGHT)
        self._name_input.setPlaceholderText("Nom de la catégorie")
        form.addRow("Nom:", self._name_input)

        # Parent dropdown (only for new categories)
        from PyQt6.QtWidgets import QComboBox

        self._parent_combo = QComboBox()
        self._parent_combo.setMinimumHeight(INPUT_MIN_HEIGHT)

        # Add "Aucun" option for top-level categories
        self._parent_combo.addItem("-- Aucune (catégorie parent) --", None)

        # Add parent options
        parents = self.category_service.get_parent_options()
        for pid, pname in parents:
            # Don't allow setting self as parent
            if pid != self.category_id:
                self._parent_combo.addItem(pname, pid)

        form.addRow("Catégorie parente:", self._parent_combo)

        root.addLayout(form)

        # Error label
        self._error_label = QLabel()
        self._error_label.setStyleSheet(ERROR_LABEL)
        self._error_label.setVisible(False)
        self._error_label.setWordWrap(True)
        root.addWidget(self._error_label)

        # Buttons
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
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load_category(self) -> None:
        """Load existing category data if editing."""
        if self.category_id:
            category = self.category_service.get_category_by_id(self.category_id)
            if category:
                self._name_input.setText(category.nom)

                # Set parent
                if category.parent_id:
                    index = self._parent_combo.findData(category.parent_id)
                    if index >= 0:
                        self._parent_combo.setCurrentIndex(index)
        elif self.default_parent_id:
            # Set default parent for new child category
            index = self._parent_combo.findData(self.default_parent_id)
            if index >= 0:
                self._parent_combo.setCurrentIndex(index)

    def _save(self) -> None:
        """Save the category."""
        name = self._name_input.text().strip()
        parent_id = self._parent_combo.currentData()

        if not name:
            self._show_error("Le nom de la catégorie ne peut pas être vide")
            return

        if self.category_id:
            # Update existing
            error = self.category_service.update_category(self.category_id, name, parent_id)
            if error:
                self._show_error(error)
                return
        else:
            # Create new
            cat_id, error = self.category_service.create_category(name, parent_id)
            if error:
                self._show_error(error)
                return

        self.accept()

    def _show_error(self, message: str) -> None:
        """Show an error message."""
        self._error_label.setText(message)
        self._error_label.setVisible(True)
