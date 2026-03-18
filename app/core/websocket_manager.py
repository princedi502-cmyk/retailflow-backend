"""
WebSocket manager for real-time updates
"""

from typing import List, Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
import json
import asyncio
from datetime import datetime

class WebSocketManager:
    def __init__(self):
        # Store active connections by user_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Store connection metadata
        self.connection_metadata: Dict[WebSocket, Dict] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Store WebSocket connection (already accepted in router)"""
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "connected_at": datetime.now()
        }
        
        print(f"WebSocket connected for user {user_id}. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.connection_metadata:
            user_id = self.connection_metadata[websocket]["user_id"]
            
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            del self.connection_metadata[websocket]
            print(f"WebSocket disconnected for user {user_id}. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, user_id: str):
        """Send message to specific user's connections"""
        if user_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[user_id].copy():
                try:
                    await connection.send_text(message)
                except:
                    disconnected.append(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                self.disconnect(conn)

    async def broadcast_to_all(self, message: str):
        """Broadcast message to all connected users"""
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, user_id)

    async def send_sales_update(self, user_id: str, sales_data: dict):
        """Send sales metrics update to specific user"""
        message = {
            "type": "sales_update",
            "data": sales_data,
            "timestamp": datetime.now().isoformat()
        }
        await self.send_personal_message(json.dumps(message), user_id)

    async def broadcast_sales_update(self, sales_data: dict):
        """Broadcast sales metrics update to all users"""
        message = {
            "type": "sales_update",
            "data": sales_data,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast_to_all(json.dumps(message))

    async def send_order_notification(self, user_id: str, order_data: dict):
        """Send order creation notification"""
        message = {
            "type": "order_created",
            "data": order_data,
            "timestamp": datetime.now().isoformat()
        }
        await self.send_personal_message(json.dumps(message), user_id)

    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return sum(len(connections) for connections in self.active_connections.values())

    def get_user_connections(self, user_id: str) -> int:
        """Get number of connections for specific user"""
        return len(self.active_connections.get(user_id, set()))

# Global WebSocket manager instance
websocket_manager = WebSocketManager()
