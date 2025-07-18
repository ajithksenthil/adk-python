"""MemCube Memory System for LLM Agents.

A structured, lifecycle-aware memory system that complements FSA state tracking
by storing persistent knowledge, artifacts, and experience across projects.
"""

from .models import InsightCard
from .models import MemCube
from .models import MemCubeHeader
from .models import MemCubePayload
from .models import MemoryChain
from .models import MemoryChainLink
from .models import MemoryGovernance
from .models import MemoryLifecycle
from .models import MemoryPack
from .models import MemoryType
from .storage import MemCubeStorage

try:  # Optional dependency
  from .storage import SupabaseMemCubeStorage
except Exception:  # pragma: no cover - ignore if supabase missing
  SupabaseMemCubeStorage = None

from .marketplace import MarketplaceService
from .marketplace import MemPackImporter
from .marketplace import MemPackPublisher
from .operator import MemoryOperator
from .operator import MemoryScheduler
from .operator import MemorySelector

__all__ = [
    # Models
    "MemoryType",
    "MemCubeHeader",
    "MemCubePayload",
    "MemCube",
    "MemoryPack",
    "MemoryLifecycle",
    "MemoryGovernance",
    "InsightCard",
    "MemoryChain",
    "MemoryChainLink",
    # Storage
    "MemCubeStorage",
    "SupabaseMemCubeStorage",
    # Operator
    "MemoryOperator",
    "MemoryScheduler",
    "MemorySelector",
    # Marketplace
    "MemPackPublisher",
    "MemPackImporter",
    "MarketplaceService",
]
