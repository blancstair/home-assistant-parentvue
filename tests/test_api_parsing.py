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


def test_class_focus_args_are_taken_from_gradebook_buttons() -> None:
    """Course focus arguments come verbatim from the website's own data-focus JSON."""
    client = ParentVueClient.__new__(ParentVueClient)
    client.base_url = "https://example.invalid"
    html = """
    <div class="row gb-class-header gb-class-row" data-guid="111">
      <button class="course-title"
        data-focus='{"LoadParams":{"ControlName":"Gradebook_ClassDetails"},"FocusArgs":{"classID":111,"AGU":"0"}}'>
        1: Example Course</button>
    </div>
    <div class="row gb-class-header gb-class-row" data-guid="222">
      <button class="course-title"
        data-focus='{"LoadParams":{"ControlName":"Gradebook_RichContentClassDetails"},"FocusArgs":{"classID":222}}'>
        2: Content Only</button>
    </div>
    """
    focus = client._parse_class_focus_args(html, child_key="child")
    assert len(focus) == 1
    (args,) = focus.values()
    assert args == {"classID": 111, "AGU": "0"}


def test_class_assignments_parser_reads_grid_data_source() -> None:
    """Assignment rows are decoded from the synthetic DevExpress grid config."""
    html = """
    <div id="AssignmentsGrid"></div>
    <script>
      $('#AssignmentsGrid').dxDataGrid(PXP.DevExpress.ExtendGridConfiguration({
        "columns":[{"calculateDisplayValue":PXP.DataGridTemplates.CalculateValue}],
        "dataSource":[
          {"Date":"9/23/26",
           "GBAssignment":"{\\"href\\":\\"javascript:\\",\\"hrefAttributes\\":\\"data-focus={}\\",\\"value\\":\\"Quiz One\\",\\"dataType\\":\\"LinkColumn\\"}",
           "GBAssignmentType":"Summative",
           "GBScore":"{\\"href\\":\\"javascript:\\",\\"value\\":\\"Not Graded\\",\\"dataType\\":\\"LinkColumn\\"}",
           "GBScoreType":"Raw Score","GBPoints":"9.0000 Points Possible","GBNotes":""},
          {"Date":"9/20/2026",
           "GBAssignment":"{\\"value\\":\\"Worksheet\\",\\"dataType\\":\\"LinkColumn\\"}",
           "GBAssignmentType":"Formative",
           "GBScore":"{\\"value\\":\\"8 out of 10\\",\\"dataType\\":\\"LinkColumn\\"}",
           "GBScoreType":"Raw Score","GBPoints":"8.0000 / 10.0000","GBNotes":"late"}
        ],
        "noDataText":"No Data","onInitialized":PXP.Actions.GB.onGBClassDetailsLoad}))
    </script>
    """
    rows = ParentVueClient._parse_class_assignments(html)
    assert len(rows) == 2
    quiz, worksheet = rows
    assert quiz.name == "Quiz One"
    assert quiz.due_date.isoformat() == "2026-09-23"
    assert quiz.score == "Not Graded"
    assert quiz.is_graded is False
    assert quiz.points == "9.0000 Points Possible"
    assert worksheet.due_date.isoformat() == "2026-09-20"
    assert worksheet.score == "8 out of 10"
    assert worksheet.is_graded is True
    assert worksheet.notes == "late"


def test_link_column_discards_focus_arguments() -> None:
    """Only the display value survives; embedded focus/identifier data is dropped."""
    raw = '{"href":"javascript:","hrefAttributes":"data-focus={\\"studentGU\\":\\"x\\"}","value":"Essay"}'
    assert ParentVueClient._link_column_value(raw) == "Essay"
    assert ParentVueClient._link_column_value("Plain") == "Plain"
    assert ParentVueClient._link_column_value("") is None
