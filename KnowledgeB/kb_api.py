#!/usr/bin/env python3
"""
Knowledge Base API Endpoints
Provides REST API for knowledge base operations
"""

import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append('..')

from knowledge_base import KnowledgeBaseService

load_dotenv()

app = Flask(__name__)
app.secret_key = 'knowledge-base-secret-key'
app.config['CORS_HEADERS'] = 'Content-Type'

# Configure CORS
CORS(app, resources={r"/api/kb/*": {"origins": "*"}}, 
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "OPTIONS"])

# Initialize Knowledge Base Service
kb_service = KnowledgeBaseService()

@app.route('/api/kb/ingest/file', methods=['POST', 'OPTIONS'])
@cross_origin(supports_credentials=True)
def ingest_file():
    """Ingest a single file into knowledge base"""
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    
    data = request.json
    file_path = data.get('file_path')
    
    if not file_path:
        return jsonify({"error": "No file path provided"}), 400
    
    result = kb_service.process_local_file(file_path)
    
    # Standardize response for frontend
    if result.get('success'):
        result['chunks_created'] = result.get('chunks_stored', 0)
    
    return jsonify(result)

@app.route('/api/kb/ingest/folder', methods=['POST', 'OPTIONS'])
@cross_origin(supports_credentials=True)
def ingest_folder():
    """Ingest all files in a folder into knowledge base"""
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    
    data = request.json
    folder_path = data.get('folder_path')
    extensions = data.get('extensions', None)
    
    if not folder_path:
        return jsonify({"error": "No folder path provided"}), 400
    
    result = kb_service.process_folder(folder_path, extensions)
    return jsonify(result)

@app.route('/api/kb/ingest/git', methods=['POST', 'OPTIONS'])
@cross_origin(supports_credentials=True)
def ingest_git_repo():
    """Ingest a git repository into knowledge base"""
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    
    data = request.json
    repo_url = data.get('repo_url')
    branch = data.get('branch', 'main')
    
    if not repo_url:
        return jsonify({"error": "No repository URL provided"}), 400
    
    result = kb_service.process_git_repo(repo_url, branch)
    return jsonify(result)

@app.route('/api/kb/ingest/website', methods=['POST', 'OPTIONS'])
@cross_origin(supports_credentials=True)
def ingest_website():
    """Ingest website content into knowledge base"""
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    
    data = request.json
    url = data.get('url')
    max_depth = data.get('max_depth', 2)
    
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    result = kb_service.process_website(url, max_depth)
    return jsonify(result)

@app.route('/api/kb/search', methods=['POST', 'OPTIONS'])
@cross_origin(supports_credentials=True)
def search_knowledge():
    """Search the knowledge base"""
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    
    data = request.json
    query = data.get('query')
    limit = data.get('limit', 5)
    
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    results = kb_service.search_knowledge(query, limit)
    return jsonify({"results": results})

@app.route('/api/kb/stats', methods=['GET', 'OPTIONS'])
@cross_origin(supports_credentials=True)
def get_stats():
    """Get knowledge base statistics"""
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    
    stats = kb_service.get_knowledge_stats()
    return jsonify(stats)

@app.route('/api/kb/sync-cache', methods=['POST', 'OPTIONS'])
@cross_origin(supports_credentials=True)
def sync_cache():
    """Sync cache entries to knowledge base"""
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    
    data = request.json
    cache_entries = data.get('cache_entries', [])
    
    if not cache_entries:
        return jsonify({"error": "No cache entries provided"}), 400
    
    result = kb_service.sync_cache_to_knowledge(cache_entries)
    return jsonify(result)

@app.route('/api/kb/health', methods=['GET', 'OPTIONS'])
@cross_origin(supports_credentials=True)
def health_check():
    """Health check endpoint"""
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    
    return jsonify({
        "status": "healthy",
        "service": "knowledge_base",
        "has_openai_key": bool(os.getenv("OPENAI_API_KEY"))
    })

if __name__ == '__main__':
    print("Starting Knowledge Base API...")
    print("API will be available at: http://localhost:5002")
    app.run(debug=True, port=5002)