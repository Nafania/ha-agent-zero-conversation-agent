"""Conversation platform for Agent Zero."""

from __future__ import annotations

import logging
from typing import Literal

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import (
    AgentZeroAuthenticationError,
    AgentZeroClient,
    AgentZeroConversationError,
)
from .const import (
    CONF_AGENT_PROFILE,
    CONF_BASE_URL,
    CONF_LIFETIME_HOURS,
    CONF_PROJECT_NAME,
    CONF_TIMEOUT,
    DEFAULT_LIFETIME_HOURS,
    DEFAULT_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Agent Zero conversation entity."""
    client = AgentZeroClient(
        session=async_get_clientsession(hass),
        base_url=entry.data[CONF_BASE_URL],
        api_key=entry.data[CONF_API_KEY],
        timeout=entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
    )
    async_add_entities([AgentZeroConversationEntity(entry, client)])


class AgentZeroConversationEntity(conversation.ConversationEntity):
    """Conversation agent backed by Agent Zero."""

    _attr_should_poll = False
    _attr_supports_streaming = False

    def __init__(self, entry: ConfigEntry, client: AgentZeroClient) -> None:
        """Initialize Agent Zero conversation entity."""
        self._entry = entry
        self._client = client
        self._agent_context_by_conversation: dict[str, str] = {}
        self._attr_name = entry.title
        self._attr_unique_id = entry.entry_id

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return supported languages."""
        return MATCH_ALL

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        """Send fallback utterance to Agent Zero and return speech."""
        ha_conversation_id = user_input.conversation_id or chat_log.conversation_id
        agent_zero_context_id = None
        if ha_conversation_id:
            agent_zero_context_id = self._agent_context_by_conversation.get(
                ha_conversation_id
            )

        try:
            reply = await self._client.async_send_message(
                user_input.text,
                context_id=agent_zero_context_id,
                lifetime_hours=self._entry.data.get(
                    CONF_LIFETIME_HOURS, DEFAULT_LIFETIME_HOURS
                ),
                project_name=self._entry.data.get(CONF_PROJECT_NAME),
                agent_profile=self._entry.data.get(CONF_AGENT_PROFILE),
            )
        except AgentZeroAuthenticationError:
            _LOGGER.exception("Agent Zero API key rejected")
            speech = "Agent Zero API key is invalid."
        except AgentZeroConversationError:
            _LOGGER.exception("Agent Zero conversation request failed")
            speech = "Agent Zero is unavailable."
        else:
            speech = reply.response
            if ha_conversation_id and reply.context_id:
                self._agent_context_by_conversation[ha_conversation_id] = (
                    reply.context_id
                )

        chat_log.async_add_assistant_content_without_tools(
            conversation.AssistantContent(
                agent_id=user_input.agent_id,
                content=speech,
            )
        )

        response = intent.IntentResponse(language=user_input.language)
        response.async_set_speech(speech)
        return conversation.ConversationResult(
            conversation_id=ha_conversation_id,
            response=response,
            continue_conversation=False,
        )

