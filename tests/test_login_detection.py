"""Regression tests for ParentVUE login-page detection."""

from custom_components.parentvue.api import ParentVueClient


def test_login_url_is_login() -> None:
    """The actual ParentVUE login route is always a login response."""
    assert ParentVueClient._looks_like_login(
        "https://district.example/PXP2_Login_Parent.aspx",
        "<html></html>",
    )


def test_authenticated_student_selector_wins_over_password_controls() -> None:
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


def test_same_form_username_and_password_is_login() -> None:
    """A username/password pair in one form identifies a login form."""
    body = """
    <html>
      <form>
        <input name="username" type="text">
        <input name="password" type="password">
      </form>
    </html>
    """
    assert ParentVueClient._looks_like_login(
        "https://district.example/SomeRedirectTarget.aspx",
        body,
    )


def test_separate_unrelated_controls_are_not_login() -> None:
    """Unrelated controls in separate forms must not create a false positive."""
    body = """
    <html>
      <form><input name="username_setting" type="text"></form>
      <form><input name="new_password" type="password"></form>
    </html>
    """
    assert not ParentVueClient._looks_like_login(
        "https://district.example/Home_PXP2.aspx",
        body,
    )
