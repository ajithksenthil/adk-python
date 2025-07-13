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

"""Data Architecture Orchestrator - Coordinates vector stores, data layers, and feature store."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import uuid

try:
    from .vector_store import VectorStoreManager, VectorStoreType
    from .data_layers import DataLayerManager, DataQualityLevel, StorageBackend
    from .feature_store import FeatureStoreManager, StorageMode
except ImportError:
    from vector_store import VectorStoreManager, VectorStoreType
    from data_layers import DataLayerManager, DataQualityLevel, StorageBackend
    from feature_store import FeatureStoreManager, StorageMode

if TYPE_CHECKING:
    from data_mesh.event_bus import EventBus
    from data_mesh.lineage_service import LineageService

logger = logging.getLogger(__name__)


class DataArchitectureOrchestrator:
    """Main orchestrator for data architecture components."""
    
    def __init__(
        self,
        vector_store_config: Optional[Dict[str, Any]] = None,
        data_layer_config: Optional[Dict[str, Any]] = None,
        feature_store_config: Optional[Dict[str, Any]] = None,
        event_bus: Optional["EventBus"] = None,
        lineage_service: Optional["LineageService"] = None
    ):
        # Initialize core components
        self.vector_store_manager = self._init_vector_store(vector_store_config)
        self.data_layer_manager = self._init_data_layers(data_layer_config)
        self.feature_store_manager = self._init_feature_store(feature_store_config)
        
        # Integration components
        self.event_bus = event_bus
        self.lineage_service = lineage_service
        
        # Orchestration state
        self._initialized = False
        self._sync_tasks = {}
    
    def _init_vector_store(self, config: Optional[Dict[str, Any]]) -> VectorStoreManager:
        """Initialize vector store manager."""
        config = config or {}
        store_type = VectorStoreType(config.get("type", "in_memory"))
        
        return VectorStoreManager(
            store_type=store_type,
            config=config
        )
    
    def _init_data_layers(self, config: Optional[Dict[str, Any]]) -> DataLayerManager:
        """Initialize data layer manager."""
        config = config or {}
        storage_backend = StorageBackend(config.get("backend", "local"))
        
        return DataLayerManager(
            storage_backend=storage_backend,
            storage_config=config
        )
    
    def _init_feature_store(self, config: Optional[Dict[str, Any]]) -> FeatureStoreManager:
        """Initialize feature store manager."""
        return FeatureStoreManager()
    
    async def initialize(self):
        """Initialize the data architecture orchestrator."""
        if self._initialized:
            return
        
        logger.info("Initializing Data Architecture Orchestrator")
        
        # Setup event bus integration
        if self.event_bus:
            await self._setup_event_integration()
        
        # Start background sync tasks
        await self._start_sync_tasks()
        
        self._initialized = True
        logger.info("Data Architecture Orchestrator initialized successfully")
    
    async def shutdown(self):
        """Shutdown the orchestrator."""
        if not self._initialized:
            return
        
        logger.info("Shutting down Data Architecture Orchestrator")
        
        # Stop sync tasks
        for task_name, task in self._sync_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self._sync_tasks.clear()
        self._initialized = False
        logger.info("Data Architecture Orchestrator shutdown complete")
    
    async def _setup_event_integration(self):
        """Setup integration with event bus."""
        if not self.event_bus:
            return
        
        try:
            # Import event bus components
            from data_mesh.event_bus import Topics, EventHandler, EventType
            
            # Setup event handlers for data flow
            async def handle_data_ingestion_event(event):
                """Handle data ingestion events."""
                await self._process_ingestion_event(event)
            
            # Subscribe to data ingestion events (if topic exists)
            ingestion_handler = EventHandler(handler_func=handle_data_ingestion_event)
            
            # Check if DATA_INGESTION topic exists
            if hasattr(Topics, 'DATA_INGESTION'):
                await self.event_bus.subscribe(Topics.DATA_INGESTION, ingestion_handler)
            else:
                # Use existing topic for demo
                await self.event_bus.subscribe(Topics.AUDIT, ingestion_handler)
            
            logger.info("Data architecture event integration configured")
        
        except (ImportError, AttributeError) as e:
            logger.warning(f"Event bus integration not available: {e}")
    
    async def _start_sync_tasks(self):
        """Start background synchronization tasks."""
        # Feature store sync task
        self._sync_tasks["feature_sync"] = asyncio.create_task(
            self._feature_sync_loop()
        )
        
        # Vector-feature sync task
        self._sync_tasks["vector_feature_sync"] = asyncio.create_task(
            self._vector_feature_sync_loop()
        )
        
        logger.info("Background sync tasks started")
    
    async def _feature_sync_loop(self):
        """Background task to sync offline features to online store."""
        while True:
            try:
                # Sync all feature groups every hour
                for feature_group_name in self.feature_store_manager.list_feature_groups():
                    await self.feature_store_manager.sync_online_offline(feature_group_name)
                
                # Wait 1 hour before next sync
                await asyncio.sleep(3600)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Feature sync error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _vector_feature_sync_loop(self):
        """Background task to sync vectors with feature store."""
        while True:
            try:
                # Sync vector embeddings with feature metadata every 6 hours
                await self._sync_vectors_with_features()
                
                # Wait 6 hours before next sync
                await asyncio.sleep(21600)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Vector-feature sync error: {e}")
                await asyncio.sleep(600)  # Wait 10 minutes on error
    
    async def _process_ingestion_event(self, event):
        """Process data ingestion event."""
        try:
            payload = event.payload
            source_system = payload.get("source_system")
            data_type = payload.get("data_type")
            lineage_id = event.metadata.trace_id
            
            logger.info(f"Processing ingestion event: {source_system} -> {data_type}")
            
            # Track lineage if service available
            if self.lineage_service:
                await self.lineage_service.track_data_ingestion(
                    source_system=source_system,
                    data_type=data_type,
                    lineage_id=lineage_id
                )
        
        except Exception as e:
            logger.error(f"Error processing ingestion event: {e}")
    
    async def ingest_data_flow(
        self,
        raw_data: List[Dict[str, Any]],
        source_system: str,
        data_type: str,
        bronze_table: str,
        create_embeddings: bool = True,
        create_features: bool = True
    ) -> Dict[str, Any]:
        """Execute full data ingestion flow: Bronze -> Silver -> Gold + Vectors + Features."""
        flow_id = str(uuid.uuid4())
        lineage_id = str(uuid.uuid4())
        
        logger.info(f"Starting data flow {flow_id} for {source_system}")
        
        try:
            # Step 1: Ingest to Bronze layer
            bronze_lineage = await self.data_layer_manager.ingest_raw_data(
                data=raw_data,
                source_system=source_system,
                table_name=bronze_table,
                lineage_id=lineage_id
            )
            
            if not bronze_lineage:
                return {"success": False, "error": "Bronze ingestion failed", "flow_id": flow_id}
            
            # Step 2: Process to Silver layer
            silver_table = f"{bronze_table}_silver"
            silver_success = await self.data_layer_manager.process_bronze_to_silver(
                bronze_table=bronze_table,
                silver_table=silver_table
            )
            
            if not silver_success:
                return {"success": False, "error": "Silver processing failed", "flow_id": flow_id}
            
            # Step 3: Create Gold marts
            gold_results = await self.data_layer_manager.create_gold_marts(
                silver_table=silver_table
            )
            
            # Step 4: Create vector embeddings if requested
            vector_results = {}
            if create_embeddings:
                vector_results = await self._create_embeddings_from_data(
                    raw_data, data_type, lineage_id
                )
            
            # Step 5: Materialize features if requested
            feature_results = {}
            if create_features:
                feature_results = await self._materialize_features_from_data(
                    raw_data, data_type, lineage_id
                )
            
            # Publish success event
            if self.event_bus:
                await self._publish_flow_completion_event(
                    flow_id, source_system, data_type, lineage_id, True
                )
            
            return {
                "success": True,
                "flow_id": flow_id,
                "lineage_id": lineage_id,
                "bronze_records": len(raw_data),
                "silver_processed": silver_success,
                "gold_marts": gold_results,
                "vector_embeddings": vector_results,
                "features": feature_results
            }
        
        except Exception as e:
            logger.error(f"Data flow {flow_id} failed: {e}")
            
            # Publish failure event
            if self.event_bus:
                await self._publish_flow_completion_event(
                    flow_id, source_system, data_type, lineage_id, False, str(e)
                )
            
            return {"success": False, "error": str(e), "flow_id": flow_id}
    
    async def _create_embeddings_from_data(
        self,
        raw_data: List[Dict[str, Any]],
        data_type: str,
        lineage_id: str
    ) -> Dict[str, Any]:
        """Create vector embeddings from raw data."""
        try:
            # Convert raw data to documents for embedding
            documents = []
            for item in raw_data:
                # Extract text content for embedding
                text_fields = ["title", "description", "content", "text", "name"]
                text_content = ""
                
                for field in text_fields:
                    if field in item and item[field]:
                        text_content += f"{item[field]} "
                
                if not text_content.strip():
                    # Use JSON representation if no text fields found
                    text_content = json.dumps(item)
                
                doc = {
                    "id": item.get("id", str(uuid.uuid4())),
                    "text": text_content.strip(),
                    "title": item.get("title", f"{data_type} document"),
                    "source": f"{data_type}_ingestion",
                    "type": data_type,
                    "metadata": item
                }
                documents.append(doc)
            
            # Store embeddings with lineage tracking
            namespace = f"{data_type}_embeddings"
            stored_ids = await self.vector_store_manager.store_embeddings(
                documents=documents,
                namespace=namespace,
                lineage_id=lineage_id
            )
            
            return {
                "success": True,
                "documents_embedded": len(documents),
                "stored_ids": stored_ids,
                "namespace": namespace,
                "lineage_id": lineage_id
            }
        
        except Exception as e:
            logger.error(f"Vector embedding creation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _materialize_features_from_data(
        self,
        raw_data: List[Dict[str, Any]],
        data_type: str,
        lineage_id: str
    ) -> Dict[str, Any]:
        """Materialize features from raw data."""
        try:
            # Determine appropriate feature group based on data type
            feature_group_mapping = {
                "customers": "customer_features",
                "orders": "customer_features",
                "products": "product_features",
                "inventory": "product_features"
            }
            
            feature_group_name = feature_group_mapping.get(data_type)
            if not feature_group_name:
                return {"success": False, "error": f"No feature group mapping for data type: {data_type}"}
            
            # Materialize features
            success = await self.feature_store_manager.materialize_features(
                feature_group_name=feature_group_name,
                source_data=raw_data,
                storage_mode=StorageMode.BOTH
            )
            
            return {
                "success": success,
                "feature_group": feature_group_name,
                "records_processed": len(raw_data),
                "lineage_id": lineage_id
            }
        
        except Exception as e:
            logger.error(f"Feature materialization failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _sync_vectors_with_features(self):
        """Sync vector embeddings with feature store data."""
        try:
            # Get vector store stats
            vector_stats = await self.vector_store_manager.get_store_stats()
            
            # For each namespace in vector store, check if we can enrich with features
            for namespace in vector_stats.get("namespaces", []):
                if "customer" in namespace.lower():
                    await self._enrich_vectors_with_features(namespace, "customer_features")
                elif "product" in namespace.lower():
                    await self._enrich_vectors_with_features(namespace, "product_features")
            
            logger.info("Vector-feature sync completed")
        
        except Exception as e:
            logger.error(f"Vector-feature sync failed: {e}")
    
    async def _enrich_vectors_with_features(self, namespace: str, feature_group: str):
        """Enrich vector metadata with feature store data."""
        try:
            # This is a simplified implementation
            # In production, you would query vectors, extract entity IDs,
            # fetch corresponding features, and update vector metadata
            logger.debug(f"Enriching vectors in namespace '{namespace}' with features from '{feature_group}'")
        
        except Exception as e:
            logger.error(f"Vector enrichment failed for namespace '{namespace}': {e}")
    
    async def _publish_flow_completion_event(
        self,
        flow_id: str,
        source_system: str,
        data_type: str,
        lineage_id: str,
        success: bool,
        error: Optional[str] = None
    ):
        """Publish data flow completion event."""
        try:
            from data_mesh.event_bus import Event, EventMetadata, EventType, EventPriority
            
            # Use available event type
            event_type = getattr(EventType, 'DATA_FLOW_COMPLETE', EventType.TASK_COMPLETE)
            
            event = Event(
                event_type=event_type,
                metadata=EventMetadata(
                    source_pillar="Data Architecture",
                    priority=EventPriority.NORMAL,
                    trace_id=lineage_id,
                    tags={
                        "flow_id": flow_id,
                        "source_system": source_system,
                        "data_type": data_type,
                        "success": str(success)
                    }
                ),
                payload={
                    "flow_id": flow_id,
                    "source_system": source_system,
                    "data_type": data_type,
                    "lineage_id": lineage_id,
                    "success": success,
                    "error": error,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            from data_mesh.event_bus import Topics
            # Use available topic
            topic = getattr(Topics, 'DATA_FLOW', Topics.AUDIT)
            await self.event_bus.publish(topic, event)
        
        except Exception as e:
            logger.error(f"Failed to publish flow completion event: {e}")
    
    async def search_and_retrieve(
        self,
        query: str,
        include_features: bool = True,
        namespace: Optional[str] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """Unified search across vectors with optional feature enrichment."""
        try:
            # Perform vector similarity search
            search_results = await self.vector_store_manager.similarity_search(
                query_text=query,
                top_k=top_k,
                namespace=namespace,
                lineage_id=str(uuid.uuid4())
            )
            
            if not search_results:
                return {
                    "success": True,
                    "query": query,
                    "results": [],
                    "message": "No similar documents found"
                }
            
            # Enrich with features if requested
            enriched_results = []
            for result in search_results:
                enriched_result = {
                    "id": result.id,
                    "score": result.score,
                    "content": result.metadata.get("title", ""),
                    "source": result.metadata.get("source", ""),
                    "lineage_id": result.lineage_id,
                    "metadata": result.metadata
                }
                
                # Try to get features for this entity
                if include_features:
                    features = await self._get_features_for_entity(result.id, result.metadata)
                    if features:
                        enriched_result["features"] = features
                
                enriched_results.append(enriched_result)
            
            return {
                "success": True,
                "query": query,
                "results_count": len(enriched_results),
                "results": enriched_results
            }
        
        except Exception as e:
            logger.error(f"Search and retrieve failed: {e}")
            return {"success": False, "error": str(e), "query": query}
    
    async def _get_features_for_entity(
        self,
        entity_id: str,
        metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get features for an entity based on its metadata."""
        try:
            # Determine feature group based on metadata
            entity_type = metadata.get("type", "").lower()
            
            if "customer" in entity_type:
                features = await self.feature_store_manager.get_online_features(
                    feature_group_name="customer_features",
                    entity_ids=[entity_id]
                )
                return features.get(entity_id)
            
            elif "product" in entity_type:
                features = await self.feature_store_manager.get_online_features(
                    feature_group_name="product_features",
                    entity_ids=[entity_id]
                )
                return features.get(entity_id)
            
            return None
        
        except Exception as e:
            logger.warning(f"Failed to get features for entity {entity_id}: {e}")
            return None
    
    async def create_ml_training_dataset(
        self,
        feature_groups: List[str],
        include_embeddings: bool = True,
        days_back: int = 30,
        entity_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create comprehensive ML training dataset with features and embeddings."""
        try:
            dataset_id = str(uuid.uuid4())
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days_back)
            
            # Create feature training dataset
            feature_dataset = await self.feature_store_manager.create_training_dataset(
                feature_groups=feature_groups,
                entity_ids=entity_filter,
                start_time=start_time,
                end_time=end_time
            )
            
            result = {
                "dataset_id": dataset_id,
                "feature_dataset": feature_dataset,
                "embeddings": None
            }
            
            # Add embeddings if requested
            if include_embeddings:
                embeddings_data = await self._extract_embeddings_for_training(
                    entity_filter, start_time, end_time
                )
                result["embeddings"] = embeddings_data
            
            logger.info(f"Created ML training dataset: {dataset_id}")
            return {"success": True, "dataset": result}
        
        except Exception as e:
            logger.error(f"ML training dataset creation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _extract_embeddings_for_training(
        self,
        entity_filter: Optional[List[str]],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Extract embeddings for training dataset."""
        # This is a simplified implementation
        # In production, you would query the vector store for embeddings
        # created within the time range and matching entity filter
        return {
            "embedding_count": 0,
            "dimensions": 1536,
            "note": "Embedding extraction not implemented in this demo"
        }
    
    async def get_data_architecture_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive dashboard for data architecture."""
        try:
            # Get stats from all components
            vector_stats = await self.vector_store_manager.get_store_stats()
            layer_stats = await self.data_layer_manager.get_layer_stats()
            feature_stats = await self.feature_store_manager.get_feature_store_stats()
            
            return {
                "orchestrator_status": "operational" if self._initialized else "stopped",
                "sync_tasks": {
                    name: "running" if not task.done() else "stopped"
                    for name, task in self._sync_tasks.items()
                },
                "vector_store": vector_stats,
                "data_layers": layer_stats,
                "feature_store": feature_stats,
                "integration": {
                    "event_bus_connected": bool(self.event_bus),
                    "lineage_service_connected": bool(self.lineage_service),
                    "background_sync_enabled": len(self._sync_tasks) > 0
                },
                "last_updated": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Dashboard generation failed: {e}")
            return {"error": str(e)}
    
    async def create_agent_tools(self) -> List[Dict[str, Any]]:
        """Create tool configurations for agent integration."""
        tools = []
        
        try:
            # Vector search tool
            vector_tool = await self.vector_store_manager.create_retrieval_tool()
            tools.append(vector_tool)
            
            # Feature retrieval tools
            for feature_group in self.feature_store_manager.list_feature_groups():
                feature_tool = await self.feature_store_manager.create_feature_serving_function(
                    feature_group
                )
                tools.append(feature_tool)
            
            # Combined search and retrieve tool
            combined_tool = {
                "type": "function",
                "function": {
                    "name": "search_and_retrieve",
                    "description": "Search for documents and retrieve with features",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "include_features": {
                                "type": "boolean",
                                "description": "Include feature data in results",
                                "default": True
                            },
                            "namespace": {
                                "type": "string",
                                "description": "Vector store namespace to search"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of results to return",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                },
                "implementation": {
                    "orchestrator": self
                }
            }
            tools.append(combined_tool)
            
            return tools
        
        except Exception as e:
            logger.error(f"Tool creation failed: {e}")
            return []


# Tool functions for agent integration
async def search_and_retrieve_tool(
    query: str,
    orchestrator: DataArchitectureOrchestrator,
    include_features: bool = True,
    namespace: Optional[str] = None,
    top_k: int = 5
) -> Dict[str, Any]:
    """Unified search and retrieve tool for agent use."""
    return await orchestrator.search_and_retrieve(
        query=query,
        include_features=include_features,
        namespace=namespace,
        top_k=top_k
    )