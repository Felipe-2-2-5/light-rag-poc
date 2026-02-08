#!/bin/bash
#
# Start LightRAG API Server for Custom GPT Integration
#

echo "Starting LightRAG API Server..."
echo ""

# Set default port if not specified
export API_PORT="${API_PORT:-8001}"

# Make sure we're using the right storage directory
export LIGHTRAG_WORKING_DIR="${LIGHTRAG_WORKING_DIR:-./lightrag_storage}"

# Check if storage exists
if [ ! -d "$LIGHTRAG_WORKING_DIR" ]; then
    echo "❌ Error: LightRAG storage not found at $LIGHTRAG_WORKING_DIR"
    echo ""
    echo "Please run ingestion first:"
    echo "  python lightrag/lightrag_ingest.py --input <your-document>"
    exit 1
fi

# Start the server
python lightrag_api_server.py
