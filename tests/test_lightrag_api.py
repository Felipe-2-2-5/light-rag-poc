#!/usr/bin/env python3
"""
Test script for LightRAG API Server
"""

import requests
import json
import sys

API_BASE_URL = "http://localhost:8001"

def test_health():
    """Test health endpoint"""
    print("=" * 80)
    print("Testing Health Endpoint")
    print("=" * 80)
    
    response = requests.get(f"{API_BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.status_code == 200


def test_retrieve(query, mode="hybrid"):
    """Test main retrieve endpoint"""
    print("\n" + "=" * 80)
    print(f"Testing Retrieve Endpoint: {query}")
    print("=" * 80)
    
    payload = {
        "query": query,
        "mode": mode
    }
    
    response = requests.post(
        f"{API_BASE_URL}/retrieve",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nQuery: {data['query']}")
        print(f"Mode: {data['mode']}")
        print(f"Confidence: {data['confidence']}")
        print(f"\nAnswer:\n{data['answer']}")
        print(f"\nEvidence: {data['evidence_used']}")
    else:
        print(f"Error: {response.text}")
    
    return response.status_code == 200


def test_simple(query, mode="hybrid"):
    """Test simple GET endpoint"""
    print("\n" + "=" * 80)
    print(f"Testing Simple Endpoint: {query}")
    print("=" * 80)
    
    response = requests.get(
        f"{API_BASE_URL}/retrieve/simple",
        params={"query": query, "mode": mode}
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nQuery: {data['query']}")
        print(f"Confidence: {data['confidence']}")
        print(f"\nAnswer:\n{data['answer']}")
    else:
        print(f"Error: {response.text}")
    
    return response.status_code == 200


def main():
    """Run all tests"""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║   LightRAG API Server Test Suite                        ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Test 1: Health check
    try:
        if not test_health():
            print("\n❌ Health check failed!")
            print("\nMake sure the server is running:")
            print("  python3 lightrag_api_server.py")
            return 1
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Cannot connect to API server at {API_BASE_URL}")
        print("\nMake sure the server is running:")
        print("  python3 lightrag_api_server.py")
        return 1
    
    # Test 2: Main retrieve endpoint
    success = test_retrieve(
        "Internal Knowledge Navigator platform purpose and rules",
        mode="hybrid"
    )
    
    if not success:
        print("\n❌ Retrieve endpoint failed!")
        return 1
    
    # Test 3: Simple endpoint
    success = test_simple(
        "What is LightRAG?",
        mode="hybrid"
    )
    
    if not success:
        print("\n❌ Simple endpoint failed!")
        return 1
    
    # Test 4: Try different modes
    print("\n" + "=" * 80)
    print("Testing Different Search Modes")
    print("=" * 80)
    
    for mode in ["naive", "local", "global", "hybrid"]:
        print(f"\n--- Mode: {mode} ---")
        test_simple("What are the main features of the system?", mode=mode)
    
    print("\n" + "=" * 80)
    print("✅ All tests passed!")
    print("=" * 80)
    print("\nYour LightRAG API is ready for Custom GPT integration!")
    print("\nNext steps:")
    print("1. Expose via ngrok: ngrok http 8001")
    print("2. Update custom-gpt/openapi-schema.yaml with ngrok URL")
    print("3. Import schema to Custom GPT Actions")
    print("4. Test in Custom GPT chat interface")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
