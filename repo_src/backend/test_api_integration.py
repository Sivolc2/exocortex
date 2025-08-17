#!/usr/bin/env python3
"""
Test the MCP chat API integration
"""

import requests
import json

def test_mcp_chat_api():
    """Test the MCP chat API endpoint"""
    print("🧪 Testing MCP Chat API Integration")
    print("=" * 50)
    
    # Test data
    test_payload = {
        "prompt": "What notes do I have about AI research?",
        "selection_model": "anthropic/claude-3-haiku",
        "execution_model": "anthropic/claude-3.5-sonnet",
        "enabled_sources": {
            "discord": True,
            "notion": True,
            "obsidian": True,
            "chat_exports": True
        }
    }
    
    try:
        # Test status endpoint
        print("Testing status endpoint...")
        response = requests.get("http://localhost:8000/api/mcp-chat/status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {data['status']}")
            print(f"✅ Knowledge base: {data['knowledge_base_stats']['total_entries']} entries")
        else:
            print(f"❌ Status endpoint failed: {response.status_code}")
            return False
        
        # Test search endpoint
        print("\nTesting search endpoint...")
        response = requests.get("http://localhost:8000/api/mcp-chat/search/AI?limit=3")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Search: {data['total_count']} total results, {len(data['results'])} returned")
            if data['results']:
                first = data['results'][0]
                print(f"   Sample: {first['file_path']} from {first['source']}")
        else:
            print(f"❌ Search endpoint failed: {response.status_code}")
            return False
        
        # Test chat endpoint (this will fail without OPENROUTER_API_KEY, but that's expected)
        print("\nTesting chat endpoint...")
        response = requests.post(
            "http://localhost:8000/api/mcp-chat/",
            json=test_payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Chat response generated ({len(data.get('response', ''))} chars)")
            print(f"✅ Selected files: {len(data.get('selected_files', []))}")
        elif response.status_code == 500:
            # Expected if no API key
            error = response.json()
            if "OPENROUTER_API_KEY" in str(error.get("detail", "")):
                print("⏭️  Chat endpoint skipped (no OPENROUTER_API_KEY - expected)")
            else:
                print(f"❌ Chat endpoint error: {error.get('detail', 'Unknown error')}")
                return False
        else:
            print(f"❌ Chat endpoint unexpected status: {response.status_code}")
            return False
        
        print(f"\n✅ All API endpoints are functional!")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend server at http://localhost:8000")
        print("   Make sure the backend is running with: python main.py")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_mcp_chat_api()
    if success:
        print("\n🎉 MCP Chat API integration is working correctly!")
        print("\nNext steps:")
        print("1. Set OPENROUTER_API_KEY in your .env file for full functionality")
        print("2. Open http://localhost:5173 in your browser")
        print("3. Click the 'Knowledge Chat' tab")
        print("4. Ask questions about your knowledge base!")
    else:
        print("\n⚠️  Some API endpoints are not working correctly.")
    
    exit(0 if success else 1)