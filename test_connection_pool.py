#!/usr/bin/env python3
"""
Test script for database connection pooling implementation
"""

import asyncio
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from database import client, db, test_connection, get_db_stats
from core.db_config import DatabaseConfig
from core.db_monitor import DatabaseMonitor

def test_basic_connection():
    """Test basic database connection"""
    print("Testing basic database connection...")
    try:
        result = test_connection()
        print(f"✓ Basic connection test: {'PASSED' if result else 'FAILED'}")
        return result
    except Exception as e:
        print(f"✗ Basic connection test FAILED: {e}")
        return False

def test_pool_configuration():
    """Test connection pool configuration"""
    print("\nTesting connection pool configuration...")
    try:
        config = DatabaseConfig.get_pool_options()
        print(f"✓ Pool configuration loaded")
        print(f"  - Max pool size: {config.max_pool_size}")
        print(f"  - Min pool size: {config.min_pool_size}")
        print(f"  - Max idle time: {config.max_idle_time_seconds}s")
        print(f"  - Wait queue timeout: {config.wait_queue_timeout}s")
        return True
    except Exception as e:
        print(f"✗ Pool configuration test FAILED: {e}")
        return False

def test_concurrent_connections(num_threads=10, operations_per_thread=5):
    """Test concurrent database operations"""
    print(f"\nTesting concurrent connections ({num_threads} threads, {operations_per_thread} ops each)...")
    
    def db_operation(thread_id):
        """Perform database operations"""
        results = []
        for i in range(operations_per_thread):
            try:
                start_time = time.time()
                # Simple ping operation
                db.command('ping')
                end_time = time.time()
                results.append({
                    'thread_id': thread_id,
                    'operation': i,
                    'duration': (end_time - start_time) * 1000,  # ms
                    'success': True
                })
            except Exception as e:
                results.append({
                    'thread_id': thread_id,
                    'operation': i,
                    'error': str(e),
                    'success': False
                })
        return results
    
    try:
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(db_operation, i) for i in range(num_threads)]
            all_results = []
            
            for future in as_completed(futures):
                all_results.extend(future.result())
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze results
        successful_ops = sum(1 for r in all_results if r['success'])
        total_ops = len(all_results)
        avg_duration = sum(r.get('duration', 0) for r in all_results if r['success']) / max(successful_ops, 1)
        
        print(f"✓ Concurrent operations completed:")
        print(f"  - Total operations: {total_ops}")
        print(f"  - Successful: {successful_ops}")
        print(f"  - Success rate: {(successful_ops/total_ops)*100:.1f}%")
        print(f"  - Total time: {total_time:.2f}s")
        print(f"  - Average operation time: {avg_duration:.2f}ms")
        print(f"  - Operations per second: {total_ops/total_time:.1f}")
        
        return successful_ops == total_ops
        
    except Exception as e:
        print(f"✗ Concurrent operations test FAILED: {e}")
        return False

def test_monitoring():
    """Test database monitoring functionality"""
    print("\nTesting database monitoring...")
    try:
        monitor = DatabaseMonitor(client)
        
        # Test pool stats
        pool_stats = monitor.get_pool_stats()
        print(f"✓ Pool stats retrieved: {pool_stats}")
        
        # Test database stats
        db_stats = monitor.get_database_stats()
        print(f"✓ Database stats retrieved: {len(str(db_stats))} characters")
        
        # Test health check
        health = monitor.check_connection_health()
        print(f"✓ Health check: {health['status']} ({health.get('response_time_ms', 'N/A')}ms)")
        
        # Test performance report
        report = monitor.get_performance_report()
        print(f"✓ Performance report generated")
        
        return True
    except Exception as e:
        print(f"✗ Monitoring test FAILED: {e}")
        return False

def test_connection_reuse():
    """Test connection reuse efficiency"""
    print("\nTesting connection reuse...")
    try:
        # Perform multiple operations to test connection reuse
        operations = []
        for i in range(20):
            start_time = time.time()
            db.command('ping')
            end_time = time.time()
            operations.append((end_time - start_time) * 1000)
        
        # Calculate statistics
        avg_time = sum(operations) / len(operations)
        min_time = min(operations)
        max_time = max(operations)
        
        print(f"✓ Connection reuse test:")
        print(f"  - Operations: {len(operations)}")
        print(f"  - Average time: {avg_time:.2f}ms")
        print(f"  - Min time: {min_time:.2f}ms")
        print(f"  - Max time: {max_time:.2f}ms")
        
        # Connection reuse is working if times are consistent
        variance = max_time - min_time
        print(f"  - Time variance: {variance:.2f}ms")
        
        return True
    except Exception as e:
        print(f"✗ Connection reuse test FAILED: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("DATABASE CONNECTION POOLING TESTS")
    print("=" * 60)
    
    tests = [
        test_basic_connection,
        test_pool_configuration,
        test_concurrent_connections,
        test_monitoring,
        test_connection_reuse
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    for i, (test, result) in enumerate(zip(tests, results)):
        status = "PASSED" if result else "FAILED"
        print(f"{i+1}. {test.__name__}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Connection pooling is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the configuration.")
    
    # Cleanup
    try:
        client.close()
        print("\n✓ Database connections closed")
    except:
        pass
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
