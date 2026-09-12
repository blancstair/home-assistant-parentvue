"""Parser regression tests using synthetic, non-student data."""

from custom_components.parentvue.api import (
    ParentVueClient,
    _grade_label,
    _percentage,
)


def test_grade_label_and_percentage_stay_separate() -> None:
    """ParentVUE's label is preserved without calculating it from percentage."""
    assert _grade_label("A 94.3%") == "A"
    assert _percentage("A 94.3%") == 94.3
    assert _grade_label("94.3%") is None


def test_synergy_mail_badge_parser() -> None:
    """Only the unread count is retained from a synthetic navigation badge."""
    html = """
    <nav>
      <a href="/messages">
        <span>Synergy Mail</span>
        <span class="notification-badge">3</span>
      </a>
    </nav>
    """
    assert ParentVueClient._parse_synergy_mail_unread(html) == (3, True)


def test_attendance_day_parser() -> None:
    """A synthetic attendance event is normalized without private fixture data."""
    payload = {
        "d": {
            "periods": [
                {
                    "period": "1",
                    "courseName": "Example Course",
                    "attendanceReasonType": "Tardy",
                    "reason": "Late",
                }
            ]
        }
    }
    parsed = ParentVueClient._parse_attendance_day(payload)
    assert parsed.available is True
    assert parsed.tardies == 1
    assert len(parsed.events) == 1
    assert parsed.events[0].period == "1"


def test_attendance_year_parser() -> None:
    """Synthetic cumulative totals can be read from simple label/value rows."""
    html = """
    <table>
      <tr><td>Absences</td><td>4</td></tr>
      <tr><td>Tardies</td><td>2</td></tr>
      <tr><td>Early Dismissals</td><td>1</td></tr>
    </table>
    """
    parsed = ParentVueClient._parse_attendance_year(html)
    assert parsed.available is True
    assert parsed.absences == 4
    assert parsed.tardies == 2
    assert parsed.early_dismissals == 1


def test_authenticated_student_selector_beats_password_controls() -> None:
    """Authenticated pages must not be mistaken for login forms."""
    body = """
    <html>
      <div class="student-info" data-agu="0">
        <div class="student-name">Synthetic Student</div>
      </div>
      <form id="account-settings">
        <input name="username_setting" type="text">
        <input name="new_password" type="password">
      </form>
    </html>
    """
    assert not ParentVueClient._looks_like_login(
        "https://district.example/Home_PXP2.aspx",
        body,
    )
