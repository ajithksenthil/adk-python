# Control Plane with Policy Engine

This sample demonstrates a comprehensive Control Plane implementation for ADK agents, providing centralized governance, policy enforcement, budget controls, and autonomy management as outlined in the enterprise reference architecture.

## Overview

The Control Plane provides:

1. **Policy Engine** - Runtime policy enforcement with OPA integration
2. **AML Registry** - Autonomy Maturity Level (0-5) management
3. **Treasury** - Budget caps and spending controls
4. **Policy Compiler** - Business rule to policy translation
5. **Controlled Agents** - Policy-enforced agent wrappers

## Architecture Components

### 1. Policy Engine (`policy_engine.py`)

The policy engine evaluates policies before tool execution:

- **Local Policy Engine** - In-memory policy evaluation
- **OPA Policy Engine** - Integration with Open Policy Agent
- **Policy Types**:
  - Budget policies (spending limits, approval thresholds)
  - Autonomy policies (tool access based on AML)
  - Compliance policies (required tags, data residency)
  - Security policies
  - Data access policies
  - Tool access policies

### 2. AML Registry (`aml_registry.py`)

Manages agent autonomy levels (0-5):

- **AML 0**: Read-only insights (100% human involvement)
- **AML 1**: Suggest actions (approve every action)
- **AML 2**: Batch execution (approve batches)
- **AML 3**: Real-time execution under hard caps (approve exceptions)
- **AML 4**: Self-correcting execution, soft caps (quarterly audit)
- **AML 5**: Uncapped with treasury limits (kill-switch only)

### 3. Treasury (`treasury.py`)

Manages budget allocation and spending controls:

- Per-pillar budget allocation
- Transaction approval workflows
- Single and multisig approval requirements
- Spending limit enforcement
- Audit trail generation

### 4. Policy Compiler (`policy_compiler.py`)

Translates business rules into enforceable policies:

- Natural language rule parsing
- YAML/JSON rule support
- OPA Rego code generation
- Rule validation and compilation

### 5. Control Plane Agent (`control_plane_agent.py`)

Wraps ADK agents with policy enforcement:

- Intercepts tool calls for policy evaluation
- Enforces budget constraints
- Tracks audit trail
- Manages approval workflows

### 6. Blockchain Treasury (`blockchain_treasury.py`)

Enhanced treasury with blockchain multisig wallet integration:

- **Multisig Wallets**: Each pillar has a dedicated multisig wallet
- **Signature Requirements**: Based on transaction amount and pillar
- **Daily Limits**: Per-wallet spending caps
- **Smart Contract Support**: Gnosis Safe and custom contracts
- **Emergency Controls**: Pause operations and transfer to emergency wallet

Key Features:
- Mock blockchain connector for testing
- Gnosis Safe connector for production
- Transaction signature collection
- On-chain policy enforcement
- Audit trail on blockchain

### 7. Web3Auth Integration (`web3auth_integration.py`)

Seamless wallet authentication and key management via Web3Auth:

- **Social Login**: Google, Facebook, Twitter, Discord, Email
- **Non-Custodial**: Users control their private keys
- **Multi-Factor Auth**: Built-in security features
- **Session Management**: Secure session handling
- **Key Recovery**: Social recovery options

Key Features:
- One-click social login for blockchain signing
- No seed phrases or wallet setup required
- Enterprise-grade security with MFA
- Customizable authentication flows
- Support for multiple blockchain networks

## Usage

### Basic Setup

```python
from google.adk.agents import Agent
from contributing.samples.control_plane import (
    ControlPlaneAgent,
    AMLRegistry,
    LocalPolicyEngine,
    Treasury,
    AutonomyLevel
)

# Create your base agent
my_agent = Agent(
    name="my_agent",
    model="gemini-2.0-flash",
    instruction="Your agent instructions",
    tools=[tool1, tool2]
)

# Wrap with control plane
controlled_agent = ControlPlaneAgent(
    wrapped_agent=my_agent,
    pillar="Growth Engine",
    initial_autonomy_level=AutonomyLevel.AML_3
)
```

### Blockchain Treasury Setup

Enable blockchain multisig wallets for enhanced security:

```python
from contributing.samples.control_plane import (
    BlockchainTreasury,
    WalletType
)

# Create blockchain-enabled treasury
base_treasury = Treasury(total_budget=1000000.0)
blockchain_treasury = BlockchainTreasury(
    treasury=base_treasury,
    default_wallet_type=WalletType.GNOSIS_SAFE
)

# Use with control plane
controlled_agent = ControlPlaneAgent(
    wrapped_agent=my_agent,
    pillar="Growth Engine",
    treasury=blockchain_treasury,
    enable_blockchain=True
)
```

### Web3Auth Setup

Enable social login for blockchain signers:

```python
from contributing.samples.control_plane import (
    Web3AuthTreasuryIntegration,
    create_web3auth_config
)

# Configure Web3Auth
config = create_web3auth_config(
    client_id="YOUR_WEB3AUTH_CLIENT_ID",
    environment="testnet"  # or "mainnet"
)

# Initialize integration
web3auth = Web3AuthTreasuryIntegration(
    blockchain_treasury=blockchain_treasury,
    web3auth_config=config
)

# Authorize new signer
auth_result = await web3auth.authorize_signer(
    email="treasurer@company.com",
    pillar="Mission & Governance"
)
# Redirect user to auth_result["auth_url"]
```

### Running the Sample

1. **Set Environment Variables** (for Web3Auth):
   ```bash
   export WEB3AUTH_CLIENT_ID="your_client_id_here"
   export WEB3AUTH_NETWORK="testnet"  # or "mainnet"
   ```

2. **Start the Control Plane server**:
   ```bash
   cd contributing/samples/control_plane
   python -m uvicorn server:app --reload
   ```

3. **Access the Web UI**:
   ```
   http://localhost:8000
   ```

4. **Use the CLI**:
   ```bash
   adk chat contributing/samples/control_plane
   ```

5. **Run Examples**:
   ```bash
   # Blockchain treasury examples
   python blockchain_example.py
   
   # Web3Auth integration examples
   python web3auth_example.py
   ```

### API Endpoints

The Control Plane provides REST APIs for management:

- `GET /control-plane/status` - Overall system status
- `GET /control-plane/agents/{name}` - Agent status and constraints
- `POST /control-plane/policies` - Add new policy rules
- `PUT /control-plane/autonomy` - Update agent autonomy level
- `GET /control-plane/treasury/summary` - Budget summary
- `GET /control-plane/treasury/pending` - Pending approvals
- `POST /control-plane/treasury/approve` - Approve/reject transactions
- `GET /control-plane/audit/{pillar}` - Audit log by pillar

#### Blockchain Endpoints

- `GET /control-plane/blockchain/wallets` - Blockchain wallet information
- `GET /control-plane/blockchain/pending-signatures` - Transactions pending signatures
- `POST /control-plane/blockchain/sign` - Sign a blockchain transaction
- `GET /control-plane/blockchain/transaction/{tx_id}` - Transaction status
- `POST /control-plane/blockchain/emergency-pause` - Emergency pause operations

#### Web3Auth Endpoints

- `POST /control-plane/web3auth/authorize-signer` - Start authorization flow
- `POST /control-plane/web3auth/callback` - Handle auth callback
- `GET /control-plane/web3auth/dashboard/{session_id}` - Signer dashboard
- `POST /control-plane/web3auth/sign` - Sign transaction via Web3Auth
- `POST /control-plane/web3auth/logout/{session_id}` - Logout user
- `GET /control-plane/web3auth/status` - Integration status

### Adding Policies

#### Natural Language Rules

```python
from contributing.samples.control_plane import BusinessRule, RuleLanguage

rule = BusinessRule(
    name="marketing_budget",
    description="Marketing daily spending limit",
    rule_text="Daily limit is $1000, require approval above $500",
    language=RuleLanguage.NATURAL,
    pillar="Growth Engine"
)
```

#### YAML Rules

```yaml
type: budget
parameters:
  max_daily_cost: 1000
  require_approval_above: 500
  max_cost_per_action: 100
```

#### Direct Policy Creation

```python
from contributing.samples.control_plane import BudgetPolicyRule, PolicyType

policy = BudgetPolicyRule(
    name="global_limit",
    description="Global transaction limit",
    policy_type=PolicyType.BUDGET,
    max_cost_per_action=1000.0,
    require_approval_above=500.0
)
```

## Example Scenarios

### Scenario 1: Budget-Controlled Marketing Agent

The Growth Engine agent has:
- AML 3 (real-time execution with caps)
- Daily budget of $1000
- Approval required above $500
- Can use analysis and communication tools

### Scenario 2: Compliance-First Governance Agent

The Mission & Governance agent has:
- AML 1 (suggest actions only)
- Strict compliance requirements
- Limited tool access (read-only)
- All actions require approval

### Scenario 3: Autonomous Platform Agent

The Platform & Infrastructure agent has:
- AML 4 (self-correcting execution)
- Database modification capabilities
- Automated maintenance tasks
- Quarterly audit reviews

### Scenario 4: Blockchain Multisig Transaction

High-value transactions requiring blockchain signatures:
- $10,000 marketing campaign requires 2/4 signatures
- Mission & Governance transactions require 3/4 signatures
- Emergency operations require all 4 signatures
- Daily limits enforced on-chain

Example workflow:
1. Agent requests $15,000 transaction
2. Treasury approves, creates blockchain transaction
3. System collects required signatures
4. Transaction executes on blockchain
5. Audit trail recorded on-chain

### Scenario 5: Web3Auth Social Login

Simplified blockchain signing with social authentication:
- CFO signs in with Google account
- No wallet setup or seed phrases needed
- Multi-factor authentication enabled
- One-click transaction approval
- Social recovery options available

Example workflow:
1. New signer authorized via email invite
2. Clicks link and signs in with Google
3. Web3Auth creates non-custodial wallet
4. Views pending transactions in dashboard
5. Approves with single click
6. Private key never leaves device

## Integration with OPA

To use Open Policy Agent:

1. **Start OPA server**:
   ```bash
   opa run --server
   ```

2. **Load policies**:
   ```bash
   opa put /v1/policies/adk policy.rego
   ```

3. **Configure policy engine**:
   ```python
   from contributing.samples.control_plane import OPAPolicyEngine
   
   policy_engine = OPAPolicyEngine(opa_url="http://localhost:8181")
   ```

## Extending the Control Plane

### Custom Policy Types

```python
from contributing.samples.control_plane import PolicyRule, PolicyType

class DataClassificationPolicy(PolicyRule):
    """Custom policy for data classification."""
    classification_required: List[str]
    allowed_classifications: List[str]
    
    def evaluate(self, context):
        # Custom evaluation logic
        pass
```

### Custom Tool Cost Functions

```python
@Tool(
    name="dynamic_cost_tool",
    cost_function=lambda args: args.get("quantity", 1) * 0.05
)
def dynamic_tool(quantity: int):
    return f"Processed {quantity} items"
```

### Autonomy Progression

```python
# Check if agent ready for promotion
if aml_registry.evaluate_promotion(agent_name):
    profile = aml_registry.get_profile(agent_name)
    profile.promote()
```

## Best Practices

1. **Start with Low Autonomy**: Begin agents at AML 1-2 and promote based on performance
2. **Layer Policies**: Use multiple policy types for defense-in-depth
3. **Monitor Drift**: Track policy violations and demote on incidents
4. **Regular Audits**: Review audit logs and adjust policies
5. **Test Policies**: Use the policy compiler to validate business rules

### Blockchain Best Practices

1. **Wallet Security**: Use hardware wallets for production signers
2. **Signature Thresholds**: Set based on risk (higher value = more signatures)
3. **Daily Limits**: Implement per-wallet daily spending caps
4. **Emergency Planning**: Test emergency pause procedures regularly
5. **Gas Management**: Monitor and optimize blockchain transaction costs
6. **Audit Trail**: Maintain on-chain and off-chain audit logs

## Troubleshooting

### Policy Denied Execution

Check:
- Agent's current autonomy level
- Budget availability in treasury
- Required compliance tags
- Tool access permissions

### Transaction Pending Approval

- Check pending approvals: `GET /control-plane/treasury/pending`
- Approve via API or increase autonomy level
- Review approval thresholds in policies

### OPA Connection Failed

- Verify OPA server is running
- Check network connectivity
- Fall back to LocalPolicyEngine if needed

## Related Documentation

- [ADK Agent Documentation](../../README.md)
- [Reference Architecture](../react_supabase/ARCHITECTURE.md)
- [OPA Documentation](https://www.openpolicyagent.org/)
- [Web3Auth Documentation](https://web3auth.io/docs/)
- [Gnosis Safe Documentation](https://docs.safe.global/)

## Security Considerations

1. **Policy Storage**: Store policies securely, version control changes
2. **Approval Authority**: Implement proper authentication for approvers
3. **Audit Retention**: Maintain audit logs for compliance periods
4. **Treasury Keys**: Secure wallet keys for blockchain integration
5. **Network Security**: Use TLS for OPA communication

### Web3Auth Security

1. **Non-Custodial**: Private keys never leave user's device
2. **MFA Support**: Enable multi-factor authentication
3. **Session Security**: Short-lived sessions with refresh
4. **Social Recovery**: Configure trusted guardians
5. **Whitelisted Domains**: Restrict auth redirects
6. **Key Sharding**: Distributed key generation