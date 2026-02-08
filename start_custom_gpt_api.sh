#!/bin/bash
# Quick start script for Custom GPT Integration
# This script helps start all necessary services for testing

set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║   Custom GPT Integration - Quick Start                  ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check if running in correct directory
if [ ! -f "api_server.py" ]; then
    echo "❌ Error: api_server.py not found. Please run from project root."
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if port is in use
port_in_use() {
    lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1
}

echo "🔍 Checking prerequisites..."

# Check Python
if ! command_exists python3; then
    echo "❌ Python 3 not found. Please install Python 3.8+"
    exit 1
fi
echo "✅ Python 3 found"

# Check pip packages
echo "📦 Checking Python packages..."
python3 -c "import fastapi, uvicorn, neo4j, sentence_transformers" 2>/dev/null || {
    echo "⚠️  Some packages missing. Installing..."
    pip install -r requirements.txt
}
echo "✅ Python packages installed"

# Check Docker
if ! command_exists docker; then
    echo "⚠️  Docker not found. Install from: https://docs.docker.com/get-docker/"
    echo "   You can still run the API if Neo4j is running elsewhere."
fi

# Check if Neo4j is running
echo ""
echo "🔍 Checking Neo4j..."
if port_in_use 7687; then
    echo "✅ Neo4j appears to be running on port 7687"
else
    echo "⚠️  Neo4j doesn't appear to be running"
    if command_exists docker; then
        echo "   Starting Neo4j with docker-compose..."
        docker-compose up -d
        echo "   Waiting for Neo4j to start..."
        sleep 5
    else
        echo "   Please start Neo4j manually"
        exit 1
    fi
fi

# Check if FAISS index exists
echo ""
echo "🔍 Checking FAISS index..."
if [ -f "outputs/faiss.index" ] && [ -f "outputs/meta.json" ]; then
    echo "✅ FAISS index found"
else
    echo "⚠️  FAISS index not found"
    echo "   Running ingestion on sample data..."
    if [ -f "data/vn_law_sample.txt" ]; then
        python3 src/ingest.py data/vn_law_sample.txt
    else
        echo "   ❌ No sample data found. Please run ingestion manually:"
        echo "      python src/ingest.py your_document.txt"
        exit 1
    fi
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   Starting Services                                      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check if API server is already running
if port_in_use 8000; then
    echo "⚠️  Port 8000 is already in use. Please stop the existing server first."
    echo "   To find the process: lsof -ti:8000"
    echo "   To kill it: kill -9 \$(lsof -ti:8000)"
    exit 1
fi

# Start API server
echo "🚀 Starting API server..."
echo "   (Press Ctrl+C to stop all services)"
echo ""

# Trap to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null || true
    fi
    if [ ! -z "$NGROK_PID" ]; then
        kill $NGROK_PID 2>/dev/null || true
    fi
    exit 0
}
trap cleanup SIGINT SIGTERM


# Start API server in background
source ~/.lightRAG_env/bin/activate && python api_server.py > api_server.log 2>&1 &
API_PID=$!

# Wait for API to start
echo "⏳ Waiting for API server to initialize..."
sleep 5

# Check if API is responding
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API server is running at http://localhost:8000"
else
    echo "❌ API server failed to start. Check api_server.log for errors."
    tail -20 api_server.log
    exit 1
fi

# Test API
echo ""
echo "🧪 Running API tests..."
source ~/.lightRAG_env/bin/activate && python test_custom_gpt_api.py --url http://localhost:8000

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   Services Running                                       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "✅ API Server: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo "🔍 Health Check: http://localhost:8000/health"
echo "📊 Logs: tail -f api_server.log"
echo ""

# Check if ngrok is available
if command_exists ngrok; then
    echo "🌐 ngrok is available. Starting tunnel..."
    echo ""
    ngrok http 8000 > /dev/null 2>&1 &
    NGROK_PID=$!
    
    sleep 3
    
    # Get ngrok URL
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o 'https://[^"]*\.ngrok[^"]*' | head -1)
    
    if [ ! -z "$NGROK_URL" ]; then
        echo "✅ ngrok tunnel active!"
        echo "   Public URL: $NGROK_URL"
        echo "   Dashboard: http://localhost:4040"
        echo ""
        echo "📋 Next steps:"
        echo "   1. Copy the ngrok URL above"
        echo "   2. Update custom-gpt/openapi-schema.yaml with this URL"
        echo "   3. Import schema to Custom GPT Actions"
        echo "   4. Test: curl $NGROK_URL/health"
    else
        echo "⚠️  ngrok started but couldn't get URL"
        echo "   Check: http://localhost:4040"
        kill $NGROK_PID 2>/dev/null || true
        NGROK_PID=""
    fi
else
    echo "📦 ngrok not installed. To expose API publicly:"
    echo "   1. Install: brew install ngrok (Mac) or download from ngrok.com"
    echo "   2. Run: ngrok http 8000"
    echo ""
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   Ready for Custom GPT Integration                      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "See CUSTOM_GPT_INTEGRATION.md for detailed setup instructions."
echo ""
echo "Press Ctrl+C to stop all services..."

# Keep script running
wait
