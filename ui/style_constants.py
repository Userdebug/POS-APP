"""Styles inline reutilisables pour widgets Qt."""

from styles.design_tokens import TOKENS

VALIDER_BUTTON_ENABLED_STYLE = f"font-weight:700; background-color:{TOKENS['button_success']}; color:#f8fafc; border:1px solid {TOKENS['button_success_border']};"
VALIDER_BUTTON_DISABLED_STYLE = f"font-weight:700; background-color:{TOKENS['button_disabled']}; color:{TOKENS['button_disabled_text']}; border:1px solid {TOKENS['button_disabled_border']};"

TOTAL_CAISSE_ENABLED_STYLE = (
    f"text-align: center; font-size: 14px; font-weight: 700; padding: 1px 3px; "
    f"background-color: {TOKENS['total_caisse_bg']}; color: {TOKENS['total_caisse_text']}; border: 2px solid {TOKENS['total_caisse_border']};"
)
TOTAL_CAISSE_DISABLED_STYLE = (
    f"text-align: center; font-size: 14px; font-weight: 700; padding: 1px 3px; "
    f"background-color: {TOKENS['button_disabled']}; color: {TOKENS['button_disabled_text']}; border: 1px solid {TOKENS['button_disabled']};"
)
TOTAL_FACTURE_ENABLED_STYLE = (
    f"font-size: 14px; font-weight: 700; color: {TOKENS['total_facture_text']}; background-color: {TOKENS['total_facture_bg']}; "
    f"border: 2px solid {TOKENS['total_facture_border']}; padding: 2px 4px;"
)
TOTAL_FACTURE_DISABLED_STYLE = (
    f"font-size: 14px; font-weight: 700; color: {TOKENS['button_disabled_text']}; background-color: {TOKENS['button_disabled_border']}; "
    f"border: 1px solid {TOKENS['button_disabled']}; padding: 2px 4px;"
)

PANIER_TAB_BASE_STYLE = (
    f"text-align: center; font-size: 14px; font-weight: 700; padding: 1px 3px; "
    f"background-color: {TOKENS['panier_tab_bg']}; color: {TOKENS['panier_tab_text']};"
)
PANIER_TAB_ACTIVE_BORDER_STYLE = f"border: 2px solid {TOKENS['panier_tab_active_border']};"
PANIER_TAB_INACTIVE_BORDER_STYLE = f"border: 1px solid {TOKENS['panier_tab_inactive_border']};"
