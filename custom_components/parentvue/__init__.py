"""ParentVUE integration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import aiohttp

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import ParentVueClient
from .const import (
    CONF_BASE_URL,
    DASHBOARD_CARD_RESOURCE_URL,
    DASHBOARD_CARD_URL,
    PLATFORMS,
    VERSION,
)
from .coordinator import ParentVueDataUpdateCoordinator


CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass(slots=True)
class ParentVueRuntimeData:
    """Runtime data for a ParentVUE config entry."""

    client: ParentVueClient
    coordinator: ParentVueDataUpdateCoordinator


type ParentVueConfigEntry = ConfigEntry[ParentVueRuntimeData]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up ParentVUE integration resources."""
    card_path = Path(__file__).parent / "frontend" / "parentvue-dashboard-card.js"

    if card_path.exists():
        try:
            await hass.http.async_register_static_paths(
                [
                    StaticPathConfig(
                        DASHBOARD_CARD_URL,
                        str(card_path),
                        True,
                    )
                ]
            )
        except RuntimeError:
            # The integration can be reloaded during development; the path may
            # already be registered from the original setup.
            pass

        add_extra_js_url(hass, DASHBOARD_CARD_RESOURCE_URL)

    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ParentVueConfigEntry,
) -> bool:
    """Set up ParentVUE from a config entry."""
    session = async_create_clientsession(
        hass,
        cookie_jar=aiohttp.CookieJar(),
        headers={
            "User-Agent": f"HomeAssistant-ParentVUE/{VERSION}",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    client = ParentVueClient(
        entry.data[CONF_BASE_URL],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        session,
    )

    coordinator = ParentVueDataUpdateCoordinator(
        hass,
        entry,
        client,
    )

    entry.runtime_data = ParentVueRuntimeData(
        client=client,
        coordinator=coordinator,
    )

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ParentVueConfigEntry,
) -> bool:
    """Unload a ParentVUE config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
