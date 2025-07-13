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

"""Comprehensive demonstration of Data Architecture components and workflows."""

import asyncio
import json
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List

# Import data architecture components
try:
    # Try relative imports first (when running as module)
    from .data_orchestrator import DataArchitectureOrchestrator
    from .vector_store import VectorStoreType
    from .data_layers import StorageBackend
    from .feature_store import StorageMode
except ImportError:
    # Fall back to absolute imports (when running as script)
    from data_orchestrator import DataArchitectureOrchestrator
    from vector_store import VectorStoreType
    from data_layers import StorageBackend
    from feature_store import StorageMode

# Import existing infrastructure for integration
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_mesh.event_bus import EventBusFactory
from data_mesh.lineage_service import LineageService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataArchitectureDemo:
    """Comprehensive demonstration of data architecture features."""
    
    def __init__(self):
        # Initialize data mesh components
        self.event_bus = EventBusFactory.create("memory")
        self.lineage_service = LineageService()
        
        # Initialize data architecture with configuration
        self.orchestrator = DataArchitectureOrchestrator(
            vector_store_config={
                "type": "in_memory",
                "dimension": 1536
            },
            data_layer_config={
                "backend": "local",
                "base_path": "/tmp/data_architecture_demo"
            },
            feature_store_config={
                "online_store": "redis",
                "offline_store": "bigquery"
            },
            event_bus=self.event_bus,
            lineage_service=self.lineage_service
        )
    
    async def initialize(self):
        """Initialize all components."""
        logger.info("🚀 Initializing Data Architecture Demo")
        
        # Initialize orchestrator
        await self.orchestrator.initialize()
        
        logger.info("✅ Demo initialization complete")
    
    async def demonstrate_full_data_flow(self):
        """Demonstrate the complete data flow from the specification."""
        logger.info("\n" + "="*80)
        logger.info("📊 DEMONSTRATING FULL DATA FLOW")
        logger.info("Scenario: NetSuite CDC → Bronze → Silver → Gold → Vector/Features → Agent Use")
        logger.info("="*80)
        
        # Step 1: Event lands - NetSuite CDC emits invoice_paid into Kafka
        logger.info("\n1. 📥 Event Ingestion: NetSuite CDC invoice_paid event")
        invoice_data = await self._simulate_netsuite_cdc_event()
        
        # Step 2-6: Bronze → Silver → Gold → Vector → Features
        logger.info("\n2-6. 🔄 Data Pipeline: Bronze → Silver → Gold + Vector + Features")
        pipeline_result = await self.orchestrator.ingest_data_flow(
            raw_data=invoice_data,
            source_system="netsuite",
            data_type="invoices",
            bronze_table="invoices_bronze",
            create_embeddings=True,
            create_features=True
        )
        
        if pipeline_result["success"]:
            logger.info(f"✅ Pipeline completed successfully:")
            logger.info(f"   📊 Bronze records: {pipeline_result['bronze_records']}")
            logger.info(f"   🔧 Silver processed: {pipeline_result['silver_processed']}")
            logger.info(f"   🏆 Gold marts: {list(pipeline_result['gold_marts'].keys())}")
            logger.info(f"   🔍 Vector embeddings: {pipeline_result['vector_embeddings']['success']}")
            logger.info(f"   🎯 Features: {pipeline_result['features']['success']}")
        else:
            logger.error(f"❌ Pipeline failed: {pipeline_result['error']}")
            return
        
        # Step 7: Agents act - demonstrate agent usage
        logger.info("\n7. 🤖 Agent Actions: Customer Success and Growth Engine")
        await self._demonstrate_agent_usage(pipeline_result["lineage_id"])
        
        return pipeline_result["lineage_id"]
    
    async def _simulate_netsuite_cdc_event(self) -> List[Dict]:
        """Simulate NetSuite CDC invoice_paid events."""
        invoices = []
        
        for i in range(5):
            invoice = {
                "id": f"INV-{1000 + i}",
                "customer_id": f"CUST-{100 + i % 3}",  # 3 different customers
                "invoice_number": f"INV-2025-{1000 + i}",
                "amount": random.uniform(500, 5000),
                "status": "paid",
                "payment_date": (datetime.now() - timedelta(days=i)).isoformat(),
                "due_date": (datetime.now() - timedelta(days=i+30)).isoformat(),
                "line_items": [
                    {
                        "product_id": f"PROD-{200 + j}",
                        "description": f"Professional Services - Month {i+j+1}",
                        "quantity": 1,
                        "unit_price": random.uniform(100, 1000),
                        "total": random.uniform(100, 1000)
                    }
                    for j in range(random.randint(1, 3))
                ],
                "memo": f"Payment received for services rendered in month {i+1}. Customer satisfaction rating: {random.randint(4, 5)}/5.",
                "payment_method": random.choice(["credit_card", "bank_transfer", "check"]),
                "currency": "USD",
                "metadata": {
                    "sales_rep": f"rep_{i % 2}",
                    "region": random.choice(["north", "south", "east", "west"]),
                    "contract_type": random.choice(["monthly", "annual", "project"])
                }
            }
            invoices.append(invoice)
        
        logger.info(f"Generated {len(invoices)} NetSuite invoice_paid events")
        return invoices
    
    async def _demonstrate_agent_usage(self, lineage_id: str):
        """Demonstrate how agents would use the data architecture."""
        
        # Customer Success Agent: Vector search + Features for churn risk
        logger.info("\n🎯 Customer Success Agent: Churn Risk Assessment")
        await self._demo_customer_success_agent()
        
        # Growth Engine Agent: Pricing optimization with similar deals
        logger.info("\n💰 Growth Engine Agent: Pricing Optimization")
        await self._demo_growth_engine_agent()
        
        # Intelligence Agent: Feature analysis for insights
        logger.info("\n🧠 Intelligence Agent: Feature Analysis")
        await self._demo_intelligence_agent(lineage_id)
    
    async def _demo_customer_success_agent(self):
        """Demo Customer Success agent using vector search + features."""
        try:
            # Search for similar customer situations
            search_result = await self.orchestrator.search_and_retrieve(
                query="customer payment delayed high value professional services",
                include_features=True,
                namespace="invoices_embeddings",
                top_k=3
            )
            
            if search_result["success"] and search_result["results"]:
                logger.info(f"   🔍 Found {search_result['results_count']} similar customer situations")
                
                for i, result in enumerate(search_result["results"][:2]):
                    logger.info(f"   📄 Result {i+1}: {result['content'][:50]}... (score: {result['score']:.3f})")
                    if "features" in result:
                        logger.info(f"       Features: {list(result['features'].keys())}")
            else:
                logger.info("   ℹ️ No similar situations found (expected for fresh data)")
            
            # Get customer features directly
            customer_features = await self.orchestrator.feature_store_manager.get_online_features(
                feature_group_name="customer_features",
                entity_ids=["CUST-100", "CUST-101"],
                feature_names=["total_orders", "total_spent", "last_order_days_ago"]
            )
            
            if customer_features:
                logger.info(f"   💡 Customer insights:")
                for cust_id, features in customer_features.items():
                    logger.info(f"       {cust_id}: {features}")
            else:
                logger.info("   💡 Customer features ready for future analysis")
        
        except Exception as e:
            logger.error(f"Customer Success demo error: {e}")
    
    async def _demo_growth_engine_agent(self):
        """Demo Growth Engine agent using vector similarity for pricing."""
        try:
            # Search for similar deals to inform pricing
            search_result = await self.orchestrator.search_and_retrieve(
                query="professional services monthly contract pricing",
                include_features=True,
                namespace="invoices_embeddings",
                top_k=5
            )
            
            if search_result["success"]:
                logger.info(f"   🔍 Analyzed {search_result['results_count']} similar deals for pricing insights")
                
                # Mock pricing recommendation based on search results
                if search_result["results"]:
                    scores = [r["score"] for r in search_result["results"]]
                    avg_similarity = sum(scores) / len(scores)
                    recommended_price = 1500 * (1 + avg_similarity)  # Mock calculation
                    
                    logger.info(f"   💰 Pricing recommendation: ${recommended_price:.2f}")
                    logger.info(f"   📊 Based on {len(scores)} similar deals (avg similarity: {avg_similarity:.3f})")
                else:
                    logger.info("   💰 Pricing recommendation: Use baseline pricing for new patterns")
            
            # Check product features for inventory-based pricing
            product_features = await self.orchestrator.feature_store_manager.get_online_features(
                feature_group_name="product_features",
                entity_ids=["PROD-200", "PROD-201"],
                feature_names=["sales_last_30d", "avg_rating", "inventory_level"]
            )
            
            if product_features:
                logger.info(f"   📦 Product insights for pricing:")
                for prod_id, features in product_features.items():
                    logger.info(f"       {prod_id}: {features}")
            else:
                logger.info("   📦 Product features available for inventory-based pricing")
        
        except Exception as e:
            logger.error(f"Growth Engine demo error: {e}")
    
    async def _demo_intelligence_agent(self, lineage_id: str):
        """Demo Intelligence agent analyzing data lineage and features."""
        try:
            # Trace data lineage
            lineage_trace = await self.orchestrator.data_layer_manager.get_lineage_trace(lineage_id)
            
            logger.info(f"   🔍 Data lineage analysis:")
            logger.info(f"       Bronze tables: {list(lineage_trace['bronze_tables'].keys())}")
            logger.info(f"       Silver tables: {list(lineage_trace['silver_tables'].keys())}")
            logger.info(f"       Gold tables: {list(lineage_trace['gold_tables'].keys())}")
            
            # Analyze feature store metrics
            feature_stats = await self.orchestrator.feature_store_manager.get_feature_store_stats()
            
            logger.info(f"   📊 Feature store analysis:")
            logger.info(f"       Feature groups: {feature_stats['feature_groups']}")
            logger.info(f"       Total features: {feature_stats['total_features']}")
            
            # Generate insights
            logger.info(f"   💡 Generated insights:")
            logger.info(f"       - Payment velocity increased by processing {lineage_trace['bronze_tables'].get('invoices_bronze', 0)} invoices")
            logger.info(f"       - Customer behavior patterns ready for ML model training")
            logger.info(f"       - Cross-pillar data flow complete with lineage ID: {lineage_id[:8]}...")
        
        except Exception as e:
            logger.error(f"Intelligence agent demo error: {e}")
    
    async def demonstrate_vector_store_capabilities(self):
        """Demonstrate vector store features for RAG and similarity search."""
        logger.info("\n" + "="*60)
        logger.info("🔍 VECTOR STORE CAPABILITIES")
        logger.info("="*60)
        
        # Store sample documents with different types
        logger.info("\n1. 📚 Storing diverse document types")
        
        documents = [
            {
                "id": "doc_customer_guide",
                "text": "Customer onboarding guide for professional services. Includes pricing tiers, service levels, and support contacts.",
                "title": "Customer Onboarding Guide",
                "source": "documentation",
                "type": "customer_guide",
                "metadata": {"category": "onboarding", "audience": "customers"}
            },
            {
                "id": "doc_pricing_policy",
                "text": "Pricing policy for professional services. Monthly contracts start at $1000. Annual contracts receive 15% discount.",
                "title": "Professional Services Pricing Policy",
                "source": "policy",
                "type": "pricing",
                "metadata": {"category": "pricing", "audience": "sales"}
            },
            {
                "id": "doc_support_escalation",
                "text": "Support escalation procedures for high-value customers. Critical issues require 2-hour response time.",
                "title": "Support Escalation Procedures",
                "source": "procedures",
                "type": "support",
                "metadata": {"category": "support", "audience": "support_team"}
            }
        ]
        
        stored_ids = await self.orchestrator.vector_store_manager.store_embeddings(
            documents=documents,
            namespace="knowledge_base",
            lineage_id="demo_vector_lineage"
        )
        
        logger.info(f"✅ Stored {len(stored_ids)} documents in knowledge base")
        
        # Demonstrate similarity search queries
        logger.info("\n2. 🔍 Similarity search queries")
        
        queries = [
            "How do I price a new customer contract?",
            "What should I do for an urgent customer issue?",
            "Customer wants information about getting started"
        ]
        
        for query in queries:
            results = await self.orchestrator.vector_store_manager.similarity_search(
                query_text=query,
                namespace="knowledge_base",
                top_k=2
            )
            
            logger.info(f"\n   Query: '{query}'")
            for result in results:
                logger.info(f"   📄 {result.metadata['title']} (score: {result.score:.3f})")
        
        # Get vector store statistics
        stats = await self.orchestrator.vector_store_manager.get_store_stats()
        logger.info(f"\n📊 Vector Store Stats: {stats['total_vectors']} vectors, {len(stats['namespaces'])} namespaces")
    
    async def demonstrate_feature_store_workflows(self):
        """Demonstrate feature store online/offline workflows."""
        logger.info("\n" + "="*60)
        logger.info("🎯 FEATURE STORE WORKFLOWS")
        logger.info("="*60)
        
        # Materialize customer features
        logger.info("\n1. 💾 Materializing customer features")
        
        customer_data = [
            {
                "customer_id": "CUST-001",
                "count(*)": 12,  # total_orders
                "amount": 15000,  # total_spent
                "order_date": (datetime.now() - timedelta(days=5)).isoformat()  # last order
            },
            {
                "customer_id": "CUST-002", 
                "count(*)": 8,
                "amount": 8500,
                "order_date": (datetime.now() - timedelta(days=12)).isoformat()
            },
            {
                "customer_id": "CUST-003",
                "count(*)": 25,
                "amount": 42000,
                "order_date": (datetime.now() - timedelta(days=2)).isoformat()
            }
        ]
        
        customer_success = await self.orchestrator.feature_store_manager.materialize_features(
            feature_group_name="customer_features",
            source_data=customer_data,
            storage_mode=StorageMode.BOTH
        )
        
        logger.info(f"✅ Customer features materialized: {customer_success}")
        
        # Materialize product features
        logger.info("\n2. 📦 Materializing product features")
        
        product_data = [
            {
                "product_id": "PROD-101",
                "quantity": 150,  # sales_last_30d
                "revenue": 75000,  # revenue_last_30d
                "rating": 4.5,    # avg_rating
                "inventory": 500  # inventory_level
            },
            {
                "product_id": "PROD-102",
                "quantity": 89,
                "revenue": 44500,
                "rating": 4.2,
                "inventory": 250
            }
        ]
        
        product_success = await self.orchestrator.feature_store_manager.materialize_features(
            feature_group_name="product_features",
            source_data=product_data,
            storage_mode=StorageMode.BOTH
        )
        
        logger.info(f"✅ Product features materialized: {product_success}")
        
        # Demonstrate online feature serving (real-time inference)
        logger.info("\n3. ⚡ Online feature serving (real-time inference)")
        
        online_customer_features = await self.orchestrator.feature_store_manager.get_online_features(
            feature_group_name="customer_features",
            entity_ids=["CUST-001", "CUST-002"]
        )
        
        logger.info(f"⚡ Online customer features:")
        for customer_id, features in online_customer_features.items():
            logger.info(f"   {customer_id}: {features}")
        
        # Demonstrate offline features (batch processing)
        logger.info("\n4. 📊 Offline features (batch processing)")
        
        training_dataset = await self.orchestrator.feature_store_manager.create_training_dataset(
            feature_groups=["customer_features", "product_features"],
            start_time=datetime.now() - timedelta(days=7),
            end_time=datetime.now()
        )
        
        logger.info(f"📊 Training dataset created:")
        logger.info(f"   Feature groups: {training_dataset['metadata']['feature_groups']}")
        logger.info(f"   Total rows: {training_dataset['metadata']['total_rows']}")
    
    async def demonstrate_data_layer_lifecycle(self):
        """Demonstrate Bronze/Silver/Gold data layer lifecycle."""
        logger.info("\n" + "="*60)
        logger.info("📊 DATA LAYER LIFECYCLE")
        logger.info("="*60)
        
        # Bronze layer: Raw data ingestion
        logger.info("\n1. 🥉 Bronze Layer: Raw data ingestion")
        
        raw_sales_data = [
            {
                "transaction_id": "TXN-001",
                "customer_email": "john.doe@example.com",  # PII to be masked
                "amount": "1500.00",  # String to be cleaned
                "product_name": "  Professional Services  ",  # Whitespace to be cleaned
                "timestamp": datetime.now().isoformat()
            },
            {
                "transaction_id": "TXN-002",
                "customer_email": "jane.smith@company.com",
                "amount": "2200.50",
                "product_name": "consulting services",
                "timestamp": (datetime.now() - timedelta(hours=2)).isoformat()
            }
        ]
        
        bronze_lineage = await self.orchestrator.data_layer_manager.ingest_raw_data(
            data=raw_sales_data,
            source_system="sales_system",
            table_name="sales_bronze"
        )
        
        logger.info(f"✅ Bronze ingestion complete, lineage ID: {bronze_lineage[:8]}...")
        
        # Silver layer: Data cleaning and transformation
        logger.info("\n2. 🥈 Silver Layer: Data cleaning and PII masking")
        
        silver_success = await self.orchestrator.data_layer_manager.process_bronze_to_silver(
            bronze_table="sales_bronze",
            silver_table="sales_silver"
        )
        
        logger.info(f"✅ Silver transformation complete: {silver_success}")
        
        # Read Silver data to show transformations
        silver_data = await self.orchestrator.data_layer_manager.silver.read("sales_silver")
        if silver_data:
            logger.info(f"   🔧 Transformations applied:")
            sample_record = silver_data[0]
            logger.info(f"       Email masked: {sample_record.data.get('customer_email', 'N/A')}")
            logger.info(f"       Name cleaned: '{sample_record.data.get('product_name', 'N/A')}'")
        
        # Gold layer: Business marts
        logger.info("\n3. 🥇 Gold Layer: Business marts creation")
        
        gold_results = await self.orchestrator.data_layer_manager.create_gold_marts(
            silver_table="sales_silver"
        )
        
        logger.info(f"✅ Gold marts created:")
        for mart_name, success in gold_results.items():
            status = "✅" if success else "❌"
            logger.info(f"   {status} {mart_name}")
        
        # Show data layer statistics
        layer_stats = await self.orchestrator.data_layer_manager.get_layer_stats()
        logger.info(f"\n📊 Data Layer Statistics:")
        logger.info(f"   Bronze: {layer_stats['bronze']['total_records']} records in {layer_stats['bronze']['table_count']} tables")
        logger.info(f"   Silver: {layer_stats['silver']['total_records']} records, {layer_stats['silver']['transformation_rules']} rules")
        logger.info(f"   Gold: {layer_stats['gold']['total_records']} records, {layer_stats['gold']['business_marts']} marts")
    
    async def demonstrate_agent_tool_integration(self):
        """Demonstrate agent tool integration."""
        logger.info("\n" + "="*60)
        logger.info("🤖 AGENT TOOL INTEGRATION")
        logger.info("="*60)
        
        # Create agent tools
        logger.info("\n1. 🔧 Creating agent tools")
        
        tools = await self.orchestrator.create_agent_tools()
        
        logger.info(f"✅ Created {len(tools)} agent tools:")
        for tool in tools:
            tool_name = tool["function"]["name"]
            description = tool["function"]["description"]
            logger.info(f"   🛠️ {tool_name}: {description}")
        
        # Simulate agent tool usage
        logger.info("\n2. 🤖 Simulating agent tool usage")
        
        # Vector search tool usage
        try:
            from .vector_store import vector_search_tool
        except ImportError:
            from data_architecture.vector_store import vector_search_tool
        
        search_result = await vector_search_tool(
            query="pricing policy for new customers",
            manager=self.orchestrator.vector_store_manager,
            namespace="knowledge_base",
            top_k=3
        )
        
        logger.info(f"🔍 Vector search result:")
        logger.info(f"   Success: {search_result['success']}")
        logger.info(f"   Results: {search_result['results_count']}")
        
        # Feature retrieval tool usage
        try:
            from .feature_store import get_features_tool
        except ImportError:
            from data_architecture.feature_store import get_features_tool
        
        feature_result = await get_features_tool(
            entity_ids=["CUST-001", "CUST-002"],
            manager=self.orchestrator.feature_store_manager,
            feature_group="customer_features",
            use_online=True
        )
        
        logger.info(f"🎯 Feature retrieval result:")
        logger.info(f"   Success: {feature_result['success']}")
        logger.info(f"   Store type: {feature_result['store_type']}")
        logger.info(f"   Entities: {feature_result['entity_count']}")
        
        # Combined search and retrieve tool
        try:
            from .data_orchestrator import search_and_retrieve_tool
        except ImportError:
            from data_architecture.data_orchestrator import search_and_retrieve_tool
        
        combined_result = await search_and_retrieve_tool(
            query="customer onboarding process",
            orchestrator=self.orchestrator,
            include_features=True,
            top_k=2
        )
        
        logger.info(f"🔄 Combined search result:")
        logger.info(f"   Success: {combined_result['success']}")
        if 'results_count' in combined_result:
            logger.info(f"   Results with features: {combined_result['results_count']}")
        else:
            logger.info(f"   Combined search completed")
    
    async def demonstrate_ml_training_dataset_creation(self):
        """Demonstrate ML training dataset creation."""
        logger.info("\n" + "="*60)
        logger.info("🤖 ML TRAINING DATASET CREATION")
        logger.info("="*60)
        
        # Create comprehensive training dataset
        training_dataset = await self.orchestrator.create_ml_training_dataset(
            feature_groups=["customer_features", "product_features"],
            include_embeddings=True,
            days_back=30
        )
        
        if training_dataset["success"]:
            dataset = training_dataset["dataset"]
            
            logger.info(f"✅ ML training dataset created:")
            logger.info(f"   Dataset ID: {dataset['dataset_id']}")
            logger.info(f"   Feature groups: {dataset['feature_dataset']['metadata']['feature_groups']}")
            logger.info(f"   Total rows: {dataset['feature_dataset']['metadata']['total_rows']}")
            logger.info(f"   Time range: {dataset['feature_dataset']['metadata']['time_range']}")
            
            # Show sample data structure
            if dataset['feature_dataset']['dataset']:
                sample_group = list(dataset['feature_dataset']['dataset'].keys())[0]
                sample_data = dataset['feature_dataset']['dataset'][sample_group]
                
                if sample_data:
                    logger.info(f"\n📊 Sample data from {sample_group}:")
                    sample_record = sample_data[0]
                    for key, value in list(sample_record.items())[:5]:
                        logger.info(f"   {key}: {value}")
        else:
            logger.error(f"❌ Training dataset creation failed: {training_dataset['error']}")
    
    async def get_comprehensive_dashboard(self):
        """Show comprehensive dashboard of all components."""
        logger.info("\n" + "="*60)
        logger.info("📊 COMPREHENSIVE DASHBOARD")
        logger.info("="*60)
        
        dashboard = await self.orchestrator.get_data_architecture_dashboard()
        
        logger.info(f"🚀 Orchestrator Status: {dashboard['orchestrator_status']}")
        
        logger.info(f"\n🔧 Sync Tasks:")
        for task_name, status in dashboard['sync_tasks'].items():
            status_icon = "✅" if status == "running" else "⏸️"
            logger.info(f"   {status_icon} {task_name}: {status}")
        
        logger.info(f"\n🔍 Vector Store:")
        vector_stats = dashboard['vector_store']
        logger.info(f"   Type: {vector_stats['store_type']}")
        logger.info(f"   Dimensions: {vector_stats['dimension']}")
        logger.info(f"   Total vectors: {vector_stats['total_vectors']}")
        logger.info(f"   Namespaces: {vector_stats['namespaces']}")
        
        logger.info(f"\n📊 Data Layers:")
        layer_stats = dashboard['data_layers']
        for layer in ['bronze', 'silver', 'gold']:
            stats = layer_stats[layer]
            logger.info(f"   {layer.title()}: {stats['total_records']} records, {stats['table_count']} tables")
        
        logger.info(f"\n🎯 Feature Store:")
        feature_stats = dashboard['feature_store']
        logger.info(f"   Feature groups: {feature_stats['feature_groups']}")
        logger.info(f"   Total features: {feature_stats['total_features']}")
        logger.info(f"   Groups: {feature_stats['groups']}")
        
        logger.info(f"\n🔗 Integration:")
        integration = dashboard['integration']
        for component, connected in integration.items():
            status = "✅" if connected else "❌"
            logger.info(f"   {status} {component}")
    
    async def cleanup(self):
        """Cleanup demo resources."""
        logger.info("\n🧹 Cleaning up demo resources...")
        
        await self.orchestrator.shutdown()
        await self.event_bus.close()
        
        logger.info("✅ Cleanup complete")


async def main():
    """Run the comprehensive data architecture demonstration."""
    print("🚀 Data Architecture Demo - Vector Stores, Data Layers, and Feature Store")
    print("=" * 80)
    print("This demo showcases the complete data architecture:")
    print("- Vector store integration (Pinecone/pgvector) for RAG")
    print("- Bronze/Silver/Gold data layers with lineage tracking")
    print("- Feature store with online/offline storage")
    print("- End-to-end data flow from CDC to agent usage")
    print("- Integration with data mesh and lineage service")
    print("=" * 80)
    
    demo = DataArchitectureDemo()
    
    try:
        # Initialize demo
        await demo.initialize()
        
        # Run comprehensive demonstrations
        lineage_id = await demo.demonstrate_full_data_flow()
        await demo.demonstrate_vector_store_capabilities()
        await demo.demonstrate_feature_store_workflows()
        await demo.demonstrate_data_layer_lifecycle()
        await demo.demonstrate_agent_tool_integration()
        await demo.demonstrate_ml_training_dataset_creation()
        
        # Show final dashboard
        await demo.get_comprehensive_dashboard()
        
        print("\n" + "="*80)
        print("🎉 DATA ARCHITECTURE DEMONSTRATION COMPLETE!")
        print("="*80)
        print("\nKey capabilities demonstrated:")
        print("✅ Vector embeddings with lineage tracking")
        print("✅ Bronze/Silver/Gold data pipeline with transformations")
        print("✅ Feature store online/offline consistency")
        print("✅ Agent tool integration for RAG and features")
        print("✅ ML training dataset generation")
        print("✅ Event-driven data flow orchestration")
        print("✅ Comprehensive data lineage tracking")
        print("\nThe AI-native enterprise now has industrial-grade data architecture:")
        print("🔍 Contextual memory and search for every LLM tool step")
        print("🏭 Industrial data hygiene with replay capabilities")
        print("⚡ Production-grade ML feature delivery without skew")
        print("🔗 Unified data flow from ingestion to agent action")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise
    finally:
        await demo.cleanup()


if __name__ == "__main__":
    asyncio.run(main())