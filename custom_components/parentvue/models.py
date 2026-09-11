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


@dataclass(frozen=True, slots=True)
class ParentVueData:
    """All normalized data from one coordinator refresh."""

    children: tuple[ParentVueChild, ...]
    fetched_at: datetime

    def child_by_key(self, child_key: str) -> ParentVueChild | None:
        """Return a child by privacy-preserving key."""
        return next((child for child in self.children if child.key == child_key), None)
