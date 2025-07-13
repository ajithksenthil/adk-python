# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Vector store integration for embedding storage and similarity search."""

import asyncio
import json
import logging
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

logger = logging.getLogger(__name__)


class VectorStoreType(Enum):
    """Supported vector store types."""
    PINECONE = "pinecone"
    PGVECTOR = "pgvector"
    MILVUS = "milvus"
    IN_MEMORY = "in_memory"  # For testing


@dataclass
class VectorRecord:
    """A vector record with metadata."""
    id: str
    vector: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    lineage_id: Optional[str] = None
    namespace: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "vector": self.vector,
            "metadata": self.metadata,
            "lineage_id": self.lineage_id,
            "namespace": self.namespace,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class SimilarityResult:
    """Result from similarity search."""
    id: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    lineage_id: Optional[str] = None
    namespace: Optional[str] = None


class VectorStore(ABC):
    """Abstract base class for vector stores."""
    
    @abstractmethod
    async def upsert(
        self,
        records: List[VectorRecord],
        namespace: Optional[str] = None
    ) -> bool:
        """Upsert vector records."""
        pass
    
    @abstractmethod
    async def query(
        self,
        vector: List[float],
        top_k: int = 10,
        namespace: Optional[str] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SimilarityResult]:
        """Query for similar vectors."""
        pass
    
    @abstractmethod
    async def delete(
        self,
        ids: List[str],
        namespace: Optional[str] = None
    ) -> bool:
        """Delete vectors by IDs."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        pass


class InMemoryVectorStore(VectorStore):
    """In-memory vector store for testing and development."""
    
    def __init__(self, dimension: int = 1536):
        self.dimension = dimension
        self.records: Dict[str, Dict[str, VectorRecord]] = {}  # namespace -> id -> record
        self._default_namespace = "default"
    
    async def upsert(
        self,
        records: List[VectorRecord],
        namespace: Optional[str] = None
    ) -> bool:
        """Upsert vector records to memory."""
        ns = namespace or self._default_namespace
        
        if ns not in self.records:
            self.records[ns] = {}
        
        for record in records:
            if len(record.vector) != self.dimension:
                logger.warning(f"Vector dimension mismatch: expected {self.dimension}, got {len(record.vector)}")
                continue
            
            # Store with lineage tracking
            record.namespace = ns
            self.records[ns][record.id] = record
        
        logger.debug(f"Upserted {len(records)} vectors to namespace '{ns}'")
        return True
    
    async def query(
        self,
        vector: List[float],
        top_k: int = 10,
        namespace: Optional[str] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SimilarityResult]:
        """Query for similar vectors using cosine similarity."""
        ns = namespace or self._default_namespace
        
        if ns not in self.records or len(self.records[ns]) == 0:
            return []
        
        if len(vector) != self.dimension:
            logger.warning(f"Query vector dimension mismatch: expected {self.dimension}, got {len(vector)}")
            return []
        
        # Calculate similarities
        similarities = []
        query_array = np.array(vector)
        query_norm = np.linalg.norm(query_array)
        
        for record_id, record in self.records[ns].items():
            # Apply metadata filter if provided
            if filter_metadata:
                if not all(
                    record.metadata.get(k) == v 
                    for k, v in filter_metadata.items()
                ):
                    continue
            
            # Calculate cosine similarity
            record_array = np.array(record.vector)
            record_norm = np.linalg.norm(record_array)
            
            if query_norm == 0 or record_norm == 0:
                similarity = 0.0
            else:
                similarity = np.dot(query_array, record_array) / (query_norm * record_norm)
            
            similarities.append(SimilarityResult(
                id=record.id,
                score=float(similarity),
                metadata=record.metadata.copy(),
                lineage_id=record.lineage_id,
                namespace=record.namespace
            ))
        
        # Sort by similarity score (descending) and return top-k
        similarities.sort(key=lambda x: x.score, reverse=True)
        return similarities[:top_k]
    
    async def delete(
        self,
        ids: List[str],
        namespace: Optional[str] = None
    ) -> bool:
        """Delete vectors by IDs."""
        ns = namespace or self._default_namespace
        
        if ns not in self.records:
            return True
        
        deleted_count = 0
        for vector_id in ids:
            if vector_id in self.records[ns]:
                del self.records[ns][vector_id]
                deleted_count += 1
        
        logger.debug(f"Deleted {deleted_count} vectors from namespace '{ns}'")
        return True
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        total_vectors = sum(len(records) for records in self.records.values())
        
        return {
            "store_type": "in_memory",
            "dimension": self.dimension,
            "total_vectors": total_vectors,
            "namespaces": list(self.records.keys()),
            "namespace_counts": {
                ns: len(records) for ns, records in self.records.items()
            }
        }


class PineconeVectorStore(VectorStore):
    """Pinecone vector store implementation."""
    
    def __init__(
        self,
        api_key: str,
        environment: str,
        index_name: str,
        dimension: int = 1536
    ):
        self.api_key = api_key
        self.environment = environment
        self.index_name = index_name
        self.dimension = dimension
        self._client = None
        self._index = None
    
    async def _initialize(self):
        """Initialize Pinecone client (mock implementation)."""
        if self._client is None:
            # Mock Pinecone client for demonstration
            logger.info(f"Initializing Pinecone client for index: {self.index_name}")
            self._client = MockPineconeClient(self.api_key, self.environment)
            self._index = self._client.Index(self.index_name)
    
    async def upsert(
        self,
        records: List[VectorRecord],
        namespace: Optional[str] = None
    ) -> bool:
        """Upsert vectors to Pinecone."""
        await self._initialize()
        
        # Convert to Pinecone format
        pinecone_records = []
        for record in records:
            pinecone_record = {
                "id": record.id,
                "values": record.vector,
                "metadata": {
                    **record.metadata,
                    "lineage_id": record.lineage_id,
                    "timestamp": record.timestamp.isoformat()
                }
            }
            pinecone_records.append(pinecone_record)
        
        # Mock upsert operation
        result = await self._index.upsert(
            vectors=pinecone_records,
            namespace=namespace
        )
        
        logger.info(f"Upserted {len(records)} vectors to Pinecone namespace '{namespace}'")
        return result.get("upserted_count", 0) == len(records)
    
    async def query(
        self,
        vector: List[float],
        top_k: int = 10,
        namespace: Optional[str] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SimilarityResult]:
        """Query Pinecone for similar vectors."""
        await self._initialize()
        
        # Mock query operation
        result = await self._index.query(
            vector=vector,
            top_k=top_k,
            namespace=namespace,
            filter=filter_metadata,
            include_metadata=True
        )
        
        # Convert results
        similarities = []
        for match in result.get("matches", []):
            similarities.append(SimilarityResult(
                id=match["id"],
                score=match["score"],
                metadata=match.get("metadata", {}),
                lineage_id=match.get("metadata", {}).get("lineage_id"),
                namespace=namespace
            ))
        
        return similarities
    
    async def delete(
        self,
        ids: List[str],
        namespace: Optional[str] = None
    ) -> bool:
        """Delete vectors from Pinecone."""
        await self._initialize()
        
        result = await self._index.delete(ids=ids, namespace=namespace)
        return result.get("deleted_count", 0) > 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Pinecone index statistics."""
        await self._initialize()
        
        stats = await self._index.describe_index_stats()
        return {
            "store_type": "pinecone",
            "index_name": self.index_name,
            "dimension": self.dimension,
            "total_vectors": stats.get("total_vector_count", 0),
            "namespaces": stats.get("namespaces", {})
        }


class MockPineconeClient:
    """Mock Pinecone client for demonstration."""
    
    def __init__(self, api_key: str, environment: str):
        self.api_key = api_key
        self.environment = environment
    
    def Index(self, index_name: str):
        return MockPineconeIndex(index_name)


class MockPineconeIndex:
    """Mock Pinecone index for demonstration."""
    
    def __init__(self, index_name: str):
        self.index_name = index_name
        self._storage = InMemoryVectorStore()
    
    async def upsert(self, vectors: List[Dict], namespace: Optional[str] = None):
        """Mock upsert operation."""
        records = []
        for v in vectors:
            records.append(VectorRecord(
                id=v["id"],
                vector=v["values"],
                metadata=v.get("metadata", {}),
                lineage_id=v.get("metadata", {}).get("lineage_id"),
                namespace=namespace
            ))
        
        await self._storage.upsert(records, namespace)
        return {"upserted_count": len(vectors)}
    
    async def query(
        self,
        vector: List[float],
        top_k: int = 10,
        namespace: Optional[str] = None,
        filter: Optional[Dict] = None,
        include_metadata: bool = True
    ):
        """Mock query operation."""
        results = await self._storage.query(
            vector=vector,
            top_k=top_k,
            namespace=namespace,
            filter_metadata=filter
        )
        
        matches = []
        for result in results:
            match = {
                "id": result.id,
                "score": result.score
            }
            if include_metadata:
                match["metadata"] = result.metadata
            matches.append(match)
        
        return {"matches": matches}
    
    async def delete(self, ids: List[str], namespace: Optional[str] = None):
        """Mock delete operation."""
        await self._storage.delete(ids, namespace)
        return {"deleted_count": len(ids)}
    
    async def describe_index_stats(self):
        """Mock stats operation."""
        stats = await self._storage.get_stats()
        return {
            "total_vector_count": stats["total_vectors"],
            "namespaces": stats["namespace_counts"]
        }


class PgVectorStore(VectorStore):
    """PostgreSQL with pgvector extension implementation."""
    
    def __init__(
        self,
        connection_string: str,
        table_name: str = "embeddings",
        dimension: int = 1536
    ):
        self.connection_string = connection_string
        self.table_name = table_name
        self.dimension = dimension
        self._pool = None
    
    async def _initialize(self):
        """Initialize PostgreSQL connection pool."""
        if self._pool is None:
            # Mock connection pool for demonstration
            logger.info(f"Initializing pgvector connection to table: {self.table_name}")
            self._pool = MockPostgresPool(self.connection_string)
    
    async def upsert(
        self,
        records: List[VectorRecord],
        namespace: Optional[str] = None
    ) -> bool:
        """Upsert vectors to PostgreSQL with pgvector."""
        await self._initialize()
        
        # Mock SQL operations
        for record in records:
            await self._pool.execute(
                f"""
                INSERT INTO {self.table_name} 
                (id, vector, metadata, lineage_id, namespace, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id, namespace) DO UPDATE SET
                vector = EXCLUDED.vector,
                metadata = EXCLUDED.metadata,
                lineage_id = EXCLUDED.lineage_id,
                timestamp = EXCLUDED.timestamp
                """,
                record.id,
                record.vector,
                json.dumps(record.metadata),
                record.lineage_id,
                namespace,
                record.timestamp
            )
        
        logger.info(f"Upserted {len(records)} vectors to pgvector table '{self.table_name}'")
        return True
    
    async def query(
        self,
        vector: List[float],
        top_k: int = 10,
        namespace: Optional[str] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SimilarityResult]:
        """Query pgvector for similar vectors using cosine similarity."""
        await self._initialize()
        
        # Mock pgvector similarity search
        where_clause = "WHERE 1=1"
        params = [vector, top_k]
        
        if namespace:
            where_clause += " AND namespace = $3"
            params.append(namespace)
        
        if filter_metadata:
            # Mock metadata filtering
            where_clause += " AND metadata @> $4"
            params.append(json.dumps(filter_metadata))
        
        query = f"""
        SELECT id, vector, metadata, lineage_id, namespace,
               1 - (vector <=> $1) as cosine_similarity
        FROM {self.table_name}
        {where_clause}
        ORDER BY vector <=> $1
        LIMIT $2
        """
        
        # Mock query execution
        results = await self._pool.fetch(query, *params)
        
        similarities = []
        for row in results:
            similarities.append(SimilarityResult(
                id=row["id"],
                score=row["cosine_similarity"],
                metadata=json.loads(row["metadata"]),
                lineage_id=row["lineage_id"],
                namespace=row["namespace"]
            ))
        
        return similarities
    
    async def delete(
        self,
        ids: List[str],
        namespace: Optional[str] = None
    ) -> bool:
        """Delete vectors from PostgreSQL."""
        await self._initialize()
        
        where_clause = "WHERE id = ANY($1)"
        params = [ids]
        
        if namespace:
            where_clause += " AND namespace = $2"
            params.append(namespace)
        
        query = f"DELETE FROM {self.table_name} {where_clause}"
        result = await self._pool.execute(query, *params)
        
        logger.info(f"Deleted vectors from pgvector table '{self.table_name}'")
        return True
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get pgvector table statistics."""
        await self._initialize()
        
        # Mock stats query
        stats_query = f"""
        SELECT 
            COUNT(*) as total_vectors,
            COUNT(DISTINCT namespace) as namespace_count,
            namespace,
            COUNT(*) as count
        FROM {self.table_name}
        GROUP BY namespace
        """
        
        rows = await self._pool.fetch(stats_query)
        
        total_vectors = sum(row["count"] for row in rows)
        namespace_counts = {row["namespace"]: row["count"] for row in rows}
        
        return {
            "store_type": "pgvector",
            "table_name": self.table_name,
            "dimension": self.dimension,
            "total_vectors": total_vectors,
            "namespaces": list(namespace_counts.keys()),
            "namespace_counts": namespace_counts
        }


class MockPostgresPool:
    """Mock PostgreSQL connection pool."""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._storage = InMemoryVectorStore()
    
    async def execute(self, query: str, *params):
        """Mock SQL execution."""
        logger.debug(f"Mock SQL: {query[:100]}... with {len(params)} params")
        return "OK"
    
    async def fetch(self, query: str, *params):
        """Mock SQL fetch."""
        logger.debug(f"Mock SQL fetch: {query[:100]}... with {len(params)} params")
        
        # Return mock results for stats query
        if "GROUP BY namespace" in query:
            return [
                {"namespace": "default", "count": 100},
                {"namespace": "documents", "count": 250}
            ]
        
        # Return mock similarity results
        return [
            {
                "id": f"mock_result_{i}",
                "vector": [0.1] * 1536,
                "metadata": '{"source": "mock"}',
                "lineage_id": f"lineage_{i}",
                "namespace": "default",
                "cosine_similarity": 0.9 - (i * 0.1)
            }
            for i in range(min(10, len(params) > 1 and params[1] or 10))
        ]


class VectorStoreManager:
    """Manager for vector store operations with lineage tracking."""
    
    def __init__(
        self,
        store_type: VectorStoreType = VectorStoreType.IN_MEMORY,
        config: Optional[Dict[str, Any]] = None
    ):
        self.store_type = store_type
        self.config = config or {}
        self.store = self._create_store()
        
        # Embedding function (mock)
        self._embedding_model = "text-embedding-3-small"  # Mock OpenAI model
    
    def _create_store(self) -> VectorStore:
        """Create vector store based on type."""
        if self.store_type == VectorStoreType.IN_MEMORY:
            return InMemoryVectorStore(
                dimension=self.config.get("dimension", 1536)
            )
        elif self.store_type == VectorStoreType.PINECONE:
            return PineconeVectorStore(
                api_key=self.config["api_key"],
                environment=self.config["environment"],
                index_name=self.config["index_name"],
                dimension=self.config.get("dimension", 1536)
            )
        elif self.store_type == VectorStoreType.PGVECTOR:
            return PgVectorStore(
                connection_string=self.config["connection_string"],
                table_name=self.config.get("table_name", "embeddings"),
                dimension=self.config.get("dimension", 1536)
            )
        else:
            raise ValueError(f"Unsupported vector store type: {self.store_type}")
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embeddings for text (mock implementation)."""
        # Mock embedding generation using text hash
        import hashlib
        
        # Create a deterministic but varied embedding based on text content
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        # Convert hash to numerical values and normalize
        embedding = []
        for i in range(0, len(text_hash), 2):
            hex_val = text_hash[i:i+2]
            embedding.append(int(hex_val, 16) / 255.0)
        
        # Pad or truncate to desired dimension
        dimension = self.config.get("dimension", 1536)
        while len(embedding) < dimension:
            embedding.extend(embedding[:min(len(embedding), dimension - len(embedding))])
        
        embedding = embedding[:dimension]
        
        # Add some randomness based on text content
        import random
        random.seed(hash(text) % 2**32)
        noise = [random.gauss(0, 0.01) for _ in range(dimension)]
        embedding = [e + n for e, n in zip(embedding, noise)]
        
        # Normalize to unit vector
        norm = sum(x**2 for x in embedding) ** 0.5
        if norm > 0:
            embedding = [x / norm for x in embedding]
        
        return embedding
    
    async def store_embeddings(
        self,
        documents: List[Dict[str, Any]],
        namespace: Optional[str] = None,
        lineage_id: Optional[str] = None
    ) -> List[str]:
        """Store document embeddings with lineage tracking."""
        records = []
        stored_ids = []
        
        for doc in documents:
            # Generate embedding for document text
            text = doc.get("text", "")
            embedding = await self.embed_text(text)
            
            # Create vector record
            record_id = doc.get("id", str(uuid.uuid4()))
            record = VectorRecord(
                id=record_id,
                vector=embedding,
                metadata={
                    "title": doc.get("title", ""),
                    "source": doc.get("source", ""),
                    "document_type": doc.get("type", "text"),
                    "char_count": len(text),
                    **doc.get("metadata", {})
                },
                lineage_id=lineage_id or str(uuid.uuid4()),
                namespace=namespace
            )
            
            records.append(record)
            stored_ids.append(record_id)
        
        # Store in vector store
        success = await self.store.upsert(records, namespace)
        
        if success:
            logger.info(f"Stored {len(records)} embeddings with lineage ID: {lineage_id}")
        else:
            logger.error(f"Failed to store embeddings")
        
        return stored_ids if success else []
    
    async def similarity_search(
        self,
        query_text: str,
        top_k: int = 10,
        namespace: Optional[str] = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
        lineage_id: Optional[str] = None
    ) -> List[SimilarityResult]:
        """Perform similarity search with lineage tracking."""
        # Generate query embedding
        query_embedding = await self.embed_text(query_text)
        
        # Search vector store
        results = await self.store.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=namespace,
            filter_metadata=filter_metadata
        )
        
        # Log search for lineage tracking
        if lineage_id:
            logger.info(f"Similarity search performed with lineage ID: {lineage_id}")
            logger.debug(f"Query: '{query_text[:100]}...', Results: {len(results)}")
        
        return results
    
    async def update_embeddings(
        self,
        updates: List[Dict[str, Any]],
        namespace: Optional[str] = None,
        lineage_id: Optional[str] = None
    ) -> bool:
        """Update existing embeddings."""
        return await self.store_embeddings(updates, namespace, lineage_id)
    
    async def delete_embeddings(
        self,
        ids: List[str],
        namespace: Optional[str] = None
    ) -> bool:
        """Delete embeddings by IDs."""
        return await self.store.delete(ids, namespace)
    
    async def get_store_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        stats = await self.store.get_stats()
        stats["embedding_model"] = self._embedding_model
        return stats
    
    async def create_retrieval_tool(
        self,
        namespace: Optional[str] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """Create a retrieval tool configuration for agent use."""
        return {
            "type": "function",
            "function": {
                "name": "vector_search",
                "description": f"Search for relevant documents using semantic similarity",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query text"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": f"Number of results to return (default: {top_k})",
                            "default": top_k
                        },
                        "filter": {
                            "type": "object",
                            "description": "Metadata filters to apply"
                        }
                    },
                    "required": ["query"]
                }
            },
            "implementation": {
                "manager": self,
                "namespace": namespace,
                "default_top_k": top_k
            }
        }


# Tool function for agent integration
async def vector_search_tool(
    query: str,
    manager: VectorStoreManager,
    namespace: Optional[str] = None,
    top_k: int = 5,
    filter_metadata: Optional[Dict[str, Any]] = None,
    lineage_id: Optional[str] = None
) -> Dict[str, Any]:
    """Vector search tool for agent use."""
    try:
        results = await manager.similarity_search(
            query_text=query,
            top_k=top_k,
            namespace=namespace,
            filter_metadata=filter_metadata,
            lineage_id=lineage_id
        )
        
        return {
            "success": True,
            "query": query,
            "results_count": len(results),
            "results": [
                {
                    "id": r.id,
                    "score": r.score,
                    "content": r.metadata.get("title", ""),
                    "source": r.metadata.get("source", ""),
                    "lineage_id": r.lineage_id
                }
                for r in results
            ]
        }
    
    except Exception as e:
        logger.error(f"Vector search tool error: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query
        }