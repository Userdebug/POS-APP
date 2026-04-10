"""
Service for calculating sales analytics metrics.
"""

import sqlite3
from typing import Dict


class SalesAnalyticsService:
    """Service for calculating sales-based metrics like average daily sales."""

    def __init__(self, db_connection: sqlite3.Connection):
        """
        Initialize the service with a database connection.

        Args:
            db_connection: SQLite database connection
        """
        self.db = db_connection

    def calculate_metric(self, product_id: int, interval_days: int) -> Dict[str, float]:
        """
        Calculate average daily sales quantity for a product over the specified interval.

        Args:
            product_id: ID of the product
            interval_days: Number of days to look back (e.g., 30 for m3, 100 for m10)

        Returns:
            Dictionary with 'value' (average daily quantity) and 'label' (e.g., 'm3', 'm10')
        """
        # Calculate label based on interval (e.g., 30 days -> m3, 100 days -> m10)
        label = f"m{interval_days // 10}"

        # Handle edge case
        if interval_days <= 0:
            return {"value": 0.0, "label": label}

        try:
            cursor = self.db.cursor()

            # Get the most recent date in the ventes table for this product
            cursor.execute("SELECT MAX(jour) FROM ventes WHERE produit_id = ?", (product_id,))
            result = cursor.fetchone()
            end_date_str = result[0] if result and result[0] else None

            if not end_date_str:
                # No sales data found
                return {"value": 0.0, "label": label}

            # Calculate start date (interval_days before end_date)
            # We use SQLite date functions for consistency
            cursor.execute(
                """
                SELECT 
                    COALESCE(SUM(quantite), 0) as total_quantity
                FROM ventes 
                WHERE produit_id = ? 
                AND jour >= date(?, '-' || ? || ' days')
                AND jour <= date(?)
                """,
                (product_id, end_date_str, interval_days, end_date_str),
            )

            result = cursor.fetchone()
            total_quantity = result[0] if result else 0

            # Calculate average daily quantity
            average_daily = total_quantity / interval_days if interval_days > 0 else 0.0

            return {
                "value": round(average_daily),  # Return as integer to match original m3 type
                "label": label,
            }
        except sqlite3.Error as e:
            # Log the error in a real application
            print(f"Error calculating metric for product {product_id}: {e}")
            return {"value": 0.0, "label": label}
