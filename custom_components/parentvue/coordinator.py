"""DataUpdateCoordinator for ParentVUE."""

from __future__ import annotations

from datetime import date
import logging
from time import monotonic

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    ParentVueConnectionError,
    ParentVueEndpointUnavailable,
    ParentVueError,
    ParentVueInvalidAuth,
    ParentVueNoStudents,
    ParentVueUnsupportedDeployment,
)
from .const import DOMAIN, MIN_NETWORK_INTERVAL, UPDATE_INTERVAL
from .models import ParentVueData

_LOGGER = logging.getLogger(__name__)


class ParentVueDataUpdateCoordinator(DataUpdateCoordinator[ParentVueData]):
    """Coordinate conservative ParentVUE website polling."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
            always_update=False,
        )
        self.client = client
        self._last_network_attempt: float | None = None

    async def _async_update_data(self) -> ParentVueData:
        """Fetch ParentVUE data, enforcing a hard two-hour network minimum."""
        now_mono = monotonic()

        if (
            self._last_network_attempt is not None
            and self.data is not None
            and now_mono - self._last_network_attempt
            < MIN_NETWORK_INTERVAL.total_seconds()
        ):
            _LOGGER.debug(
                "ParentVUE refresh requested inside the two-hour safety window; "
                "returning cached coordinator data"
            )
            return self.data

        self._last_network_attempt = now_mono

        try:
            local_day: date = dt_util.now().date()
            return await self.client.async_fetch_data(local_day)
        except ParentVueInvalidAuth as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="invalid_auth",
            ) from err
        except ParentVueNoStudents as err:
            raise UpdateFailed("No students are available in ParentVUE") from err
        except ParentVueEndpointUnavailable as err:
            raise UpdateFailed("A required ParentVUE endpoint is unavailable") from err
        except ParentVueUnsupportedDeployment as err:
            raise UpdateFailed("Unsupported ParentVUE website deployment") from err
        except ParentVueConnectionError as err:
            raise UpdateFailed("Unable to reach ParentVUE") from err
        except ParentVueError as err:
            raise UpdateFailed("ParentVUE returned an application error") from err
