"""Sensor platform for ParentVUE."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import ParentVueConfigEntry
from .entity import ParentVueEntity
from .models import ParentVueChild, ParentVueClassMeeting, ParentVueCourse

_LOCAL_STATE_REFRESH = timedelta(minutes=1)


def _find_course(child: ParentVueChild | None, course_key: str) -> ParentVueCourse | None:
    if child is None:
        return None
    return next((course for course in child.courses if course.key == course_key), None)


def _now_naive_local() -> datetime:
    """Return HA local time without tzinfo for district wall-clock comparisons."""
    return dt_util.now().replace(tzinfo=None)


def _current_meeting(child: ParentVueChild | None) -> ParentVueClassMeeting | None:
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


def _next_meeting(child: ParentVueChild | None) -> ParentVueClassMeeting | None:
    if child is None:
        return None
    now = _now_naive_local()
    return next(
        (meeting for meeting in child.schedule if meeting.start > now),
        None,
    )


def _meeting_attributes(meeting: ParentVueClassMeeting | None) -> dict[str, Any]:
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


class ParentVueStudentNameSensor(ParentVueEntity, SensorEntity):
    """Student-name sensor."""

    _attr_name = "Student name"

    def __init__(self, coordinator, child_key: str) -> None:
        super().__init__(coordinator, child_key)
        self._attr_unique_id = f"{child_key}_student_name"

    @property
    def native_value(self) -> str | None:
        return self.child.name if self.child else None


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


class ParentVueTodayScheduleSensor(ParentVueEntity, SensorEntity):
    """Today's complete cached schedule."""

    _attr_name = "Today's schedule"

    def __init__(self, coordinator, child_key: str) -> None:
        super().__init__(coordinator, child_key)
        self._attr_unique_id = f"{child_key}_today_schedule"

    @property
    def available(self) -> bool:
        child = self.child
        return super().available and child is not None and child.schedule_available

    @property
    def native_value(self) -> int | None:
        child = self.child
        if child is None or not child.schedule_available:
            return None
        return len(child.schedule)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        child = self.child
        if child is None:
            return {}
        return {
            "classes": [
                {
                    "name": meeting.class_name,
                    "period": meeting.period,
                    "teacher": meeting.teacher,
                    "room": meeting.room,
                    "start": meeting.start.isoformat(),
                    "end": meeting.end.isoformat(),
                    "is_online": meeting.is_online,
                }
                for meeting in child.schedule
            ],
            "schedule_available": child.schedule_available,
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
        return _meeting_attributes(_current_meeting(self.child))


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
        return _meeting_attributes(_next_meeting(self.child))


_MeetingGetter = Callable[[ParentVueChild | None], ParentVueClassMeeting | None]


class ParentVueMeetingFieldSensor(_ScheduleSensorBase):
    """A scalar field from the current or next cached class meeting."""

    def __init__(
        self,
        coordinator,
        child_key: str,
        *,
        scope: str,
        field: str,
        name: str,
        meeting_getter: _MeetingGetter,
    ) -> None:
        super().__init__(coordinator, child_key)
        self._scope = scope
        self._field = field
        self._meeting_getter = meeting_getter
        self._attr_name = name
        self._attr_unique_id = f"{child_key}_{scope}_class_{field}"

    @property
    def native_value(self) -> str | None:
        meeting = self._meeting_getter(self.child)
        if meeting is None:
            return None

        if self._field == "period":
            return meeting.period
        if self._field == "teacher":
            return meeting.teacher
        if self._field == "room":
            return meeting.room
        if self._field == "start":
            return meeting.start.strftime("%H:%M")
        if self._field == "end":
            return meeting.end.strftime("%H:%M")
        if self._field == "delivery":
            return "Online" if meeting.is_online else "In person"
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return _meeting_attributes(self._meeting_getter(self.child))


class ParentVueAttendanceTodaySensor(ParentVueEntity, SensorEntity):
    """Today's attendance-event collection."""

    _attr_name = "Attendance today"

    def __init__(self, coordinator, child_key: str) -> None:
        super().__init__(coordinator, child_key)
        self._attr_unique_id = f"{child_key}_attendance_today"

    @property
    def available(self) -> bool:
        child = self.child
        return (
            super().available
            and child is not None
            and child.attendance_today.available
        )

    @property
    def native_value(self) -> int | None:
        child = self.child
        if child is None or not child.attendance_today.available:
            return None
        return len(child.attendance_today.events)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        child = self.child
        if child is None:
            return {}
        attendance = child.attendance_today
        return {
            "absences": attendance.absences,
            "tardies": attendance.tardies,
            "excused": attendance.excused,
            "unexcused": attendance.unexcused,
            "dismissals": attendance.dismissals,
            "events": [
                {
                    "period": event.period,
                    "course": event.course,
                    "teacher": event.teacher,
                    "room": event.room,
                    "type": event.event_type,
                    "reason": event.reason,
                }
                for event in attendance.events
            ],
        }


class ParentVueAttendanceTodayCountSensor(ParentVueEntity, SensorEntity):
    """One numeric field from today's attendance."""

    def __init__(
        self,
        coordinator,
        child_key: str,
        *,
        field: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, child_key)
        self._field = field
        self._attr_name = name
        self._attr_unique_id = f"{child_key}_attendance_today_{field}"

    @property
    def available(self) -> bool:
        child = self.child
        return (
            super().available
            and child is not None
            and child.attendance_today.available
        )

    @property
    def native_value(self) -> int | None:
        child = self.child
        if child is None or not child.attendance_today.available:
            return None
        attendance = child.attendance_today
        if self._field == "events":
            return len(attendance.events)
        return int(getattr(attendance, self._field))


class ParentVueAttendanceYearSensor(ParentVueEntity, SensorEntity):
    """School-year attendance summary."""

    _attr_name = "Attendance school year"

    def __init__(self, coordinator, child_key: str) -> None:
        super().__init__(coordinator, child_key)
        self._attr_unique_id = f"{child_key}_attendance_year"

    @property
    def available(self) -> bool:
        child = self.child
        return (
            super().available
            and child is not None
            and child.attendance_year.available
        )

    @property
    def native_value(self) -> int | None:
        child = self.child
        if child is None or not child.attendance_year.available:
            return None
        return child.attendance_year.absences

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        child = self.child
        if child is None:
            return {}
        attendance = child.attendance_year
        return {
            "absences": attendance.absences,
            "excused_absences": attendance.excused_absences,
            "unexcused_absences": attendance.unexcused_absences,
            "tardies": attendance.tardies,
            "early_dismissals": attendance.early_dismissals,
        }


class ParentVueAttendanceYearCountSensor(ParentVueEntity, SensorEntity):
    """One cumulative school-year attendance total."""

    def __init__(
        self,
        coordinator,
        child_key: str,
        *,
        field: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, child_key)
        self._field = field
        self._attr_name = name
        self._attr_unique_id = f"{child_key}_attendance_year_{field}"

    @property
    def available(self) -> bool:
        child = self.child
        return (
            super().available
            and child is not None
            and child.attendance_year.available
        )

    @property
    def native_value(self) -> int | None:
        child = self.child
        if child is None or not child.attendance_year.available:
            return None
        value = getattr(child.attendance_year, self._field)
        return int(value) if value is not None else None


class ParentVueSynergyMailUnreadSensor(CoordinatorEntity, SensorEntity):
    """Account-level unread Synergy Mail count."""

    _attr_has_entity_name = True
    _attr_name = "Synergy Mail unread"

    def __init__(self, coordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_synergy_mail_unread"

    @property
    def available(self) -> bool:
        data = self.coordinator.data
        return (
            super().available
            and data is not None
            and data.synergy_mail_available
        )

    @property
    def native_value(self) -> int | None:
        data = self.coordinator.data
        if data is None or not data.synergy_mail_available:
            return None
        return data.synergy_mail_unread


class _CourseSensorBase(ParentVueEntity, SensorEntity):
    """Base class for one stable Grade Book course field."""

    def __init__(
        self,
        coordinator,
        child_key: str,
        course: ParentVueCourse,
        *,
        suffix: str,
        label: str,
    ) -> None:
        super().__init__(coordinator, child_key)
        self._course_key = course.key
        self._attr_unique_id = f"{child_key}_course_{course.key}_{suffix}"
        self._attr_name = f"{course.name} {label}"

    @property
    def course(self) -> ParentVueCourse | None:
        return _find_course(self.child, self._course_key)

    @property
    def available(self) -> bool:
        return super().available and self.course is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        course = self.course
        if course is None:
            return {}
        return {
            "course_name": course.name,
            "teacher": course.teacher,
            "room": course.room,
            "period": course.period,
            "mark_period": course.mark_period,
            "letter_grade": course.grade,
            "percentage": course.percentage,
            "missing_assignments": course.missing_assignments,
            "last_updated": course.last_updated,
            "is_online": course.is_online,
        }


class ParentVueCourseNameSensor(_CourseSensorBase):
    """Course-name sensor."""

    def __init__(self, coordinator, child_key: str, course: ParentVueCourse) -> None:
        super().__init__(
            coordinator,
            child_key,
            course,
            suffix="name",
            label="name",
        )

    @property
    def native_value(self) -> str | None:
        return self.course.name if self.course else None


class ParentVueCourseGradeSensor(_CourseSensorBase):
    """ParentVUE letter-grade sensor.

    The unique ID is retained from earlier versions for registry continuity.
    """

    def __init__(self, coordinator, child_key: str, course: ParentVueCourse) -> None:
        super().__init__(
            coordinator,
            child_key,
            course,
            suffix="grade",
            label="grade",
        )

    @property
    def native_value(self) -> str | None:
        course = self.course
        return course.grade if course else None


class ParentVueCoursePercentageSensor(_CourseSensorBase):
    """Exact ParentVUE percentage sensor when published."""

    _attr_native_unit_of_measurement = "%"

    def __init__(self, coordinator, child_key: str, course: ParentVueCourse) -> None:
        super().__init__(
            coordinator,
            child_key,
            course,
            suffix="percentage",
            label="percentage",
        )

    @property
    def native_value(self) -> float | None:
        course = self.course
        return course.percentage if course else None


class ParentVueCourseTeacherSensor(_CourseSensorBase):
    """Course-teacher sensor."""

    def __init__(self, coordinator, child_key: str, course: ParentVueCourse) -> None:
        super().__init__(
            coordinator,
            child_key,
            course,
            suffix="teacher",
            label="teacher",
        )

    @property
    def native_value(self) -> str | None:
        course = self.course
        return course.teacher if course else None


class ParentVueCourseRoomSensor(_CourseSensorBase):
    """Course-room sensor."""

    def __init__(self, coordinator, child_key: str, course: ParentVueCourse) -> None:
        super().__init__(
            coordinator,
            child_key,
            course,
            suffix="room",
            label="room",
        )

    @property
    def native_value(self) -> str | None:
        course = self.course
        return course.room if course else None


class ParentVueCoursePeriodSensor(_CourseSensorBase):
    """Course-period sensor."""

    def __init__(self, coordinator, child_key: str, course: ParentVueCourse) -> None:
        super().__init__(
            coordinator,
            child_key,
            course,
            suffix="period",
            label="period",
        )

    @property
    def native_value(self) -> str | None:
        course = self.course
        return course.period if course else None


class ParentVueCourseMarkingPeriodSensor(_CourseSensorBase):
    """Course-marking-period sensor."""

    def __init__(self, coordinator, child_key: str, course: ParentVueCourse) -> None:
        super().__init__(
            coordinator,
            child_key,
            course,
            suffix="marking_period",
            label="marking period",
        )

    @property
    def native_value(self) -> str | None:
        course = self.course
        return course.mark_period if course else None


class ParentVueCourseMissingAssignmentsSensor(_CourseSensorBase):
    """Per-course missing-assignment count."""

    def __init__(self, coordinator, child_key: str, course: ParentVueCourse) -> None:
        super().__init__(
            coordinator,
            child_key,
            course,
            suffix="missing_assignments",
            label="missing assignments",
        )

    @property
    def native_value(self) -> int | None:
        course = self.course
        return course.missing_assignments if course else None


class ParentVueCourseDeliverySensor(_CourseSensorBase):
    """Course delivery-mode sensor when today's schedule identifies it."""

    def __init__(self, coordinator, child_key: str, course: ParentVueCourse) -> None:
        super().__init__(
            coordinator,
            child_key,
            course,
            suffix="delivery",
            label="delivery",
        )

    @property
    def native_value(self) -> str | None:
        course = self.course
        if course is None or course.is_online is None:
            return None
        return "Online" if course.is_online else "In person"


class ParentVueCourseLastUpdatedSensor(_CourseSensorBase):
    """ParentVUE's published Grade Book update label."""

    def __init__(self, coordinator, child_key: str, course: ParentVueCourse) -> None:
        super().__init__(
            coordinator,
            child_key,
            course,
            suffix="last_updated",
            label="last updated",
        )

    @property
    def native_value(self) -> str | None:
        course = self.course
        return course.last_updated if course else None


_MEETING_FIELDS: tuple[tuple[str, str], ...] = (
    ("period", "period"),
    ("teacher", "teacher"),
    ("room", "room"),
    ("start", "start time"),
    ("end", "end time"),
    ("delivery", "delivery"),
)

_COURSE_ENTITY_CLASSES: tuple[type[_CourseSensorBase], ...] = (
    ParentVueCourseNameSensor,
    ParentVueCourseGradeSensor,
    ParentVueCoursePercentageSensor,
    ParentVueCourseTeacherSensor,
    ParentVueCourseRoomSensor,
    ParentVueCoursePeriodSensor,
    ParentVueCourseMarkingPeriodSensor,
    ParentVueCourseMissingAssignmentsSensor,
    ParentVueCourseDeliverySensor,
    ParentVueCourseLastUpdatedSensor,
)


_ATTENDANCE_TODAY_FIELDS: tuple[tuple[str, str], ...] = (
    ("events", "Attendance today event count"),
    ("absences", "Attendance today absences"),
    ("tardies", "Attendance today tardies"),
    ("excused", "Attendance today excused"),
    ("unexcused", "Attendance today unexcused"),
    ("dismissals", "Attendance today dismissals"),
)

_ATTENDANCE_YEAR_FIELDS: tuple[tuple[str, str], ...] = (
    ("absences", "Attendance year absences"),
    ("excused_absences", "Attendance year excused absences"),
    ("unexcused_absences", "Attendance year unexcused absences"),
    ("tardies", "Attendance year tardies"),
    ("early_dismissals", "Attendance year early dismissals"),
)


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
                f"{child.key}:student_name": ParentVueStudentNameSensor,
                f"{child.key}:school": ParentVueSchoolSensor,
                f"{child.key}:grade_level": ParentVueGradeLevelSensor,
                f"{child.key}:missing": ParentVueMissingAssignmentsSensor,
                f"{child.key}:today_schedule": ParentVueTodayScheduleSensor,
                f"{child.key}:current_class": ParentVueCurrentClassSensor,
                f"{child.key}:next_class": ParentVueNextClassSensor,
                f"{child.key}:attendance_today": ParentVueAttendanceTodaySensor,
                f"{child.key}:attendance_year": ParentVueAttendanceYearSensor,
            }

            for registry_key, entity_cls in child_entity_keys.items():
                if registry_key in known:
                    continue
                known.add(registry_key)
                entities.append(entity_cls(coordinator, child.key))

            for scope, meeting_getter in (
                ("current", _current_meeting),
                ("next", _next_meeting),
            ):
                for field, label in _MEETING_FIELDS:
                    registry_key = f"{child.key}:{scope}:{field}"
                    if registry_key in known:
                        continue
                    known.add(registry_key)
                    entities.append(
                        ParentVueMeetingFieldSensor(
                            coordinator,
                            child.key,
                            scope=scope,
                            field=field,
                            name=f"{scope.title()} class {label}",
                            meeting_getter=meeting_getter,
                        )
                    )

            for field, name in _ATTENDANCE_TODAY_FIELDS:
                registry_key = f"{child.key}:attendance_today:{field}"
                if registry_key not in known:
                    known.add(registry_key)
                    entities.append(
                        ParentVueAttendanceTodayCountSensor(
                            coordinator,
                            child.key,
                            field=field,
                            name=name,
                        )
                    )

            for field, name in _ATTENDANCE_YEAR_FIELDS:
                registry_key = f"{child.key}:attendance_year:{field}"
                if registry_key not in known:
                    known.add(registry_key)
                    entities.append(
                        ParentVueAttendanceYearCountSensor(
                            coordinator,
                            child.key,
                            field=field,
                            name=name,
                        )
                    )

            for course in child.courses:
                for entity_cls in _COURSE_ENTITY_CLASSES:
                    suffix = entity_cls.__name__
                    registry_key = f"{child.key}:course:{course.key}:{suffix}"
                    if registry_key in known:
                        continue
                    known.add(registry_key)
                    entities.append(entity_cls(coordinator, child.key, course))

        account_registry_key = f"{entry.entry_id}:synergy_mail_unread"
        if account_registry_key not in known:
            known.add(account_registry_key)
            entities.append(
                ParentVueSynergyMailUnreadSensor(
                    coordinator,
                    entry.entry_id,
                )
            )

        if entities:
            async_add_entities(entities)

    async_add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(async_add_new_entities))
