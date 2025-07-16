"""
MemCube Supabase Python Client

A Python SDK for interacting with the MemCube memory system on Supabase.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime

import httpx
from supabase import create_client, Client


class MemoryType(str, Enum):
    PLAINTEXT = "PLAINTEXT"
    ACTIVATION = "ACTIVATION"
    PARAMETER = "PARAMETER"


class MemoryPriority(str, Enum):
    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"


@dataclass
class MemoryGovernance:
    read_roles: List[str] = None
    write_roles: List[str] = None
    ttl_days: int = 365
    shareable: bool = True
    license: Optional[str] = None
    pii_tagged: bool = False
    
    def __post_init__(self):
        if self.read_roles is None:
            self.read_roles = ["MEMBER", "AGENT"]
        if self.write_roles is None:
            self.write_roles = ["AGENT"]


@dataclass
class Memory:
    id: str
    label: str
    type: MemoryType
    priority: MemoryPriority
    content: Optional[str] = None
    version: Optional[int] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    usage_hits: Optional[int] = None
    token_count: Optional[int] = None


@dataclass
class ScheduledMemory:
    id: str
    label: str
    type: str
    content: str
    tokens: int
    relevance_score: float = 0.0


@dataclass
class MemoryScheduleResponse:
    agent_id: str
    task_id: str
    memories: List[ScheduledMemory]
    total_tokens: int
    count: int


class MemCubeClient:
    """
    Python client for MemCube Supabase backend.
    
    Example:
        ```python
        client = MemCubeClient(url, key, project_id="my-project")
        
        # Create memory
        memory = await client.create_memory(
            label="python-tip",
            content="Use type hints",
            type=MemoryType.PLAINTEXT
        )
        
        # Schedule memories for agent
        memories = await client.schedule_memories(
            agent_id="bot-001",
            task_id="TASK-123",
            tags=["python"]
        )
        ```
    """
    
    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        project_id: Optional[str] = None,
        timeout: int = 30
    ):
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.project_id = project_id
        self.timeout = timeout
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._http_client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._http_client:
            await self._http_client.aclose()
    
    # Authentication
    
    async def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """Sign in with email and password."""
        response = self.supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        return response.dict()
    
    async def sign_out(self) -> None:
        """Sign out current user."""
        self.supabase.auth.sign_out()
    
    def get_session(self) -> Optional[Dict[str, Any]]:
        """Get current session."""
        session = self.supabase.auth.get_session()
        return session.dict() if session else None
    
    # Memory CRUD
    
    async def create_memory(
        self,
        label: str,
        content: str,
        type: MemoryType = MemoryType.PLAINTEXT,
        project_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        governance: Optional[MemoryGovernance] = None
    ) -> Memory:
        """Create a new memory."""
        project_id = project_id or self.project_id
        if not project_id:
            raise ValueError("Project ID required")
        
        payload = {
            "action": "create",
            "label": label,
            "content": content,
            "type": type.value,
            "project_id": project_id,
            "tags": tags or []
        }
        
        if governance:
            payload["governance"] = asdict(governance)
        
        response = await self._invoke_function("memories-crud", payload)
        
        return Memory(
            id=response["id"],
            label=response["label"],
            type=MemoryType(response["type"]),
            priority=MemoryPriority.WARM,
            created_at=datetime.fromisoformat(response["created_at"])
        )
    
    async def get_memory(self, memory_id: str) -> Memory:
        """Get a memory by ID."""
        response = await self._invoke_function("memories-crud", {
            "action": "get",
            "memory_id": memory_id
        })
        
        metadata = response.get("metadata", {})
        
        return Memory(
            id=response["id"],
            label=response["label"],
            type=MemoryType(response["type"]),
            priority=MemoryPriority(metadata.get("priority", "WARM")),
            content=response.get("content"),
            version=metadata.get("version"),
            created_by=metadata.get("created_by"),
            created_at=datetime.fromisoformat(metadata["created_at"]) if metadata.get("created_at") else None,
            usage_hits=metadata.get("usage_hits"),
            token_count=metadata.get("token_count")
        )
    
    async def update_memory(
        self,
        memory_id: str,
        content: str,
        increment_version: bool = True
    ) -> Dict[str, Any]:
        """Update memory content."""
        response = await self._invoke_function("memories-crud", {
            "action": "update",
            "memory_id": memory_id,
            "content": content,
            "increment_version": increment_version
        })
        
        return response
    
    async def archive_memory(self, memory_id: str) -> Dict[str, str]:
        """Archive a memory."""
        response = await self._invoke_function("memories-crud", {
            "action": "archive",
            "memory_id": memory_id
        })
        
        return response
    
    # Memory querying
    
    async def query_memories(
        self,
        project_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        type_filter: Optional[MemoryType] = None,
        priority_filter: Optional[MemoryPriority] = None,
        limit: int = 10
    ) -> List[Memory]:
        """Query memories with filters."""
        project_id = project_id or self.project_id
        if not project_id:
            raise ValueError("Project ID required")
        
        query = self.supabase.table("memories").select(
            "*, memory_payloads(content, token_count)"
        ).eq("project_id", project_id)
        
        if type_filter:
            query = query.eq("type", type_filter.value)
        
        if priority_filter:
            query = query.eq("priority", priority_filter.value)
        
        if tags:
            # Simple tag filtering by label
            for tag in tags:
                query = query.ilike("label", f"%{tag}%")
        
        query = query.limit(limit)
        
        response = query.execute()
        
        memories = []
        for item in response.data:
            payload = item.get("memory_payloads", [{}])[0] if item.get("memory_payloads") else {}
            
            memories.append(Memory(
                id=item["id"],
                label=item["label"],
                type=MemoryType(item["type"]),
                priority=MemoryPriority(item["priority"]),
                content=payload.get("content"),
                version=item.get("version"),
                created_by=item.get("created_by"),
                created_at=datetime.fromisoformat(item["created_at"]) if item.get("created_at") else None,
                usage_hits=item.get("usage_hits"),
                token_count=payload.get("token_count")
            ))
        
        return memories
    
    # Memory scheduling
    
    async def schedule_memories(
        self,
        agent_id: str,
        task_id: str,
        project_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        token_budget: int = 4000,
        prefer_hot: bool = True,
        include_insights: bool = False,
        embedding: Optional[List[float]] = None
    ) -> MemoryScheduleResponse:
        """Schedule memories for an agent."""
        project_id = project_id or self.project_id
        if not project_id:
            raise ValueError("Project ID required")
        
        payload = {
            "agent_id": agent_id,
            "task_id": task_id,
            "project_id": project_id,
            "need_tags": tags or [],
            "token_budget": token_budget,
            "prefer_hot": prefer_hot,
            "include_insights": include_insights
        }
        
        if embedding:
            payload["embedding"] = embedding
        
        response = await self._invoke_function("memories-schedule", payload)
        
        memories = [
            ScheduledMemory(**mem)
            for mem in response.get("memories", [])
        ]
        
        return MemoryScheduleResponse(
            agent_id=response["agent_id"],
            task_id=response["task_id"],
            memories=memories,
            total_tokens=response["total_tokens"],
            count=response["count"]
        )
    
    # Insights
    
    async def create_insight(
        self,
        insight: str,
        evidence_refs: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        sentiment: float = 0.0,
        project_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """Create an insight and convert to memory."""
        project_id = project_id or self.project_id
        if not project_id:
            raise ValueError("Project ID required")
        
        # Get current user
        session = self.get_session()
        if not session or not session.get("user"):
            raise ValueError("Not authenticated")
        
        user_id = session["user"]["id"]
        
        # Create insight
        response = self.supabase.table("insights").insert({
            "project_id": project_id,
            "insight": insight,
            "evidence_refs": evidence_refs or [],
            "tags": tags or [],
            "sentiment": sentiment,
            "created_by": user_id
        }).execute()
        
        insight_data = response.data[0]
        
        # Convert to memory
        memory = await self.create_memory(
            label=f"insight::{insight_data['id'][:8]}",
            content=f"Insight: {insight}\nSupport: {insight_data['support_count']}\nSentiment: {sentiment}",
            type=MemoryType.PLAINTEXT,
            project_id=project_id,
            tags=["insight"] + (tags or [])
        )
        
        return insight_data["id"], memory.id
    
    # Task linking
    
    async def link_memory_to_task(
        self,
        memory_id: str,
        task_id: str,
        role: str = "READ"
    ) -> None:
        """Link a memory to a task."""
        self.supabase.table("memory_task_links").insert({
            "memory_id": memory_id,
            "task_id": task_id,
            "role": role
        }).execute()
    
    async def get_task_memories(self, task_id: str) -> List[Memory]:
        """Get memories linked to a task."""
        response = self.supabase.table("memory_task_links").select(
            "memories(*, memory_payloads(content, token_count))"
        ).eq("task_id", task_id).execute()
        
        memories = []
        for item in response.data:
            mem_data = item["memories"]
            payload = mem_data.get("memory_payloads", [{}])[0] if mem_data.get("memory_payloads") else {}
            
            memories.append(Memory(
                id=mem_data["id"],
                label=mem_data["label"],
                type=MemoryType(mem_data["type"]),
                priority=MemoryPriority(mem_data["priority"]),
                content=payload.get("content"),
                token_count=payload.get("token_count")
            ))
        
        return memories
    
    # Agent helpers
    
    async def enhance_prompt(
        self,
        prompt: str,
        task_id: str,
        agent_id: str,
        tags: Optional[List[str]] = None,
        token_budget: int = 2000
    ) -> str:
        """Enhance prompt with relevant memories."""
        scheduled = await self.schedule_memories(
            agent_id=agent_id,
            task_id=task_id,
            tags=tags,
            token_budget=token_budget
        )
        
        if not scheduled.memories:
            return prompt
        
        # Build memory section
        memory_section = "\n\n".join(
            mem.content for mem in scheduled.memories
        )
        
        # Inject into prompt
        if "<MEMORIES>" in prompt:
            return prompt.replace("<MEMORIES>", memory_section)
        else:
            return f"{memory_section}\n\n{prompt}"
    
    async def capture_experience(
        self,
        label: str,
        content: str,
        tags: Optional[List[str]] = None
    ) -> Memory:
        """Capture an experience as a memory."""
        return await self.create_memory(
            label=label,
            content=content,
            type=MemoryType.PLAINTEXT,
            tags=tags
        )
    
    # Private methods
    
    async def _invoke_function(self, function_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a Supabase Edge Function."""
        if not self._http_client:
            self._http_client = httpx.AsyncClient(timeout=self.timeout)
        
        # Get auth token
        session = self.get_session()
        headers = {}
        
        if session and session.get("access_token"):
            headers["Authorization"] = f"Bearer {session['access_token']}"
        
        # Call edge function
        response = self.supabase.functions.invoke(
            function_name,
            invoke_options={
                "body": payload,
                "headers": headers
            }
        )
        
        if hasattr(response, "data"):
            return response.data
        else:
            raise Exception(f"Function error: {response}")


# Convenience functions

def create_memcube_client(
    supabase_url: str,
    supabase_key: str,
    project_id: Optional[str] = None
) -> MemCubeClient:
    """Create a MemCube client instance."""
    return MemCubeClient(supabase_url, supabase_key, project_id)


# Agent integration example
class MemoryAgent:
    """Example agent with integrated memory support."""
    
    def __init__(self, agent_id: str, client: MemCubeClient):
        self.agent_id = agent_id
        self.memory_client = client
        self._experience_buffer: List[Tuple[str, str, List[str]]] = []
    
    async def process_task(self, task_id: str, task_description: str) -> str:
        """Process a task with memory enhancement."""
        # Get relevant memories
        base_prompt = f"Task: {task_description}\n\n<MEMORIES>"
        
        enhanced_prompt = await self.memory_client.enhance_prompt(
            prompt=base_prompt,
            task_id=task_id,
            agent_id=self.agent_id,
            tags=self._extract_tags(task_description)
        )
        
        # Simulate task execution
        result = f"Completed task {task_id}"
        
        # Capture experience
        self._experience_buffer.append((
            f"task_{task_id}_result",
            f"Task: {task_description}\nResult: {result}",
            ["task", task_id]
        ))
        
        return result
    
    async def flush_experiences(self) -> int:
        """Flush buffered experiences to memory."""
        count = 0
        
        for label, content, tags in self._experience_buffer:
            try:
                await self.memory_client.capture_experience(label, content, tags)
                count += 1
            except Exception as e:
                print(f"Failed to store experience: {e}")
        
        self._experience_buffer.clear()
        return count
    
    def _extract_tags(self, text: str) -> List[str]:
        """Extract relevant tags from text."""
        # Simple keyword extraction
        keywords = ["react", "python", "api", "database", "frontend", "backend"]
        return [kw for kw in keywords if kw in text.lower()]