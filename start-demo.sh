#!/bin/bash

echo "Starting Memory Agent Demo..."

# Start the API server in the background
echo "Starting API server on port 8000..."
.venv/bin/memory-agent start --port 8000 &
API_PID=$!

# Wait for API to start
sleep 3

# Start the Terminal UI in a new terminal (if available)
if command -v osascript &> /dev/null; then
    # macOS
    osascript -e 'tell app "Terminal" to do script "cd '$(pwd)' && .venv/bin/memory-agent monitor"'
elif command -v gnome-terminal &> /dev/null; then
    # Linux with GNOME
    gnome-terminal -- bash -c "cd $(pwd) && .venv/bin/memory-agent monitor; exec bash"
else
    echo "Please run '.venv/bin/memory-agent monitor' in a new terminal"
fi

# Start the dashboard
echo "Starting React dashboard..."
cd dashboard/dashboard
npm run dev &
DASHBOARD_PID=$!

cd ../..

echo ""
echo "Memory Agent is running!"
echo "- API Server: http://localhost:8000"
echo "- API Docs: http://localhost:8000/docs"
echo "- Dashboard: http://localhost:5173"
echo "- Terminal UI: Run '.venv/bin/memory-agent monitor' in a new terminal"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for Ctrl+C
trap "echo 'Stopping services...'; kill $API_PID $DASHBOARD_PID 2>/dev/null; exit" INT
wait