"""
WebSocket router for real-time updates
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from app.api.router.dependency import get_current_user_ws
from app.core.websocket_manager import websocket_manager
import json

router = APIRouter(prefix="/ws", tags=["websocket"])

@router.websocket("/analytics")
async def websocket_analytics_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    """WebSocket endpoint for real-time analytics updates"""
    
    print(f"WebSocket connection attempt - IP: {websocket.client.host if websocket.client else 'unknown'}")
    print(f"Token provided: {token[:20]}..." if token and len(token) > 20 else f"Token: {token}")
    
    # Authenticate user from token BEFORE accepting the connection
    try:
        print("Attempting to authenticate user...")
        user = await get_current_user_ws(token)
        user_id = str(user["_id"])
        user_role = user.get("role", "unknown")
        print(f"WebSocket authenticated successfully - User: {user_id}, Role: {user_role}")
    except Exception as e:
        print(f"WebSocket authentication failed: {e}")
        print(f"Exception type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        # Accept connection first, then close with error
        await websocket.accept()
        await websocket.close(code=4001, reason="Authentication failed")
        return

    # Accept the connection after successful authentication
    try:
        await websocket.accept()
        print("WebSocket connection accepted")
    except Exception as e:
        print(f"Failed to accept WebSocket connection: {e}")
        return

    try:
        await websocket_manager.connect(websocket, user_id)
        print(f"WebSocket connected to manager for user {user_id}")
        
        # Send initial connection confirmation
        welcome_message = {
            "type": "connection_established",
            "message": f"Connected to analytics updates as {user_role}",
            "user_id": user_id,
            "user_role": user_role,
            "timestamp": websocket_manager.connection_metadata[websocket]["connected_at"].isoformat()
        }
        
        await websocket.send_text(json.dumps(welcome_message))
        print(f"Sent welcome message to user {user_id}")
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for client messages (ping, subscribe, etc.)
                data = await websocket.receive_text()
                print(f"Received message from user {user_id}: {data}")
                
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    # Respond to ping with pong
                    pong_response = {
                        "type": "pong",
                        "timestamp": websocket_manager.connection_metadata[websocket]["connected_at"].isoformat()
                    }
                    await websocket.send_text(json.dumps(pong_response))
                    print(f"Sent pong response to user {user_id}")
                elif message.get("type") == "subscribe":
                    # Handle subscription to specific data types
                    subscription_response = {
                        "type": "subscription_confirmed",
                        "subscriptions": message.get("subscriptions", []),
                        "timestamp": websocket_manager.connection_metadata[websocket]["connected_at"].isoformat()
                    }
                    await websocket.send_text(json.dumps(subscription_response))
                    print(f"Subscription confirmed for user {user_id}: {message.get('subscriptions', [])}")
                    
            except json.JSONDecodeError as e:
                print(f"JSON decode error from user {user_id}: {e}")
                # Invalid JSON, send error
                error_response = {
                    "type": "error",
                    "message": "Invalid JSON format"
                }
                await websocket.send_text(json.dumps(error_response))
            except Exception as e:
                print(f"Error processing message from user {user_id}: {e}")
                break
                
    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected for user {user_id}: Code={e.code}, Reason='{e.reason}'")
        websocket_manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error for user {user_id}: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        websocket_manager.disconnect(websocket)

@router.get("/connections")
async def get_connection_info(user=Depends(get_current_user_ws)):
    """Get information about active WebSocket connections"""
    return {
        "total_connections": websocket_manager.get_connection_count(),
        "user_connections": websocket_manager.get_user_connections(str(user["_id"])),
        "active_users": len(websocket_manager.active_connections)
    }
