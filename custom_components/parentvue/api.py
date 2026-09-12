"""Website client for Edupoint ParentVUE.

This client intentionally targets the authenticated ParentVUE website workflow,
not the legacy StudentVUE mobile SOAP login.  It keeps all HTML/JSON parsing
inside this module so Home Assistant entities consume only normalized models.

No credentials, cookies, raw pages, or raw API responses are logged.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import date, datetime
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

import aiohttp
from bs4 import BeautifulSoup, Tag

from .const import BROWSER_ACCEPT, BROWSER_USER_AGENT
from .models import (
    ParentVueAttendanceDay,
    ParentVueAttendanceEvent,
    ParentVueAttendanceYear,
    ParentVueChild,
    ParentVueClassMeeting,
    ParentVueCourse,
    ParentVueData,
)

_LOGGER = logging.getLogger(__name__)

_LOGIN_PATH = "/PXP2_Login_Parent.aspx?regenerateSessionId=true"
_HOME_PATH = "/Home_PXP2.aspx"
_GRADEBOOK_PATH = "/PXP2_Gradebook.aspx"
_ATTENDANCE_PATH = "/PXP2_Attendance.aspx"
_ATTENDANCE_DAY_PATH = "/service/PXP2Communication.asmx/AttGetCalendarDay"
_DAY_CONTENT_PATH = "/Service/PXP2WebCommonService.asmx/DayContent"

_RE_MISSING = re.compile(r"(\d+)\s+Missing\s+Assignment", re.IGNORECASE)
_RE_GRADE_PREFIX = re.compile(r"^\s*Grade\s*:?\s*", re.IGNORECASE)
_RE_ROOM_PREFIX = re.compile(r"^\s*Room\s*:?\s*", re.IGNORECASE)
_RE_LAST_UPDATE = re.compile(r"^\s*Last\s+Update\s*:?\s*", re.IGNORECASE)


class ParentVueError(Exception):
    """Base ParentVUE error."""


class ParentVueInvalidAuth(ParentVueError):
    """Credentials were rejected."""


class ParentVueConnectionError(ParentVueError):
    """The ParentVUE server could not be reached."""


class ParentVueUnsupportedDeployment(ParentVueError):
    """The server is not a supported ParentVUE website deployment."""


class ParentVueEndpointUnavailable(ParentVueError):
    """A required ParentVUE website endpoint is unavailable."""


class ParentVueSessionExpired(ParentVueError):
    """The authenticated ParentVUE web session is no longer valid."""


class ParentVueNoStudents(ParentVueError):
    """The ParentVUE account has no discoverable students."""


def normalize_base_url(value: str) -> str:
    """Normalize a user-supplied ParentVUE URL to scheme + host.

    Credentials are intentionally restricted to HTTPS deployments.
    """
    value = value.strip()
    parsed = urlsplit(value)

    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValueError("ParentVUE URL must be a valid HTTPS URL")

    # Strip any path/query a user may have pasted from a login page.
    port = f":{parsed.port}" if parsed.port and parsed.port != 443 else ""
    return urlunsplit(("https", f"{parsed.hostname}{port}", "", "", ""))


def _privacy_key(*parts: str) -> str:
    """Create a stable key without exposing the underlying identifier."""
    material = "\x1f".join(parts).encode("utf-8", errors="replace")
    return hashlib.sha256(material).hexdigest()[:24]


def _text(node: Tag | None) -> str | None:
    if node is None:
        return None
    value = " ".join(node.stripped_strings).strip()
    return value or None


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value or value.casefold() in {"n/a", "na", "--", "-"}:
        return None
    return value


def _percentage(value: str | None) -> float | None:
    """Convert '94.5%' to 94.5 when available."""
    if not value:
        return None
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*%", value)
    return float(match.group(1)) if match else None


def _grade_label(value: str | None) -> str | None:
    """Return ParentVUE's grade label without an embedded percentage.

    ParentVUE remains authoritative for the grade label; the integration never
    calculates a letter grade from the percentage.
    """
    if not value:
        return None
    label = re.sub(r"-?\d+(?:\.\d+)?\s*%", "", value)
    label = re.sub(r"^[\s·•|:/-]+|[\s·•|:/-]+$", "", label).strip()
    return _normalize_optional(label)


class ParentVueClient:
    """Client for the authenticated ParentVUE website."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        self.base_url = normalize_base_url(base_url)
        self._username = username
        self._password = password
        self._session = session
        self._last_home_html: str | None = None

    def _url(self, path: str) -> str:
        return urljoin(f"{self.base_url}/", path.lstrip("/"))

    @staticmethod
    def _browser_headers() -> dict[str, str]:
        """Return browser-compatible headers required by ParentVUE."""
        return {
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": BROWSER_ACCEPT,
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def _get_text(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        referer: str | None = None,
        allow_login_page: bool = False,
    ) -> tuple[str, str]:
        headers = self._browser_headers()
        headers["Upgrade-Insecure-Requests"] = "1"
        if referer:
            headers["Referer"] = referer

        try:
            async with self._session.get(
                self._url(path),
                params=params,
                headers=headers,
                allow_redirects=True,
            ) as response:
                if response.status == 404:
                    raise ParentVueEndpointUnavailable("ParentVUE endpoint not found")
                if response.status >= 500:
                    raise ParentVueConnectionError("ParentVUE server returned an error")
                if response.status in (401, 403):
                    if allow_login_page:
                        raise ParentVueInvalidAuth("ParentVUE rejected authentication")
                    raise ParentVueSessionExpired("ParentVUE session was rejected")
                response.raise_for_status()
                body = await response.text(errors="replace")
                final_url = str(response.url)
        except ParentVueError:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            raise ParentVueConnectionError("Unable to reach ParentVUE") from err

        if not allow_login_page and self._looks_like_login(final_url, body):
            raise ParentVueSessionExpired("ParentVUE session expired")

        return body, final_url

    async def _post_form(
        self,
        url: str,
        data: dict[str, str],
        *,
        referer: str,
    ) -> tuple[str, str]:
        try:
            async with self._session.post(
                url,
                data=data,
                headers={
                    **self._browser_headers(),
                    "Referer": referer,
                    "Origin": self.base_url,
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Upgrade-Insecure-Requests": "1",
                },
                allow_redirects=True,
            ) as response:
                if response.status >= 500:
                    raise ParentVueConnectionError("ParentVUE server returned an error")
                if response.status in (401, 403):
                    raise ParentVueInvalidAuth("ParentVUE rejected authentication")
                response.raise_for_status()
                body = await response.text(errors="replace")
                final_url = str(response.url)
        except ParentVueError:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            raise ParentVueConnectionError("Unable to reach ParentVUE") from err

        return body, final_url

    async def _post_json(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        child_index: int,
        referer_path: str,
    ) -> Any:
        headers = {
            **self._browser_headers(),
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "AGU": str(child_index),
            "CURRENT_WEB_PORTAL": "ParentVUE",
            "Content-Type": "application/json; charset=UTF-8",
            "Origin": self.base_url,
            "Referer": self._url(referer_path),
            "X-Requested-With": "XMLHttpRequest",
        }

        try:
            async with self._session.post(
                self._url(path),
                json=payload,
                headers=headers,
                allow_redirects=True,
            ) as response:
                if response.status == 404:
                    raise ParentVueEndpointUnavailable("ParentVUE endpoint not found")
                if response.status >= 500:
                    raise ParentVueConnectionError("ParentVUE server returned an error")
                if response.status in (401, 403):
                    raise ParentVueSessionExpired("ParentVUE session expired")
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "")
                if "json" not in content_type.casefold():
                    body = await response.text(errors="replace")
                    if self._looks_like_login(str(response.url), body):
                        raise ParentVueSessionExpired("ParentVUE session expired")
                    raise ParentVueUnsupportedDeployment(
                        "ParentVUE returned an unexpected response type"
                    )
                result = await response.json(content_type=None)
        except ParentVueError:
            raise
        except (aiohttp.ClientError, TimeoutError, json.JSONDecodeError) as err:
            raise ParentVueConnectionError("Unable to read ParentVUE response") from err

        if isinstance(result, dict):
            d_value = result.get("d")
            if isinstance(d_value, str) and "INVALID_CONTEXT" in d_value:
                raise ParentVueSessionExpired("ParentVUE session expired")
            if isinstance(d_value, dict) and d_value.get("Error"):
                # Do not place the server-provided error in logs/exceptions because
                # it may contain account/student context.
                raise ParentVueError("ParentVUE returned an application error")

        return result

    @staticmethod
    def _looks_like_login(final_url: str, body: str) -> bool:
        """Return True only when the response is actually a ParentVUE login page."""
        path = urlsplit(final_url).path.casefold()
        if "pxp2_login_parent.aspx" in path:
            return True

        soup = BeautifulSoup(body, "html.parser")

        # The authenticated ParentVUE shell contains student selectors. Their
        # presence is stronger evidence than generic account/password controls
        # that may also exist elsewhere in an authenticated page.
        if soup.select_one(".student-info[data-agu]") is not None:
            return False

        # For unusual deployments where the URL is preserved across a redirect,
        # require username + password to belong to the SAME form. The previous
        # global search could combine unrelated controls and return a false
        # positive after a successful login.
        for password_input in soup.find_all("input", {"type": "password"}):
            if not isinstance(password_input, Tag):
                continue
            form = password_input.find_parent("form")
            if not isinstance(form, Tag):
                continue
            if form.find(
                "input",
                {"name": re.compile("username", re.IGNORECASE)},
            ) is not None:
                return True

        return False

    @staticmethod
    def _login_form(body: str) -> tuple[Tag, Tag, Tag, Tag | None]:
        soup = BeautifulSoup(body, "html.parser")

        password_input = soup.find("input", {"type": "password"})
        if not isinstance(password_input, Tag):
            raise ParentVueUnsupportedDeployment(
                "ParentVUE password field was not found"
            )

        form = password_input.find_parent("form")
        if not isinstance(form, Tag):
            raise ParentVueUnsupportedDeployment("ParentVUE login form was not found")

        username_input: Tag | None = None
        for candidate in form.find_all("input"):
            if not isinstance(candidate, Tag) or not candidate.get("name"):
                continue
            field_type = str(candidate.get("type", "text")).casefold()
            label = f"{candidate.get('name', '')} {candidate.get('id', '')}".casefold()
            if field_type in {"text", "email"} and (
                "user" in label or "login" in label or "account" in label
            ):
                username_input = candidate
                break

        if username_input is None:
            raise ParentVueUnsupportedDeployment(
                "ParentVUE username field was not found"
            )

        submit: Tag | None = None
        for candidate in form.find_all(["input", "button"]):
            if not isinstance(candidate, Tag) or not candidate.get("name"):
                continue
            field_type = str(candidate.get("type", "")).casefold()
            if field_type not in {"submit", "button"}:
                continue
            label = " ".join(
                str(candidate.get(key, ""))
                for key in ("name", "id", "value")
            ).casefold()
            if "login" in label or "log in" in label or "sign in" in label:
                submit = candidate
                break

        return form, username_input, password_input, submit

    def _parse_children(self, body: str) -> list[dict[str, Any]]:
        """Parse student selectors, hashing raw student IDs immediately."""
        soup = BeautifulSoup(body, "html.parser")
        children: list[dict[str, Any]] = []

        for element in soup.select(".student-info[data-agu]"):
            raw_index = str(element.get("data-agu", "")).strip()
            if not raw_index.isdigit():
                continue

            name = _text(element.select_one(".student-name"))
            if not name:
                continue

            school = _text(element.select_one(".school"))
            raw_student_id = _text(element.select_one(".student-id"))

            if raw_student_id:
                child_key = _privacy_key(self.base_url, raw_student_id)
            else:
                # Fallback only.  The raw name/school are not retained in the key.
                child_key = _privacy_key(
                    self.base_url, name, school or "", raw_index
                )

            children.append(
                {
                    "key": child_key,
                    "index": int(raw_index),
                    "name": name,
                    "school": school,
                }
            )

        children.sort(key=lambda item: item["index"])
        return children

    async def async_login(self) -> list[dict[str, Any]]:
        """Authenticate through the normal ParentVUE website."""
        login_html, login_url = await self._get_text(
            _LOGIN_PATH, allow_login_page=True
        )
        form, username_input, password_input, submit = self._login_form(login_html)

        data: dict[str, str] = {}
        for field in form.find_all("input"):
            if not isinstance(field, Tag) or not field.get("name"):
                continue
            field_type = str(field.get("type", "text")).casefold()
            if field_type in {"hidden", "submit"}:
                data[str(field["name"])] = str(field.get("value", ""))

        data[str(username_input["name"])] = self._username
        data[str(password_input["name"])] = self._password
        if submit is not None and submit.get("name"):
            data[str(submit["name"])] = str(submit.get("value", "Login"))

        action = str(form.get("action", "")) or login_url
        post_url = urljoin(login_url, action)

        _LOGGER.debug(
            "Submitting ParentVUE website login form to path %s; cookie names before submit: %s",
            urlsplit(post_url).path,
            sorted(cookie.key for cookie in self._session.cookie_jar),
        )

        home_html, final_url = await self._post_form(
            post_url, data, referer=login_url
        )

        children = self._parse_children(home_html)
        returned_to_login = self._looks_like_login(final_url, home_html)
        final_path = urlsplit(final_url).path
        _LOGGER.debug(
            "ParentVUE login result path: %s; returned_to_login=%s; "
            "child_selector_count=%s; cookie names after submit: %s",
            final_path,
            returned_to_login,
            len(children),
            sorted(cookie.key for cookie in self._session.cookie_jar),
        )

        if returned_to_login:
            raise ParentVueInvalidAuth(
                "ParentVUE returned to the login page after authentication"
            )

        if not children:
            if "home_pxp2.aspx" in final_path.casefold():
                raise ParentVueNoStudents(
                    "No students were found for this ParentVUE account"
                )
            raise ParentVueUnsupportedDeployment(
                "ParentVUE authenticated landing page was not recognized"
            )

        self._last_home_html = home_html
        return children

    async def async_validate(self) -> int:
        """Validate login and the website Grade Book endpoint.

        Returns the discovered child count.  No student data is returned.
        """
        children = await self.async_login()
        first = children[0]

        gradebook_html, final_url = await self._get_text(
            _GRADEBOOK_PATH,
            params={"AGU": first["index"]},
            referer=self._url(_HOME_PATH),
        )

        if "pxp2_gradebook.aspx" not in urlsplit(final_url).path.casefold():
            raise ParentVueEndpointUnavailable(
                "ParentVUE Grade Book endpoint is unavailable"
            )

        soup = BeautifulSoup(gradebook_html, "html.parser")
        # An empty grade book is valid, but this marker verifies that we reached
        # the expected ParentVUE Grade Book implementation.
        if (
            soup.select_one(".student-grade-description") is None
            and "PXP.GBFocusData" not in gradebook_html
            and soup.select_one(".gb-class-row") is None
        ):
            raise ParentVueUnsupportedDeployment(
                "ParentVUE Grade Book structure was not recognized"
            )

        return len(children)

    def _parse_gradebook(
        self,
        body: str,
        *,
        child_key: str,
        child_index: int,
        fallback_name: str,
        fallback_school: str | None,
    ) -> tuple[str, str | None, str | None, tuple[ParentVueCourse, ...]]:
        """Parse the server-rendered Grade Book summary."""
        soup = BeautifulSoup(body, "html.parser")

        selector = soup.select_one(f'.student-info[data-agu="{child_index}"]')
        name = _text(selector.select_one(".student-name")) if selector else None
        school = _text(selector.select_one(".school")) if selector else None

        grade_level = _text(soup.select_one(".student-grade-description"))
        if grade_level:
            grade_level = _RE_GRADE_PREFIX.sub("", grade_level).strip() or None

        courses: list[ParentVueCourse] = []

        # Use only the presentation rows. ParentVUE also emits print/detail rows
        # with the same gb-class-row class.
        for header in soup.select(".gb-class-header.gb-class-row"):
            raw_course_id = str(header.get("data-guid", "")).strip()
            title = _text(header.select_one(".course-title"))
            if not title:
                continue

            teacher = _text(header.select_one(".teacher.hide-for-screen"))
            if teacher is None:
                teacher = _text(header.select_one(".teacher"))

            room = _text(header.select_one(".teacher-room"))
            if room:
                room = _RE_ROOM_PREFIX.sub("", room).strip() or None

            mark_row: Tag | None = None
            sibling = header.find_next_sibling()
            while isinstance(sibling, Tag):
                classes = set(sibling.get("class", []))
                if "gb-class-header" in classes:
                    break
                if (
                    "gb-class-row" in classes
                    and str(sibling.get("data-guid", "")) == raw_course_id
                ):
                    mark_row = sibling
                    break
                sibling = sibling.find_next_sibling()

            mark_period: str | None = None
            grade: str | None = None
            percentage: float | None = None
            missing: int | None = None
            last_updated: str | None = None

            if mark_row is not None:
                mark_period = _normalize_optional(_text(mark_row.select_one(".course-markperiod")))
                raw_grade = _text(mark_row.select_one(".mark"))
                grade = _grade_label(raw_grade)

                # Some ParentVUE deployments render the percentage directly in
                # the summary mark; retain it when present. If the letter and
                # percentage are separate, look only in elements explicitly
                # identified as percentage/percent fields rather than scanning
                # arbitrary row text.
                percentage = _percentage(raw_grade)
                if percentage is None:
                    percent_node = mark_row.select_one(
                        "[class*='percentage'], [class*='percent']"
                    )
                    percentage = _percentage(_text(percent_node))

                less_emphasis = _text(mark_row.select_one(".class-item-lessemphasis"))
                if less_emphasis:
                    missing_match = _RE_MISSING.search(less_emphasis)
                    if missing_match:
                        missing = int(missing_match.group(1))

                last_updated = _text(mark_row.select_one(".last-update"))
                if last_updated:
                    last_updated = _RE_LAST_UPDATE.sub("", last_updated).strip() or None

            course_key = _privacy_key(
                self.base_url,
                child_key,
                raw_course_id or title,
            )

            courses.append(
                ParentVueCourse(
                    key=course_key,
                    name=title,
                    teacher=teacher,
                    room=room,
                    period=None,
                    mark_period=mark_period,
                    grade=grade,
                    percentage=percentage,
                    missing_assignments=missing,
                    last_updated=last_updated,
                    is_online=None,
                )
            )

        return (
            name or fallback_name,
            school or fallback_school,
            grade_level,
            tuple(courses),
        )

    async def _fetch_schedule(
        self,
        *,
        child_index: int,
        day: date,
    ) -> tuple[ParentVueClassMeeting, ...]:
        result = await self._post_json(
            _DAY_CONTENT_PATH,
            {"date": day.strftime("%m/%d/%Y")},
            child_index=child_index,
            referer_path=f"/PXP2_Calendar.aspx?AGU={child_index}",
        )

        if not isinstance(result, dict) or "d" not in result:
            raise ParentVueUnsupportedDeployment(
                "ParentVUE schedule response was not recognized"
            )

        payload = result["d"]
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError as err:
                raise ParentVueUnsupportedDeployment(
                    "ParentVUE schedule payload was malformed"
                ) from err

        if not isinstance(payload, dict):
            raise ParentVueUnsupportedDeployment(
                "ParentVUE schedule payload was not recognized"
            )

        meetings: list[ParentVueClassMeeting] = []

        for school in payload.get("schools") or []:
            if not isinstance(school, dict):
                continue
            for item in school.get("classes") or []:
                if not isinstance(item, dict):
                    continue

                name = str(item.get("className") or "").strip()
                start_info = item.get("startInfo")
                end_info = item.get("endInfo")
                if not name or not isinstance(start_info, dict) or not isinstance(end_info, dict):
                    continue

                try:
                    start = datetime(
                        int(start_info["year"]),
                        int(start_info["month"]),
                        int(start_info["day"]),
                        int(start_info["hours"]),
                        int(start_info["minutes"]),
                        int(start_info.get("seconds", 0)),
                    )
                    end = datetime(
                        int(end_info["year"]),
                        int(end_info["month"]),
                        int(end_info["day"]),
                        int(end_info["hours"]),
                        int(end_info["minutes"]),
                        int(end_info.get("seconds", 0)),
                    )
                except (KeyError, TypeError, ValueError):
                    continue

                meetings.append(
                    ParentVueClassMeeting(
                        class_name=name,
                        period=_normalize_optional(str(item.get("period") or "")),
                        teacher=_normalize_optional(str(item.get("teacherName") or "")),
                        room=_normalize_optional(str(item.get("roomName") or "")),
                        start=start,
                        end=end,
                        is_online=bool(item.get("isOnlineCourse", False)),
                    )
                )

        meetings.sort(key=lambda meeting: meeting.start)
        return tuple(meetings)

    @staticmethod
    def _enrich_courses_with_schedule(
        courses: tuple[ParentVueCourse, ...],
        schedule: tuple[ParentVueClassMeeting, ...],
    ) -> tuple[ParentVueCourse, ...]:
        """Add period/room hints from today's schedule without changing IDs."""
        if not schedule:
            return courses

        by_name: dict[str, list[ParentVueClassMeeting]] = {}
        for meeting in schedule:
            by_name.setdefault(meeting.class_name.casefold().strip(), []).append(meeting)

        enriched: list[ParentVueCourse] = []
        for course in courses:
            matches = by_name.get(course.name.casefold().strip(), [])
            meeting = matches[0] if len(matches) == 1 else None
            if meeting is None:
                enriched.append(course)
                continue

            enriched.append(
                ParentVueCourse(
                    key=course.key,
                    name=course.name,
                    teacher=course.teacher or meeting.teacher,
                    room=course.room or meeting.room,
                    period=meeting.period,
                    mark_period=course.mark_period,
                    grade=course.grade,
                    percentage=course.percentage,
                    missing_assignments=course.missing_assignments,
                    last_updated=course.last_updated,
                    is_online=meeting.is_online,
                )
            )

        return tuple(enriched)


    @staticmethod
    def _parse_synergy_mail_unread(body: str | None) -> tuple[int | None, bool]:
        """Parse the Synergy Mail navigation badge from authenticated HTML.

        ParentVUE displays an unread indicator beside the Synergy Mail navigation
        item. Only the count is retained; message subjects, senders and bodies are
        deliberately ignored.
        """
        if not body:
            return None, False

        soup = BeautifulSoup(body, "html.parser")
        labels = [
            node
            for node in soup.find_all(string=re.compile(r"\bSynergy\s+Mail\b", re.IGNORECASE))
            if str(node).strip()
        ]
        if not labels:
            return None, False

        badge_tokens = ("badge", "count", "unread", "notification")

        for label in labels:
            element = label.parent if isinstance(label.parent, Tag) else None
            depth = 0
            while isinstance(element, Tag) and depth < 5:
                # First, inspect explicit data/ARIA metadata.
                for attr_name, attr_value in element.attrs.items():
                    name = str(attr_name).casefold()
                    if not any(token in name for token in badge_tokens):
                        continue
                    values = (
                        attr_value
                        if isinstance(attr_value, list)
                        else [attr_value]
                    )
                    for value in values:
                        match = re.search(r"\b(\d+)\b", str(value))
                        if match:
                            return int(match.group(1)), True

                # Then inspect descendants whose class/id clearly denotes a badge.
                for candidate in element.find_all(True):
                    identity = " ".join(
                        [
                            str(candidate.get("id", "")),
                            " ".join(str(x) for x in candidate.get("class", [])),
                            str(candidate.get("aria-label", "")),
                        ]
                    ).casefold()
                    if not any(token in identity for token in badge_tokens):
                        continue
                    text = _text(candidate)
                    if text:
                        match = re.search(r"\b(\d+)\b", text)
                        if match:
                            return int(match.group(1)), True

                # Some themes render "Synergy Mail 3" directly in the nav item.
                text = _text(element)
                if text and len(text) <= 120:
                    match = re.search(
                        r"\bSynergy\s+Mail\b\D{0,30}\b(\d+)\b",
                        text,
                        re.IGNORECASE,
                    )
                    if match:
                        return int(match.group(1)), True

                element = element.parent if isinstance(element.parent, Tag) else None
                depth += 1

        # The navigation item exists but no unread badge is rendered. ParentVUE
        # uses the badge as the unread indicator, so its absence represents zero.
        return 0, True

    @staticmethod
    def _unwrap_json_payload(result: Any) -> Any:
        """Unwrap ASP.NET JSON responses without logging private content."""
        payload = result.get("d") if isinstance(result, dict) and "d" in result else result
        if isinstance(payload, str):
            try:
                return json.loads(payload)
            except json.JSONDecodeError:
                return None
        return payload

    @staticmethod
    def _normalized_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
        return {
            re.sub(r"[^a-z0-9]", "", str(key).casefold()): value
            for key, value in mapping.items()
        }

    @staticmethod
    def _attendance_value(
        normalized: dict[str, Any],
        keys: tuple[str, ...],
    ) -> str | None:
        for key in keys:
            value = normalized.get(key)
            if value is None:
                continue
            if isinstance(value, (str, int, float)):
                text = str(value).strip()
                if text:
                    return text
        return None

    @classmethod
    def _parse_attendance_day(cls, result: Any) -> ParentVueAttendanceDay:
        """Normalize a ParentVUE AttGetCalendarDay response conservatively."""
        payload = cls._unwrap_json_payload(result)
        if not isinstance(payload, (dict, list)):
            return ParentVueAttendanceDay(False, (), 0, 0, 0, 0, 0)

        candidate_dicts: list[dict[str, Any]] = []

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                normalized = cls._normalized_mapping(value)
                key_blob = " ".join(normalized)
                if (
                    "attendance" in key_blob
                    or "reason" in key_blob
                    or (
                        "period" in normalized
                        and any(
                            key in normalized
                            for key in (
                                "course",
                                "coursename",
                                "class",
                                "classname",
                                "teacher",
                                "teachername",
                            )
                        )
                    )
                ):
                    candidate_dicts.append(value)
                for nested in value.values():
                    walk(nested)
            elif isinstance(value, list):
                for nested in value:
                    walk(nested)

        walk(payload)

        events: list[ParentVueAttendanceEvent] = []
        seen: set[tuple[str | None, ...]] = set()

        for candidate in candidate_dicts:
            normalized = cls._normalized_mapping(candidate)
            period = cls._attendance_value(
                normalized,
                ("period", "periodname", "periodnumber"),
            )
            course = cls._attendance_value(
                normalized,
                ("course", "coursename", "class", "classname"),
            )
            teacher = cls._attendance_value(
                normalized,
                ("teacher", "teachername"),
            )
            room = cls._attendance_value(
                normalized,
                ("room", "roomname"),
            )
            event_type = cls._attendance_value(
                normalized,
                (
                    "attendancetype",
                    "attendancereasontype",
                    "reasontype",
                    "attendancecode",
                    "type",
                ),
            )
            reason = cls._attendance_value(
                normalized,
                (
                    "attendancereason",
                    "reason",
                    "reasonname",
                    "attendancedescription",
                    "description",
                ),
            )

            # Do not manufacture an event from structural container dictionaries.
            if not any((event_type, reason)):
                continue

            signature = (period, course, teacher, room, event_type, reason)
            if signature in seen:
                continue
            seen.add(signature)
            events.append(
                ParentVueAttendanceEvent(
                    period=period,
                    course=course,
                    teacher=teacher,
                    room=room,
                    event_type=event_type,
                    reason=reason,
                )
            )

        absences = 0
        tardies = 0
        excused = 0
        unexcused = 0
        dismissals = 0

        for event in events:
            text = " ".join(
                value for value in (event.event_type, event.reason) if value
            ).casefold()
            if "unexcused" in text:
                unexcused += 1
            elif "excused" in text:
                excused += 1

            if "tard" in text:
                tardies += 1
            elif "dismiss" in text or "early release" in text:
                dismissals += 1
            elif "absen" in text:
                absences += 1

        return ParentVueAttendanceDay(
            available=True,
            events=tuple(events),
            absences=absences,
            tardies=tardies,
            excused=excused,
            unexcused=unexcused,
            dismissals=dismissals,
        )

    @staticmethod
    def _attendance_year_metric(
        soup: BeautifulSoup,
        aliases: tuple[str, ...],
    ) -> int | None:
        """Find a compact label/value pair in the attendance page."""
        for tag in soup.find_all(["div", "span", "td", "th", "li", "p", "label"]):
            if not isinstance(tag, Tag):
                continue
            own_text = _text(tag)
            if not own_text or len(own_text) > 100:
                continue

            simplified = own_text.strip().strip(":").casefold()
            for alias in aliases:
                alias_cf = alias.casefold()

                # Do not let the generic "Absences" label consume a more
                # specific "Excused Absences" or "Unexcused Absences" count.
                if (
                    alias_cf == "absences"
                    and re.search(
                        r"\b(?:un)?excused\s+absences\b",
                        own_text,
                        re.IGNORECASE,
                    )
                ):
                    continue

                # Label and number in the same compact element.
                match = re.search(
                    rf"\b{re.escape(alias)}\b\s*:?\s*(\d+)\b",
                    own_text,
                    re.IGNORECASE,
                )
                if match:
                    return int(match.group(1))

                # Label in one cell, value in the sibling/row.
                if simplified != alias_cf:
                    continue

                sibling = tag.find_next_sibling()
                if isinstance(sibling, Tag):
                    sibling_text = _text(sibling)
                    if sibling_text:
                        number = re.fullmatch(r"\s*(\d+)\s*", sibling_text)
                        if number:
                            return int(number.group(1))

                row = tag.find_parent(["tr", "li"])
                if isinstance(row, Tag):
                    row_text = _text(row)
                    if row_text and len(row_text) <= 140:
                        number = re.search(
                            rf"\b{re.escape(alias)}\b\s*:?\s*(\d+)\b",
                            row_text,
                            re.IGNORECASE,
                        )
                        if number:
                            return int(number.group(1))

        return None

    @classmethod
    def _parse_attendance_year(cls, body: str) -> ParentVueAttendanceYear:
        """Parse cumulative attendance totals when the website renders them."""
        soup = BeautifulSoup(body, "html.parser")

        excused = cls._attendance_year_metric(
            soup,
            ("Excused Absences", "Excused"),
        )
        unexcused = cls._attendance_year_metric(
            soup,
            ("Unexcused Absences", "Unexcused"),
        )
        absences = cls._attendance_year_metric(
            soup,
            ("Total Absences", "Days Absent", "Absences"),
        )
        tardies = cls._attendance_year_metric(
            soup,
            ("Total Tardies", "Tardies"),
        )
        dismissals = cls._attendance_year_metric(
            soup,
            ("Early Dismissals", "Dismissals"),
        )

        available = any(
            value is not None
            for value in (absences, excused, unexcused, tardies, dismissals)
        )
        return ParentVueAttendanceYear(
            available=available,
            absences=absences,
            excused_absences=excused,
            unexcused_absences=unexcused,
            tardies=tardies,
            early_dismissals=dismissals,
        )

    async def _fetch_attendance(
        self,
        *,
        child_index: int,
        day: date,
    ) -> tuple[ParentVueAttendanceDay, ParentVueAttendanceYear]:
        """Fetch attendance without making attendance failure fatal to grades."""
        empty_day = ParentVueAttendanceDay(False, (), 0, 0, 0, 0, 0)
        empty_year = ParentVueAttendanceYear(False, None, None, None, None, None)

        try:
            attendance_html, _ = await self._get_text(
                _ATTENDANCE_PATH,
                params={"AGU": child_index},
                referer=self._url(_HOME_PATH),
            )
            year = self._parse_attendance_year(attendance_html)
        except ParentVueSessionExpired:
            raise
        except ParentVueError:
            attendance_html = ""
            year = empty_year

        try:
            result = await self._post_json(
                _ATTENDANCE_DAY_PATH,
                {"date": day.strftime("%m/%d/%Y")},
                child_index=child_index,
                referer_path=f"{_ATTENDANCE_PATH}?AGU={child_index}",
            )
            today = self._parse_attendance_day(result)
        except ParentVueSessionExpired:
            raise
        except ParentVueError:
            today = empty_day

        return today, year

    async def _fetch_all_after_login(
        self,
        discovered: list[dict[str, Any]],
        day: date,
    ) -> ParentVueData:
        children: list[ParentVueChild] = []

        for child in discovered:
            child_index = int(child["index"])

            gradebook_html, _ = await self._get_text(
                _GRADEBOOK_PATH,
                params={"AGU": child_index},
                referer=self._url(_HOME_PATH),
            )

            (
                name,
                school,
                grade_level,
                courses,
            ) = self._parse_gradebook(
                gradebook_html,
                child_key=str(child["key"]),
                child_index=child_index,
                fallback_name=str(child["name"]),
                fallback_school=child.get("school"),
            )

            # Schedule is useful but optional. A temporary/feature-specific
            # schedule error should not discard otherwise valid grade data.
            try:
                schedule = await self._fetch_schedule(
                    child_index=child_index,
                    day=day,
                )
                schedule_available = True
            except ParentVueSessionExpired:
                raise
            except ParentVueError:
                schedule = ()
                schedule_available = False

            courses = self._enrich_courses_with_schedule(courses, schedule)

            # Attendance is optional. A feature-specific response mismatch must
            # not discard otherwise valid grade/schedule data.
            try:
                attendance_today, attendance_year = await self._fetch_attendance(
                    child_index=child_index,
                    day=day,
                )
            except ParentVueSessionExpired:
                raise
            except ParentVueError:
                attendance_today = ParentVueAttendanceDay(
                    False, (), 0, 0, 0, 0, 0
                )
                attendance_year = ParentVueAttendanceYear(
                    False, None, None, None, None, None
                )

            children.append(
                ParentVueChild(
                    key=str(child["key"]),
                    account_index=child_index,
                    name=name,
                    school=school,
                    grade_level=grade_level,
                    courses=courses,
                    schedule=schedule,
                    schedule_available=schedule_available,
                    attendance_today=attendance_today,
                    attendance_year=attendance_year,
                )
            )

        synergy_mail_unread, synergy_mail_available = (
            self._parse_synergy_mail_unread(self._last_home_html)
        )

        return ParentVueData(
            children=tuple(children),
            fetched_at=datetime.now(),
            synergy_mail_unread=synergy_mail_unread,
            synergy_mail_available=synergy_mail_available,
        )

    async def async_fetch_data(self, day: date) -> ParentVueData:
        """Fetch all children and normalized Grade Book/schedule data.

        One session-expiration retry is allowed.  A normal coordinator refresh
        begins with a fresh website login because ParentVUE sessions are shorter
        than the integration's two-hour network interval.
        """
        for attempt in range(2):
            discovered = await self.async_login()
            try:
                return await self._fetch_all_after_login(discovered, day)
            except ParentVueSessionExpired:
                if attempt == 0:
                    continue
                raise ParentVueInvalidAuth(
                    "ParentVUE session could not be renewed"
                )

        raise ParentVueInvalidAuth("ParentVUE session could not be renewed")
