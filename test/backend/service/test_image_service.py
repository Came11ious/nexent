import types

import pytest

import backend.services.image_service as image_service


class DummyStream:
    def __init__(self, status: int, payload: dict):
        self.status = status
        self._payload = payload
        self._text = "error-text"

    async def json(self):
        return self._payload

    async def text(self):
        return self._text


class DummyResponseCtx:
    def __init__(self, response: DummyStream):
        self._resp = response

    async def __aenter__(self):
        return self._resp

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummySession:
    def __init__(self, response: DummyStream):
        self._response = response
        self.last_url = None

    def get(self, url: str):
        self.last_url = url
        return DummyResponseCtx(self._response)


class DummySessionCtx:
    def __init__(self, session: DummySession):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_proxy_image_impl_success(monkeypatch):
    """proxy_image_impl should proxy request and return JSON on success."""
    response_payload = {"success": True, "base64": "xxx", "content_type": "image/png"}
    dummy_stream = DummyStream(status=200, payload=response_payload)
    dummy_session = DummySession(dummy_stream)

    monkeypatch.setattr(
        image_service,
        "aiohttp",
        types.SimpleNamespace(ClientSession=lambda: DummySessionCtx(dummy_session)),
    )

    out = await image_service.proxy_image_impl("http://example.com/img.png")
    assert out == response_payload
    assert "url=" in dummy_session.last_url


@pytest.mark.asyncio
async def test_proxy_image_impl_error(monkeypatch):
    """proxy_image_impl should log and return error payload when upstream fails."""
    error_stream = DummyStream(status=500, payload={"unexpected": "oops"})
    dummy_session = DummySession(error_stream)

    monkeypatch.setattr(
        image_service,
        "aiohttp",
        types.SimpleNamespace(ClientSession=lambda: DummySessionCtx(dummy_session)),
    )

    out = await image_service.proxy_image_impl("http://example.com/bad.png")
    assert out["success"] is False
    assert "error" in out