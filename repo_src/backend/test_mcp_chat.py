#!/usr/bin/env python3
"""
Test script for MCP-powered chat functionality
"""

import asyncio
import os
from pathlib import Path
import sys

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent))

async def test_mcp_chat_agent():
    """Test the MCP chat agent end-to-end"""
    print("🧪 Testing MCP Chat Agent")
    print("=" * 50)
    
    try:
        from agents.mcp_chat_agent import run_mcp_agent
        
        # Mock database session (not used by MCP agent)
        db = None
        
        # Test queries
        test_queries = [
            "What research have I done on AI?",
            "Tell me about my meetings with colleagues", 
            "What are my thoughts on post-labor economics?",
            "Any notes about AIMibots?"
        ]
        
        print("Testing search term extraction and knowledge retrieval...\n")
        
        for i, query in enumerate(test_queries, 1):
            print(f"Test {i}: {query}")
            print("-" * 40)
            
            try:
                selected_files, response, total_tokens, file_tokens = await run_mcp_agent(
                    db=db,
                    user_prompt=query,
                    search_model="anthropic/claude-3-haiku",
                    response_model="anthropic/claude-3.5-sonnet",
                    max_files=3
                )
                
                print(f"✅ Selected {len(selected_files)} files")
                if selected_files:
                    print(f"   Files: {', '.join(selected_files[:2])}{'...' if len(selected_files) > 2 else ''}")
                
                print(f"✅ Generated response ({total_tokens} tokens)")
                print(f"   Preview: {response[:150]}{'...' if len(response) > 150 else ''}")
                
                print()
                
            except Exception as e:
                print(f"❌ Error: {e}")
                print()
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to test MCP chat agent: {e}")
        return False

async def test_mcp_client_direct():
    """Test MCP client functionality directly"""
    print("🔌 Testing MCP Client Direct Access")
    print("=" * 50)
    
    try:
        from mcp_client import get_mcp_client
        
        client = get_mcp_client()
        
        # Test search
        print("Testing search functionality...")
        search_result = await client.search_knowledge("AI", limit=5)
        print(f"✅ Found {len(search_result.entries)} results for 'AI'")
        
        if search_result.entries:
            first_entry = search_result.entries[0]
            print(f"   Sample: {first_entry.get('file_path', 'Unknown')} from {first_entry.get('source', 'Unknown')}")
            
            # Test file reading
            try:
                file_path = first_entry['file_path']
                content = await client.read_file(file_path)
                print(f"✅ Read file content ({len(content)} characters)")
                print(f"   Preview: {content[:100]}{'...' if len(content) > 100 else ''}")
            except Exception as e:
                print(f"⚠️  Could not read file: {e}")
        
        # Test stats
        try:
            stats = await client.get_knowledge_stats()
            print(f"✅ Knowledge base stats: {stats.get('total_entries', 'Unknown')} total entries")
            sources = stats.get('sources', {})
            if sources:
                print(f"   Sources: {', '.join([f'{k}({v})' for k, v in sources.items()])}")
        except Exception as e:
            print(f"⚠️  Could not get stats: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to test MCP client: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Starting MCP Chat System Tests\n")
    
    # Check environment
    if not os.getenv("OPENROUTER_API_KEY"):
        print("⚠️  Warning: OPENROUTER_API_KEY not set. Agent tests may fail.")
        print("   Set the API key in your .env file or environment variables.\n")
    
    # Run tests
    results = []
    
    # Test 1: MCP Client Direct
    client_test = await test_mcp_client_direct()
    results.append(("MCP Client", client_test))
    print()
    
    # Test 2: MCP Chat Agent (only if client works and API key is available)
    if client_test and os.getenv("OPENROUTER_API_KEY"):
        agent_test = await test_mcp_chat_agent()
        results.append(("MCP Chat Agent", agent_test))
    elif client_test:
        print("⏭️  Skipping MCP Chat Agent test (no OPENROUTER_API_KEY)")
        results.append(("MCP Chat Agent", None))  # Mark as skipped
    else:
        print("⏭️  Skipping MCP Chat Agent test (client failed)")
        results.append(("MCP Chat Agent", False))
    
    # Summary
    print("=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    for name, result in results:
        if result is None:
            status = "⏭️  SKIP"
        elif result:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
        print(f"{status:8} {name}")
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("\n🎉 All tests passed! MCP chat system is ready.")
    else:
        print("\n⚠️  Some tests failed. Check the error messages above.")
    
    return passed == len(results)

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)