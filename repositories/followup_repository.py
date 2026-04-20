"""DEPRECATED — Use repositories.daily_tracking_repository.DailyTrackingRepository
and services.daily_tracking_service.DailyTrackingService instead.

This file is kept temporarily for backward compatibility during migration.
All Tcollecte operations have moved to the new service.
"""

from __future__ import annotations
import logging
from typing import Any

logger = logging.getLogger(__name__)


class FollowupRepository:
    """Deprecated stub forwarding to DailyTrackingService.

    All previous Tcollecte methods have been removed. This stub exists
    solely to avoid breaking imports during transition. It will be
    removed entirely in a future release.
    """

    def __init__(self, **kwargs: Any) -> None:
        logger.warning("FollowupRepository is deprecated — use DailyTrackingService")
        self._kwargs = kwargs

    def __getattr__(self, name: str) -> Any:
        raise AttributeError(
            f"FollowupRepository.{name} has been removed. "
            f"Use DailyTrackingService or DailyTrackingRepository instead."
        )
