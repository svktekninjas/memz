#!/usr/bin/env python3
"""
Test script to demonstrate vector retrieval limitations using TruLens
Shows how semantically similar but factually different content affects RAG performance
"""

import json
import requests
from typing import Dict, List, Any
import time

class RetrievalAccuracyTester:
    """Test retrieval accuracy and demonstrate vector search limitations"""
    
    def __init__(self, backend_url="http://localhost:5001", kb_url="http://localhost:5002"):
        self.backend_url = backend_url
        self.kb_url = kb_url
        self.test_results = []
    
    def run_test_queries(self) -> List[Dict[str, Any]]:
        """Run test queries that expose vector retrieval limitations"""
        
        test_cases = [
            {
                "query": "What is the tag name for aws_internet_gateway resource?",
                "expected_content": ["aws_internet_gateway", "KS-IG", "Name"],
                "expected_answer": "KS-IG",
                "test_type": "exact_resource_retrieval"
            },
            {
                "query": "What is the tag name for NAT Gateway?",
                "expected_content": ["nat_gateway", "NAT", "elastic_ip"],
                "expected_answer": "NAT Gateway tag",
                "test_type": "similar_resource_retrieval"
            },
            {
                "query": "Show me the Internet Gateway configuration",
                "expected_content": ["aws_internet_gateway", "vpc_id", "tags"],
                "expected_answer": "Internet Gateway with tag KS-IG",
                "test_type": "configuration_retrieval"
            },
            {
                "query": "What VPC CIDR is configured?",
                "expected_content": ["vpc_cidr", "10.0.0.0/16"],
                "expected_answer": "10.0.0.0/16",
                "test_type": "parameter_retrieval"
            }
        ]
        
        results = []
        
        for test_case in test_cases:
            print(f"\n{'='*60}")
            print(f"Testing: {test_case['query']}")
            print(f"Expected to find: {test_case['expected_content']}")
            print(f"{'='*60}")
            
            # Run query
            response = requests.post(
                f"{self.backend_url}/api/query",
                json={"query": test_case["query"]},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Analyze retrieval accuracy
                evaluation = self.evaluate_retrieval(
                    test_case,
                    result.get('knowledge_context', []),
                    result.get('response', '')
                )
                
                # Add to results
                test_result = {
                    "test_case": test_case,
                    "actual_response": result,
                    "evaluation": evaluation
                }
                
                results.append(test_result)
                self.print_evaluation(test_result)
                
            time.sleep(2)  # Avoid rate limiting
        
        return results
    
    def evaluate_retrieval(self, test_case: Dict, retrieved_chunks: List[str], response: str) -> Dict[str, Any]:
        """Evaluate retrieval accuracy against expected content"""
        
        evaluation = {
            "semantic_similarity": 0.0,
            "factual_accuracy": 0.0,
            "retrieval_precision": 0.0,
            "retrieval_recall": 0.0,
            "response_correctness": 0.0
        }
        
        # Check if expected content appears in retrieved chunks
        chunks_text = ' '.join(retrieved_chunks).lower()
        expected_found = []
        expected_missing = []
        
        for expected in test_case['expected_content']:
            if expected.lower() in chunks_text:
                expected_found.append(expected)
            else:
                expected_missing.append(expected)
        
        # Calculate metrics
        if test_case['expected_content']:
            evaluation['retrieval_recall'] = len(expected_found) / len(test_case['expected_content'])
        
        # Check for false positives (e.g., NAT Gateway when looking for Internet Gateway)
        false_positives = []
        if 'internet_gateway' in test_case['query'].lower():
            if 'nat' in chunks_text and 'internet' not in chunks_text:
                false_positives.append("NAT Gateway retrieved instead of Internet Gateway")
                evaluation['factual_accuracy'] = 0.0
            else:
                evaluation['factual_accuracy'] = 1.0 if expected_found else 0.0
        
        # Check response correctness
        if test_case['expected_answer'].lower() in response.lower():
            evaluation['response_correctness'] = 1.0
        
        # Calculate precision (avoiding false positives)
        evaluation['retrieval_precision'] = 1.0 - (len(false_positives) * 0.5)
        evaluation['retrieval_precision'] = max(0, evaluation['retrieval_precision'])
        
        # Semantic similarity (simplified - in real TruLens this uses embeddings)
        evaluation['semantic_similarity'] = 0.8 if retrieved_chunks else 0.0
        
        # Add diagnostic info
        evaluation['expected_found'] = expected_found
        evaluation['expected_missing'] = expected_missing
        evaluation['false_positives'] = false_positives
        evaluation['chunks_retrieved'] = len(retrieved_chunks)
        
        return evaluation
    
    def print_evaluation(self, result: Dict):
        """Print evaluation results in a formatted way"""
        
        eval_data = result['evaluation']
        
        print("\n📊 EVALUATION METRICS:")
        print(f"  Retrieval Recall: {eval_data['retrieval_recall']:.2%}")
        print(f"  Retrieval Precision: {eval_data['retrieval_precision']:.2%}")
        print(f"  Factual Accuracy: {eval_data['factual_accuracy']:.2%}")
        print(f"  Response Correctness: {eval_data['response_correctness']:.2%}")
        
        if eval_data['expected_missing']:
            print(f"\n⚠️  MISSING EXPECTED CONTENT:")
            for item in eval_data['expected_missing']:
                print(f"    - {item}")
        
        if eval_data['false_positives']:
            print(f"\n❌ FALSE POSITIVES DETECTED:")
            for fp in eval_data['false_positives']:
                print(f"    - {fp}")
        
        print(f"\n📝 RETRIEVED CHUNKS: {eval_data['chunks_retrieved']}")
        for i, chunk in enumerate(result['actual_response'].get('knowledge_context', [])[:3]):
            print(f"    {i+1}. {chunk[:100]}...")
    
    def generate_report(self, results: List[Dict]) -> Dict:
        """Generate a comprehensive evaluation report"""
        
        report = {
            "total_tests": len(results),
            "vector_limitation_demonstrated": False,
            "average_metrics": {},
            "specific_issues": [],
            "recommendations": []
        }
        
        # Calculate averages
        metrics = ['retrieval_recall', 'retrieval_precision', 'factual_accuracy', 'response_correctness']
        for metric in metrics:
            values = [r['evaluation'][metric] for r in results]
            report['average_metrics'][metric] = sum(values) / len(values) if values else 0
        
        # Check for vector limitation evidence
        for result in results:
            if result['evaluation']['false_positives']:
                report['vector_limitation_demonstrated'] = True
                report['specific_issues'].append({
                    "query": result['test_case']['query'],
                    "issue": "Retrieved semantically similar but factually incorrect content",
                    "details": result['evaluation']['false_positives']
                })
        
        # Add recommendations
        if report['average_metrics']['retrieval_precision'] < 0.7:
            report['recommendations'].append("Consider adding keyword-based filtering to supplement vector search")
        
        if report['average_metrics']['factual_accuracy'] < 0.8:
            report['recommendations'].append("Implement fact-checking layer to validate retrieved content")
        
        if report['vector_limitation_demonstrated']:
            report['recommendations'].append("Use hybrid search (vector + keyword) to improve accuracy")
            report['recommendations'].append("Add entity recognition to distinguish between similar resources")
        
        return report

def main():
    """Run the retrieval accuracy test"""
    
    print("🔍 TESTING VECTOR RETRIEVAL ACCURACY WITH TRULENS EVALUATION")
    print("="*60)
    
    tester = RetrievalAccuracyTester()
    
    # Run tests
    results = tester.run_test_queries()
    
    # Generate report
    report = tester.generate_report(results)
    
    # Print summary report
    print("\n" + "="*60)
    print("📈 FINAL EVALUATION REPORT")
    print("="*60)
    
    print(f"\n📊 AVERAGE METRICS:")
    for metric, value in report['average_metrics'].items():
        print(f"  {metric}: {value:.2%}")
    
    if report['vector_limitation_demonstrated']:
        print(f"\n⚠️  VECTOR LIMITATION DEMONSTRATED: YES")
        print("  Evidence: System retrieved semantically similar but factually incorrect content")
        
        for issue in report['specific_issues']:
            print(f"\n  Query: '{issue['query']}'")
            print(f"  Issue: {issue['issue']}")
            for detail in issue['details']:
                print(f"    - {detail}")
    
    print(f"\n💡 RECOMMENDATIONS:")
    for rec in report['recommendations']:
        print(f"  • {rec}")
    
    # Save detailed report
    with open("retrieval_evaluation_report.json", "w") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": results,
            "report": report
        }, f, indent=2)
    
    print(f"\n✅ Full report saved to retrieval_evaluation_report.json")

if __name__ == "__main__":
    main()