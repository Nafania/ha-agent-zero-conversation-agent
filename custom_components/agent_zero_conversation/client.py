"""HTTP client for Agent Zero external API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class AgentZeroConversationError(Exception):
    """Base error for Agent Zero conversation failures."""


class AgentZeroAuthenticationError(AgentZeroConversationError):
    """Raised when Agent Zero rejects the configured API key."""


class AgentZeroConnectionError(AgentZeroConversationError):
    """Raised when Agent Zero cannot be reached."""


@dataclass(frozen=True)
class AgentZeroReply:
    """Agent Zero API reply."""

    response: str
    context_id: str | None


def normalize_base_url(base_url: str) -> str:
    """Normalize an Agent Zero base URL for endpoint joining."""
    return base_url.strip().rstrip("/")


class AgentZeroClient:
    """Small wrapper around Agent Zero's external HTTP API."""

    def __init__(
        self,
        session: Any,
        base_url: str,
        api_key: str,
        timeout: float = 60,
    ) -> None:
        self._session = session
        self._base_url = normalize_base_url(base_url)
        self._api_key = api_key
        self._timeout = timeout

    async def async_health_check(self) -> None:
        """Check that the Agent Zero instance is reachable."""
        url = f"{self._base_url}/api/health"
        try:
            async with self._session.get(url, timeout=self._timeout) as response:
                if response.status >= 400:
                    text = await response.text()
                    raise AgentZeroConnectionError(
                        f"Agent Zero health check failed: HTTP {response.status}: {text}"
                    )
                await response.json(content_type=None)
        except AgentZeroConversationError:
            raise
        except Exception as err:  # noqa: BLE001 - surface aiohttp/runtime details.
            raise AgentZeroConnectionError(
                f"Agent Zero health check failed: {err}"
            ) from err

    async def async_send_message(
        self,
        message: str,
        *,
        context_id: str | None = None,
        lifetime_hours: float = 24,
        project_name: str | None = None,
        agent_profile: str | None = None,
    ) -> AgentZeroReply:
        """Send a user message to Agent Zero and return the assistant reply."""
        payload: dict[str, Any] = {
            "message": message,
            "lifetime_hours": lifetime_hours,
        }
        if context_id:
            payload["context_id"] = context_id
        if project_name:
            payload["project_name"] = project_name
        if agent_profile:
            payload["agent_profile"] = agent_profile

        headers = {
            "X-API-KEY": self._api_key,
            "Content-Type": "application/json",
        }

        url = f"{self._base_url}/api/api_message"
        try:
            async with self._session.post(
                url,
                json=payload,
                headers=headers,
                timeout=self._timeout,
            ) as response:
                if response.status in (401, 403):
                    text = await response.text()
                    raise AgentZeroAuthenticationError(text or "Invalid API key")
                if response.status >= 400:
                    text = await response.text()
                    raise AgentZeroConversationError(
                        f"Agent Zero returned HTTP {response.status}: {text}"
                    )

                data = await response.json(content_type=None)
        except AgentZeroConversationError:
            raise
        except Exception as err:  # noqa: BLE001 - surface aiohttp/runtime details.
            raise AgentZeroConnectionError(f"Agent Zero request failed: {err}") from err

        response_text = data.get("response")
        if not isinstance(response_text, str) or not response_text.strip():
            raise AgentZeroConversationError("Agent Zero response did not include text")

        response_context_id = data.get("context_id")
        if not isinstance(response_context_id, str):
            response_context_id = None

        return AgentZeroReply(
            response=response_text,
            context_id=response_context_id,
        )

