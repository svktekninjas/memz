#!/usr/bin/env python3
"""
Mem0 Backend API with Session Cache and TruLens Evaluation
Handles user queries with memory context and session history
"""

import os
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, session
from flask_cors import CORS, cross_origin
from mem0 import Memory
from openai import OpenAI
from dotenv import load_dotenv

# Import TruLens evaluation
try:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from evaluation.trulens_eval import MemzEvaluator, MemzRAGTriad
    TRULENS_ENABLED = True
except ImportError:
    print("TruLens not available - running without evaluation")
    TRULENS_ENABLED = False

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Fixed key for session management
app.config['CORS_HEADERS'] = 'Content-Type'

# Configure CORS properly
CORS(app, resources={r"/api/*": {"origins": "*"}}, 
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "OPTIONS"])

# Global cache for session history (in production, use Redis or similar)
session_cache = {}

class Mem0Backend:
    def __init__(self):
        """Initialize Mem0 and OpenAI clients"""
        
        # Check for API key
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found in environment")
        
        # Configure Mem0
        config = {
            "llm": {
                "provider": "openai",
                "config": {
                    "model": "gpt-3.5-turbo",  # This model supports JSON mode required by mem0
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
                    "path": "/Users/swaroop/MEMZ/memQuadrents/qdrant_storage"  # Use absolute path
                }
            }
        }
        
        # Initialize Mem0 and OpenAI
        self.memory = Memory.from_config(config)
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.user_id = "web_user"  # Default user
    
    def process_query(self, query, session_id):
        """
        Process user query with memory context
        Steps:
        1. Intercept user question
        2. Search memories
        3. Add memories to prompt
        4. Call LLM with enhanced prompt
        """
        
        # Step 1: Intercept user question (already done via API)
        print(f"Processing query: {query[:100]}...")
        
        # Step 2: Search memories and knowledge base
        memories = []
        knowledge = []
        
        try:
            # Search user memories
            memory_results = self.memory.search(query, user_id=self.user_id)
            if memory_results:
                memories = [m.get('memory', '') for m in memory_results if 'memory' in m]
                print(f"Found {len(memories)} relevant memories")
        except Exception as e:
            print(f"Memory search error: {e}")
        
        try:
            # Search knowledge base (if KB service is running)
            import requests
            kb_response = requests.post(
                'http://localhost:5002/api/kb/search',
                json={'query': query, 'limit': 3},
                timeout=2
            )
            if kb_response.status_code == 200:
                kb_data = kb_response.json()
                print(f"KB API response structure: {list(kb_data.keys())}")
                if 'results' in kb_data:
                    # Handle nested results structure
                    results = kb_data['results']
                    print(f"Results type: {type(results)}")
                    if isinstance(results, dict) and 'results' in results:
                        results = results['results']
                        print(f"Extracted nested results, count: {len(results)}")
                    if isinstance(results, list):
                        knowledge = [r.get('memory', '') for r in results if isinstance(r, dict) and 'memory' in r]
                        print(f"Found {len(knowledge)} knowledge base entries")
                    else:
                        print(f"Results not a list, type: {type(results)}")
        except Exception as e:
            # KB service might not be running, continue without it
            print(f"KB search error: {e}")
            pass
        
        # Step 3: Add memories and knowledge to prompt
        context = ""
        
        if knowledge:
            context += "Relevant information from knowledge base:\n"
            for kb in knowledge[:3]:  # Limit to 3 most relevant
                context += f"- {kb}\n"
            context += "\n"
        
        if memories:
            context += "Relevant context from previous interactions:\n"
            for mem in memories[:3]:  # Limit to 3 most relevant
                context += f"- {mem}\n"
            context += "\n"
        
        if not memories and not knowledge:
            # No context found - that's okay, start fresh
            context = "No previous context available. Starting fresh.\n\n"
        
        # Step 4: Call LLM with enhanced prompt
        system_prompt = """You are a helpful AI assistant with access to conversation memory.
Use the provided context to give more personalized and relevant responses.
If no context is available, respond normally."""
        
        enhanced_prompt = f"{context}User Query: {query}"
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": enhanced_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            ai_response = response.choices[0].message.content
            
            # Store the interaction in memory for future context
            try:
                self.memory.add(
                    [{"role": "user", "content": query},
                     {"role": "assistant", "content": ai_response}],
                    user_id=self.user_id
                )
                print("Interaction saved to memory")
            except Exception as e:
                print(f"Failed to save memory: {e}")
            
            return {
                "response": ai_response,
                "memories_used": len(memories),
                "knowledge_used": len(knowledge),
                "context": memories[:3] if memories else [],
                "knowledge_context": knowledge[:3] if knowledge else []
            }
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return {
                "response": f"Error processing query: {str(e)}",
                "memories_used": 0,
                "context": []
            }

# Initialize backend
backend = Mem0Backend()

# Initialize TruLens evaluator if available
if TRULENS_ENABLED:
    evaluator = MemzEvaluator()
    rag_evaluator = MemzRAGTriad(evaluator)

@app.route('/api/query', methods=['POST', 'OPTIONS'])
@cross_origin(supports_credentials=True)
def handle_query():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    """Handle user query API endpoint"""
    
    data = request.json
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    # Get or create session ID
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    session_id = session['session_id']
    
    # Initialize session cache if needed
    if session_id not in session_cache:
        session_cache[session_id] = []
    
    # Process the query
    result = backend.process_query(query, session_id)
    
    # Perform TruLens evaluation if enabled
    if TRULENS_ENABLED:
        try:
            # Basic evaluations
            evaluations = evaluator.evaluate_query(query, result)
            
            # RAG Triad evaluation
            rag_scores = rag_evaluator.evaluate_rag_triad(query, result)
            evaluations.update(rag_scores)
            
            # Log results
            evaluator.log_evaluation(query, result, evaluations)
            
            # Add evaluation scores to result
            result['evaluation_scores'] = evaluations
            
        except Exception as e:
            print(f"TruLens evaluation error: {e}")
            result['evaluation_scores'] = {}
    
    # Add to session cache
    cache_entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "response": result['response'],
        "memories_used": result['memories_used'],
        "knowledge_used": result.get('knowledge_used', 0),
        "evaluation_scores": result.get('evaluation_scores', {})
    }
    session_cache[session_id].append(cache_entry)
    
    # Keep only last 50 entries per session
    if len(session_cache[session_id]) > 50:
        session_cache[session_id] = session_cache[session_id][-50:]
    
    return jsonify({
        "success": True,
        "query": query,
        "response": result['response'],
        "memories_used": result['memories_used'],
        "knowledge_used": result.get('knowledge_used', 0),
        "context": result['context'],
        "knowledge_context": result.get('knowledge_context', []),
        "cache_id": cache_entry['id']
    })

@app.route('/api/cache', methods=['GET', 'OPTIONS'])
@cross_origin(supports_credentials=True)
def get_cache():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    """Get session cache history"""
    
    if 'session_id' not in session:
        return jsonify({"cache": []})
    
    session_id = session['session_id']
    cache = session_cache.get(session_id, [])
    
    # Return cache in reverse order (newest first)
    return jsonify({"cache": list(reversed(cache))})

@app.route('/api/clear_cache', methods=['POST', 'OPTIONS'])
@cross_origin(supports_credentials=True)
def clear_cache():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    """Clear session cache"""
    
    if 'session_id' in session:
        session_id = session['session_id']
        if session_id in session_cache:
            del session_cache[session_id]
    
    return jsonify({"success": True, "message": "Cache cleared"})

@app.route('/api/health', methods=['GET', 'OPTIONS'])
@cross_origin(supports_credentials=True)
def health_check():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "has_openai_key": bool(os.getenv("OPENAI_API_KEY")),
        "session_active": 'session_id' in session,
        "trulens_enabled": TRULENS_ENABLED
    })

@app.route('/api/evaluation/dashboard', methods=['GET', 'OPTIONS'])
@cross_origin(supports_credentials=True)
def launch_evaluation_dashboard():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    """Launch TruLens evaluation dashboard"""
    
    if not TRULENS_ENABLED:
        return jsonify({"error": "TruLens not enabled"}), 400
    
    try:
        # Launch dashboard in background
        import threading
        def run_dashboard():
            evaluator.launch_dashboard()
        
        thread = threading.Thread(target=run_dashboard, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "message": "TruLens dashboard launching",
            "url": "http://localhost:8501"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/evaluation/metrics', methods=['GET', 'OPTIONS'])
@cross_origin(supports_credentials=True)
def get_evaluation_metrics():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    """Get recent evaluation metrics"""
    
    if not TRULENS_ENABLED:
        return jsonify({"error": "TruLens not enabled"}), 400
    
    try:
        # Read recent evaluation logs
        import os
        if os.path.exists("evaluation_logs.jsonl"):
            logs = []
            with open("evaluation_logs.jsonl", 'r') as f:
                for line in f:
                    logs.append(json.loads(line))
            
            # Get last 10 evaluations
            recent_logs = logs[-10:] if len(logs) > 10 else logs
            
            # Calculate averages
            if recent_logs:
                avg_scores = {}
                score_counts = {}
                
                for log in recent_logs:
                    for metric, score in log.get('evaluations', {}).items():
                        if metric not in avg_scores:
                            avg_scores[metric] = 0
                            score_counts[metric] = 0
                        avg_scores[metric] += score
                        score_counts[metric] += 1
                
                for metric in avg_scores:
                    avg_scores[metric] = avg_scores[metric] / score_counts[metric]
                
                return jsonify({
                    "recent_evaluations": recent_logs,
                    "average_scores": avg_scores,
                    "total_evaluations": len(logs)
                })
        
        return jsonify({
            "recent_evaluations": [],
            "average_scores": {},
            "total_evaluations": 0
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Starting Mem0 Backend API...")
    print("API will be available at: http://localhost:5001")
    print("Make sure OPENAI_API_KEY is set in .env file")
    app.run(debug=True, port=5001)