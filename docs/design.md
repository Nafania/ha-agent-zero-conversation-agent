# ha-agent-zero-conversation-agent Design

## Goal

Create a small Home Assistant custom integration that exposes Agent Zero as a
Conversation Agent for Assist.

Project/HACS name is `ha-agent-zero-conversation-agent`. Home Assistant domain
is `agent_zero_conversation` because custom component folders must be valid
Python package names.

## Behavior

Home Assistant owns microphone, STT, local smart-home intents, and TTS. The user
selects this integration as the assistant's Conversation Agent and enables
Home Assistant's built-in "Prefer handling commands locally" option. Home
Assistant then executes recognized smart-home commands locally and calls Agent
Zero only for fallback conversation requests.

## Architecture

The integration registers one `ConversationEntity`. When HA calls
`_async_handle_message`, the entity sends `user_input.text` to Agent Zero's
`POST /api/api_message` endpoint with `X-API-KEY`, converts the `response` field
into `IntentResponse` speech, and stores the returned Agent Zero `context_id` per
HA `conversation_id` for follow-up messages.

## Scope

- No n8n, Node-RED, webhook mapper, or OpenAI-compatible shim.
- No HA control tools are exposed to Agent Zero by this integration.
- Setup checks `GET /api/health` only to avoid creating Agent Zero chats during
  configuration.
- API key validation happens on first message.

## Error Handling

Agent Zero request failures are logged in Home Assistant and converted into a
spoken fallback message so Assist does not fail with a generic intent error.
