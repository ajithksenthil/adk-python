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

"""Schema registry for event validation and versioning."""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import jsonschema
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class SchemaFormat(Enum):
  """Supported schema formats."""
  JSON_SCHEMA = "json_schema"
  AVRO = "avro"
  PROTOBUF = "protobuf"


class CompatibilityMode(Enum):
  """Schema compatibility modes."""
  BACKWARD = "backward"  # New schema can read old data
  FORWARD = "forward"  # Old schema can read new data
  FULL = "full"  # Bidirectional compatibility
  NONE = "none"  # No compatibility checks


@dataclass
class SchemaVersion:
  """Schema version information."""
  version: int
  schema: Dict[str, Any]
  format: SchemaFormat
  created_at: datetime = field(default_factory=datetime.now)
  deprecated: bool = False
  deprecation_date: Optional[datetime] = None
  metadata: Dict[str, Any] = field(default_factory=dict)


class SchemaSubject(BaseModel):
  """Schema subject containing all versions."""
  name: str
  versions: Dict[int, SchemaVersion] = Field(default_factory=dict)
  latest_version: int = 0
  compatibility_mode: CompatibilityMode = CompatibilityMode.BACKWARD
  metadata: Dict[str, Any] = Field(default_factory=dict)
  
  class Config:
    arbitrary_types_allowed = True
  
  def add_version(self, schema: Dict[str, Any], format: SchemaFormat) -> int:
    """Add a new schema version."""
    version = self.latest_version + 1
    self.versions[version] = SchemaVersion(
      version=version,
      schema=schema,
      format=format
    )
    self.latest_version = version
    return version
  
  def get_version(self, version: Optional[int] = None) -> Optional[SchemaVersion]:
    """Get a specific version or latest if not specified."""
    if version is None:
      version = self.latest_version
    return self.versions.get(version)


class SchemaRegistry(ABC):
  """Abstract base class for schema registry implementations."""
  
  @abstractmethod
  async def register_schema(
    self,
    subject: str,
    schema: Dict[str, Any],
    format: SchemaFormat = SchemaFormat.JSON_SCHEMA
  ) -> int:
    """Register a new schema version."""
    pass
  
  @abstractmethod
  async def get_schema(
    self,
    subject: str,
    version: Optional[int] = None
  ) -> Optional[Dict[str, Any]]:
    """Get a schema by subject and version."""
    pass
  
  @abstractmethod
  async def validate(
    self,
    subject: str,
    data: Dict[str, Any],
    version: Optional[int] = None
  ) -> bool:
    """Validate data against a schema."""
    pass
  
  @abstractmethod
  async def check_compatibility(
    self,
    subject: str,
    new_schema: Dict[str, Any],
    format: SchemaFormat = SchemaFormat.JSON_SCHEMA
  ) -> bool:
    """Check if new schema is compatible with existing."""
    pass
  
  @abstractmethod
  async def list_subjects(self) -> List[str]:
    """List all registered subjects."""
    pass
  
  @abstractmethod
  async def delete_subject(self, subject: str) -> bool:
    """Delete a subject and all its versions."""
    pass


class LocalSchemaRegistry(SchemaRegistry):
  """In-memory schema registry for development."""
  
  def __init__(self):
    self._subjects: Dict[str, SchemaSubject] = {}
    self._initialize_default_schemas()
  
  def _initialize_default_schemas(self):
    """Initialize with default event schemas."""
    # Base event schema
    base_event_schema = {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "type": "object",
      "properties": {
        "event_type": {"type": "string"},
        "metadata": {
          "type": "object",
          "properties": {
            "event_id": {"type": "string"},
            "trace_id": {"type": "string"},
            "source_pillar": {"type": "string"},
            "source_agent": {"type": "string"},
            "timestamp": {"type": "string", "format": "date-time"},
            "priority": {"type": "string", "enum": ["low", "normal", "high", "critical"]}
          },
          "required": ["event_id", "trace_id", "timestamp"]
        },
        "payload": {"type": "object"},
        "schema_version": {"type": "string"}
      },
      "required": ["event_type", "metadata", "payload"]
    }
    
    # Register base schema
    self._subjects["event.base"] = SchemaSubject(name="event.base")
    self._subjects["event.base"].add_version(base_event_schema, SchemaFormat.JSON_SCHEMA)
    
    # Pillar-specific schemas
    self._register_pillar_schemas()
  
  def _register_pillar_schemas(self):
    """Register schemas for each business pillar."""
    # Mission & Governance events
    policy_update_schema = {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "type": "object",
      "properties": {
        "policy_name": {"type": "string"},
        "policy_type": {"type": "string"},
        "changes": {
          "type": "object",
          "properties": {
            "old_value": {},
            "new_value": {},
            "effective_date": {"type": "string", "format": "date-time"}
          }
        },
        "approver": {"type": "string"},
        "approval_id": {"type": "string"}
      },
      "required": ["policy_name", "policy_type", "changes"]
    }
    
    self._subjects["event.policy.update"] = SchemaSubject(name="event.policy.update")
    self._subjects["event.policy.update"].add_version(policy_update_schema, SchemaFormat.JSON_SCHEMA)
    
    # Growth Engine events
    campaign_launch_schema = {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "type": "object",
      "properties": {
        "campaign_id": {"type": "string"},
        "campaign_name": {"type": "string"},
        "channel": {"type": "string", "enum": ["email", "social", "display", "search", "affiliate"]},
        "budget": {"type": "number", "minimum": 0},
        "target_audience": {
          "type": "object",
          "properties": {
            "segments": {"type": "array", "items": {"type": "string"}},
            "size": {"type": "integer", "minimum": 0}
          }
        },
        "metrics": {
          "type": "object",
          "properties": {
            "expected_reach": {"type": "integer"},
            "expected_conversions": {"type": "integer"},
            "expected_roi": {"type": "number"}
          }
        }
      },
      "required": ["campaign_id", "campaign_name", "channel", "budget"]
    }
    
    self._subjects["event.campaign.launch"] = SchemaSubject(name="event.campaign.launch")
    self._subjects["event.campaign.launch"].add_version(campaign_launch_schema, SchemaFormat.JSON_SCHEMA)
    
    # Platform & Infrastructure events
    service_deployed_schema = {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "type": "object",
      "properties": {
        "service_name": {"type": "string"},
        "version": {"type": "string"},
        "environment": {"type": "string", "enum": ["dev", "staging", "prod"]},
        "deployment_type": {"type": "string", "enum": ["rolling", "blue_green", "canary"]},
        "resources": {
          "type": "object",
          "properties": {
            "cpu": {"type": "string"},
            "memory": {"type": "string"},
            "replicas": {"type": "integer", "minimum": 1}
          }
        },
        "health_check_url": {"type": "string", "format": "uri"},
        "rollback_version": {"type": "string"}
      },
      "required": ["service_name", "version", "environment"]
    }
    
    self._subjects["event.service.deployed"] = SchemaSubject(name="event.service.deployed")
    self._subjects["event.service.deployed"].add_version(service_deployed_schema, SchemaFormat.JSON_SCHEMA)
  
  async def register_schema(
    self,
    subject: str,
    schema: Dict[str, Any],
    format: SchemaFormat = SchemaFormat.JSON_SCHEMA
  ) -> int:
    """Register a new schema version."""
    if subject not in self._subjects:
      self._subjects[subject] = SchemaSubject(name=subject)
    
    # Check compatibility if not first version
    if self._subjects[subject].latest_version > 0:
      is_compatible = await self.check_compatibility(subject, schema, format)
      if not is_compatible:
        raise ValueError(f"Schema not compatible with subject {subject}")
    
    version = self._subjects[subject].add_version(schema, format)
    logger.info(f"Registered schema version {version} for subject {subject}")
    return version
  
  async def get_schema(
    self,
    subject: str,
    version: Optional[int] = None
  ) -> Optional[Dict[str, Any]]:
    """Get a schema by subject and version."""
    if subject not in self._subjects:
      return None
    
    schema_version = self._subjects[subject].get_version(version)
    return schema_version.schema if schema_version else None
  
  async def validate(
    self,
    subject: str,
    data: Dict[str, Any],
    version: Optional[int] = None
  ) -> bool:
    """Validate data against a schema."""
    schema = await self.get_schema(subject, version)
    if not schema:
      logger.warning(f"No schema found for subject {subject}")
      return False
    
    try:
      jsonschema.validate(data, schema)
      return True
    except jsonschema.ValidationError as e:
      logger.error(f"Validation failed for subject {subject}: {e.message}")
      return False
  
  async def check_compatibility(
    self,
    subject: str,
    new_schema: Dict[str, Any],
    format: SchemaFormat = SchemaFormat.JSON_SCHEMA
  ) -> bool:
    """Check if new schema is compatible with existing."""
    if subject not in self._subjects:
      return True  # No existing schema, so compatible
    
    mode = self._subjects[subject].compatibility_mode
    if mode == CompatibilityMode.NONE:
      return True
    
    # Get latest schema
    latest = self._subjects[subject].get_version()
    if not latest:
      return True
    
    # Simple compatibility check for JSON Schema
    if format == SchemaFormat.JSON_SCHEMA:
      return self._check_json_schema_compatibility(
        latest.schema,
        new_schema,
        mode
      )
    
    # For other formats, would implement specific checks
    return True
  
  def _check_json_schema_compatibility(
    self,
    old_schema: Dict[str, Any],
    new_schema: Dict[str, Any],
    mode: CompatibilityMode
  ) -> bool:
    """Check JSON Schema compatibility."""
    old_props = old_schema.get("properties", {})
    new_props = new_schema.get("properties", {})
    old_required = set(old_schema.get("required", []))
    new_required = set(new_schema.get("required", []))
    
    if mode == CompatibilityMode.BACKWARD:
      # New schema can read old data
      # All old required fields must be in new schema
      if not old_required.issubset(new_props.keys()):
        return False
      # New required fields must have defaults
      new_only_required = new_required - old_required
      # Simplified check - in practice would verify defaults
      return True
    
    elif mode == CompatibilityMode.FORWARD:
      # Old schema can read new data
      # All new required fields must be in old schema
      if not new_required.issubset(old_props.keys()):
        return False
      return True
    
    elif mode == CompatibilityMode.FULL:
      # Both backward and forward compatible
      return (
        self._check_json_schema_compatibility(old_schema, new_schema, CompatibilityMode.BACKWARD) and
        self._check_json_schema_compatibility(old_schema, new_schema, CompatibilityMode.FORWARD)
      )
    
    return True
  
  async def list_subjects(self) -> List[str]:
    """List all registered subjects."""
    return list(self._subjects.keys())
  
  async def delete_subject(self, subject: str) -> bool:
    """Delete a subject and all its versions."""
    if subject in self._subjects:
      del self._subjects[subject]
      logger.info(f"Deleted subject {subject}")
      return True
    return False
  
  def get_subject_info(self, subject: str) -> Optional[Dict[str, Any]]:
    """Get detailed information about a subject."""
    if subject not in self._subjects:
      return None
    
    subj = self._subjects[subject]
    return {
      "name": subj.name,
      "latest_version": subj.latest_version,
      "compatibility_mode": subj.compatibility_mode.value,
      "versions": list(subj.versions.keys()),
      "metadata": subj.metadata
    }


class ConfluentSchemaRegistry(SchemaRegistry):
  """Schema registry client for Confluent Schema Registry."""
  
  def __init__(self, url: str = "http://localhost:8081"):
    self.url = url
    logger.info(f"Confluent Schema Registry client initialized: {url}")
  
  async def register_schema(
    self,
    subject: str,
    schema: Dict[str, Any],
    format: SchemaFormat = SchemaFormat.JSON_SCHEMA
  ) -> int:
    """Register schema with Confluent registry."""
    # In production, would use requests or httpx
    # response = requests.post(
    #   f"{self.url}/subjects/{subject}/versions",
    #   json={"schema": json.dumps(schema)}
    # )
    logger.info(f"Would register schema for {subject} to Confluent")
    return 1
  
  async def get_schema(
    self,
    subject: str,
    version: Optional[int] = None
  ) -> Optional[Dict[str, Any]]:
    """Get schema from Confluent registry."""
    # In production, would fetch from Confluent
    logger.info(f"Would fetch schema for {subject} from Confluent")
    return None
  
  async def validate(
    self,
    subject: str,
    data: Dict[str, Any],
    version: Optional[int] = None
  ) -> bool:
    """Validate using Confluent registry."""
    # Would validate against Confluent schema
    return True
  
  async def check_compatibility(
    self,
    subject: str,
    new_schema: Dict[str, Any],
    format: SchemaFormat = SchemaFormat.JSON_SCHEMA
  ) -> bool:
    """Check compatibility using Confluent."""
    # Would use Confluent compatibility API
    return True
  
  async def list_subjects(self) -> List[str]:
    """List subjects from Confluent."""
    # Would fetch from Confluent API
    return []
  
  async def delete_subject(self, subject: str) -> bool:
    """Delete subject from Confluent."""
    # Would delete via Confluent API
    return True


class SchemaEvolutionHelper:
  """Helper for schema evolution patterns."""
  
  @staticmethod
  def add_optional_field(
    schema: Dict[str, Any],
    field_name: str,
    field_schema: Dict[str, Any]
  ) -> Dict[str, Any]:
    """Add an optional field to schema (backward compatible)."""
    new_schema = schema.copy()
    if "properties" not in new_schema:
      new_schema["properties"] = {}
    new_schema["properties"][field_name] = field_schema
    return new_schema
  
  @staticmethod
  def add_required_field_with_default(
    schema: Dict[str, Any],
    field_name: str,
    field_schema: Dict[str, Any],
    default_value: Any
  ) -> Dict[str, Any]:
    """Add required field with default (backward compatible)."""
    new_schema = schema.copy()
    if "properties" not in new_schema:
      new_schema["properties"] = {}
    
    field_schema_with_default = field_schema.copy()
    field_schema_with_default["default"] = default_value
    new_schema["properties"][field_name] = field_schema_with_default
    
    if "required" not in new_schema:
      new_schema["required"] = []
    new_schema["required"].append(field_name)
    
    return new_schema
  
  @staticmethod
  def deprecate_field(
    schema: Dict[str, Any],
    field_name: str,
    deprecation_message: str
  ) -> Dict[str, Any]:
    """Mark a field as deprecated."""
    new_schema = schema.copy()
    if "properties" in new_schema and field_name in new_schema["properties"]:
      new_schema["properties"][field_name]["deprecated"] = True
      new_schema["properties"][field_name]["description"] = (
        new_schema["properties"][field_name].get("description", "") + 
        f" DEPRECATED: {deprecation_message}"
      )
    return new_schema


# Schema validation decorators
def validate_event(subject: str, registry: SchemaRegistry):
  """Decorator to validate event data against schema."""
  def decorator(func):
    async def wrapper(event_data: Dict[str, Any], *args, **kwargs):
      is_valid = await registry.validate(subject, event_data)
      if not is_valid:
        raise ValueError(f"Event data does not match schema for {subject}")
      return await func(event_data, *args, **kwargs)
    return wrapper
  return decorator