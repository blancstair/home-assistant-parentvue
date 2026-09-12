"""Normalized data models for ParentVUE."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ParentVueClassMeeting:
    """A single class meeting from the ParentVUE daily schedule."""

    class_name: str
    period: str | None
    teacher: str | None
    room: str | None
    start: datetime
    end: datetime
    is_online: bool = False


@dataclass(frozen=True, slots=True)
class ParentVueCourse:
    """A course from the ParentVUE Grade Book."""

    key: str
    name: str
    teacher: str | None
    room: str | None
    period: str | None
    mark_period: str | None
    grade: str | None
    percentage: float | None
    missing_assignments: int | None
    last_updated: str | None
    is_online: bool | None = None


@dataclass(frozen=True, slots=True)
class ParentVueAttendanceEvent:
    """One normalized ParentVUE attendance event."""

    period: str | None
    course: str | None
    teacher: str | None
    room: str | None
    event_type: str | None
    reason: str | None


@dataclass(frozen=True, slots=True)
class ParentVueAttendanceDay:
    """Normalized attendance information for one school day."""

    available: bool
    events: tuple[ParentVueAttendanceEvent, ...]
    absences: int
    tardies: int
    excused: int
    unexcused: int
    dismissals: int


@dataclass(frozen=True, slots=True)
class ParentVueAttendanceYear:
    """Cumulative school-year attendance totals when ParentVUE publishes them."""

    available: bool
    absences: int | None
    excused_absences: int | None
    unexcused_absences: int | None
    tardies: int | None
    early_dismissals: int | None


@dataclass(frozen=True, slots=True)
class ParentVueChild:
    """A child available to a ParentVUE parent account."""

    key: str
    account_index: int
    name: str
    school: str | None
    grade_level: str | None
    courses: tuple[ParentVueCourse, ...]
    schedule: tuple[ParentVueClassMeeting, ...]
    schedule_available: bool
    attendance_today: ParentVueAttendanceDay
    attendance_year: ParentVueAttendanceYear


@dataclass(frozen=True, slots=True)
class ParentVueData:
    """All normalized data from one coordinator refresh."""

    children: tuple[ParentVueChild, ...]
    fetched_at: datetime
    synergy_mail_unread: int | None = None
    synergy_mail_available: bool = False

    def child_by_key(self, child_key: str) -> ParentVueChild | None:
        """Return a child by privacy-preserving key."""
        return next((child for child in self.children if child.key == child_key), None)
