#!/usr/bin/env python3
"""
Test script for the Exocortex MCP server

This script validates that the MCP server functions correctly without
requiring full MCP protocol interaction.
"""

import sys
from pathlib import Path

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_server_imports():
    """Test that the server imports correctly"""
    try:
        from mcp_server import server, load_knowledge_index, search_knowledge_base, get_file_content
        print("✅ Server imports successfully")
        return True
    except Exception as e:
        print(f"❌ Server import failed: {e}")
        return False

def test_knowledge_index_loading():
    """Test loading the knowledge index"""
    try:
        from mcp_server import load_knowledge_index
        entries = load_knowledge_index()
        if entries:
            print(f"✅ Loaded {len(entries)} knowledge base entries")
            
            # Show a sample entry
            sample = entries[0]
            print(f"   Sample entry: {sample.file_path} from {sample.source}")
            return True
        else:
            print("⚠️  Knowledge index is empty")
            return False
    except Exception as e:
        print(f"❌ Knowledge index loading failed: {e}")
        return False

def test_search_functionality():
    """Test the search functionality"""
    try:
        from mcp_server import search_knowledge_base
        
        # Test a generic search
        results = search_knowledge_base("AI", limit=5)
        print(f"✅ Search for 'AI' returned {len(results['entries'])} results")
        
        if results['entries']:
            print(f"   Sample result: {results['entries'][0]['file_path']}")
        
        # Test source filtering
        results = search_knowledge_base("research", source_filter="obsidian", limit=3)
        print(f"✅ Filtered search returned {len(results['entries'])} obsidian results")
        
        return True
    except Exception as e:
        print(f"❌ Search functionality failed: {e}")
        return False

def test_file_access():
    """Test file content access"""
    try:
        from mcp_server import load_knowledge_index, get_file_content
        
        entries = load_knowledge_index()
        if not entries:
            print("⚠️  No entries to test file access")
            return False
        
        # Try to read the first few files
        for i, entry in enumerate(entries[:3]):
            try:
                content = get_file_content(entry.file_path)
                print(f"✅ Successfully read {entry.file_path} ({len(content)} chars)")
            except Exception as e:
                print(f"⚠️  Could not read {entry.file_path}: {e}")
        
        return True
    except Exception as e:
        print(f"❌ File access test failed: {e}")
        return False

def test_data_structure():
    """Test that data files exist"""
    from mcp_server import DATA_ROOT, KNOWLEDGE_INDEX_JSON, PROCESSED_ROOT
    
    print(f"📂 Data root: {DATA_ROOT}")
    
    if not DATA_ROOT.exists():
        print(f"❌ Data root does not exist: {DATA_ROOT}")
        return False
    
    if not KNOWLEDGE_INDEX_JSON.exists():
        print(f"❌ Knowledge index does not exist: {KNOWLEDGE_INDEX_JSON}")
        return False
    
    if not PROCESSED_ROOT.exists():
        print(f"❌ Processed data root does not exist: {PROCESSED_ROOT}")
        return False
    
    print("✅ All data directories and files exist")
    return True

def run_all_tests():
    """Run all tests"""
    print("🧪 Testing Exocortex MCP Server\n")
    
    tests = [
        ("Data Structure", test_data_structure),
        ("Server Imports", test_server_imports),
        ("Knowledge Index Loading", test_knowledge_index_loading),
        ("Search Functionality", test_search_functionality),
        ("File Access", test_file_access)
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n--- {name} ---")
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} failed with exception: {e}")
            results.append((name, False))
    
    print("\n" + "="*50)
    print("📊 Test Results Summary")
    print("="*50)
    
    passed = 0
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:8} {name}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("\n🎉 All tests passed! Your MCP server is ready to use.")
    else:
        print("\n⚠️  Some tests failed. Please check the error messages above.")
    
    return passed == len(results)

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)