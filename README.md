# ha-agent-zero-conversation-agent

Custom Home Assistant conversation agent that sends fallback Assist requests to
Agent Zero through its external API.

Use this with Home Assistant's built-in **Prefer handling commands locally**
option:

1. Home Assistant tries local smart-home intents first.
2. If Home Assistant does not understand the request, Assist sends it to this
   Agent Zero conversation agent.
3. Home Assistant speaks Agent Zero's response through the configured TTS engine.

## Install

### Manual

Copy this folder into Home Assistant:

```text
<home-assistant-config>/custom_components/agent_zero_conversation
```

Restart Home Assistant.

The project/HACS name is `ha-agent-zero-conversation-agent`. The Home Assistant
integration domain stays `agent_zero_conversation` because HA custom component
domains are Python package names and cannot use hyphens.

### HACS custom repository

Add this repository to HACS as an **Integration**, install it, then restart Home
Assistant.

## Configure

1. Open **Settings -> Devices & services**.
2. Select **Add integration**.
3. Search for **ha-agent-zero-conversation-agent**.
4. Enter:
   - **Agent Zero base URL**: URL reachable from Home Assistant, for example
     `http://192.168.1.50:80`.
   - **Agent Zero API key**: Agent Zero external API token.
   - **Timeout**: start with `60`; use `120` if Agent Zero often takes longer.
   - **Project name**: optional Agent Zero project to activate on new chats.
   - **Agent profile**: optional Agent Zero profile to use.
5. Open **Settings -> Voice assistants**.
6. Edit your assistant.
7. Set **Conversation agent** to **Agent Zero**.
8. Enable **Prefer handling commands locally**.
9. Keep your existing microphone/STT/TTS settings.

## Agent Zero API Key

Agent Zero exposes `POST /api/api_message` for external applications. The token
is shown in Agent Zero's external API settings/examples and is sent as the
`X-API-KEY` header.

This integration checks only `GET /api/health` during setup, so setup does not
create a chat or spend model calls. The API key is validated when the first
message is sent.

## Docker/LAN URL Note

Do not use `localhost` unless Home Assistant and Agent Zero run in the same
network namespace. From Home Assistant OS or a Docker container, use the Agent
Zero host IP, container DNS name, or reverse proxy URL.

## Test

Say:

```text
turn on kitchen lights
```

Expected: Home Assistant handles locally.

Then say:

```text
what can you do?
```

Expected: request goes to Agent Zero and response is spoken by Home Assistant.
