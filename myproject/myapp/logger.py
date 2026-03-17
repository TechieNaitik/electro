import os
from datetime import datetime
from django.conf import settings

def log_action(user_info, action, details):
    """
    Logs an action to a daily log file in the logs/ directory.
    
    :param user_info: String representing the user (e.g., 'Customer: John Doe <john@example.com>' or 'Admin: admin')
    :param action: String representing the action (e.g., 'Placed Order', 'Created Brand')
    :param details: String representing additional details (e.g., 'Order #123', 'Brand: Samsung')
    """
    log_dir = os.path.join(settings.BASE_DIR, 'logs')
    
    # Create logs/ folder if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Daily log file name (e.g., 2024-05-15.txt)
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(log_dir, f"{today}.txt")
    
    # Timestamp for the log entry
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Format the log entry
    log_entry = f"[{timestamp}] User: {user_info} | Action: {action} | Details: {details}\n"
    
    # Append to the log file (create if it doesn't exist)
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        # If logging fails, we don't want to crash the whole app, but maybe print it to console
        print(f"Logging Error: {e}")
