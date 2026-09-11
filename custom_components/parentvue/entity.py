"""Base entities for ParentVUE."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import ParentVueDataUpdateCoordinator
from .models import ParentVueChild


class ParentVueEntity(CoordinatorEntity[ParentVueDataUpdateCoordinator]):
    """Base class for a ParentVUE child entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ParentVueDataUpdateCoordinator,
        child_key: str,
    ) -> None:
        super().__init__(coordinator)
        self._child_key = child_key
        child = self.child
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, child_key)},
            name=child.name if child else "ParentVUE student",
            manufacturer=MANUFACTURER,
            model=MODEL,
            configuration_url=coordinator.client.base_url,
        )

    @property
    def child(self) -> ParentVueChild | None:
        """Return current normalized child data."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.child_by_key(self._child_key)

    @property
    def available(self) -> bool:
        """Return availability."""
        return super().available and self.child is not None
