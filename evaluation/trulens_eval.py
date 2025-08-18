#!/usr/bin/env python3
"""
TruLens Evaluation Module for MEMZ
Tracks and evaluates the quality of memory retrieval and responses
"""

import os
from typing import Dict, Any, List
from datetime import datetime
import json

from trulens_eval import Feedback, Tru, Select
from trulens_eval import TruCustomApp
from trulens_eval import OpenAI as TruOpenAI
from dotenv import load_dotenv

load_dotenv()

class MemzEvaluator:
    """TruLens evaluator for MEMZ memory system"""
    
    def __init__(self):
        """Initialize TruLens session and feedback providers"""
        # Initialize TruLens session with local database
        self.session = Tru(
            database_url="sqlite:///memz_trulens.db"
        )
        
        # Initialize OpenAI provider for feedback functions
        self.provider = TruOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Define feedback functions
        self.setup_feedback_functions()
        
    def setup_feedback_functions(self):
        """Setup feedback functions for evaluation"""
        
        # Context Relevance - Are the retrieved memories/KB chunks relevant?
        self.f_context_relevance = Feedback(
            self.provider.context_relevance,
            name="Context Relevance"
        ).on_input().on(Select.Record.app.memories).aggregate(lambda x: sum(x) / len(x) if x else 0)
        
        # Answer Relevance - Is the response relevant to the query?
        self.f_answer_relevance = Feedback(
            self.provider.relevance,
            name="Answer Relevance"
        ).on_input().on_output()
        
        # Groundedness - Is the response grounded in the retrieved context?
        self.f_groundedness = Feedback(
            self.provider.groundedness_measure_with_cot_reasons,
            name="Groundedness"
        ).on(Select.Record.app.memories).on_output().aggregate(lambda x: sum(x) / len(x) if x else 0)
        
        # Memory Quality - How good are the memories being stored?
        self.f_memory_quality = Feedback(
            self.provider.comprehensiveness_with_cot_reasons,
            name="Memory Quality"
        ).on_input().on(Select.Record.app.memories).aggregate(lambda x: sum(x) / len(x) if x else 0)
        
        # KB Chunk Effectiveness - Are KB chunks helping answer questions?
        self.f_kb_effectiveness = Feedback(
            self.provider.relevance,
            name="KB Effectiveness"
        ).on_input().on(Select.Record.app.knowledge).aggregate(lambda x: sum(x) / len(x) if x else 0)
    
    def create_app_wrapper(self, app_function):
        """Create a TruLens wrapper for the MEMZ app"""
        
        class MemzApp:
            def __init__(self):
                self.memories = []
                self.knowledge = []
                
            def process_query(self, query: str, session_id: str = None):
                """Process query with instrumentation"""
                result = app_function(query, session_id)
                
                # Store retrieved context for evaluation
                self.memories = result.get('context', [])
                self.knowledge = result.get('knowledge_context', [])
                
                return result
        
        # Create TruCustomApp instance
        memz_app = MemzApp()
        
        tru_app = TruCustomApp(
            memz_app,
            app_name="MEMZ Memory System",
            app_version="1.0",
            feedbacks=[
                self.f_context_relevance,
                self.f_answer_relevance,
                self.f_groundedness,
                self.f_memory_quality,
                self.f_kb_effectiveness
            ]
        )
        
        return tru_app, memz_app
    
    def evaluate_query(self, query: str, result: Dict[str, Any]) -> Dict[str, float]:
        """Evaluate a single query result"""
        
        evaluations = {}
        
        try:
            # Evaluate context relevance if memories were used
            if result.get('memories_used', 0) > 0:
                context = result.get('context', [])
                if context:
                    relevance_scores = [
                        self.provider.context_relevance(query, ctx) 
                        for ctx in context[:3]  # Evaluate top 3
                    ]
                    evaluations['context_relevance'] = sum(relevance_scores) / len(relevance_scores)
            
            # Evaluate KB effectiveness if KB chunks were used
            if result.get('knowledge_used', 0) > 0:
                kb_context = result.get('knowledge_context', [])
                if kb_context:
                    kb_scores = [
                        self.provider.relevance(query, kb) 
                        for kb in kb_context[:3]  # Evaluate top 3
                    ]
                    evaluations['kb_effectiveness'] = sum(kb_scores) / len(kb_scores)
            
            # Evaluate answer relevance
            response = result.get('response', '')
            if response:
                evaluations['answer_relevance'] = self.provider.relevance(query, response)
                
                # Evaluate groundedness if context exists
                all_context = result.get('context', []) + result.get('knowledge_context', [])
                if all_context:
                    groundedness = self.provider.groundedness_measure_with_cot_reasons(
                        ' '.join(all_context[:5]),  # Use top 5 context items
                        response
                    )
                    evaluations['groundedness'] = groundedness[0] if isinstance(groundedness, tuple) else groundedness
            
        except Exception as e:
            print(f"Evaluation error: {e}")
        
        return evaluations
    
    def log_evaluation(self, query: str, result: Dict[str, Any], evaluations: Dict[str, float]):
        """Log evaluation results"""
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "memories_used": result.get('memories_used', 0),
            "knowledge_used": result.get('knowledge_used', 0),
            "evaluations": evaluations,
            "response_length": len(result.get('response', ''))
        }
        
        # Append to evaluation log file
        log_file = "evaluation_logs.jsonl"
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        # Also print summary
        print(f"\n📊 Evaluation Results for query: '{query[:50]}...'")
        print(f"  Memories used: {result.get('memories_used', 0)}")
        print(f"  KB chunks used: {result.get('knowledge_used', 0)}")
        for metric, score in evaluations.items():
            print(f"  {metric}: {score:.2f}")
    
    def get_dashboard_url(self):
        """Get the TruLens dashboard URL"""
        return "http://localhost:8501"
    
    def launch_dashboard(self):
        """Launch the TruLens dashboard"""
        print("🚀 Launching TruLens Dashboard...")
        print(f"📊 Dashboard available at: {self.get_dashboard_url()}")
        from trulens_eval import run_dashboard
        run_dashboard(self.session)


class MemzRAGTriad:
    """Specialized RAG Triad evaluation for MEMZ"""
    
    def __init__(self, evaluator: MemzEvaluator):
        self.evaluator = evaluator
        self.provider = evaluator.provider
    
    def evaluate_rag_triad(self, query: str, result: Dict[str, Any]) -> Dict[str, float]:
        """
        Evaluate the RAG Triad:
        1. Context Relevance - Are retrieved items relevant?
        2. Groundedness - Is response based on retrieved context?
        3. Answer Relevance - Does response answer the question?
        """
        
        triad_scores = {}
        
        # 1. Context Relevance
        all_context = result.get('context', []) + result.get('knowledge_context', [])
        if all_context:
            relevance_scores = []
            for ctx in all_context[:5]:  # Top 5 context items
                try:
                    score = self.provider.context_relevance(query, ctx)
                    relevance_scores.append(score)
                except:
                    pass
            
            if relevance_scores:
                triad_scores['context_relevance'] = sum(relevance_scores) / len(relevance_scores)
        
        # 2. Groundedness
        response = result.get('response', '')
        if response and all_context:
            try:
                groundedness = self.provider.groundedness_measure_with_cot_reasons(
                    ' '.join(all_context[:5]),
                    response
                )
                triad_scores['groundedness'] = groundedness[0] if isinstance(groundedness, tuple) else groundedness
            except:
                pass
        
        # 3. Answer Relevance
        if response:
            try:
                triad_scores['answer_relevance'] = self.provider.relevance(query, response)
            except:
                pass
        
        # Calculate overall RAG score
        if triad_scores:
            triad_scores['rag_triad_score'] = sum(triad_scores.values()) / len(triad_scores)
        
        return triad_scores


def integrate_trulens(backend_process_query):
    """
    Integrate TruLens with the MEMZ backend
    
    Args:
        backend_process_query: The original process_query function from backend
    
    Returns:
        Wrapped function with evaluation
    """
    evaluator = MemzEvaluator()
    rag_evaluator = MemzRAGTriad(evaluator)
    
    def evaluated_process_query(query: str, session_id: str = None):
        """Process query with TruLens evaluation"""
        
        # Call original function
        result = backend_process_query(query, session_id)
        
        # Perform evaluations
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
        
        return result
    
    return evaluated_process_query


if __name__ == "__main__":
    # Test the evaluator
    evaluator = MemzEvaluator()
    
    # Sample result for testing
    test_result = {
        "response": "Terraform is an Infrastructure as Code tool by HashiCorp.",
        "memories_used": 2,
        "knowledge_used": 3,
        "context": ["Previous discussion about Terraform", "User asked about IaC tools"],
        "knowledge_context": ["Terraform is an IaC tool", "HashiCorp created Terraform", "Used for infrastructure"]
    }
    
    # Evaluate
    scores = evaluator.evaluate_query("What is Terraform?", test_result)
    print("Evaluation scores:", scores)
    
    # Launch dashboard
    evaluator.launch_dashboard()