"""Diagnostics for ParentVUE."""

from __future__ import annotations

from typing import Any

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from . import ParentVueConfigEntry

_TO_REDACT = {CONF_USERNAME, CONF_PASSWORD}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ParentVueConfigEntry,
) -> dict[str, Any]:
    """Return privacy-preserving diagnostics.

    Student names, schools, course names, identifiers, grades, assignments,
    schedule details, cookies, and raw server responses are deliberately absent.
    """
    coordinator = entry.runtime_data.coordinator
    data = coordinator.data

    return {
        "entry_data": async_redact_data(dict(entry.data), _TO_REDACT),
        "last_update_success": coordinator.last_update_success,
        "student_count": len(data.children) if data else 0,
        "course_counts": (
            [len(child.courses) for child in data.children] if data else []
        ),
        "schedule_entry_counts": (
            [len(child.schedule) for child in data.children] if data else []
        ),
        "schedule_available": (
            [child.schedule_available for child in data.children] if data else []
        ),
        "polling_policy": {
            "automatic_interval": "2 hours 1 minute",
            "minimum_network_interval": "2 hours",
        },
    }
