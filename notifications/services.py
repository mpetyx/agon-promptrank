import requests
import json
from django.conf import settings

def send_slack_notification(message: str, webhook_url: str = None):
    """
    Sends a payload to a slack/teams webhook.
    """
    webhook_url = webhook_url or getattr(settings, 'SLACK_WEBHOOK_URL', None)
    if not webhook_url:
        print("No slack webhook configured.")
        return False
        
    payload = {
        "text": message
    }
    
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Failed to send notification: {e}")
        return False

def format_badge_message(user, badge):
    """
    Called asynchronously from Celery when a new badge is awarded.
    """
    return f"🏆 *Achievement Unlocked!* {user.username} just earned the *{badge.name}* badge!"
