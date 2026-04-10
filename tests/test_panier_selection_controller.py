import unittest

from controllers.panier_selection_controller import PanierSelectionController


class TestPanierSelectionController(unittest.TestCase):
    def test_refresh_panier_target(self) -> None:
        self.assertIsNone(
            PanierSelectionController.refresh_basket_target(
                row_count=0,
                previous_active_row=1,
                has_brouillon=False,
            )
        )
        self.assertEqual(
            4,
            PanierSelectionController.refresh_basket_target(
                row_count=5,
                previous_active_row=1,
                has_brouillon=True,
            ),
        )
        self.assertEqual(
            1,
            PanierSelectionController.refresh_basket_target(
                row_count=5,
                previous_active_row=1,
                has_brouillon=False,
            ),
        )
        self.assertEqual(
            4,
            PanierSelectionController.refresh_basket_target(
                row_count=5,
                previous_active_row=99,
                has_brouillon=False,
            ),
        )

    def test_refresh_facture_target(self) -> None:
        self.assertIsNone(
            PanierSelectionController.refresh_invoice_target(row_count=0, previous_active_row=0)
        )
        self.assertEqual(
            2,
            PanierSelectionController.refresh_invoice_target(row_count=5, previous_active_row=2),
        )
        self.assertEqual(
            4,
            PanierSelectionController.refresh_invoice_target(row_count=5, previous_active_row=99),
        )

    def test_next_caisse_row(self) -> None:
        self.assertIsNone(
            PanierSelectionController.next_cash_register_row(current_row=-1, row_count=4)
        )
        self.assertEqual(
            2, PanierSelectionController.next_cash_register_row(current_row=1, row_count=4)
        )
        self.assertEqual(
            3, PanierSelectionController.next_cash_register_row(current_row=3, row_count=4)
        )

    def test_next_reception_action(self) -> None:
        action = PanierSelectionController.next_reception_action(current_row=0, items_count=0)
        self.assertTrue(action.add_new_row)
        self.assertIsNone(action.next_row)

        action = PanierSelectionController.next_reception_action(current_row=1, items_count=3)
        self.assertFalse(action.add_new_row)
        self.assertEqual(2, action.next_row)

        action = PanierSelectionController.next_reception_action(current_row=2, items_count=3)
        self.assertTrue(action.add_new_row)
        self.assertIsNone(action.next_row)

    def test_validation_enabled(self) -> None:
        # Test Caisse mode with draft line
        self.assertTrue(
            PanierSelectionController.validation_enabled(
                mode="caisse",
                has_brouillon=True,
                has_achats_brouillon=False,
                panier_row_count=0,
                panier_current_row=-1,
                facture_row_count=0,
                facture_current_row=-1,
            )
        )
        # Test Caisse mode without draft line
        self.assertFalse(
            PanierSelectionController.validation_enabled(
                mode="caisse",
                has_brouillon=False,
                has_achats_brouillon=False,
                panier_row_count=0,
                panier_current_row=-1,
                facture_row_count=0,
                facture_current_row=-1,
            )
        )
        # Test Reception mode with draft line
        self.assertTrue(
            PanierSelectionController.validation_enabled(
                mode="reception",
                has_brouillon=False,
                has_achats_brouillon=True,
                panier_row_count=0,
                panier_current_row=-1,
                facture_row_count=0,
                facture_current_row=-1,
            )
        )
        # Test Reception mode without draft line but with selected row
        self.assertTrue(
            PanierSelectionController.validation_enabled(
                mode="reception",
                has_brouillon=False,
                has_achats_brouillon=False,
                panier_row_count=0,
                panier_current_row=-1,
                facture_row_count=3,
                facture_current_row=1,
            )
        )


if __name__ == "__main__":
    unittest.main()
