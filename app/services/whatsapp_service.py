import os
import time
import platform
from typing import Optional
from datetime import datetime

# pywhatkit is optional - only import if available
try:
    import pywhatkit
    PYWHATKIT_AVAILABLE = True
except ImportError:
    PYWHATKIT_AVAILABLE = False
    print("Warning: pywhatkit not installed. WhatsApp messaging will not work.")


class WhatsAppService:
    """Service for sending WhatsApp messages using pywhatkit."""
    
    def __init__(self, enabled: bool = True, country_code: str = "+91"):
        self.enabled = enabled and PYWHATKIT_AVAILABLE
        self.country_code = country_code
        
    def format_phone_number(self, phone: str) -> str:
        """Format phone number for WhatsApp."""
        # Remove any non-digit characters
        digits = ''.join(filter(str.isdigit, phone))
        
        # If number doesn't start with country code, add it
        if not digits.startswith(self.country_code.replace("+", "")):
            digits = self.country_code.replace("+", "") + digits
        
        return digits
    
    def format_bill_message(self, order_data: dict, shop_name: str, 
                           bill_url: str, total: float) -> str:
        """Format WhatsApp message with bill details."""
        order_id = str(order_data.get("id", order_data.get("_id", "Unknown")))
        short_id = order_id[-8:].upper() if len(order_id) > 8 else order_id.upper()
        
        message = f"""🛍️ Thank you for shopping at {shop_name}!

📋 *Order Details*
Bill No: {short_id}
Total: ₹{total:.2f}

📄 *View Your Bill*
{bill_url}

Thank you for your business! 🙏

_Powered by RetailFlow_"""
        
        return message
    
    def send_bill_link(self, phone_number: str, message: str) -> dict:
        """
        Send WhatsApp message with bill link.
        
        Args:
            phone_number: Customer phone number
            message: Formatted message to send
            
        Returns:
            Dict with success status and message
        """
        if not self.enabled:
            return {
                "success": False,
                "message": "WhatsApp service is disabled or pywhatkit not installed"
            }
        
        try:
            # Format phone number
            formatted_phone = self.format_phone_number(phone_number)
            
            # Add country code prefix for pywhatkit
            if not formatted_phone.startswith("+"):
                formatted_phone = "+" + formatted_phone
            
            print(f"Sending WhatsApp message to: {formatted_phone}")
            print(f"Message preview: {message[:100]}...")
            
            # Send message using pywhatkit
            # This opens WhatsApp Web and sends the message
            # Note: Requires WhatsApp Web to be logged in on the computer
            pywhatkit.sendwhatmsg_to_instantly(
                phone=formatted_phone,
                message=message,
                wait_time=10,  # Seconds to wait for WhatsApp Web to open
                tab_close=True,  # Close tab after sending
                close_time=3     # Seconds to wait before closing
            )
            
            return {
                "success": True,
                "message": f"WhatsApp message sent to {formatted_phone}",
                "sent_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"WhatsApp send failed: {error_msg}")
            
            # Common error messages for better UX
            if "browser" in error_msg.lower() or "chrome" in error_msg.lower():
                error_msg = "Browser not found. Please install Chrome or Firefox."
            elif "internet" in error_msg.lower():
                error_msg = "No internet connection. Please check your connection."
            elif "qr" in error_msg.lower() or "login" in error_msg.lower():
                error_msg = "WhatsApp Web not logged in. Please scan QR code at web.whatsapp.com"
            
            return {
                "success": False,
                "message": f"Failed to send WhatsApp: {error_msg}"
            }
    
    def send_bill_via_whatsapp(self, phone_number: str, order_data: dict,
                               shop_name: str, bill_url: str, total: float) -> dict:
        """
        Convenience method to format and send bill message.
        
        Args:
            phone_number: Customer phone number
            order_data: Order details
            shop_name: Shop name for message
            bill_url: URL to view/download bill
            total: Order total amount
            
        Returns:
            Dict with success status and message
        """
        message = self.format_bill_message(order_data, shop_name, bill_url, total)
        return self.send_bill_link(phone_number, message)


# Global instance
whatsapp_service = WhatsAppService(
    enabled=os.getenv("ENABLE_WHATSAPP_BILLING", "true").lower() == "true",
    country_code=os.getenv("WHATSAPP_COUNTRY_CODE", "+91")
)


async def send_bill_whatsapp(phone_number: str, order_data: dict,
                             shop_name: str, bill_url: str, total: float) -> dict:
    """
    Async wrapper for sending WhatsApp bill.
    
    Note: pywhatkit is synchronous, so we run it in a way that doesn't block,
    but the actual browser automation will still take time (10-15 seconds).
    """
    # Run the synchronous pywhatkit in a separate thread to not block
    import asyncio
    loop = asyncio.get_event_loop()
    
    result = await loop.run_in_executor(
        None,
        whatsapp_service.send_bill_via_whatsapp,
        phone_number,
        order_data,
        shop_name,
        bill_url,
        total
    )
    
    return result
