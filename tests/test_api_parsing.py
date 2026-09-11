"""Parser regression tests using synthetic, non-student data."""

from custom_components.parentvue.api import ParentVueClient


def test_placeholder() -> None:
    """Initial repository test placeholder.

    Real parser fixtures will be added after 0.1.0 is exercised in Home Assistant.
    """
    assert ParentVueClient is not None
