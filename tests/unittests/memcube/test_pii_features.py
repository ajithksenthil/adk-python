from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from contributing.samples.memcube_system import service
from contributing.samples.memcube_system.in_memory_storage import InMemoryMemCubeStorage
from contributing.samples.memcube_system.operator import MemoryOperator, MemorySelector, MemoryScheduler
from contributing.samples.memcube_system.storage import SupabaseMemCubeStorage, StorageMode, MemCubePayload, MemoryType


@pytest.fixture
def test_app() -> TestClient:
    storage = InMemoryMemCubeStorage()
    service.storage = storage
    service.operator = MemoryOperator(storage)
    service.scheduler = MemoryScheduler(storage, MemorySelector(storage))
    client = TestClient(service.app)
    return client


@pytest.mark.asyncio
async def test_unauthorized_access_returns_403(test_app: TestClient) -> None:
    create_resp = test_app.post(
        "/memories",
        json={
            "project_id": "p1",
            "label": "pii",
            "content": "Contact me at john@example.com",
            "created_by": "u1",
            "type": "PLAINTEXT",
            "governance": {"read_roles": ["ADMIN"]},
        },
    )
    mem_id = create_resp.json()["id"]
    resp = test_app.get(f"/memories/{mem_id}?role=MEMBER")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_encrypted_payload_unreadable_without_decryption() -> None:
    storage = SupabaseMemCubeStorage("http://x", "y")
    payload = MemCubePayload(type=MemoryType.PLAINTEXT, content="secret")
    ref = await storage._store_payload("m1", payload, StorageMode.INLINE, encrypt=True)
    raw = await storage._retrieve_payload("m1", ref, StorageMode.INLINE, MemoryType.PLAINTEXT, encrypted=False)
    assert raw.content != "secret"
    dec = await storage._retrieve_payload("m1", ref, StorageMode.INLINE, MemoryType.PLAINTEXT, encrypted=True)
    assert dec.content == "secret"
