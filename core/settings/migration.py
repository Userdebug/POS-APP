"""Migration utilities for settings system."""

from __future__ import annotations


def migrate_legacy_parameters(db_manager) -> None:
    """Migrate legacy parametres to new settings system.

    This is called during initialization to ensure existing parameters
    are available in the new settings system.
    """
    settings = db_manager.settings

    # Migration mapping: key -> (category, type, transform_fn)
    migrations = [
        # General settings
        (
            "autosave_enabled",
            "general",
            "boolean",
            lambda v: v == "1" if v else True,
        ),
        ("backup_dir", "general", "string", lambda v: v or "backups/"),
        (
            "backup_retention",
            "general",
            "int",
            lambda v: int(v) if v else 10,
        ),
        # Financial settings
        ("TVA_TAUX", "financial", "float", lambda v: float(v) if v else 20.0),
        (
            "COFFRE_TOTAL",
            "financial",
            "int",
            lambda v: int(v) if v else 0,
        ),
        # Display settings
        ("APP_MODE", "display", "string", lambda v: v or "caisse"),
        # Internal settings (not migrated to visible settings, but need to exist)
        ("LAST_CLOSED_DATE", "general", "string", lambda v: v or ""),
        ("DAILY_RESET_PENDING", "general", "boolean", lambda v: v == "1" if v else False),
    ]

    for key, category, value_type, transform_fn in migrations:
        # Skip if already exists in new settings
        if settings.get_item(key):
            continue

        # Get from legacy parametres
        legacy_value = db_manager._params.get(key)
        if legacy_value is None:
            continue

        try:
            transformed = transform_fn(legacy_value)
            is_visible = key not in ("LAST_CLOSED_DATE", "DAILY_RESET_PENDING")
            settings.set_item(
                key=key,
                value=transformed,
                value_type=value_type,
                category_key=category,
            )
            # Mark internal settings as invisible
            if not is_visible:
                item = settings.get_item(key)
                if item:
                    item.is_visible = False
                    settings._repo.update_item(item)
        except (ValueError, TypeError):
            # Skip invalid values
            pass

    # Set default currency label if not exists
    if not settings.get_item("currency_label"):
        settings.set_item(
            key="currency_label",
            value="Ar",
            value_type="string",
            description="Symbole de la devise",
            category_key="display",
        )

    # Set default billetal denominations if not exists
    if not settings.get_item("billetage_denominations"):
        settings.set_item(
            key="billetage_denominations",
            value=[20000, 10000, 5000, 2000, 1000, 500, 200, 100],
            value_type="json",
            description="Coupures de billets",
            category_key="display",
        )
