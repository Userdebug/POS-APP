# ui/components/quantity_editor.py
"""
Widget réutilisable pour la saisie de quantité avec boutons +/-.
Ce composant peut être utilisé dans toutes les zones de saisie de quantité.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIntValidator
from PyQt6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QWidget


class QuantityEditor(QWidget):
    """Widget de saisie de quantité avec boutons + et -.

    Args:
        quantity: Quantité initiale (défaut: 0)
        min_quantity: Quantité minimum autorisée (défaut: 0)
        on_minus: Callback appelé lors du clic sur le bouton -
        on_plus: Callback appelé lors du clic sur le bouton +
        parent: Widget parent optionnel
    """

    quantity_changed = pyqtSignal(int)

    def __init__(
        self,
        quantity: int,
        min_quantity: int,
        on_minus,
        on_plus,
        parent,
        min_val: int = 0,
        max_val: int = 9999,
    ):
        super().__init__(parent)
        # Si min_quantity is None, pas de minimum (autorise valeurs negatives)
        self._min_quantity = min_quantity if min_quantity is not None else float("-inf")
        self._min_val = min_val
        self._max_val = max_val
        self._on_minus = on_minus
        self._on_plus = on_plus
        self._build_ui(quantity)

    def _build_ui(self, qte: int):
        """Construit l'interface utilisateur du widget."""
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        btn_minus = QPushButton("-")
        btn_minus.setFixedWidth(18)
        btn_minus.setFixedHeight(18)
        if self._on_minus:
            btn_minus.clicked.connect(self._on_minus)
        btn_minus.clicked.connect(lambda: self._on_value_changed(-1))

        self._input_qte = QLineEdit(str(max(self._min_quantity, int(qte))))
        self._input_qte.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._input_qte.setMaxLength(4)  # Allow up to 9999
        self._input_qte.setValidator(
            QIntValidator(self._min_val, self._max_val, self)
        )  # Int validator with configurable bounds
        self._input_qte.editingFinished.connect(self._on_manual_edit)

        btn_plus = QPushButton("+")
        btn_plus.setFixedWidth(18)
        btn_plus.setFixedHeight(18)
        if self._on_plus:
            btn_plus.clicked.connect(self._on_plus)
        btn_plus.clicked.connect(lambda: self._on_value_changed(+1))

        lay.addWidget(btn_minus)
        lay.addWidget(self._input_qte, 1)
        lay.addWidget(btn_plus)

        # Store button references for state management
        self._btn_minus = btn_minus
        self._btn_plus = btn_plus
        self._update_buttons_state()

    def set_quantity(self, qte: int):
        """Met à jour l'affichage de la quantité.

        Args:
            qte: Nouvelle quantité (minimum défini par min_quantity)
        """
        if self._min_quantity == float("-inf"):
            self._input_qte.setText(str(int(qte)))
        else:
            self._input_qte.setText(str(max(self._min_quantity, int(qte))))
        self.quantity_changed.emit(self.quantity())
        self._update_buttons_state()

    def _on_manual_edit(self):
        """Gère l'édition manuelle du champ de quantité."""
        self._validate_and_emit()

    def _validate_and_emit(self):
        """Valide la valeur et émet le signal si changé."""
        text = self._input_qte.text().strip()
        try:
            value = int(float(text))
        except ValueError:
            value = 0
        # Apply min/max constraints
        value = max(self._min_val, min(self._max_val, value))
        # Apply min_quantity constraint
        if self._min_quantity != float("-inf"):
            value = max(self._min_quantity, value)
        self._input_qte.setText(str(value))
        self.quantity_changed.emit(value)
        self._update_buttons_state()

    def _on_value_changed(self, delta: int):
        """Modifie la quantité et émet le signal quantity_changed.

        Args:
            delta: Variation à appliquer (+1 ou -1)
        """
        current = self.quantity()
        new_value = current + delta
        # Apply min/max constraints
        new_value = max(self._min_val, min(self._max_val, new_value))
        # Apply min_quantity constraint if set (but allow negative when min_quantity is None)
        if self._min_quantity != float("-inf"):
            new_value = max(self._min_quantity, new_value)
        self._input_qte.setText(str(int(new_value)))
        self.quantity_changed.emit(int(new_value))
        self._update_buttons_state()

    def quantity(self) -> int:
        """Retourne la quantité actuelle.

        Returns:
            La quantité actuelle sous forme d'entier
        """
        text = self._input_qte.text().strip()
        try:
            return int(float(text))
        except ValueError:
            return 0

    def reset(self):
        """Remet la quantité à la valeur minimum."""
        self.set_quantity(self._min_quantity)

    def _update_buttons_state(self):
        """Met à jour l'état des boutons +/- en fonction des limites.

        Désactive le bouton moins si la valeur est au minimum,
        et le bouton plus si elle est au maximum.
        """
        current = self.quantity()
        self._btn_minus.setEnabled(current > self._min_val)
        self._btn_plus.setEnabled(current < self._max_val)
