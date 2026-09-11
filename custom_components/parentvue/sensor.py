"""Sensor platform for ParentVUE."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from . import ParentVueConfigEntry
from .entity import ParentVueEntity
from .models import ParentVueClassMeeting, ParentVueCourse

_LOCAL_STATE_REFRESH = timedelta(minutes=1)


def _find_course(child, course_key: str) -> ParentVueCourse | None:
    if child is None:
        return None
    return next((course for course in child.courses if course.key == course_key), None)


def _now_naive_local() -> datetime:
    """Return HA local time without tzinfo for comparison to district wall-clock data."""
    return dt_util.now().replace(tzinfo=None)


def _current_meeting(child) -> ParentVueClassMeeting | None:
    if child is None:
        return None
    now = _now_naive_local()
    return next(
        (
            meeting
            for meeting in child.schedule
            if meeting.start <= now < meeting.end
        ),
        None,
    )


def _next_meeting(child) -> ParentVueClassMeeting | None:
    if child is None:
        return None
    now = _now_naive_local()
    return next(
        (meeting for meeting in child.schedule if meeting.start > now),
        None,
    )


class ParentVueSchoolSensor(ParentVueEntity, SensorEntity):
    """School sensor."""

    _attr_name = "School"

    def __init__(self, coordinator, child_key: str) -> None:
        super().__init__(coordinator, child_key)
        self._attr_unique_id = f"{child_key}_school"

    @property
    def native_value(self) -> str | None:
        return self.child.school if self.child else None


class ParentVueGradeLevelSensor(ParentVueEntity, SensorEntity):
    """Grade-level sensor."""

    _attr_name = "Grade level"

    def __init__(self, coordinator, child_key: str) -> None:
        super().__init__(coordinator, child_key)
        self._attr_unique_id = f"{child_key}_grade_level"

    @property
    def native_value(self) -> str | None:
        return self.child.grade_level if self.child else None


class ParentVueMissingAssignmentsSensor(ParentVueEntity, SensorEntity):
    """Aggregate missing-assignment count."""

    _attr_name = "Missing assignments"

    def __init__(self, coordinator, child_key: str) -> None:
        super().__init__(coordinator, child_key)
        self._attr_unique_id = f"{child_key}_missing_assignments"

    @property
    def native_value(self) -> int | None:
        child = self.child
        if child is None:
            return None
        values = [
            course.missing_assignments
            for course in child.courses
            if course.missing_assignments is not None
        ]
        return sum(values) if values else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        child = self.child
        if child is None:
            return {}
        return {
            "courses_with_missing": sum(
                1
                for course in child.courses
                if (course.missing_assignments or 0) > 0
            ),
            "course_count": len(child.courses),
        }


class _ScheduleSensorBase(ParentVueEntity, SensorEntity):
    """Base sensor using a cached daily schedule.

    The one-minute local timer only re-evaluates cached schedule data. It never
    contacts ParentVUE and therefore does not alter the two-hour server policy.
    """

    @property
    def available(self) -> bool:
        child = self.child
        return super().available and child is not None and child.schedule_available

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._async_local_tick,
                _LOCAL_STATE_REFRESH,
            )
        )

    @callback
    def _async_local_tick(self, now: datetime) -> None:
        self.async_write_ha_state()

    @staticmethod
    def _attributes(meeting: ParentVueClassMeeting | None) -> dict[str, Any]:
        if meeting is None:
            return {}
        return {
            "period": meeting.period,
            "teacher": meeting.teacher,
            "room": meeting.room,
            "start": meeting.start.isoformat(),
            "end": meeting.end.isoformat(),
            "is_online": meeting.is_online,
        }


class ParentVueCurrentClassSensor(_ScheduleSensorBase):
    """Current-class sensor."""

    _attr_name = "Current class"

    def __init__(self, coordinator, child_key: str) -> None:
        super().__init__(coordinator, child_key)
        self._attr_unique_id = f"{child_key}_current_class"

    @property
    def native_value(self) -> str:
        meeting = _current_meeting(self.child)
        return meeting.class_name if meeting else "No current class"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes(_current_meeting(self.child))


class ParentVueNextClassSensor(_ScheduleSensorBase):
    """Next-class sensor."""

    _attr_name = "Next class"

    def __init__(self, coordinator, child_key: str) -> None:
        super().__init__(coordinator, child_key)
        self._attr_unique_id = f"{child_key}_next_class"

    @property
    def native_value(self) -> str:
        meeting = _next_meeting(self.child)
        return meeting.class_name if meeting else "No more classes today"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes(_next_meeting(self.child))


class ParentVueCourseGradeSensor(ParentVueEntity, SensorEntity):
    """A Grade Book course sensor."""

    def __init__(self, coordinator, child_key: str, course: ParentVueCourse) -> None:
        super().__init__(coordinator, child_key)
        self._course_key = course.key
        self._attr_unique_id = f"{child_key}_course_{course.key}_grade"
        self._attr_name = f"{course.name} grade"

    @property
    def course(self) -> ParentVueCourse | None:
        return _find_course(self.child, self._course_key)

    @property
    def available(self) -> bool:
        return super().available and self.course is not None

    @property
    def native_value(self) -> str | float | None:
        course = self.course
        if course is None:
            return None
        if course.grade is not None:
            return course.grade
        if course.percentage is not None:
            return course.percentage
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        course = self.course
        if course is None:
            return {}

        attrs: dict[str, Any] = {
            "course_name": course.name,
            "teacher": course.teacher,
            "room": course.room,
            "period": course.period,
            "mark_period": course.mark_period,
            "missing_assignments": course.missing_assignments,
            "last_updated": course.last_updated,
        }
        if course.percentage is not None:
            attrs["percentage"] = course.percentage
        return attrs


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ParentVueConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up ParentVUE sensors."""
    coordinator = entry.runtime_data.coordinator
    known: set[str] = set()

    @callback
    def async_add_new_entities() -> None:
        entities: list[SensorEntity] = []

        for child in coordinator.data.children:
            child_entity_keys = {
                f"{child.key}:school": ParentVueSchoolSensor,
                f"{child.key}:grade_level": ParentVueGradeLevelSensor,
                f"{child.key}:missing": ParentVueMissingAssignmentsSensor,
                f"{child.key}:current_class": ParentVueCurrentClassSensor,
                f"{child.key}:next_class": ParentVueNextClassSensor,
            }

            for registry_key, entity_cls in child_entity_keys.items():
                if registry_key in known:
                    continue
                known.add(registry_key)
                entities.append(entity_cls(coordinator, child.key))

            for course in child.courses:
                registry_key = f"{child.key}:course:{course.key}"
                if registry_key in known:
                    continue
                known.add(registry_key)
                entities.append(
                    ParentVueCourseGradeSensor(
                        coordinator,
                        child.key,
                        course,
                    )
                )

        if entities:
            async_add_entities(entities)

    async_add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(async_add_new_entities))
