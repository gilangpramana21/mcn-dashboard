"""Notification Service — alert when campaign metrics exceed configured thresholds."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass
class Notification:
    campaign_id: str
    metric_name: str
    current_value: float
    threshold_value: float
    message: str


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class NotificationService:
    """Compares metrics against configured thresholds and emits notifications."""

    async def check_and_notify(
        self,
        campaign_id: str,
        metrics: Dict[str, float],
        alert_thresholds: Dict[str, float],
        redis: Optional[Any] = None,
    ) -> List[Notification]:
        """Return a Notification for every metric that exceeds its threshold.

        Parameters
        ----------
        campaign_id:
            ID of the campaign being monitored.
        metrics:
            Mapping of metric_name → current_value.
        alert_thresholds:
            Mapping of metric_name → threshold_value (from CampaignSettings).
        redis:
            Optional Redis client (reserved for future pub/sub publishing).
        """
        notifications: List[Notification] = []

        for metric_name, threshold_value in alert_thresholds.items():
            current_value = metrics.get(metric_name)
            if current_value is None:
                continue

            if current_value > threshold_value:
                notification = Notification(
                    campaign_id=campaign_id,
                    metric_name=metric_name,
                    current_value=current_value,
                    threshold_value=threshold_value,
                    message=(
                        f"Metrik '{metric_name}' pada kampanye '{campaign_id}' "
                        f"melampaui threshold: nilai saat ini {current_value} "
                        f"> threshold {threshold_value}."
                    ),
                )
                notifications.append(notification)

                # Optionally publish to Redis pub/sub
                if redis is not None:
                    try:
                        await redis.publish(
                            f"alerts:{campaign_id}",
                            notification.message,
                        )
                    except Exception:
                        pass  # Non-critical; don't block notification list

        return notifications
