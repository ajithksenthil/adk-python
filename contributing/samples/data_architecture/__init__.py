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

"""Data Architecture - Vector stores, data layers, and feature store for AI-native enterprise."""

from .vector_store import VectorStoreManager, VectorRecord, SimilarityResult, VectorStoreType
from .data_layers import DataLayerManager, BronzeLayer, SilverLayer, GoldLayer, StorageBackend, DataQualityLevel
from .feature_store import FeatureStoreManager, FeatureGroup, OnlineFeatures, OfflineFeatures, StorageMode
from .data_orchestrator import DataArchitectureOrchestrator

__all__ = [
    "VectorStoreManager",
    "VectorRecord", 
    "SimilarityResult",
    "VectorStoreType",
    "DataLayerManager",
    "BronzeLayer",
    "SilverLayer", 
    "GoldLayer",
    "StorageBackend",
    "DataQualityLevel",
    "FeatureStoreManager",
    "FeatureGroup",
    "OnlineFeatures",
    "OfflineFeatures",
    "StorageMode",
    "DataArchitectureOrchestrator"
]