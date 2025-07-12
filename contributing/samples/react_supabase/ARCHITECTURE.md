# Reference Architecture: React + Supabase with ADK

This document sketches how the sample in this directory can be extended to an AI-native platform.
It maps the [ADK](https://github.com/google/adk-python) building blocks to the layers and pillars
outlined in the high-level architecture diagram.

## Cross-cutting Layers

- **Control Plane** – Integrates a policy engine (e.g. OPA) and an autonomy dial
  (AML 0–5) before each agent tool call. Treasury caps are enforced via Supabase
  or blockchain multisig wallets.
- **Data / Integration Mesh** – Uses Pub/Sub or Kafka as the event bus. Session
  data and lineage IDs are stored in Supabase Postgres. A vector store such as
  `pgvector` backs retrieval-augmented agents.
- **Trust & Observability Mesh** – ADK emits OpenTelemetry spans which can be
  shipped to an observability stack for audits and nightly trajectory evaluations.

## Orchestrator Fabric

- **Kernel** – The `root_agent` defined in `agent.py` represents the entry point
  for each workflow. Agents can delegate to sub-agents or remote A2A agents.
- **Runtime** – The FastAPI server in `server.py` exposes `/run_sse` and other
  endpoints that your React frontend consumes. Deploy this service on GKE or
  Cloud Run.

## Pillar Agents

Each business pillar (Mission, Product, Growth, etc.) can be implemented as a
collection of ADK agents. The autonomy level for each workflow is controlled via
policy checks. See the architecture overview for examples of autonomy caps.

## Deployment Notes

1. Start the FastAPI service with a Supabase connection string.
2. Serve the React frontend (see `frontend/`) which streams events from the
   `/run_sse` endpoint.
3. Scale the service by deploying additional agent pods behind a load balancer.

This reference is intentionally high level; adapt it to your infrastructure and
compliance requirements.
