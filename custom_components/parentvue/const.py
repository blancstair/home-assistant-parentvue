"""Constants for the ParentVUE integration."""

from datetime import timedelta

DOMAIN = "parentvue"
NAME = "ParentVUE"
VERSION = "0.2.1"

CONF_BASE_URL = "base_url"

DEFAULT_BASE_URL = "https://va-cps-psv.edupoint.com"

# The scheduled interval is deliberately just over two hours.  Together with
# MIN_NETWORK_INTERVAL this guarantees that neither scheduled nor manual entity
# refreshes cause ParentVUE network refreshes more often than once every 2 hours.
UPDATE_INTERVAL = timedelta(hours=2, minutes=1)
MIN_NETWORK_INTERVAL = timedelta(hours=2)

REQUEST_TIMEOUT_SECONDS = 30

PLATFORMS: tuple[str, ...] = ("sensor",)

MANUFACTURER = "Edupoint"
MODEL = "ParentVUE student"

# Bundled ParentVUE dashboard card.
DASHBOARD_CARD_URL = "/parentvue/frontend/parentvue-dashboard-card.js"
DASHBOARD_CARD_RESOURCE_URL = f"{DASHBOARD_CARD_URL}?v={VERSION}"
