#!/usr/bin/env python3
"""
Knowledge Base Service for Mem0
Handles ingestion of various data sources into vector store
"""

import os
import json
import hashlib
import requests
import subprocess
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from urllib.parse import urlparse

# Document processing libraries
import PyPDF2
from docx import Document
from bs4 import BeautifulSoup
import markdown

# Mem0 and AI libraries
from mem0 import Memory
from openai import OpenAI
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

load_dotenv()

class KnowledgeBaseService:
    def __init__(self):
        """Initialize Knowledge Base with Mem0 configuration"""
        
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Configure Mem0 for knowledge base
        self.config = {
            "llm": {
                "provider": "openai",
                "config": {
                    "model": "gpt-3.5-turbo",  # This model supports JSON mode
                    "temperature": 0.3,  # Lower temperature for factual content
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
                    "collection_name": "kb_memories",
                    "embedding_model_dims": 1536,
                    "path": "/Users/swaroop/MEMZ/memQuadrents/qdrant_storage"
                }
            }
        }
        
        self.memory = Memory.from_config(self.config)
        self.processed_hashes = set()  # Track processed content to avoid duplicates
        self.stats_cache = {
            "total_chunks": 0,
            "sources": {},
            "unique_sources": 0,
            "total_memories": 0
        }  # Cache stats since mem0 get_all has issues
    
    def process_local_file(self, file_path: str) -> Dict[str, Any]:
        """Process a single local file"""
        
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}
        
        file_type = path.suffix.lower()
        content = ""
        metadata = {
            "source": str(path),
            "type": "file",
            "file_type": file_type,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            if file_type in ['.txt', '.md', '.json', '.py', '.js', '.html', '.css', '.yml', '.yaml', '.tf', '.tfvars']:
                # Text files (including Terraform files)
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
            elif file_type == '.pdf':
                # PDF files
                content = self._extract_pdf_content(path)
                
            elif file_type in ['.docx', '.doc']:
                # Word documents
                content = self._extract_word_content(path)
                
            else:
                return {"error": f"Unsupported file type: {file_type}"}
            
            # Process content into chunks
            chunks = self._chunk_content(content, chunk_size=1000)
            
            # Store in vector database
            stored_count = 0
            for i, chunk in enumerate(chunks):
                chunk_metadata = {**metadata, "chunk_index": i, "total_chunks": len(chunks)}
                
                # Create a hash to check for duplicates
                content_hash = hashlib.md5(chunk.encode()).hexdigest()
                if content_hash not in self.processed_hashes:
                    # Mem0 expects a simple string, not message format
                    memory_content = f"From {path.name}: {chunk}"
                    result = self.memory.add(
                        memory_content,
                        user_id="knowledge_base",
                        metadata=chunk_metadata
                    )
                    print(f"Memory add result: {result}")  # Debug output
                    self.processed_hashes.add(content_hash)
                    stored_count += 1
                    
                    # Update stats cache
                    self.stats_cache["total_chunks"] += 1
                    self.stats_cache["total_memories"] += 1
                    source_key = str(path)
                    self.stats_cache["sources"][source_key] = self.stats_cache["sources"].get(source_key, 0) + 1
                    self.stats_cache["unique_sources"] = len(self.stats_cache["sources"])
            
            return {
                "success": True,
                "file": str(path),
                "chunks_processed": len(chunks),
                "chunks_stored": stored_count,
                "metadata": metadata
            }
            
        except Exception as e:
            return {"error": f"Failed to process file: {str(e)}"}
    
    def process_folder(self, folder_path: str, extensions: List[str] = None) -> Dict[str, Any]:
        """Process all files in a folder recursively"""
        
        path = Path(folder_path)
        if not path.exists():
            return {"error": f"Folder not found: {folder_path}"}
        
        if extensions is None:
            extensions = ['.txt', '.md', '.pdf', '.docx', '.py', '.js', '.json', '.html', '.css', '.tf', '.tfvars', '.yml', '.yaml']
        
        results = []
        for file_path in path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                # Skip hidden files and common ignore patterns
                if any(part.startswith('.') for part in file_path.parts):
                    continue
                if any(ignore in str(file_path) for ignore in ['node_modules', '__pycache__', 'venv', '.git']):
                    continue
                    
                result = self.process_local_file(str(file_path))
                results.append(result)
        
        return {
            "success": True,
            "folder": str(path),
            "files_processed": len(results),
            "results": results
        }
    
    def process_git_repo(self, repo_url: str, branch: str = "main") -> Dict[str, Any]:
        """Clone and process a git repository"""
        
        # Create temp directory for cloning
        temp_dir = Path("../temp_repos") / hashlib.md5(repo_url.encode()).hexdigest()
        
        try:
            # Clone the repository
            if temp_dir.exists():
                # Pull latest changes if already cloned
                subprocess.run(["git", "pull"], cwd=temp_dir, check=True)
            else:
                temp_dir.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(["git", "clone", "--depth", "1", "--branch", branch, repo_url, str(temp_dir)], check=True)
            
            # Process the cloned repository
            result = self.process_folder(str(temp_dir))
            result["source"] = repo_url
            result["branch"] = branch
            
            return result
            
        except subprocess.CalledProcessError as e:
            return {"error": f"Failed to clone repository: {str(e)}"}
        except Exception as e:
            return {"error": f"Failed to process repository: {str(e)}"}
    
    def process_website(self, url: str, max_depth: int = 2) -> Dict[str, Any]:
        """Scrape and process website content"""
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Extract metadata
            metadata = {
                "source": url,
                "type": "website",
                "title": soup.title.string if soup.title else urlparse(url).netloc,
                "timestamp": datetime.now().isoformat()
            }
            
            # Process content into chunks
            chunks = self._chunk_content(text, chunk_size=800)
            
            # Store in vector database
            stored_count = 0
            for i, chunk in enumerate(chunks):
                chunk_metadata = {**metadata, "chunk_index": i, "total_chunks": len(chunks)}
                
                content_hash = hashlib.md5(chunk.encode()).hexdigest()
                if content_hash not in self.processed_hashes:
                    # Mem0 expects a simple string, not message format
                    memory_content = f"Web content from {metadata['title']}: {chunk}"
                    self.memory.add(
                        memory_content,
                        user_id="knowledge_base",
                        metadata=chunk_metadata
                    )
                    self.processed_hashes.add(content_hash)
                    stored_count += 1
            
            return {
                "success": True,
                "url": url,
                "title": metadata['title'],
                "chunks_processed": len(chunks),
                "chunks_stored": stored_count,
                "metadata": metadata
            }
            
        except requests.RequestException as e:
            return {"error": f"Failed to fetch website: {str(e)}"}
        except Exception as e:
            return {"error": f"Failed to process website: {str(e)}"}
    
    def _extract_pdf_content(self, file_path: Path) -> str:
        """Extract text content from PDF file"""
        
        content = []
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                if text.strip():  # Only add non-empty pages
                    content.append(f"Page {page_num + 1}:\n{text}")
        
        return '\n\n'.join(content)
    
    def _extract_word_content(self, file_path: Path) -> str:
        """Extract text content from Word document"""
        
        doc = Document(file_path)
        content = []
        for paragraph in doc.paragraphs:
            content.append(paragraph.text)
        
        return '\n'.join(content)
    
    def _chunk_content(self, content: str, chunk_size: int = 1000) -> List[str]:
        """Split content into manageable chunks"""
        
        # Split by paragraphs first
        paragraphs = content.split('\n\n')
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # If no paragraphs or content is too large, split by size
        if not chunks:
            chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
        
        return chunks
    
    def search_knowledge(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search the knowledge base for relevant information"""
        
        results = self.memory.search(query, user_id="knowledge_base", limit=limit)
        return results
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base from cache"""
        
        # Get web memories count (conversation memories)
        web_memories_count = 0
        try:
            # Create a separate Memory instance for web_memories collection
            web_config = {
                "llm": self.config["llm"],
                "embedder": self.config["embedder"],
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "collection_name": "web_memories",
                        "embedding_model_dims": 1536,
                        "path": "/Users/swaroop/MEMZ/memQuadrents/qdrant_storage"
                    }
                }
            }
            from mem0 import Memory
            web_memory = Memory.from_config(web_config)
            web_memories = web_memory.get_all(user_id="web_user")
            web_memories_count = len(web_memories) if web_memories else 0
        except Exception as e:
            print(f"Error getting web memories: {e}")
            web_memories_count = 0
        
        # Parse sources to categorize them
        source_types = {
            "files": [],
            "folders": [],
            "repos": [],
            "websites": []
        }
        
        for source in self.stats_cache.get("sources", {}):
            if source.endswith('.pdf') or source.endswith('.txt') or source.endswith('.md'):
                source_types["files"].append(source)
            elif source.startswith('http://') or source.startswith('https://'):
                if 'github.com' in source or 'gitlab.com' in source:
                    source_types["repos"].append(source)
                else:
                    source_types["websites"].append(source)
            elif '/' in source and not source.startswith('/'):
                source_types["repos"].append(source)
            else:
                source_types["folders"].append(source)
        
        return {
            "kb_chunks": self.stats_cache.get("total_chunks", 0),
            "web_memories": web_memories_count,
            "total_memories": self.stats_cache.get("total_memories", 0),
            "unique_sources": self.stats_cache.get("unique_sources", 0),
            "sources": self.stats_cache.get("sources", {}),
            "source_types": source_types
        }
    
    def sync_cache_to_knowledge(self, cache_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Sync selected cache entries to knowledge base"""
        
        synced_count = 0
        
        for entry in cache_entries:
            query = entry.get('query', '')
            response = entry.get('response', '')
            
            if query and response:
                # Create knowledge entry from Q&A pair
                metadata = {
                    "source": "user_cache",
                    "type": "qa_pair",
                    "timestamp": entry.get('timestamp', datetime.now().isoformat()),
                    "session_id": entry.get('session_id', 'unknown')
                }
                
                # Store Q&A as knowledge (Mem0 expects simple string)
                memory_content = f"Q: {query}\nA: {response}"
                self.memory.add(
                    memory_content,
                    user_id="knowledge_base",
                    metadata=metadata
                )
                synced_count += 1
        
        return {
            "success": True,
            "synced_count": synced_count,
            "total_entries": len(cache_entries)
        }