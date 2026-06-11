import unittest
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

CLIENT_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "agent_zero_conversation"
    / "client.py"
)
CLIENT_SPEC = spec_from_file_location("agent_zero_conversation_client", CLIENT_PATH)
assert CLIENT_SPEC is not None
client_module = module_from_spec(CLIENT_SPEC)
assert CLIENT_SPEC.loader is not None
sys.modules[CLIENT_SPEC.name] = client_module
CLIENT_SPEC.loader.exec_module(client_module)

AgentZeroAuthenticationError = client_module.AgentZeroAuthenticationError
AgentZeroClient = client_module.AgentZeroClient
AgentZeroConversationError = client_module.AgentZeroConversationError
normalize_base_url = client_module.normalize_base_url


class FakeResponse:
    def __init__(self, status=200, payload=None, text=""):
        self.status = status
        self._payload = payload if payload is not None else {}
        self._text = text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def json(self, content_type=None):
        return self._payload

    async def text(self):
        return self._text


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def post(self, url, **kwargs):
        self.requests.append(("POST", url, kwargs))
        return self.response

    def get(self, url, **kwargs):
        self.requests.append(("GET", url, kwargs))
        return self.response


class AgentZeroClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_send_message_posts_expected_payload_and_returns_reply(self):
        session = FakeSession(
            FakeResponse(payload={"context_id": "ctx-new", "response": "Hello"})
        )
        client = AgentZeroClient(
            session=session,
            base_url="http://agent-zero.local/",
            api_key="secret",
            timeout=42,
        )

        reply = await client.async_send_message(
            "Who are you?",
            context_id="ctx-old",
            lifetime_hours=12,
            project_name="Home",
            agent_profile="assistant",
        )

        self.assertEqual(reply.response, "Hello")
        self.assertEqual(reply.context_id, "ctx-new")
        self.assertEqual(len(session.requests), 1)
        method, url, kwargs = session.requests[0]
        self.assertEqual(method, "POST")
        self.assertEqual(url, "http://agent-zero.local/api/api_message")
        self.assertEqual(
            kwargs["headers"],
            {"X-API-KEY": "secret", "Content-Type": "application/json"},
        )
        self.assertEqual(
            kwargs["json"],
            {
                "message": "Who are you?",
                "context_id": "ctx-old",
                "lifetime_hours": 12,
                "project_name": "Home",
                "agent_profile": "assistant",
            },
        )
        self.assertEqual(kwargs["timeout"], 42)

    async def test_send_message_rejects_missing_response_text(self):
        session = FakeSession(FakeResponse(payload={"context_id": "ctx"}))
        client = AgentZeroClient(session, "http://agent-zero.local", "secret")

        with self.assertRaises(AgentZeroConversationError):
            await client.async_send_message("Hello")

    async def test_send_message_maps_auth_failure(self):
        session = FakeSession(FakeResponse(status=401, payload={}, text="Invalid API key"))
        client = AgentZeroClient(session, "http://agent-zero.local", "bad")

        with self.assertRaises(AgentZeroAuthenticationError):
            await client.async_send_message("Hello")

    async def test_health_check_uses_health_endpoint_without_api_key(self):
        session = FakeSession(FakeResponse(payload={"error": None}))
        client = AgentZeroClient(session, "http://agent-zero.local/", "secret")

        await client.async_health_check()

        method, url, kwargs = session.requests[0]
        self.assertEqual(method, "GET")
        self.assertEqual(url, "http://agent-zero.local/api/health")
        self.assertNotIn("headers", kwargs)

    def test_normalize_base_url_removes_trailing_slashes(self):
        self.assertEqual(
            normalize_base_url("http://agent-zero.local///"),
            "http://agent-zero.local",
        )
