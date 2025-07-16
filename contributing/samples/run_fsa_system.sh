#!/bin/bash
# Script to run the complete FSA State Memory System

echo "🚀 Starting FSA State Memory System Demo"
echo "========================================"

# Check if Redis is running
echo "Checking Redis..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis is not running. Please start Redis first:"
    echo "   docker run -p 6379:6379 redis:latest"
    exit 1
fi
echo "✅ Redis is running"

# Start State Memory Service in background
echo ""
echo "Starting State Memory Service..."
python -m uvicorn state_memory_service.service:app --host 0.0.0.0 --port 8000 &
SMS_PID=$!

# Wait for SMS to start
sleep 3

# Check if SMS is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ State Memory Service failed to start"
    kill $SMS_PID 2>/dev/null
    exit 1
fi
echo "✅ State Memory Service is running"

# Menu
echo ""
echo "What would you like to run?"
echo "1. Integration Tests"
echo "2. Demo Scenario"
echo "3. Both"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "Running integration tests..."
        python test_fsa_integration.py
        ;;
    2)
        echo ""
        echo "Running demo scenario..."
        python fsa_demo_scenario.py
        ;;
    3)
        echo ""
        echo "Running integration tests..."
        python test_fsa_integration.py
        echo ""
        echo "Running demo scenario..."
        python fsa_demo_scenario.py
        ;;
    *)
        echo "Invalid choice"
        ;;
esac

# Cleanup
echo ""
echo "Shutting down State Memory Service..."
kill $SMS_PID 2>/dev/null

echo "✅ Done!"