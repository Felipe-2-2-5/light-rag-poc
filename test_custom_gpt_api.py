#!/usr/bin/env python3
"""
Test script for Custom GPT API integration

This script tests the API server endpoints to verify the integration is working correctly.
Run this after starting api_server.py and optionally ngrok.
"""

import requests
import json
import sys
from typing import Optional

def test_health(base_url: str) -> bool:
    """Test health endpoint"""
    print("\n🔍 Testing /health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Status: {data.get('status')}")
        components = data.get('components', {})
        for comp, status in components.items():
            icon = "✅" if status else "❌"
            print(f"   {icon} {comp}: {status}")
        
        return all(components.values())
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def test_retrieve(base_url: str, query: str = "What is Article 15?") -> bool:
    """Test retrieve endpoint"""
    print(f"\n🔍 Testing /retrieve endpoint with query: '{query}'...")
    
    payload = {
        "query": query,
        "max_results": 3,
        "include_graph": True
    }
    
    try:
        response = requests.post(
            f"{base_url}/retrieve",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        # Display results
        print(f"\n📊 Results:")
        print(f"   Intent: {data.get('intent', {}).get('primary')} (confidence: {data.get('intent', {}).get('confidence')})")
        print(f"   Strategy: {data.get('retrieval_strategy')}")
        print(f"   Confidence: {data.get('confidence')} ({data.get('confidence_score')})")
        
        # Vector evidence
        vector_ev = data.get('vector_evidence', [])
        print(f"\n📝 Vector Evidence ({len(vector_ev)} chunks):")
        for i, ve in enumerate(vector_ev[:3], 1):  # Show first 3
            print(f"   {i}. chunk_id: {ve.get('chunk_id')}")
            print(f"      similarity: {ve.get('similarity')}, authority: {ve.get('authority')}")
            print(f"      text: {ve.get('text', '')[:100]}...")
        
        # Graph evidence
        graph_ev = data.get('graph_evidence')
        if graph_ev:
            nodes = graph_ev.get('nodes', [])
            edges = graph_ev.get('edges', [])
            print(f"\n🕸️  Graph Evidence:")
            print(f"   Nodes: {len(nodes)}, Edges: {len(edges)}")
            if graph_ev.get('traversal_path'):
                print(f"   Path: {graph_ev['traversal_path']}")
        
        print(f"\n📌 Summary: {data.get('evidence_summary')}")
        
        # Validate structure
        required_fields = ['query', 'intent', 'vector_evidence', 'confidence', 'retrieval_strategy']
        missing = [f for f in required_fields if f not in data]
        if missing:
            print(f"\n⚠️  Missing fields: {missing}")
            return False
        
        print("\n✅ Retrieve endpoint working correctly!")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Retrieve test failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        return False


def test_simple_retrieve(base_url: str) -> bool:
    """Test simple retrieve endpoint"""
    print("\n🔍 Testing /retrieve/simple endpoint...")
    
    try:
        response = requests.post(
            f"{base_url}/retrieve/simple?query=test&max_results=2",
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        print(f"   Results: {len(data.get('results', []))} chunks")
        print(f"   Confidence: {data.get('confidence')}")
        print("✅ Simple retrieve endpoint working!")
        return True
        
    except Exception as e:
        print(f"❌ Simple retrieve test failed: {e}")
        return False


def test_evidence_contract(base_url: str) -> bool:
    """Test that response matches the evidence contract"""
    print("\n🔍 Testing Evidence Contract Compliance...")
    
    payload = {
        "query": "What are the requirements?",
        "max_results": 5,
        "include_graph": True
    }
    
    try:
        response = requests.post(f"{base_url}/retrieve", json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        checks = {
            "Query field present": "query" in data,
            "Intent classification present": "intent" in data and "primary" in data.get("intent", {}),
            "Vector evidence present": "vector_evidence" in data and len(data.get("vector_evidence", [])) > 0,
            "Confidence level valid": data.get("confidence") in ["HIGH", "MEDIUM", "LOW"],
            "Confidence score in range": 0 <= data.get("confidence_score", -1) <= 1,
            "Retrieval strategy specified": data.get("retrieval_strategy") in ["VECTOR_PRIMARY", "GRAPH_PRIMARY", "HYBRID"],
            "Evidence summary present": "evidence_summary" in data,
        }
        
        # Check vector evidence structure
        if data.get("vector_evidence"):
            ve = data["vector_evidence"][0]
            checks["Vector evidence has chunk_id"] = "chunk_id" in ve
            checks["Vector evidence has text"] = "text" in ve
            checks["Vector evidence has similarity"] = "similarity" in ve
            checks["Vector evidence has authority"] = ve.get("authority") in ["PRIMARY", "SECONDARY", "CONTEXTUAL", "HISTORICAL"]
        
        print("\n📋 Evidence Contract Checks:")
        all_passed = True
        for check, passed in checks.items():
            icon = "✅" if passed else "❌"
            print(f"   {icon} {check}")
            if not passed:
                all_passed = False
        
        if all_passed:
            print("\n✅ Evidence contract fully compliant!")
        else:
            print("\n⚠️  Some contract checks failed")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Contract test failed: {e}")
        return False


def main():
    """Run all tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Custom GPT API Integration")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the API server (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--query",
        default="What is Article 15?",
        help="Test query to use"
    )
    parser.add_argument(
        "--skip-health",
        action="store_true",
        help="Skip health check"
    )
    
    args = parser.parse_args()
    base_url = args.url.rstrip('/')
    
    print("=" * 70)
    print("Custom GPT API Integration Test Suite")
    print("=" * 70)
    print(f"\n🌐 Testing API at: {base_url}")
    
    results = {}
    
    # Health check
    if not args.skip_health:
        results['health'] = test_health(base_url)
        if not results['health']:
            print("\n❌ Health check failed. Make sure:")
            print("   1. API server is running (python api_server.py)")
            print("   2. Neo4j is running (docker-compose up -d)")
            print("   3. FAISS index exists (outputs/faiss.index)")
            sys.exit(1)
    
    # Retrieve tests
    results['retrieve'] = test_retrieve(base_url, args.query)
    results['simple'] = test_simple_retrieve(base_url)
    results['contract'] = test_evidence_contract(base_url)
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    for test_name, passed in results.items():
        icon = "✅" if passed else "❌"
        print(f"{icon} {test_name.capitalize()}: {'PASSED' if passed else 'FAILED'}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All tests passed! Your API is ready for Custom GPT integration.")
        print("\nNext steps:")
        print("1. Start ngrok: ngrok http 8000")
        print("2. Copy ngrok URL (https://xxx.ngrok-free.app)")
        print("3. Update custom-gpt/openapi-schema.yaml with ngrok URL")
        print("4. Import schema to Custom GPT Actions")
        print("5. Test in Custom GPT chat interface")
    else:
        print("\n⚠️  Some tests failed. Review the output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
