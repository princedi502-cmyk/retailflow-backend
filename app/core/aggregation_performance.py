"""
Performance monitoring and testing for MongoDB aggregations
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pymongo import MongoClient
from app.db.mongodb import db_manager
from app.core.optimized_aggregations import OptimizedPipelines, aggregation_optimizer

logger = logging.getLogger(__name__)

class AggregationPerformanceMonitor:
    """Monitor and test aggregation query performance"""
    
    def __init__(self):
        self.test_results = []
        
    async def run_performance_test(
        self, 
        collection_name: str, 
        pipeline: List[Dict],
        test_name: str,
        iterations: int = 5
    ) -> Dict[str, Any]:
        """Run performance test for aggregation pipeline"""
        
        times = []
        results_count = 0
        
        for i in range(iterations):
            start_time = time.time()
            
            try:
                collection = db_manager.db[collection_name]
                result = await collection.aggregate(pipeline).to_list(length=1000)
                
                execution_time = (time.time() - start_time) * 1000
                times.append(execution_time)
                results_count = len(result)
                
                logger.info(f"Test {i+1}/{iterations}: {execution_time:.2f}ms")
                
            except Exception as e:
                logger.error(f"Test {i+1} failed: {str(e)}")
                times.append(float('inf'))
        
        # Calculate statistics
        valid_times = [t for t in times if t != float('inf')]
        
        if not valid_times:
            return {
                "test_name": test_name,
                "status": "failed",
                "error": "All iterations failed",
                "iterations": iterations
            }
        
        avg_time = sum(valid_times) / len(valid_times)
        min_time = min(valid_times)
        max_time = max(valid_times)
        
        test_result = {
            "test_name": test_name,
            "collection": collection_name,
            "status": "success",
            "iterations": iterations,
            "successful_iterations": len(valid_times),
            "avg_time_ms": round(avg_time, 2),
            "min_time_ms": round(min_time, 2),
            "max_time_ms": round(max_time, 2),
            "results_count": results_count,
            "pipeline_stages": len(pipeline),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        self.test_results.append(test_result)
        return test_result
    
    async def compare_pipelines(
        self,
        collection_name: str,
        original_pipeline: List[Dict],
        optimized_pipeline: List[Dict],
        test_name: str
    ) -> Dict[str, Any]:
        """Compare performance between original and optimized pipelines"""
        
        logger.info(f"Running comparison test: {test_name}")
        
        # Test original pipeline
        original_result = await self.run_performance_test(
            collection_name, original_pipeline, f"{test_name}_original", iterations=3
        )
        
        # Test optimized pipeline
        optimized_result = await self.run_performance_test(
            collection_name, optimized_pipeline, f"{test_name}_optimized", iterations=3
        )
        
        # Calculate improvement
        if (original_result["status"] == "success" and 
            optimized_result["status"] == "success"):
            
            improvement_percent = (
                (original_result["avg_time_ms"] - optimized_result["avg_time_ms"]) 
                / original_result["avg_time_ms"] * 100
            )
            
            speedup_factor = original_result["avg_time_ms"] / optimized_result["avg_time_ms"]
        else:
            improvement_percent = 0
            speedup_factor = 1
        
        comparison_result = {
            "test_name": test_name,
            "collection": collection_name,
            "original": original_result,
            "optimized": optimized_result,
            "improvement_percent": round(improvement_percent, 2),
            "speedup_factor": round(speedup_factor, 2),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Comparison completed: {improvement_percent:.2f}% improvement")
        return comparison_result
    
    def generate_performance_report(self) -> str:
        """Generate performance report from test results"""
        
        if not self.test_results:
            return "No test results available"
        
        report = ["# MongoDB Aggregation Performance Report\n"]
        report.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
        report.append(f"Total tests: {len(self.test_results)}\n")
        
        # Summary statistics
        successful_tests = [r for r in self.test_results if r["status"] == "success"]
        if successful_tests:
            avg_time = sum(r["avg_time_ms"] for r in successful_tests) / len(successful_tests)
            report.append(f"## Summary")
            report.append(f"- Successful tests: {len(successful_tests)}/{len(self.test_results)}")
            report.append(f"- Average execution time: {avg_time:.2f}ms")
            report.append(f"- Fastest query: {min(r['avg_time_ms'] for r in successful_tests):.2f}ms")
            report.append(f"- Slowest query: {max(r['avg_time_ms'] for r in successful_tests):.2f}ms\n")
        
        # Detailed results
        report.append("## Detailed Results\n")
        
        for result in self.test_results:
            report.append(f"### {result['test_name']}")
            report.append(f"- **Status**: {result['status']}")
            report.append(f"- **Collection**: {result['collection']}")
            
            if result["status"] == "success":
                report.append(f"- **Avg Time**: {result['avg_time_ms']}ms")
                report.append(f"- **Min Time**: {result['min_time_ms']}ms")
                report.append(f"- **Max Time**: {result['max_time_ms']}ms")
                report.append(f"- **Results**: {result['results_count']} documents")
                report.append(f"- **Pipeline Stages**: {result['pipeline_stages']}")
            else:
                report.append(f"- **Error**: {result.get('error', 'Unknown error')}")
            
            report.append("")
        
        return "\n".join(report)

# Global performance monitor
performance_monitor = AggregationPerformanceMonitor()

async def run_optimization_tests():
    """Run comprehensive optimization tests"""
    
    logger.info("Starting aggregation optimization tests...")
    
    # Test top products pipeline
    await performance_monitor.run_performance_test(
        "orders",
        OptimizedPipelines.top_products_pipeline(limit=10),
        "top_products_optimized"
    )
    
    # Test category sales pipeline
    await performance_monitor.run_performance_test(
        "orders",
        OptimizedPipelines.category_sales_pipeline(limit=20),
        "category_sales_optimized"
    )
    
    # Test sales trend pipeline
    await performance_monitor.run_performance_test(
        "orders",
        OptimizedPipelines.sales_trend_pipeline(days_back=30),
        "sales_trend_optimized"
    )
    
    # Test employee performance pipeline
    await performance_monitor.run_performance_test(
        "orders",
        OptimizedPipelines.employee_performance_pipeline(limit=50),
        "employee_performance_optimized"
    )
    
    # Generate report
    report = performance_monitor.generate_performance_report()
    
    # Save report to file
    with open("/home/di-01/Desktop/prince/basics/Retail-flow/aggregation_performance_report.md", "w") as f:
        f.write(report)
    
    logger.info("Optimization tests completed. Report saved to aggregation_performance_report.md")
    return report

if __name__ == "__main__":
    asyncio.run(run_optimization_tests())
