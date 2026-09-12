"""Config flow for ParentVUE."""

from __future__ import annotations

import hashlib
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    ParentVueClient,
    ParentVueConnectionError,
    ParentVueEndpointUnavailable,
    ParentVueInvalidAuth,
    ParentVueNoStudents,
    ParentVueUnsupportedDeployment,
    normalize_base_url,
)
from .const import CONF_BASE_URL, DEFAULT_BASE_URL, DOMAIN

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BASE_URL, default=DEFAULT_BASE_URL): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.URL,
                autocomplete="url",
            )
        ),
        vol.Required(CONF_USERNAME): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.TEXT,
                autocomplete="username",
            )
        ),
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD,
                autocomplete="current-password",
            )
        ),
    }
)


def _entry_unique_id(base_url: str, username: str) -> str:
    material = f"{base_url}\x1f{username.casefold()}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()[:24]


async def _validate(
    flow: ConfigFlow,
    data: dict[str, Any],
) -> tuple[str | None, int | None]:
    """Validate config-flow input and return (error, child_count)."""
    try:
        base_url = normalize_base_url(str(data[CONF_BASE_URL]))
    except ValueError:
        return "invalid_url", None

    session = async_create_clientsession(
        flow.hass,
        auto_cleanup=False,
        cookie_jar=aiohttp.CookieJar(),
    )

    client = ParentVueClient(
        base_url,
        str(data[CONF_USERNAME]),
        str(data[CONF_PASSWORD]),
        session,
    )

    try:
        child_count = await client.async_validate()
    except ParentVueInvalidAuth:
        return "invalid_auth", None
    except ParentVueNoStudents:
        return "no_students", None
    except ParentVueEndpointUnavailable:
        return "endpoint_unavailable", None
    except ParentVueUnsupportedDeployment:
        return "unsupported_deployment", None
    except ParentVueConnectionError:
        return "cannot_connect", None
    except Exception:  # noqa: BLE001 - config flow must map unknown failures safely
        return "unknown", None
    finally:
        session.detach()

    data[CONF_BASE_URL] = base_url
    return None, child_count


class ParentVueConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle ParentVUE configuration."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = dict(user_input)
            error, _ = await _validate(self, data)
            if error is None:
                unique_id = _entry_unique_id(
                    data[CONF_BASE_URL],
                    data[CONF_USERNAME],
                )
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title="ParentVUE",
                    data=data,
                )

            errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                USER_SCHEMA,
                user_input,
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: dict[str, Any],
    ) -> ConfigFlowResult:
        """Start reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Confirm updated ParentVUE credentials."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_USERNAME,
                    default=entry.data[CONF_USERNAME],
                ): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.TEXT,
                        autocomplete="username",
                    )
                ),
                vol.Required(CONF_PASSWORD): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.PASSWORD,
                        autocomplete="current-password",
                    )
                ),
            }
        )

        if user_input is not None:
            data = {
                CONF_BASE_URL: entry.data[CONF_BASE_URL],
                CONF_USERNAME: user_input[CONF_USERNAME],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }
            error, _ = await _validate(self, data)
            if error is None:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_USERNAME: data[CONF_USERNAME],
                        CONF_PASSWORD: data[CONF_PASSWORD],
                    },
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.add_suggested_values_to_schema(
                schema,
                user_input,
            ),
            errors=errors,
        )
