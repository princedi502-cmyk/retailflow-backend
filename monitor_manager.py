#!/usr/bin/env python3
"""
Database Monitoring Manager CLI
Utility for managing database monitoring from command line
"""

import asyncio
import sys
import os
import argparse
from pathlib import Path
import json
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.core.db_monitor import get_database_monitor, AlertLevel
from app.core.query_optimizer import get_query_optimizer
from app.db.mongodb import db_manager

class MonitorManager:
    """Command-line interface for database monitoring management"""
    
    def __init__(self):
        self.monitor = get_database_monitor(db_manager.client)
        self.optimizer = get_query_optimizer(db_manager.client)
    
    async def start_monitoring(self, interval=60):
        """Start continuous monitoring"""
        print(f"🚀 Starting database monitoring with {interval}s interval...")
        try:
            await self.monitor.start_continuous_monitoring(interval)
            print("✅ Monitoring started successfully")
            print("Press Ctrl+C to stop monitoring")
            
            # Keep running until interrupted
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Stopping monitoring...")
                await self.monitor.stop_continuous_monitoring()
                print("✅ Monitoring stopped")
                
        except Exception as e:
            print(f"❌ Failed to start monitoring: {str(e)}")
    
    async def stop_monitoring(self):
        """Stop continuous monitoring"""
        print("🛑 Stopping database monitoring...")
        try:
            await self.monitor.stop_continuous_monitoring()
            print("✅ Monitoring stopped successfully")
        except Exception as e:
            print(f"❌ Failed to stop monitoring: {str(e)}")
    
    async def show_status(self):
        """Show current monitoring status"""
        print("📊 Database Monitoring Status")
        print("=" * 40)
        
        # Monitoring status
        print(f"Monitoring Active: {'✅ Yes' if self.monitor.is_monitoring else '❌ No'}")
        
        # Database health
        health = self.monitor.check_connection_health()
        print(f"Database Health: {health['status']}")
        if 'response_time_ms' in health:
            print(f"Response Time: {health['response_time_ms']:.2f}ms")
        
        # Pool stats
        pool_stats = self.monitor.get_pool_stats()
        if 'error' not in pool_stats:
            print(f"Pool Connections: {pool_stats.get('total_connections', 0)}/{pool_stats.get('max_pool_size', 0)}")
        
        # Active alerts
        alerts = self.monitor.get_active_alerts()
        print(f"Active Alerts: {len(alerts)}")
        
        if alerts:
            print("\n🚨 Active Alerts:")
            for alert in alerts[-5:]:  # Show last 5 alerts
                print(f"   [{alert.level.value.upper()}] {alert.message}")
        
        # Query stats
        query_stats = self.optimizer.get_performance_stats()
        if query_stats:
            print(f"\n⚡ Query Statistics:")
            print(f"   Total Queries: {query_stats.get('total_queries', 0)}")
            print(f"   Slow Queries: {query_stats.get('slow_queries', 0)}")
            print(f"   Avg Execution Time: {query_stats.get('avg_execution_time', 0):.2f}ms")
            print(f"   Cache Size: {query_stats.get('cache_size', 0)}")
    
    async def show_alerts(self, level=None):
        """Show active alerts"""
        alerts = self.monitor.get_active_alerts(level)
        
        if not alerts:
            print("✅ No active alerts")
            return
        
        print(f"🚨 Active Alerts ({len(alerts)}):")
        print("=" * 50)
        
        for alert in alerts:
            print(f"\n[{alert.level.value.upper()}] {alert.metric_name}")
            print(f"Message: {alert.message}")
            print(f"Current: {alert.current_value:.2f} | Threshold: {alert.threshold:.2f}")
            print(f"Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    
    async def resolve_alerts(self, metric_name):
        """Resolve alerts for a specific metric"""
        success = self.monitor.resolve_alert(metric_name)
        if success:
            print(f"✅ Resolved alerts for metric: {metric_name}")
        else:
            print(f"❌ No active alerts found for metric: {metric_name}")
    
    async def show_performance_report(self):
        """Show comprehensive performance report"""
        print("📈 Performance Report")
        print("=" * 40)
        
        report = await self.monitor.get_performance_report()
        
        if 'error' in report:
            print(f"❌ Error generating report: {report['error']}")
            return
        
        # Database stats
        if 'database_stats' in report:
            db_stats = report['database_stats']
            print(f"\n🗄️  Database Statistics:")
            if 'database' in db_stats:
                db_info = db_stats['database']
                print(f"   Collections: {db_info.get('collections', 0)}")
                print(f"   Data Size: {db_info.get('dataSize', 0) / 1024 / 1024:.2f} MB")
                print(f"   Storage Size: {db_info.get('storageSize', 0) / 1024 / 1024:.2f} MB")
                print(f"   Indexes: {db_info.get('indexes', 0)}")
        
        # Query stats
        if 'query_stats' in report:
            query_stats = report['query_stats']
            print(f"\n⚡ Query Performance:")
            print(f"   Total Queries: {query_stats.get('total_queries', 0)}")
            print(f"   Slow Query %: {query_stats.get('slow_query_percentage', 0):.2f}%")
            print(f"   Avg Execution Time: {query_stats.get('avg_execution_time', 0):.2f}ms")
        
        # Alerts summary
        alerts_summary = report.get('alerts_summary', {})
        if any(alerts_summary.values()):
            print(f"\n🚨 Alerts Summary:")
            print(f"   Critical: {alerts_summary.get('critical', 0)}")
            print(f"   Warning: {alerts_summary.get('warning', 0)}")
            print(f"   Info: {alerts_summary.get('info', 0)}")
    
    async def clear_cache(self, pattern=None):
        """Clear query cache"""
        print(f"🗑️  Clearing query cache{' for pattern: ' + pattern if pattern else ''}...")
        self.optimizer.clear_cache(pattern)
        print("✅ Cache cleared successfully")
    
    async def show_recommendations(self):
        """Show performance recommendations"""
        print("💡 Performance Recommendations")
        print("=" * 40)
        
        recommendations = self.optimizer.suggest_query_improvements()
        
        if not recommendations:
            print("✅ No recommendations - performance looks good!")
            return
        
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
    
    async def update_threshold(self, metric_name, threshold):
        """Update performance threshold"""
        try:
            threshold = float(threshold)
            self.monitor.update_threshold(metric_name, threshold)
            print(f"✅ Updated {metric_name} threshold to {threshold}")
        except ValueError:
            print(f"❌ Invalid threshold value: {threshold}")
        except Exception as e:
            print(f"❌ Failed to update threshold: {str(e)}")
    
    def show_thresholds(self):
        """Show current performance thresholds"""
        print("🎯 Performance Thresholds")
        print("=" * 40)
        
        for metric, threshold in self.monitor.thresholds.items():
            print(f"{metric:<25}: {threshold:.2f}")

async def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Database Monitoring Manager")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Start monitoring
    start_parser = subparsers.add_parser('start', help='Start continuous monitoring')
    start_parser.add_argument('--interval', type=int, default=60, help='Monitoring interval in seconds')
    
    # Stop monitoring
    subparsers.add_parser('stop', help='Stop continuous monitoring')
    
    # Status
    subparsers.add_parser('status', help='Show monitoring status')
    
    # Alerts
    alerts_parser = subparsers.add_parser('alerts', help='Show active alerts')
    alerts_parser.add_argument('--level', choices=['info', 'warning', 'critical'], help='Filter by alert level')
    
    # Resolve alerts
    resolve_parser = subparsers.add_parser('resolve', help='Resolve alerts for a metric')
    resolve_parser.add_argument('metric', help='Metric name to resolve alerts for')
    
    # Performance report
    subparsers.add_parser('report', help='Show performance report')
    
    # Cache operations
    cache_parser = subparsers.add_parser('cache', help='Cache operations')
    cache_parser.add_argument('--clear', action='store_true', help='Clear cache')
    cache_parser.add_argument('--pattern', help='Pattern for selective clearing')
    
    # Recommendations
    subparsers.add_parser('recommendations', help='Show performance recommendations')
    
    # Thresholds
    subparsers.add_parser('thresholds', help='Show performance thresholds')
    
    # Update threshold
    update_parser = subparsers.add_parser('update-threshold', help='Update performance threshold')
    update_parser.add_argument('metric', help='Metric name')
    update_parser.add_argument('value', help='New threshold value')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = MonitorManager()
    
    try:
        if args.command == 'start':
            await manager.start_monitoring(args.interval)
        elif args.command == 'stop':
            await manager.stop_monitoring()
        elif args.command == 'status':
            await manager.show_status()
        elif args.command == 'alerts':
            await manager.show_alerts(args.level)
        elif args.command == 'resolve':
            await manager.resolve_alerts(args.metric)
        elif args.command == 'report':
            await manager.show_performance_report()
        elif args.command == 'cache':
            if args.clear:
                await manager.clear_cache(args.pattern)
            else:
                print("Use --clear to clear cache")
        elif args.command == 'recommendations':
            await manager.show_recommendations()
        elif args.command == 'thresholds':
            manager.show_thresholds()
        elif args.command == 'update-threshold':
            await manager.update_threshold(args.metric, args.value)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
