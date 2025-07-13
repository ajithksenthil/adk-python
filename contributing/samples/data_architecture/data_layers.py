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

"""Bronze/Silver/Gold data layer management for lakehouse architecture."""

import asyncio
import json
import logging
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import uuid

logger = logging.getLogger(__name__)


class DataQualityLevel(Enum):
    """Data quality levels in the lakehouse."""
    BRONZE = "bronze"    # Raw, exactly as ingested
    SILVER = "silver"    # Cleaned, conformed, validated
    GOLD = "gold"        # Business-ready, curated marts


class TableFormat(Enum):
    """Supported table formats."""
    DELTA = "delta"
    ICEBERG = "iceberg"
    PARQUET = "parquet"
    JSON = "json"


class StorageBackend(Enum):
    """Storage backend types."""
    LOCAL = "local"
    GCS = "gcs"
    S3 = "s3"
    AZURE = "azure"


@dataclass
class DataRecord:
    """A data record with lineage and quality metadata."""
    id: str
    data: Dict[str, Any]
    lineage_id: str
    source_system: str
    ingested_at: datetime = field(default_factory=datetime.now)
    quality_level: DataQualityLevel = DataQualityLevel.BRONZE
    schema_version: str = "1.0"
    partition_keys: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "data": self.data,
            "lineage_id": self.lineage_id,
            "source_system": self.source_system,
            "ingested_at": self.ingested_at.isoformat(),
            "quality_level": self.quality_level.value,
            "schema_version": self.schema_version,
            "partition_keys": self.partition_keys,
            "metadata": self.metadata
        }


@dataclass
class TransformationRule:
    """Data transformation rule for Silver layer processing."""
    name: str
    description: str
    source_fields: List[str]
    target_field: str
    transformation_type: str  # "clean", "mask", "validate", "enrich"
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def apply(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply transformation rule to data."""
        result = data.copy()
        
        if self.transformation_type == "clean":
            # Data cleaning transformations
            if self.target_field in result:
                value = result[self.target_field]
                if isinstance(value, str):
                    result[self.target_field] = value.strip().lower()
        
        elif self.transformation_type == "mask":
            # PII masking
            if self.target_field in result:
                result[self.target_field] = self._mask_pii(result[self.target_field])
        
        elif self.transformation_type == "validate":
            # Data validation
            if self.target_field in result:
                if not self._validate_field(result[self.target_field]):
                    result[f"{self.target_field}_validation_error"] = True
        
        elif self.transformation_type == "enrich":
            # Data enrichment
            result[self.target_field] = self._enrich_data(data, self.parameters)
        
        return result
    
    def _mask_pii(self, value: Any) -> str:
        """Mask PII data."""
        if isinstance(value, str):
            if "@" in value:  # Email
                parts = value.split("@")
                return f"{parts[0][:2]}***@{parts[1]}"
            elif len(value) > 4:  # Generic masking
                return f"{value[:2]}***{value[-2:]}"
        return "***"
    
    def _validate_field(self, value: Any) -> bool:
        """Validate field value."""
        # Simple validation logic
        if isinstance(value, str) and len(value) == 0:
            return False
        return True
    
    def _enrich_data(self, data: Dict[str, Any], params: Dict[str, Any]) -> Any:
        """Enrich data with additional information."""
        # Mock enrichment
        return params.get("default_value", "enriched_data")


@dataclass
class BusinessMart:
    """Business mart definition for Gold layer."""
    name: str
    description: str
    source_tables: List[str]
    key_metrics: List[str]
    dimensions: List[str]
    aggregation_rules: Dict[str, str]
    refresh_schedule: str = "daily"
    retention_days: int = 365
    
    def generate_mart(self, silver_data: List[DataRecord]) -> List[Dict[str, Any]]:
        """Generate business mart from Silver data."""
        # Mock mart generation
        mart_records = []
        
        # Group by dimensions and calculate metrics
        grouped_data = {}
        for record in silver_data:
            # Create dimension key
            dim_key = "_".join(
                str(record.data.get(dim, "unknown")) for dim in self.dimensions
            )
            
            if dim_key not in grouped_data:
                grouped_data[dim_key] = []
            grouped_data[dim_key].append(record)
        
        # Generate aggregated records
        for dim_key, records in grouped_data.items():
            mart_record = {}
            
            # Add dimensions
            for i, dim in enumerate(self.dimensions):
                dim_values = dim_key.split("_")
                mart_record[dim] = dim_values[i] if i < len(dim_values) else "unknown"
            
            # Calculate metrics
            for metric in self.key_metrics:
                if metric in self.aggregation_rules:
                    rule = self.aggregation_rules[metric]
                    if rule == "count":
                        mart_record[metric] = len(records)
                    elif rule == "sum":
                        mart_record[metric] = sum(
                            r.data.get(metric, 0) for r in records
                        )
                    elif rule == "avg":
                        values = [r.data.get(metric, 0) for r in records]
                        mart_record[metric] = sum(values) / len(values) if values else 0
            
            # Add metadata
            mart_record["record_count"] = len(records)
            mart_record["last_updated"] = datetime.now().isoformat()
            
            mart_records.append(mart_record)
        
        return mart_records


class DataLayer(ABC):
    """Abstract base class for data layers."""
    
    @abstractmethod
    async def write(
        self,
        records: List[DataRecord],
        table_name: str,
        partition_keys: Optional[List[str]] = None
    ) -> bool:
        """Write records to the layer."""
        pass
    
    @abstractmethod
    async def read(
        self,
        table_name: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> List[DataRecord]:
        """Read records from the layer."""
        pass
    
    @abstractmethod
    async def delete(
        self,
        table_name: str,
        filters: Dict[str, Any]
    ) -> bool:
        """Delete records from the layer."""
        pass
    
    @abstractmethod
    async def get_schema(self, table_name: str) -> Dict[str, Any]:
        """Get table schema."""
        pass


class BronzeLayer(DataLayer):
    """Bronze layer - raw data exactly as ingested."""
    
    def __init__(
        self,
        storage_backend: StorageBackend = StorageBackend.LOCAL,
        storage_config: Optional[Dict[str, Any]] = None
    ):
        self.storage_backend = storage_backend
        self.storage_config = storage_config or {}
        self.base_path = self.storage_config.get("base_path", "/tmp/bronze")
        self.table_format = TableFormat.JSON  # Raw format
        
        # Ensure base path exists
        Path(self.base_path).mkdir(parents=True, exist_ok=True)
        
        # In-memory storage for demo
        self._tables: Dict[str, List[DataRecord]] = {}
    
    async def write(
        self,
        records: List[DataRecord],
        table_name: str,
        partition_keys: Optional[List[str]] = None
    ) -> bool:
        """Write raw records to Bronze layer."""
        try:
            # Ensure all records are marked as Bronze quality
            for record in records:
                record.quality_level = DataQualityLevel.BRONZE
            
            # Store in memory for demo
            if table_name not in self._tables:
                self._tables[table_name] = []
            
            self._tables[table_name].extend(records)
            
            # Mock file write
            table_path = Path(self.base_path) / f"{table_name}.json"
            with open(table_path, 'w') as f:
                json.dump([r.to_dict() for r in self._tables[table_name]], f, indent=2)
            
            logger.info(f"Wrote {len(records)} records to Bronze table '{table_name}'")
            return True
        
        except Exception as e:
            logger.error(f"Error writing to Bronze layer: {e}")
            return False
    
    async def read(
        self,
        table_name: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> List[DataRecord]:
        """Read records from Bronze layer."""
        if table_name not in self._tables:
            return []
        
        records = self._tables[table_name]
        
        # Apply filters
        if filters:
            filtered_records = []
            for record in records:
                match = True
                for key, value in filters.items():
                    if key in record.data and record.data[key] != value:
                        match = False
                        break
                    elif key in record.metadata and record.metadata[key] != value:
                        match = False
                        break
                if match:
                    filtered_records.append(record)
            records = filtered_records
        
        # Apply limit
        if limit:
            records = records[:limit]
        
        return records
    
    async def delete(
        self,
        table_name: str,
        filters: Dict[str, Any]
    ) -> bool:
        """Delete records from Bronze layer."""
        if table_name not in self._tables:
            return True
        
        # Filter out matching records
        original_count = len(self._tables[table_name])
        self._tables[table_name] = [
            record for record in self._tables[table_name]
            if not all(
                record.data.get(k) == v or record.metadata.get(k) == v
                for k, v in filters.items()
            )
        ]
        
        deleted_count = original_count - len(self._tables[table_name])
        logger.info(f"Deleted {deleted_count} records from Bronze table '{table_name}'")
        return True
    
    async def get_schema(self, table_name: str) -> Dict[str, Any]:
        """Get Bronze table schema."""
        if table_name not in self._tables or not self._tables[table_name]:
            return {"fields": [], "record_count": 0}
        
        # Infer schema from first record
        sample_record = self._tables[table_name][0]
        fields = []
        
        for key, value in sample_record.data.items():
            fields.append({
                "name": key,
                "type": type(value).__name__,
                "nullable": True
            })
        
        return {
            "table_name": table_name,
            "quality_level": "bronze",
            "record_count": len(self._tables[table_name]),
            "fields": fields,
            "format": self.table_format.value
        }


class SilverLayer(DataLayer):
    """Silver layer - cleaned, conformed, and validated data."""
    
    def __init__(
        self,
        storage_backend: StorageBackend = StorageBackend.LOCAL,
        storage_config: Optional[Dict[str, Any]] = None,
        transformation_rules: Optional[List[TransformationRule]] = None
    ):
        self.storage_backend = storage_backend
        self.storage_config = storage_config or {}
        self.base_path = self.storage_config.get("base_path", "/tmp/silver")
        self.table_format = TableFormat.PARQUET
        self.transformation_rules = transformation_rules or []
        
        # Ensure base path exists
        Path(self.base_path).mkdir(parents=True, exist_ok=True)
        
        # In-memory storage for demo
        self._tables: Dict[str, List[DataRecord]] = {}
    
    def add_transformation_rule(self, rule: TransformationRule):
        """Add a transformation rule."""
        self.transformation_rules.append(rule)
    
    async def transform_from_bronze(
        self,
        bronze_records: List[DataRecord],
        target_table: str
    ) -> List[DataRecord]:
        """Transform Bronze records to Silver quality."""
        transformed_records = []
        
        for record in bronze_records:
            # Create Silver record
            silver_record = DataRecord(
                id=record.id,
                data=record.data.copy(),
                lineage_id=record.lineage_id,
                source_system=record.source_system,
                ingested_at=record.ingested_at,
                quality_level=DataQualityLevel.SILVER,
                schema_version=record.schema_version,
                partition_keys=record.partition_keys,
                metadata=record.metadata.copy()
            )
            
            # Apply transformation rules
            for rule in self.transformation_rules:
                silver_record.data = rule.apply(silver_record.data)
            
            # Add transformation metadata
            silver_record.metadata.update({
                "transformed_at": datetime.now().isoformat(),
                "transformation_rules_applied": len(self.transformation_rules),
                "bronze_record_id": record.id
            })
            
            transformed_records.append(silver_record)
        
        # Write to Silver layer
        await self.write(transformed_records, target_table)
        
        logger.info(f"Transformed {len(bronze_records)} Bronze records to Silver table '{target_table}'")
        return transformed_records
    
    async def write(
        self,
        records: List[DataRecord],
        table_name: str,
        partition_keys: Optional[List[str]] = None
    ) -> bool:
        """Write records to Silver layer."""
        try:
            # Ensure all records are marked as Silver quality
            for record in records:
                record.quality_level = DataQualityLevel.SILVER
            
            # Store in memory for demo
            if table_name not in self._tables:
                self._tables[table_name] = []
            
            self._tables[table_name].extend(records)
            
            # Mock Parquet write
            table_path = Path(self.base_path) / f"{table_name}.parquet.json"
            with open(table_path, 'w') as f:
                json.dump([r.to_dict() for r in self._tables[table_name]], f, indent=2)
            
            logger.info(f"Wrote {len(records)} records to Silver table '{table_name}'")
            return True
        
        except Exception as e:
            logger.error(f"Error writing to Silver layer: {e}")
            return False
    
    async def read(
        self,
        table_name: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> List[DataRecord]:
        """Read records from Silver layer."""
        if table_name not in self._tables:
            return []
        
        records = self._tables[table_name]
        
        # Apply filters
        if filters:
            filtered_records = []
            for record in records:
                match = True
                for key, value in filters.items():
                    if key in record.data and record.data[key] != value:
                        match = False
                        break
                if match:
                    filtered_records.append(record)
            records = filtered_records
        
        # Apply limit
        if limit:
            records = records[:limit]
        
        return records
    
    async def delete(
        self,
        table_name: str,
        filters: Dict[str, Any]
    ) -> bool:
        """Delete records from Silver layer."""
        if table_name not in self._tables:
            return True
        
        original_count = len(self._tables[table_name])
        self._tables[table_name] = [
            record for record in self._tables[table_name]
            if not all(record.data.get(k) == v for k, v in filters.items())
        ]
        
        deleted_count = original_count - len(self._tables[table_name])
        logger.info(f"Deleted {deleted_count} records from Silver table '{table_name}'")
        return True
    
    async def get_schema(self, table_name: str) -> Dict[str, Any]:
        """Get Silver table schema."""
        if table_name not in self._tables or not self._tables[table_name]:
            return {"fields": [], "record_count": 0}
        
        sample_record = self._tables[table_name][0]
        fields = []
        
        for key, value in sample_record.data.items():
            fields.append({
                "name": key,
                "type": type(value).__name__,
                "nullable": True,
                "quality_checked": True
            })
        
        return {
            "table_name": table_name,
            "quality_level": "silver",
            "record_count": len(self._tables[table_name]),
            "fields": fields,
            "format": self.table_format.value,
            "transformation_rules": len(self.transformation_rules)
        }


class GoldLayer(DataLayer):
    """Gold layer - business-ready curated data marts."""
    
    def __init__(
        self,
        storage_backend: StorageBackend = StorageBackend.LOCAL,
        storage_config: Optional[Dict[str, Any]] = None,
        business_marts: Optional[List[BusinessMart]] = None
    ):
        self.storage_backend = storage_backend
        self.storage_config = storage_config or {}
        self.base_path = self.storage_config.get("base_path", "/tmp/gold")
        self.table_format = TableFormat.DELTA
        self.business_marts = business_marts or []
        
        # Ensure base path exists
        Path(self.base_path).mkdir(parents=True, exist_ok=True)
        
        # In-memory storage for demo
        self._tables: Dict[str, List[Dict[str, Any]]] = {}
    
    def add_business_mart(self, mart: BusinessMart):
        """Add a business mart definition."""
        self.business_marts.append(mart)
    
    async def create_mart_from_silver(
        self,
        mart_name: str,
        silver_records: List[DataRecord]
    ) -> bool:
        """Create business mart from Silver data."""
        # Find mart definition
        mart_def = None
        for mart in self.business_marts:
            if mart.name == mart_name:
                mart_def = mart
                break
        
        if not mart_def:
            logger.error(f"No business mart definition found for '{mart_name}'")
            return False
        
        # Generate mart data
        mart_records = mart_def.generate_mart(silver_records)
        
        # Store mart data
        self._tables[mart_name] = mart_records
        
        # Mock Delta table write
        table_path = Path(self.base_path) / f"{mart_name}.delta.json"
        with open(table_path, 'w') as f:
            json.dump(mart_records, f, indent=2)
        
        logger.info(f"Created Gold mart '{mart_name}' with {len(mart_records)} records")
        return True
    
    async def write(
        self,
        records: List[DataRecord],
        table_name: str,
        partition_keys: Optional[List[str]] = None
    ) -> bool:
        """Write records to Gold layer."""
        try:
            # Convert DataRecord to dict for Gold storage
            gold_records = []
            for record in records:
                gold_record = record.data.copy()
                gold_record.update({
                    "_record_id": record.id,
                    "_lineage_id": record.lineage_id,
                    "_source_system": record.source_system,
                    "_quality_level": DataQualityLevel.GOLD.value,
                    "_created_at": datetime.now().isoformat()
                })
                gold_records.append(gold_record)
            
            # Store in memory for demo
            if table_name not in self._tables:
                self._tables[table_name] = []
            
            self._tables[table_name].extend(gold_records)
            
            # Mock Delta table write
            table_path = Path(self.base_path) / f"{table_name}.delta.json"
            with open(table_path, 'w') as f:
                json.dump(self._tables[table_name], f, indent=2)
            
            logger.info(f"Wrote {len(records)} records to Gold table '{table_name}'")
            return True
        
        except Exception as e:
            logger.error(f"Error writing to Gold layer: {e}")
            return False
    
    async def read(
        self,
        table_name: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> List[DataRecord]:
        """Read records from Gold layer."""
        if table_name not in self._tables:
            return []
        
        records = self._tables[table_name]
        
        # Apply filters
        if filters:
            filtered_records = []
            for record in records:
                match = True
                for key, value in filters.items():
                    if key in record and record[key] != value:
                        match = False
                        break
                if match:
                    filtered_records.append(record)
            records = filtered_records
        
        # Apply limit
        if limit:
            records = records[:limit]
        
        # Convert back to DataRecord format
        data_records = []
        for record in records:
            data_records.append(DataRecord(
                id=record.get("_record_id", str(uuid.uuid4())),
                data={k: v for k, v in record.items() if not k.startswith("_")},
                lineage_id=record.get("_lineage_id", ""),
                source_system=record.get("_source_system", "gold_layer"),
                quality_level=DataQualityLevel.GOLD
            ))
        
        return data_records
    
    async def delete(
        self,
        table_name: str,
        filters: Dict[str, Any]
    ) -> bool:
        """Delete records from Gold layer."""
        if table_name not in self._tables:
            return True
        
        original_count = len(self._tables[table_name])
        self._tables[table_name] = [
            record for record in self._tables[table_name]
            if not all(record.get(k) == v for k, v in filters.items())
        ]
        
        deleted_count = original_count - len(self._tables[table_name])
        logger.info(f"Deleted {deleted_count} records from Gold table '{table_name}'")
        return True
    
    async def get_schema(self, table_name: str) -> Dict[str, Any]:
        """Get Gold table schema."""
        if table_name not in self._tables or not self._tables[table_name]:
            return {"fields": [], "record_count": 0}
        
        sample_record = self._tables[table_name][0]
        fields = []
        
        for key, value in sample_record.items():
            fields.append({
                "name": key,
                "type": type(value).__name__,
                "nullable": True,
                "business_ready": True
            })
        
        return {
            "table_name": table_name,
            "quality_level": "gold",
            "record_count": len(self._tables[table_name]),
            "fields": fields,
            "format": self.table_format.value,
            "mart_definitions": len(self.business_marts)
        }


class DataLayerManager:
    """Manager for Bronze/Silver/Gold data layer operations."""
    
    def __init__(
        self,
        storage_backend: StorageBackend = StorageBackend.LOCAL,
        storage_config: Optional[Dict[str, Any]] = None
    ):
        self.storage_backend = storage_backend
        self.storage_config = storage_config or {}
        
        # Initialize layers
        self.bronze = BronzeLayer(storage_backend, storage_config)
        self.silver = SilverLayer(storage_backend, storage_config)
        self.gold = GoldLayer(storage_backend, storage_config)
        
        # Default transformation rules
        self._setup_default_transformations()
        
        # Default business marts
        self._setup_default_marts()
    
    def _setup_default_transformations(self):
        """Setup default transformation rules for Silver layer."""
        # PII masking rules
        self.silver.add_transformation_rule(TransformationRule(
            name="email_masking",
            description="Mask email addresses for privacy",
            source_fields=["email"],
            target_field="email",
            transformation_type="mask"
        ))
        
        # Data cleaning rules
        self.silver.add_transformation_rule(TransformationRule(
            name="name_cleaning",
            description="Clean and standardize names",
            source_fields=["name", "customer_name"],
            target_field="name",
            transformation_type="clean"
        ))
        
        # Validation rules
        self.silver.add_transformation_rule(TransformationRule(
            name="amount_validation",
            description="Validate monetary amounts",
            source_fields=["amount"],
            target_field="amount",
            transformation_type="validate"
        ))
    
    def _setup_default_marts(self):
        """Setup default business marts for Gold layer."""
        # Customer 360 mart
        customer_360 = BusinessMart(
            name="customer_360",
            description="360-degree customer view with key metrics",
            source_tables=["customers", "orders", "support_tickets"],
            key_metrics=["total_orders", "total_spent", "support_tickets"],
            dimensions=["customer_id", "customer_segment"],
            aggregation_rules={
                "total_orders": "count",
                "total_spent": "sum",
                "support_tickets": "count"
            }
        )
        
        # Daily cash balance mart
        daily_cash = BusinessMart(
            name="daily_cash_balance",
            description="Daily cash flow and balance tracking",
            source_tables=["transactions", "invoices"],
            key_metrics=["daily_inflow", "daily_outflow", "balance"],
            dimensions=["date", "account_type"],
            aggregation_rules={
                "daily_inflow": "sum",
                "daily_outflow": "sum",
                "balance": "sum"
            }
        )
        
        self.gold.add_business_mart(customer_360)
        self.gold.add_business_mart(daily_cash)
    
    async def ingest_raw_data(
        self,
        data: List[Dict[str, Any]],
        source_system: str,
        table_name: str,
        lineage_id: Optional[str] = None
    ) -> str:
        """Ingest raw data into Bronze layer."""
        # Create data records
        lineage_id = lineage_id or str(uuid.uuid4())
        records = []
        
        for item in data:
            record = DataRecord(
                id=str(uuid.uuid4()),
                data=item,
                lineage_id=lineage_id,
                source_system=source_system,
                quality_level=DataQualityLevel.BRONZE
            )
            records.append(record)
        
        # Write to Bronze layer
        success = await self.bronze.write(records, table_name)
        
        if success:
            logger.info(f"Ingested {len(records)} records from {source_system} with lineage ID: {lineage_id}")
        
        return lineage_id if success else ""
    
    async def process_bronze_to_silver(
        self,
        bronze_table: str,
        silver_table: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Process Bronze data to Silver layer."""
        # Read from Bronze
        bronze_records = await self.bronze.read(bronze_table, filters)
        
        if not bronze_records:
            logger.warning(f"No records found in Bronze table '{bronze_table}'")
            return False
        
        # Transform to Silver
        silver_records = await self.silver.transform_from_bronze(bronze_records, silver_table)
        
        return len(silver_records) > 0
    
    async def create_gold_marts(
        self,
        silver_table: str,
        mart_names: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """Create Gold layer business marts from Silver data."""
        # Read from Silver
        silver_records = await self.silver.read(silver_table)
        
        if not silver_records:
            logger.warning(f"No records found in Silver table '{silver_table}'")
            return {}
        
        # Create specified marts or all available marts
        target_marts = mart_names or [mart.name for mart in self.gold.business_marts]
        
        results = {}
        for mart_name in target_marts:
            success = await self.gold.create_mart_from_silver(mart_name, silver_records)
            results[mart_name] = success
        
        return results
    
    async def full_pipeline(
        self,
        raw_data: List[Dict[str, Any]],
        source_system: str,
        bronze_table: str,
        silver_table: str,
        mart_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Execute full Bronze -> Silver -> Gold pipeline."""
        pipeline_id = str(uuid.uuid4())
        
        try:
            # Step 1: Ingest to Bronze
            lineage_id = await self.ingest_raw_data(
                raw_data, source_system, bronze_table, pipeline_id
            )
            
            if not lineage_id:
                return {"success": False, "error": "Bronze ingestion failed"}
            
            # Step 2: Process to Silver
            silver_success = await self.process_bronze_to_silver(
                bronze_table, silver_table
            )
            
            if not silver_success:
                return {"success": False, "error": "Silver processing failed"}
            
            # Step 3: Create Gold marts
            mart_results = await self.create_gold_marts(silver_table, mart_names)
            
            return {
                "success": True,
                "pipeline_id": pipeline_id,
                "lineage_id": lineage_id,
                "bronze_records": len(raw_data),
                "silver_processed": silver_success,
                "gold_marts": mart_results
            }
        
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_lineage_trace(self, lineage_id: str) -> Dict[str, Any]:
        """Trace data lineage across all layers."""
        trace = {
            "lineage_id": lineage_id,
            "bronze_tables": {},
            "silver_tables": {},
            "gold_tables": {}
        }
        
        # Check Bronze layer
        for table_name in self.bronze._tables:
            records = await self.bronze.read(
                table_name, {"lineage_id": lineage_id}
            )
            if records:
                trace["bronze_tables"][table_name] = len(records)
        
        # Check Silver layer
        for table_name in self.silver._tables:
            records = await self.silver.read(
                table_name, {"lineage_id": lineage_id}
            )
            if records:
                trace["silver_tables"][table_name] = len(records)
        
        # Check Gold layer (lineage stored in metadata)
        for table_name in self.gold._tables:
            records = await self.gold.read(table_name)
            matching_records = [
                r for r in records if r.lineage_id == lineage_id
            ]
            if matching_records:
                trace["gold_tables"][table_name] = len(matching_records)
        
        return trace
    
    async def get_layer_stats(self) -> Dict[str, Any]:
        """Get statistics for all data layers."""
        bronze_tables = list(self.bronze._tables.keys())
        silver_tables = list(self.silver._tables.keys())
        gold_tables = list(self.gold._tables.keys())
        
        return {
            "bronze": {
                "tables": bronze_tables,
                "table_count": len(bronze_tables),
                "total_records": sum(
                    len(self.bronze._tables[table]) for table in bronze_tables
                )
            },
            "silver": {
                "tables": silver_tables,
                "table_count": len(silver_tables),
                "total_records": sum(
                    len(self.silver._tables[table]) for table in silver_tables
                ),
                "transformation_rules": len(self.silver.transformation_rules)
            },
            "gold": {
                "tables": gold_tables,
                "table_count": len(gold_tables),
                "total_records": sum(
                    len(self.gold._tables[table]) for table in gold_tables
                ),
                "business_marts": len(self.gold.business_marts)
            }
        }