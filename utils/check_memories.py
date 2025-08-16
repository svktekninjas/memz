#!/usr/bin/env python3
"""
Check what memories are stored in the Qdrant vector database
"""

import os
import sys
sys.path.append('..')

from dotenv import load_dotenv
from mem0 import Memory
from datetime import datetime

# Load environment variables
load_dotenv()

def check_memories():
    """Check all memories in the vector database"""
    
    print("=" * 60)
    print("MEMORY SYSTEM STATUS CHECK")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Base configuration
    base_config = {
        "llm": {
            "provider": "openai",
            "config": {
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 2000,
                "api_key": os.getenv("OPENAI_API_KEY")
            }
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": "text-embedding-3-small",
                "api_key": os.getenv("OPENAI_API_KEY")
            }
        },
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "web_memories",
                "embedding_model_dims": 1536,
                "path": "qdrant_storage"
            }
        }
    }
    
    # Check Web Memories
    print("1. WEB USER MEMORIES (web_memories collection)")
    print("-" * 50)
    try:
        memory = Memory.from_config(base_config)
        web_memories = memory.get_all(user_id="web_user")
        
        if hasattr(web_memories, '__len__'):
            count = len(web_memories)
            print(f"   Total memories: {count}")
            if count > 0 and isinstance(web_memories, list):
                print("\n   Recent memories:")
                for i, mem in enumerate(web_memories[:3], 1):
                    if isinstance(mem, dict) and 'memory' in mem:
                        content = mem['memory']
                        print(f"   {i}. {content[:100]}..." if len(content) > 100 else f"   {i}. {content}")
        else:
            print(f"   Memories type: {type(web_memories)}")
            print(f"   Content: {web_memories}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print()
    
    # Check Knowledge Base Memories
    print("2. KNOWLEDGE BASE MEMORIES (kb_memories collection)")
    print("-" * 50)
    try:
        kb_config = base_config.copy()
        kb_config['vector_store']['config']['collection_name'] = 'kb_memories'
        
        kb_memory = Memory.from_config(kb_config)
        kb_memories = kb_memory.get_all(user_id="knowledge_base")
        
        if hasattr(kb_memories, '__len__'):
            count = len(kb_memories)
            print(f"   Total memories: {count}")
            if count > 0 and isinstance(kb_memories, list):
                print("\n   Recent entries:")
                for i, mem in enumerate(kb_memories[:3], 1):
                    if isinstance(mem, dict) and 'memory' in mem:
                        content = mem['memory']
                        print(f"   {i}. {content[:100]}..." if len(content) > 100 else f"   {i}. {content}")
        else:
            print(f"   Memories type: {type(kb_memories)}")
            print(f"   Content: {kb_memories}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print()
    
    # Check for any other users in web_memories
    print("3. OTHER USERS IN SYSTEM")
    print("-" * 50)
    try:
        users_to_check = ["demo_user", "default", "swaroop", "assistant"]
        found_any = False
        
        for user in users_to_check:
            user_memories = memory.get_all(user_id=user)
            if hasattr(user_memories, '__len__') and len(user_memories) > 0:
                print(f"   User '{user}': {len(user_memories)} memories")
                found_any = True
        
        if not found_any:
            print("   No memories found for other users")
    except Exception as e:
        print(f"   Error checking other users: {e}")
    
    print()
    
    # Search test
    print("4. SEARCH TEST")
    print("-" * 50)
    try:
        test_query = "test"
        print(f"   Searching for: '{test_query}'")
        
        search_results = memory.search(test_query, user_id="web_user", limit=3)
        if search_results:
            print(f"   Found {len(search_results)} results")
            for i, result in enumerate(search_results[:2], 1):
                if 'memory' in result:
                    print(f"   {i}. {result['memory'][:80]}...")
        else:
            print("   No search results found")
    except Exception as e:
        print(f"   Search error: {e}")
    
    print()
    print("=" * 60)
    print("Memory check complete!")
    print()

if __name__ == "__main__":
    check_memories()