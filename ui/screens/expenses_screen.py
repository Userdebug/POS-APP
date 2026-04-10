"""Ecran de depenses journalieres."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ExpensesScreen(QDialog):
    def __init__(self, db_manager: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db_manager = db_manager
        self.jour = datetime.now().strftime("%d/%m/%y")
        self.setWindowTitle("Depenses")
        self.setModal(True)
        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(10)

        top = QHBoxLayout()
        titre = QLabel("Depenses Journalieres")
        titre.setStyleSheet("font-size:18px; font-weight:800;")
        self.lbl_jour = QLabel(f"Depenses du jour: {self.jour}")
        self.lbl_jour.setStyleSheet("font-weight:700;")
        top.addWidget(titre)
        top.addSpacing(12)
        top.addWidget(self.lbl_jour)
        top.addStretch(1)
        root.addLayout(top)

        form_box = QGroupBox("Ajouter une depense")
        form = QGridLayout(form_box)
        form.setSpacing(8)
        form.setContentsMargins(10, 10, 10, 10)

        # Row 0: Labels
        form.addWidget(QLabel("Designation"), 0, 0)
        form.addWidget(QLabel("Valeur"), 0, 1)
        form.addWidget(QLabel("Remarque"), 0, 2)
        form.addWidget(QLabel(""), 0, 3)  # Empty cell for button alignment

        # Row 1: Input fields
        self.input_designation = QLineEdit()
        self.input_designation.setPlaceholderText("Designation")
        form.addWidget(self.input_designation, 1, 0)

        self.input_valeur = QSpinBox()
        self.input_valeur.setRange(0, 1_000_000_000)
        self.input_valeur.setSingleStep(100)
        self.input_valeur.setSuffix(" Ar")
        form.addWidget(self.input_valeur, 1, 1)

        self.input_remarque = QLineEdit()
        self.input_remarque.setPlaceholderText("Remarque")
        form.addWidget(self.input_remarque, 1, 2)

        self.btn_ajouter = QPushButton("Ajouter")
        self.btn_ajouter.setMinimumWidth(100)
        self.btn_ajouter.clicked.connect(self._add_expense)
        form.addWidget(self.btn_ajouter, 1, 3)

        root.addWidget(form_box)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Heure", "Designation", "Valeur", "Remarque", "", ""])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        root.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self.lbl_total_jour = QLabel("Total du jour: 0 Ar")
        self.lbl_total_jour.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.lbl_total_jour.setStyleSheet("font-weight:800; font-size:16px;")
        bottom.addWidget(self.lbl_total_jour)
        root.addLayout(bottom)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.btn_fermer = QPushButton("Fermer")
        self.btn_fermer.clicked.connect(self.accept)
        actions.addWidget(self.btn_fermer)
        root.addLayout(actions)

        self.setMinimumSize(920, 560)
        self.resize(980, 600)

    def _add_expense(self) -> None:
        designation = self.input_designation.text().strip()
        valeur = int(self.input_valeur.value())
        remarque = self.input_remarque.text().strip()
        if not designation or valeur <= 0:
            return

        now = datetime.now().strftime("%d/%m/%y %H:%M:%S")
        try:
            self.db_manager.add_expense(
                designation=designation,
                valeur=valeur,
                remarque=remarque,
                date_depense=now,
            )
        except (RuntimeError, ValueError, TypeError) as exc:
            QMessageBox.warning(self, "Depenses", f"Ajout impossible: {exc}")
            return
        self.input_designation.clear()
        self.input_valeur.setValue(0)
        self.input_remarque.clear()
        self.refresh_data()

    def refresh_data(self) -> None:
        self.jour = datetime.now().strftime("%d/%m/%y")
        self.lbl_jour.setText(f"Depenses du jour: {self.jour}")

        try:
            depenses = self.db_manager.list_depenses_jour(self.jour)
            total = self.db_manager.total_depenses_jour(self.jour)
        except (RuntimeError, ValueError, TypeError) as exc:
            self.table.setRowCount(0)
            self.lbl_total_jour.setText("Total du jour: 0 Ar")
            QMessageBox.warning(self, "Depenses", f"Chargement impossible: {exc}")
            return

        self.table.setRowCount(0)
        for depense in depenses:
            row = self.table.rowCount()
            self.table.insertRow(row)
            date_text = str(depense.get("date_depense", ""))
            heure = date_text[11:16] if len(date_text) >= 16 else date_text
            self.table.setItem(row, 0, QTableWidgetItem(heure))
            self.table.setItem(row, 1, QTableWidgetItem(str(depense.get("designation", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(f"{int(depense.get('valeur', 0))}"))
            self.table.setItem(row, 3, QTableWidgetItem(str(depense.get("remarque", ""))))

            # Boutons Edit et Delete
            btn_edit = QPushButton("✏️")
            btn_edit.setFixedWidth(40)
            btn_edit.setToolTip("Modifier")
            btn_edit.clicked.connect(lambda _, d=depense: self._edit_expense(d))
            self.table.setCellWidget(row, 4, btn_edit)

            btn_delete = QPushButton("🗑️")
            btn_delete.setFixedWidth(40)
            btn_delete.setToolTip("Supprimer")
            btn_delete.clicked.connect(lambda _, d=depense: self._delete_expense(d))
            self.table.setCellWidget(row, 5, btn_delete)

        self.lbl_total_jour.setText(f"Total du jour: {total} Ar")

    def _edit_expense(self, depense: dict) -> None:
        """Ouvre un dialog pour modifier une depense existante."""
        depense_id = depense.get("id")
        if not depense_id:
            return

        # Creation d'un dialog simple pour l'edition
        dialog = QDialog(self)
        dialog.setWindowTitle("Modifier Depense")
        dialog.setMinimumWidth(400)
        layout = QVBoxLayout(dialog)

        # Designation
        h_desig = QHBoxLayout()
        h_desig.addWidget(QLabel("Designation:"))
        input_desig = QLineEdit(str(depense.get("designation", "")))
        h_desig.addWidget(input_desig)
        layout.addLayout(h_desig)

        # Valeur
        h_val = QHBoxLayout()
        h_val.addWidget(QLabel("Valeur:"))
        input_val = QSpinBox()
        input_val.setRange(0, 1_000_000_000)
        input_val.setSingleStep(100)
        input_val.setSuffix(" Ar")
        input_val.setValue(int(depense.get("valeur", 0)))
        h_val.addWidget(input_val)
        layout.addLayout(h_val)

        # Remarque
        h_rem = QHBoxLayout()
        h_rem.addWidget(QLabel("Remarque:"))
        input_rem = QLineEdit(str(depense.get("remarque", "")))
        h_rem.addWidget(input_rem)
        layout.addLayout(h_rem)

        # Boutons
        btns = QHBoxLayout()
        btn_cancel = QPushButton("Annuler")
        btn_cancel.clicked.connect(dialog.reject)
        btns.addWidget(btn_cancel)
        btn_save = QPushButton("Enregistrer")
        btn_save.clicked.connect(dialog.accept)
        btns.addWidget(btn_save)
        layout.addLayout(btns)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            designation = input_desig.text().strip()
            valeur = int(input_val.value())
            remarque = input_rem.text().strip()
            if designation and valeur > 0:
                try:
                    self.db_manager.update_depense(depense_id, designation, valeur, remarque)
                except (RuntimeError, ValueError, TypeError) as exc:
                    QMessageBox.warning(self, "Depenses", f"Modification impossible: {exc}")
                    return
                self.refresh_data()

    def _delete_expense(self, depense: dict) -> None:
        """Supprime une depense apres confirmation."""
        depense_id = depense.get("id")
        if not depense_id:
            return

        reponse = QMessageBox.question(
            self,
            "Confirmer la suppression",
            f"Voulez-vous vraiment supprimer la depense '{depense.get('designation', '')}' ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reponse == QMessageBox.StandardButton.Yes:
            try:
                self.db_manager.delete_depense(depense_id)
            except (RuntimeError, ValueError, TypeError) as exc:
                QMessageBox.warning(self, "Depenses", f"Suppression impossible: {exc}")
                return
            self.refresh_data()
