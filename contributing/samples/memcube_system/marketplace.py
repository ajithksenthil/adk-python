"""Data marketplace integration for MemCube memory packs."""

import json
import logging
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import asyncio

from .models import (
    MemCube, MemoryPack, MemoryType, MemoryGovernance,
    MemCubeHeader, MemCubePayload
)
from .storage import MemCubeStorage
from .operator import MemoryOperator

logger = logging.getLogger(__name__)


class MemPackPublisher:
    """
    Publishes memory packs to the data marketplace.
    
    Handles:
    - Pack creation and validation
    - Watermarking
    - Pricing and royalties
    - Publishing workflow
    """
    
    def __init__(self, storage: MemCubeStorage, marketplace_api: str):
        self.storage = storage
        self.marketplace_api = marketplace_api
        
    async def create_pack(self, author_id: str, title: str,
                         description: str, memory_ids: List[str],
                         price_cents: int = 0,
                         royalty_pct: int = 10,
                         cover_img: Optional[str] = None) -> MemoryPack:
        """Create a new memory pack for publishing."""
        # Validate memories exist and author has access
        valid_memories = await self._validate_memories(memory_ids, author_id)
        
        if not valid_memories:
            raise ValueError("No valid memories for pack")
            
        # Create pack
        pack = MemoryPack(
            author_id=author_id,
            title=title,
            description=description,
            cover_img=cover_img,
            price_cents=price_cents,
            royalty_pct=royalty_pct,
            watermark=price_cents > 0,  # Watermark paid packs
            memory_ids=valid_memories
        )
        
        logger.info(f"Created memory pack '{title}' with {len(valid_memories)} memories")
        return pack
        
    async def publish_pack(self, pack: MemoryPack) -> str:
        """
        Publish pack to marketplace.
        
        Returns marketplace listing ID.
        """
        # Prepare memories for distribution
        if pack.watermark:
            await self._watermark_memories(pack)
            
        # Create marketplace listing
        listing_data = {
            "id": pack.id,
            "author_id": pack.author_id,
            "title": pack.title,
            "description": pack.description,
            "cover_img": pack.cover_img,
            "price_cents": pack.price_cents,
            "royalty_pct": pack.royalty_pct,
            "memory_count": len(pack.memory_ids),
            "created_at": pack.created_at.isoformat(),
            "tags": self._extract_pack_tags(pack)
        }
        
        # TODO: Call marketplace API
        # response = await self._post_to_marketplace(listing_data)
        
        # Store pack metadata
        await self._store_pack_metadata(pack)
        
        logger.info(f"Published pack {pack.id} to marketplace")
        return pack.id
        
    async def _validate_memories(self, memory_ids: List[str], 
                               author_id: str) -> List[str]:
        """Validate memories for pack inclusion."""
        valid_ids = []
        
        for memory_id in memory_ids:
            memory = await self.storage.get_memory(memory_id)
            if not memory:
                continue
                
            # Check ownership or shareable
            if (memory.header.created_by == author_id or
                memory.header.governance.shareable):
                valid_ids.append(memory_id)
            else:
                logger.warning(f"Memory {memory_id} not accessible to {author_id}")
                
        return valid_ids
        
    async def _watermark_memories(self, pack: MemoryPack) -> None:
        """Add watermarks to pack memories."""
        watermark = self._generate_watermark(pack)
        
        for memory_id in pack.memory_ids:
            memory = await self.storage.get_memory(memory_id)
            if memory and memory.type == MemoryType.PLAINTEXT:
                # Add watermark to content
                watermarked_content = f"{memory.payload.content}\n\n{watermark}"
                
                # Update memory
                memory.payload.content = watermarked_content
                memory.header.watermark = True
                
                # Store updated version
                await self.storage.store_memory(memory)
                
    def _generate_watermark(self, pack: MemoryPack) -> str:
        """Generate watermark for pack."""
        return f"\n--- Memory Pack: {pack.title} | Author: {pack.author_id} | {pack.id[:8]} ---"
        
    def _extract_pack_tags(self, pack: MemoryPack) -> List[str]:
        """Extract tags from pack title and description."""
        text = f"{pack.title} {pack.description}".lower()
        # Simple tag extraction - could use NLP
        common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
        words = text.split()
        tags = [w for w in words if len(w) > 3 and w not in common_words]
        return list(set(tags))[:10]  # Limit tags
        
    async def _store_pack_metadata(self, pack: MemoryPack) -> None:
        """Store pack metadata for tracking."""
        # TODO: Store in database
        pass


class MemPackImporter:
    """
    Imports memory packs from marketplace.
    
    Handles:
    - Pack discovery and search
    - Purchase flow
    - Import and integration
    - License compliance
    """
    
    def __init__(self, storage: MemCubeStorage, operator: MemoryOperator,
                 marketplace_api: str):
        self.storage = storage
        self.operator = operator
        self.marketplace_api = marketplace_api
        
    async def search_packs(self, query: str, 
                          max_price_cents: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search marketplace for memory packs."""
        # TODO: Call marketplace search API
        # results = await self._search_marketplace(query, max_price_cents)
        
        # Mock results for now
        results = [
            {
                "id": "pack-001",
                "title": "React Best Practices",
                "description": "Curated React patterns and practices",
                "author": "expert-dev",
                "price_cents": 500,
                "memory_count": 25,
                "rating": 4.8
            }
        ]
        
        return results
        
    async def import_pack(self, pack_id: str, project_id: str,
                         buyer_id: str) -> List[str]:
        """
        Import a memory pack into project.
        
        Returns list of imported memory IDs.
        """
        # Get pack details
        pack_data = await self._get_pack_details(pack_id)
        
        # Handle payment if needed
        if pack_data.get("price_cents", 0) > 0:
            if not await self._process_payment(pack_id, buyer_id, pack_data["price_cents"]):
                raise ValueError("Payment failed")
                
        # Download pack memories
        pack_memories = await self._download_pack_memories(pack_id)
        
        # Import memories into project
        imported_ids = []
        for memory_data in pack_memories:
            imported = await self._import_memory(memory_data, project_id, buyer_id)
            if imported:
                imported_ids.append(imported.id)
                
        # Track royalties
        if pack_data.get("royalty_pct", 0) > 0:
            await self._track_royalty(pack_id, pack_data["author_id"], 
                                    pack_data["royalty_pct"])
                                    
        logger.info(f"Imported {len(imported_ids)} memories from pack {pack_id}")
        return imported_ids
        
    async def _get_pack_details(self, pack_id: str) -> Dict[str, Any]:
        """Get pack details from marketplace."""
        # TODO: Call marketplace API
        return {
            "id": pack_id,
            "title": "Sample Pack",
            "author_id": "author-123",
            "price_cents": 0,
            "royalty_pct": 10,
            "memory_count": 5
        }
        
    async def _process_payment(self, pack_id: str, buyer_id: str,
                             price_cents: int) -> bool:
        """Process payment for pack."""
        # TODO: Integrate payment system
        logger.info(f"Processing payment of ${price_cents/100} for {buyer_id}")
        return True
        
    async def _download_pack_memories(self, pack_id: str) -> List[Dict[str, Any]]:
        """Download memories from pack."""
        # TODO: Download from marketplace storage
        # Mock data for now
        return [
            {
                "label": "react-hooks-best-practices",
                "type": "PLAINTEXT",
                "content": "Best practices for React hooks...",
                "tags": ["react", "hooks", "frontend"]
            }
        ]
        
    async def _import_memory(self, memory_data: Dict[str, Any],
                           project_id: str, imported_by: str) -> Optional[MemCube]:
        """Import a single memory into project."""
        try:
            # Create memory from imported data
            memory = await self.operator.create_from_text(
                project_id=project_id,
                label=f"imported::{memory_data['label']}",
                content=memory_data["content"],
                created_by=imported_by,
                tags=memory_data.get("tags", [])
            )
            
            # Set origin to track import
            memory.header.origin = f"marketplace_import::{memory_data.get('pack_id', 'unknown')}"
            
            return memory
            
        except Exception as e:
            logger.error(f"Failed to import memory: {e}")
            return None
            
    async def _track_royalty(self, pack_id: str, author_id: str,
                           royalty_pct: int) -> None:
        """Track royalty for pack usage."""
        # TODO: Implement royalty tracking
        logger.info(f"Tracking {royalty_pct}% royalty for {author_id} on pack {pack_id}")


class MarketplaceService:
    """
    Main marketplace service coordinating publishing and importing.
    
    Provides high-level marketplace operations.
    """
    
    def __init__(self, storage: MemCubeStorage, operator: MemoryOperator,
                 marketplace_api: str):
        self.storage = storage
        self.operator = operator
        self.publisher = MemPackPublisher(storage, marketplace_api)
        self.importer = MemPackImporter(storage, operator, marketplace_api)
        
    async def create_and_publish_pack(self, author_id: str, project_id: str,
                                    pack_config: Dict[str, Any]) -> str:
        """Create and publish a memory pack."""
        # Select memories for pack
        memory_ids = await self._select_pack_memories(
            project_id,
            pack_config.get("tags", []),
            pack_config.get("max_memories", 50)
        )
        
        # Create pack
        pack = await self.publisher.create_pack(
            author_id=author_id,
            title=pack_config["title"],
            description=pack_config["description"],
            memory_ids=memory_ids,
            price_cents=pack_config.get("price_cents", 0),
            royalty_pct=pack_config.get("royalty_pct", 10),
            cover_img=pack_config.get("cover_img")
        )
        
        # Publish to marketplace
        listing_id = await self.publisher.publish_pack(pack)
        
        return listing_id
        
    async def discover_and_import_packs(self, project_id: str,
                                      search_query: str,
                                      buyer_id: str,
                                      auto_import: bool = False) -> List[Dict[str, Any]]:
        """Discover and optionally import relevant packs."""
        # Search marketplace
        packs = await self.importer.search_packs(search_query)
        
        # Score packs by relevance
        scored_packs = await self._score_pack_relevance(packs, project_id)
        
        # Auto-import top free packs if requested
        imported = []
        if auto_import:
            for pack in scored_packs[:3]:  # Top 3
                if pack.get("price_cents", 0) == 0:  # Free only
                    try:
                        memory_ids = await self.importer.import_pack(
                            pack["id"], project_id, buyer_id
                        )
                        imported.append({
                            "pack_id": pack["id"],
                            "title": pack["title"],
                            "memory_count": len(memory_ids)
                        })
                    except Exception as e:
                        logger.error(f"Failed to import pack {pack['id']}: {e}")
                        
        return imported if auto_import else scored_packs
        
    async def _select_pack_memories(self, project_id: str,
                                  tags: List[str],
                                  limit: int) -> List[str]:
        """Select memories for pack based on criteria."""
        from .models import MemoryQuery
        
        query = MemoryQuery(
            project_id=project_id,
            tags=tags,
            limit=limit
        )
        
        memories = await self.storage.query_memories(query)
        
        # Filter for shareable memories
        shareable = [m for m in memories if m.header.governance.shareable]
        
        return [m.id for m in shareable]
        
    async def _score_pack_relevance(self, packs: List[Dict[str, Any]],
                                  project_id: str) -> List[Dict[str, Any]]:
        """Score packs by relevance to project."""
        # TODO: Implement relevance scoring based on:
        # - Project tags/context
        # - Current memories
        # - User preferences
        
        # For now, return as-is
        return packs
        
    async def get_pack_analytics(self, author_id: str) -> Dict[str, Any]:
        """Get analytics for author's published packs."""
        # TODO: Implement analytics
        return {
            "total_packs": 0,
            "total_downloads": 0,
            "revenue_cents": 0,
            "avg_rating": 0.0
        }