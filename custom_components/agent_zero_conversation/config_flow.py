"""Config flow for ha-agent-zero-conversation-agent."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import AgentZeroClient, AgentZeroConnectionError
from .const import (
    CONF_AGENT_PROFILE,
    CONF_BASE_URL,
    CONF_LIFETIME_HOURS,
    CONF_PROJECT_NAME,
    CONF_TIMEOUT,
    DEFAULT_LIFETIME_HOURS,
    DEFAULT_NAME,
    DEFAULT_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class CannotConnect(Exception):
    """Error to indicate Agent Zero cannot be reached."""


class InvalidURL(Exception):
    """Error to indicate the configured URL is invalid."""


def _strip_optional_string(value: Any) -> str | None:
    """Return stripped string or None for empty optional form values."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _clean_user_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Normalize config flow user input before storing it."""
    data = dict(user_input)
    data[CONF_NAME] = data[CONF_NAME].strip() or DEFAULT_NAME
    data[CONF_BASE_URL] = data[CONF_BASE_URL].strip().rstrip("/")
    data[CONF_API_KEY] = data[CONF_API_KEY].strip()

    for key in (CONF_PROJECT_NAME, CONF_AGENT_PROFILE):
        value = _strip_optional_string(data.get(key))
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value

    return data


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate that the Agent Zero base URL is reachable."""
    parsed = urlparse(data[CONF_BASE_URL])
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise InvalidURL

    client = AgentZeroClient(
        session=async_get_clientsession(hass),
        base_url=data[CONF_BASE_URL],
        api_key=data[CONF_API_KEY],
        timeout=data[CONF_TIMEOUT],
    )
    try:
        await client.async_health_check()
    except AgentZeroConnectionError as err:
        raise CannotConnect from err


def _user_schema(user_input: dict[str, Any] | None = None) -> vol.Schema:
    """Return config flow schema with suggested values."""
    user_input = user_input or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_NAME,
                default=user_input.get(CONF_NAME, DEFAULT_NAME),
            ): str,
            vol.Required(
                CONF_BASE_URL,
                default=user_input.get(CONF_BASE_URL, ""),
            ): str,
            vol.Required(CONF_API_KEY): str,
            vol.Optional(
                CONF_TIMEOUT,
                default=user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
            ): vol.All(vol.Coerce(float), vol.Range(min=1, max=300)),
            vol.Optional(
                CONF_LIFETIME_HOURS,
                default=user_input.get(
                    CONF_LIFETIME_HOURS, DEFAULT_LIFETIME_HOURS
                ),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=720)),
            vol.Optional(
                CONF_PROJECT_NAME,
                default=user_input.get(CONF_PROJECT_NAME, ""),
            ): str,
            vol.Optional(
                CONF_AGENT_PROFILE,
                default=user_input.get(CONF_AGENT_PROFILE, ""),
            ): str,
        }
    )


class AgentZeroConversationConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle a config flow for ha-agent-zero-conversation-agent."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ):
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = _clean_user_input(user_input)
            try:
                await validate_input(self.hass, data)
            except InvalidURL:
                errors["base"] = "invalid_url"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected Agent Zero setup error")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(data[CONF_BASE_URL])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=data[CONF_NAME],
                    data=data,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input),
            errors=errors,
        )
