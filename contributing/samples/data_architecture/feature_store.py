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

"""Feature store implementation for ML model features with online/offline storage."""

import asyncio
import json
import logging
import redis
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import uuid

logger = logging.getLogger(__name__)


class FeatureType(Enum):
    """Feature data types."""
    FLOAT = "float"
    INT = "int"
    STRING = "string"
    BOOLEAN = "boolean"
    TIMESTAMP = "timestamp"
    ARRAY = "array"


class StorageMode(Enum):
    """Feature storage modes."""
    ONLINE = "online"     # Low-latency serving for real-time inference
    OFFLINE = "offline"   # Batch processing for training
    BOTH = "both"        # Both online and offline storage


@dataclass
class FeatureDefinition:
    """Definition of a feature."""
    name: str
    feature_type: FeatureType
    description: str
    source_table: str
    source_column: str
    transformation: Optional[str] = None
    default_value: Optional[Any] = None
    ttl_seconds: Optional[int] = None  # Time-to-live for online features
    tags: List[str] = field(default_factory=list)
    owner: str = "data_team"
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "feature_type": self.feature_type.value,
            "description": self.description,
            "source_table": self.source_table,
            "source_column": self.source_column,
            "transformation": self.transformation,
            "default_value": self.default_value,
            "ttl_seconds": self.ttl_seconds,
            "tags": self.tags,
            "owner": self.owner,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class FeatureGroup:
    """Group of related features."""
    name: str
    description: str
    features: List[FeatureDefinition]
    entity_key: str  # Primary key for joining features
    refresh_schedule: str = "hourly"
    storage_mode: StorageMode = StorageMode.BOTH
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_feature_names(self) -> List[str]:
        """Get list of feature names in this group."""
        return [f.name for f in self.features]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "features": [f.to_dict() for f in self.features],
            "entity_key": self.entity_key,
            "refresh_schedule": self.refresh_schedule,
            "storage_mode": self.storage_mode.value,
            "metadata": self.metadata
        }


@dataclass
class OnlineFeatures:
    """Online feature values for real-time serving."""
    entity_id: str
    features: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    ttl_seconds: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "entity_id": self.entity_id,
            "features": self.features,
            "timestamp": self.timestamp.isoformat(),
            "ttl_seconds": self.ttl_seconds
        }


@dataclass
class OfflineFeatures:
    """Offline feature values for batch processing."""
    entity_id: str
    features: Dict[str, Any]
    event_timestamp: datetime
    created_timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "entity_id": self.entity_id,
            "features": self.features,
            "event_timestamp": self.event_timestamp.isoformat(),
            "created_timestamp": self.created_timestamp.isoformat()
        }


class OnlineStore(ABC):
    """Abstract interface for online feature storage."""
    
    @abstractmethod
    async def write_features(
        self,
        feature_group: str,
        features: List[OnlineFeatures]
    ) -> bool:
        """Write features to online store."""
        pass
    
    @abstractmethod
    async def read_features(
        self,
        feature_group: str,
        entity_ids: List[str],
        feature_names: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Read features from online store."""
        pass
    
    @abstractmethod
    async def delete_features(
        self,
        feature_group: str,
        entity_ids: List[str]
    ) -> bool:
        """Delete features from online store."""
        pass


class OfflineStore(ABC):
    """Abstract interface for offline feature storage."""
    
    @abstractmethod
    async def write_features(
        self,
        feature_group: str,
        features: List[OfflineFeatures]
    ) -> bool:
        """Write features to offline store."""
        pass
    
    @abstractmethod
    async def read_features(
        self,
        feature_group: str,
        entity_ids: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        feature_names: Optional[List[str]] = None
    ) -> List[OfflineFeatures]:
        """Read features from offline store."""
        pass
    
    @abstractmethod
    async def create_training_dataset(
        self,
        feature_groups: List[str],
        entity_ids: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Create training dataset from offline features."""
        pass


class RedisOnlineStore(OnlineStore):
    """Redis-based online feature store."""
    
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None
    ):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.redis_password = redis_password
        self._client = None
    
    async def _get_client(self):
        """Get Redis client (mock implementation)."""
        if self._client is None:
            # Mock Redis client for demonstration
            self._client = MockRedisClient()
        return self._client
    
    def _get_feature_key(self, feature_group: str, entity_id: str) -> str:
        """Generate Redis key for feature storage."""
        return f"features:{feature_group}:{entity_id}"
    
    async def write_features(
        self,
        feature_group: str,
        features: List[OnlineFeatures]
    ) -> bool:
        """Write features to Redis."""
        try:
            client = await self._get_client()
            
            for feature_data in features:
                key = self._get_feature_key(feature_group, feature_data.entity_id)
                value = json.dumps(feature_data.to_dict())
                
                # Set with TTL if specified
                if feature_data.ttl_seconds:
                    await client.setex(key, feature_data.ttl_seconds, value)
                else:
                    await client.set(key, value)
            
            logger.info(f"Wrote {len(features)} features to Redis for group '{feature_group}'")
            return True
        
        except Exception as e:
            logger.error(f"Error writing features to Redis: {e}")
            return False
    
    async def read_features(
        self,
        feature_group: str,
        entity_ids: List[str],
        feature_names: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Read features from Redis."""
        try:
            client = await self._get_client()
            results = {}
            
            for entity_id in entity_ids:
                key = self._get_feature_key(feature_group, entity_id)
                value = await client.get(key)
                
                if value:
                    feature_data = json.loads(value)
                    features = feature_data["features"]
                    
                    # Filter features if specific names requested
                    if feature_names:
                        features = {
                            name: features[name] 
                            for name in feature_names 
                            if name in features
                        }
                    
                    results[entity_id] = features
            
            return results
        
        except Exception as e:
            logger.error(f"Error reading features from Redis: {e}")
            return {}
    
    async def delete_features(
        self,
        feature_group: str,
        entity_ids: List[str]
    ) -> bool:
        """Delete features from Redis."""
        try:
            client = await self._get_client()
            
            keys = [
                self._get_feature_key(feature_group, entity_id)
                for entity_id in entity_ids
            ]
            
            deleted = await client.delete(*keys)
            logger.info(f"Deleted {deleted} feature keys from Redis")
            return deleted > 0
        
        except Exception as e:
            logger.error(f"Error deleting features from Redis: {e}")
            return False


class MockRedisClient:
    """Mock Redis client for demonstration."""
    
    def __init__(self):
        self._data = {}
        self._ttl = {}
    
    async def set(self, key: str, value: str):
        """Set key-value pair."""
        self._data[key] = value
        return True
    
    async def setex(self, key: str, ttl: int, value: str):
        """Set key-value pair with TTL."""
        self._data[key] = value
        self._ttl[key] = datetime.now() + timedelta(seconds=ttl)
        return True
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        # Check TTL
        if key in self._ttl:
            if datetime.now() > self._ttl[key]:
                del self._data[key]
                del self._ttl[key]
                return None
        
        return self._data.get(key)
    
    async def delete(self, *keys: str) -> int:
        """Delete keys."""
        deleted = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                deleted += 1
            if key in self._ttl:
                del self._ttl[key]
        return deleted


class BigQueryOfflineStore(OfflineStore):
    """BigQuery-based offline feature store."""
    
    def __init__(
        self,
        project_id: str,
        dataset_id: str = "feature_store",
        credentials_path: Optional[str] = None
    ):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.credentials_path = credentials_path
        self._client = None
        
        # Mock storage for demonstration
        self._tables: Dict[str, List[OfflineFeatures]] = {}
    
    async def _get_client(self):
        """Get BigQuery client (mock implementation)."""
        if self._client is None:
            logger.info(f"Initializing BigQuery client for project: {self.project_id}")
            self._client = MockBigQueryClient(self.project_id, self.dataset_id)
        return self._client
    
    def _get_table_name(self, feature_group: str) -> str:
        """Generate table name for feature group."""
        return f"{self.dataset_id}.{feature_group}_features"
    
    async def write_features(
        self,
        feature_group: str,
        features: List[OfflineFeatures]
    ) -> bool:
        """Write features to BigQuery."""
        try:
            # Store in mock tables
            if feature_group not in self._tables:
                self._tables[feature_group] = []
            
            self._tables[feature_group].extend(features)
            
            client = await self._get_client()
            table_name = self._get_table_name(feature_group)
            
            # Mock BigQuery insert
            rows = [f.to_dict() for f in features]
            await client.insert_rows(table_name, rows)
            
            logger.info(f"Wrote {len(features)} features to BigQuery table '{table_name}'")
            return True
        
        except Exception as e:
            logger.error(f"Error writing features to BigQuery: {e}")
            return False
    
    async def read_features(
        self,
        feature_group: str,
        entity_ids: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        feature_names: Optional[List[str]] = None
    ) -> List[OfflineFeatures]:
        """Read features from BigQuery."""
        if feature_group not in self._tables:
            return []
        
        features = self._tables[feature_group]
        
        # Apply filters
        if entity_ids:
            features = [f for f in features if f.entity_id in entity_ids]
        
        if start_time:
            features = [f for f in features if f.event_timestamp >= start_time]
        
        if end_time:
            features = [f for f in features if f.event_timestamp <= end_time]
        
        # Filter feature names
        if feature_names:
            filtered_features = []
            for f in features:
                filtered_feature_dict = {
                    name: f.features[name] 
                    for name in feature_names 
                    if name in f.features
                }
                filtered_features.append(OfflineFeatures(
                    entity_id=f.entity_id,
                    features=filtered_feature_dict,
                    event_timestamp=f.event_timestamp,
                    created_timestamp=f.created_timestamp
                ))
            features = filtered_features
        
        return features
    
    async def create_training_dataset(
        self,
        feature_groups: List[str],
        entity_ids: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Create training dataset from offline features."""
        dataset = {}
        total_rows = 0
        
        for feature_group in feature_groups:
            features = await self.read_features(
                feature_group=feature_group,
                entity_ids=entity_ids,
                start_time=start_time,
                end_time=end_time
            )
            
            # Convert to training format
            training_data = []
            for f in features:
                row = {"entity_id": f.entity_id}
                row.update(f.features)
                row["event_timestamp"] = f.event_timestamp.isoformat()
                training_data.append(row)
            
            dataset[feature_group] = training_data
            total_rows += len(training_data)
        
        return {
            "dataset": dataset,
            "metadata": {
                "feature_groups": feature_groups,
                "total_rows": total_rows,
                "created_at": datetime.now().isoformat(),
                "time_range": {
                    "start": start_time.isoformat() if start_time else None,
                    "end": end_time.isoformat() if end_time else None
                }
            }
        }


class MockBigQueryClient:
    """Mock BigQuery client for demonstration."""
    
    def __init__(self, project_id: str, dataset_id: str):
        self.project_id = project_id
        self.dataset_id = dataset_id
    
    async def insert_rows(self, table_name: str, rows: List[Dict[str, Any]]):
        """Mock row insertion."""
        logger.debug(f"Mock BigQuery insert: {len(rows)} rows to {table_name}")
        return True


class FeatureStoreManager:
    """Main feature store manager orchestrating online and offline storage."""
    
    def __init__(
        self,
        online_store: Optional[OnlineStore] = None,
        offline_store: Optional[OfflineStore] = None
    ):
        self.online_store = online_store or RedisOnlineStore()
        self.offline_store = offline_store or BigQueryOfflineStore("demo-project")
        
        # Feature group registry
        self.feature_groups: Dict[str, FeatureGroup] = {}
        
        # Default feature groups
        self._setup_default_feature_groups()
    
    def _setup_default_feature_groups(self):
        """Setup default feature groups."""
        # Customer features
        customer_features = FeatureGroup(
            name="customer_features",
            description="Customer demographic and behavioral features",
            entity_key="customer_id",
            features=[
                FeatureDefinition(
                    name="total_orders",
                    feature_type=FeatureType.INT,
                    description="Total number of orders",
                    source_table="orders",
                    source_column="count(*)",
                    transformation="count_by_customer"
                ),
                FeatureDefinition(
                    name="total_spent",
                    feature_type=FeatureType.FLOAT,
                    description="Total amount spent",
                    source_table="orders",
                    source_column="amount",
                    transformation="sum_by_customer"
                ),
                FeatureDefinition(
                    name="last_order_days_ago",
                    feature_type=FeatureType.INT,
                    description="Days since last order",
                    source_table="orders",
                    source_column="order_date",
                    transformation="days_since_last"
                ),
                FeatureDefinition(
                    name="avg_order_value",
                    feature_type=FeatureType.FLOAT,
                    description="Average order value",
                    source_table="orders",
                    source_column="amount",
                    transformation="avg_by_customer"
                )
            ],
            refresh_schedule="daily",
            storage_mode=StorageMode.BOTH
        )
        
        # Product features
        product_features = FeatureGroup(
            name="product_features",
            description="Product performance and inventory features",
            entity_key="product_id",
            features=[
                FeatureDefinition(
                    name="sales_last_30d",
                    feature_type=FeatureType.INT,
                    description="Sales count in last 30 days",
                    source_table="order_items",
                    source_column="quantity",
                    transformation="sum_last_30d"
                ),
                FeatureDefinition(
                    name="revenue_last_30d",
                    feature_type=FeatureType.FLOAT,
                    description="Revenue in last 30 days",
                    source_table="order_items",
                    source_column="revenue",
                    transformation="sum_last_30d"
                ),
                FeatureDefinition(
                    name="avg_rating",
                    feature_type=FeatureType.FLOAT,
                    description="Average customer rating",
                    source_table="reviews",
                    source_column="rating",
                    transformation="avg"
                ),
                FeatureDefinition(
                    name="inventory_level",
                    feature_type=FeatureType.INT,
                    description="Current inventory level",
                    source_table="inventory",
                    source_column="quantity",
                    ttl_seconds=3600  # 1 hour TTL for real-time inventory
                )
            ],
            refresh_schedule="hourly",
            storage_mode=StorageMode.BOTH
        )
        
        self.register_feature_group(customer_features)
        self.register_feature_group(product_features)
    
    def register_feature_group(self, feature_group: FeatureGroup):
        """Register a feature group."""
        self.feature_groups[feature_group.name] = feature_group
        logger.info(f"Registered feature group: {feature_group.name}")
    
    async def materialize_features(
        self,
        feature_group_name: str,
        source_data: List[Dict[str, Any]],
        storage_mode: Optional[StorageMode] = None
    ) -> bool:
        """Materialize features from source data."""
        if feature_group_name not in self.feature_groups:
            logger.error(f"Feature group '{feature_group_name}' not found")
            return False
        
        feature_group = self.feature_groups[feature_group_name]
        storage_mode = storage_mode or feature_group.storage_mode
        
        # Transform source data to features
        online_features = []
        offline_features = []
        
        for data_row in source_data:
            entity_id = data_row.get(feature_group.entity_key)
            if not entity_id:
                logger.warning(f"Missing entity key '{feature_group.entity_key}' in data row")
                continue
            
            # Extract feature values
            feature_values = {}
            for feature_def in feature_group.features:
                value = self._extract_feature_value(data_row, feature_def)
                feature_values[feature_def.name] = value
            
            # Create feature objects
            if storage_mode in [StorageMode.ONLINE, StorageMode.BOTH]:
                online_feat = OnlineFeatures(
                    entity_id=str(entity_id),
                    features=feature_values,
                    ttl_seconds=getattr(feature_def, 'ttl_seconds', None)
                )
                online_features.append(online_feat)
            
            if storage_mode in [StorageMode.OFFLINE, StorageMode.BOTH]:
                offline_feat = OfflineFeatures(
                    entity_id=str(entity_id),
                    features=feature_values,
                    event_timestamp=datetime.now()
                )
                offline_features.append(offline_feat)
        
        # Write to stores
        success = True
        
        if online_features:
            online_success = await self.online_store.write_features(
                feature_group_name, online_features
            )
            success = success and online_success
        
        if offline_features:
            offline_success = await self.offline_store.write_features(
                feature_group_name, offline_features
            )
            success = success and offline_success
        
        if success:
            logger.info(f"Materialized {len(source_data)} feature records for group '{feature_group_name}'")
        
        return success
    
    def _extract_feature_value(
        self,
        data_row: Dict[str, Any],
        feature_def: FeatureDefinition
    ) -> Any:
        """Extract feature value from data row."""
        # Simple extraction - in production this would handle transformations
        value = data_row.get(feature_def.source_column, feature_def.default_value)
        
        # Handle special transformations for test data
        if feature_def.transformation == "days_since_last" and feature_def.source_column == "order_date":
            # Calculate days since last order
            try:
                from datetime import datetime
                order_date = datetime.fromisoformat(value)
                days_ago = (datetime.now() - order_date).days
                return days_ago
            except:
                return 0
        
        elif feature_def.transformation in ["sum_by_customer", "avg_by_customer"] and feature_def.source_column == "amount":
            # Use amount value directly for demo
            try:
                return float(value) if value is not None else 0.0
            except:
                return 0.0
        
        elif feature_def.transformation == "count_by_customer" and feature_def.source_column == "count(*)":
            # Use count directly
            try:
                return int(value) if value is not None else 0
            except:
                return 0
        
        # Apply basic type conversion
        if feature_def.feature_type == FeatureType.FLOAT and value is not None:
            try:
                return float(value)
            except:
                return 0.0
        elif feature_def.feature_type == FeatureType.INT and value is not None:
            try:
                return int(value)
            except:
                return 0
        elif feature_def.feature_type == FeatureType.BOOLEAN and value is not None:
            return bool(value)
        
        return value
    
    async def get_online_features(
        self,
        feature_group_name: str,
        entity_ids: List[str],
        feature_names: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Get online features for real-time inference."""
        return await self.online_store.read_features(
            feature_group_name, entity_ids, feature_names
        )
    
    async def get_offline_features(
        self,
        feature_group_name: str,
        entity_ids: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        feature_names: Optional[List[str]] = None
    ) -> List[OfflineFeatures]:
        """Get offline features for batch processing."""
        return await self.offline_store.read_features(
            feature_group_name, entity_ids, start_time, end_time, feature_names
        )
    
    async def create_training_dataset(
        self,
        feature_groups: List[str],
        entity_ids: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Create training dataset for ML models."""
        return await self.offline_store.create_training_dataset(
            feature_groups, entity_ids, start_time, end_time
        )
    
    async def sync_online_offline(self, feature_group_name: str) -> bool:
        """Sync features from offline to online store."""
        # Get recent features from offline store
        end_time = datetime.now()
        start_time = end_time - timedelta(days=1)  # Last 24 hours
        
        offline_features = await self.offline_store.read_features(
            feature_group_name=feature_group_name,
            start_time=start_time,
            end_time=end_time
        )
        
        if not offline_features:
            logger.info(f"No offline features to sync for group '{feature_group_name}'")
            return True
        
        # Convert to online format
        online_features = []
        for offline_feat in offline_features:
            online_feat = OnlineFeatures(
                entity_id=offline_feat.entity_id,
                features=offline_feat.features,
                timestamp=offline_feat.event_timestamp
            )
            online_features.append(online_feat)
        
        # Write to online store
        success = await self.online_store.write_features(
            feature_group_name, online_features
        )
        
        if success:
            logger.info(f"Synced {len(online_features)} features to online store")
        
        return success
    
    def get_feature_metadata(self, feature_group_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a feature group."""
        if feature_group_name not in self.feature_groups:
            return None
        
        feature_group = self.feature_groups[feature_group_name]
        return feature_group.to_dict()
    
    def list_feature_groups(self) -> List[str]:
        """List all registered feature groups."""
        return list(self.feature_groups.keys())
    
    async def get_feature_store_stats(self) -> Dict[str, Any]:
        """Get feature store statistics."""
        return {
            "feature_groups": len(self.feature_groups),
            "groups": list(self.feature_groups.keys()),
            "total_features": sum(
                len(fg.features) for fg in self.feature_groups.values()
            ),
            "storage_modes": {
                fg.name: fg.storage_mode.value 
                for fg in self.feature_groups.values()
            },
            "online_store": "redis",
            "offline_store": "bigquery"
        }
    
    async def create_feature_serving_function(
        self,
        feature_group_name: str,
        feature_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a function for serving features to agents."""
        if feature_group_name not in self.feature_groups:
            return {"error": f"Feature group '{feature_group_name}' not found"}
        
        feature_group = self.feature_groups[feature_group_name]
        available_features = feature_group.get_feature_names()
        
        return {
            "type": "function",
            "function": {
                "name": f"get_{feature_group_name}",
                "description": f"Get features from {feature_group.description}",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": f"List of {feature_group.entity_key} values"
                        },
                        "feature_names": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": f"Feature names to retrieve (available: {available_features})"
                        }
                    },
                    "required": ["entity_ids"]
                }
            },
            "implementation": {
                "manager": self,
                "feature_group": feature_group_name,
                "default_features": feature_names or available_features
            }
        }


# Tool function for agent integration
async def get_features_tool(
    entity_ids: List[str],
    manager: FeatureStoreManager,
    feature_group: str,
    feature_names: Optional[List[str]] = None,
    use_online: bool = True
) -> Dict[str, Any]:
    """Feature retrieval tool for agent use."""
    try:
        if use_online:
            # Use online store for real-time inference
            features = await manager.get_online_features(
                feature_group_name=feature_group,
                entity_ids=entity_ids,
                feature_names=feature_names
            )
            
            return {
                "success": True,
                "store_type": "online",
                "feature_group": feature_group,
                "entity_count": len(entity_ids),
                "features": features
            }
        else:
            # Use offline store for batch processing
            offline_features = await manager.get_offline_features(
                feature_group_name=feature_group,
                entity_ids=entity_ids,
                feature_names=feature_names
            )
            
            # Convert to dictionary format
            features = {}
            for feat in offline_features:
                features[feat.entity_id] = feat.features
            
            return {
                "success": True,
                "store_type": "offline",
                "feature_group": feature_group,
                "entity_count": len(entity_ids),
                "features": features
            }
    
    except Exception as e:
        logger.error(f"Feature retrieval tool error: {e}")
        return {
            "success": False,
            "error": str(e),
            "feature_group": feature_group,
            "entity_ids": entity_ids
        }