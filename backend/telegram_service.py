"""
telegram_service.py - Real-time Telegram Bot API dispatch service
for ClimateGuard India public health warning alerts.
"""

import os
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("climateguard.telegram")


def get_telegram_credentials() -> Tuple[str, str]:
    """Retrieve Telegram credentials from environment, returning trimmed strings."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    channel = os.getenv("TELEGRAM_CHANNEL_ID", "").strip()
    return token, channel


def send_telegram_alert(message_text: str, chat_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Send an HTML-formatted message to the specified Telegram channel or group.
    
    Returns:
        {"sent": True, "message": message_text, "channel": target_channel, "message_id": ...}
        or
        {"sent": False, "error": "<clear description>", "channel": target_channel}
    """
    token, default_channel = get_telegram_credentials()
    target_channel = (chat_id or default_channel).strip()

    if not token:
        err_msg = "Telegram Bot Token (TELEGRAM_BOT_TOKEN) is not configured in environment variables."
        logger.error(err_msg)
        return {"sent": False, "error": err_msg, "channel": target_channel or "Unconfigured"}

    if not target_channel:
        err_msg = "Telegram Channel ID (TELEGRAM_CHANNEL_ID) is not configured in environment variables."
        logger.error(err_msg)
        return {"sent": False, "error": err_msg, "channel": "Unconfigured"}

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": target_channel,
        "text": message_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            res_body = response.read().decode("utf-8")
            res_json = json.loads(res_body)

        if res_json.get("ok"):
            result_data = res_json.get("result", {})
            msg_id = result_data.get("message_id")
            logger.info(f"Telegram alert successfully dispatched to {target_channel} (message_id: {msg_id})")
            return {
                "sent": True,
                "channel": target_channel,
                "message": message_text,
                "message_id": msg_id,
                "raw": result_data
            }
        else:
            description = res_json.get("description", "Unknown Telegram API rejection")
            err_msg = f"Telegram rejected alert: {description}"
            logger.error(err_msg)
            return {"sent": False, "error": err_msg, "channel": target_channel}

    except urllib.error.HTTPError as http_err:
        try:
            err_body = http_err.read().decode("utf-8")
            err_json = json.loads(err_body)
            desc = err_json.get("description", str(http_err))
        except Exception:
            desc = f"HTTP {http_err.code}: {http_err.reason}"
        
        err_msg = f"Telegram Bot API error ({http_err.code}): {desc}"
        logger.error(err_msg)
        return {"sent": False, "error": err_msg, "channel": target_channel}

    except urllib.error.URLError as url_err:
        err_msg = f"Network connection error to Telegram API: {url_err.reason}"
        logger.error(err_msg)
        return {"sent": False, "error": err_msg, "channel": target_channel}

    except Exception as exc:
        err_msg = f"Unexpected failure dispatching Telegram alert: {str(exc)}"
        logger.exception(err_msg)
        return {"sent": False, "error": err_msg, "channel": target_channel}
