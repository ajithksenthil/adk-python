#!/bin/bash
# Run the enhanced FSA State Memory System demo

echo "🚀 Enhanced FSA State Memory System Demo"
echo "========================================"
echo ""
echo "This demo shows:"
echo "- Comprehensive project state (tasks, resources, metrics)"
echo "- Human-agent discussion threads"
echo "- Multi-agent coordination"
echo "- Policy enforcement with AML levels"
echo "- Real-time state updates"
echo ""

# Check Redis
echo "Checking prerequisites..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis is not running. Starting Redis..."
    docker run -d -p 6379:6379 --name redis-fsa redis:latest
    sleep 2
fi
echo "✅ Redis is running"

# Function to cleanup
cleanup() {
    echo ""
    echo "Cleaning up..."
    if [ ! -z "$SMS_PID" ]; then
        kill $SMS_PID 2>/dev/null
    fi
}

# Set trap for cleanup
trap cleanup EXIT

# Start Enhanced SMS
echo ""
echo "Starting Enhanced State Memory Service..."
python -m uvicorn state_memory_service.service_v2:app --host 0.0.0.0 --port 8000 > sms.log 2>&1 &
SMS_PID=$!

# Wait for startup
echo "Waiting for service to start..."
for i in {1..10}; do
    if curl -s http://localhost:8000/health > /dev/null; then
        echo "✅ Enhanced SMS is running"
        break
    fi
    sleep 1
done

# Run the enhanced test
echo ""
echo "Running enhanced FSA demonstration..."
echo "===================================="
python test_enhanced_fsa.py

echo ""
echo "Demo completed! Key features demonstrated:"
echo ""
echo "📋 Comprehensive State:"
echo "   - Task management with dependencies"
echo "   - Resource tracking (budget, inventory)"
echo "   - Real-time metrics and KPIs"
echo "   - Policy caps and AML levels"
echo ""
echo "💬 Discussion Threads:"
echo "   - Human comments on tasks"
echo "   - Agent responses and analysis"
echo "   - Voting workflows with comments"
echo ""
echo "🤖 Agent Coordination:"
echo "   - Multiple agents sharing state"
echo "   - Policy enforcement preventing errors"
echo "   - Heartbeat monitoring for availability"
echo ""
echo "📊 To explore the API:"
echo "   - State: curl http://localhost:8000/state/acme-corp/project-alpha-2024"
echo "   - Summary: curl 'http://localhost:8000/state/acme-corp/project-alpha-2024?summary=true'"
echo "   - Docs: http://localhost:8000/docs"
echo ""

# Keep running for exploration
echo "Service is still running. Press Ctrl+C to stop."
wait $SMS_PID