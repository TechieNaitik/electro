import os
import pytest
from unittest.mock import patch, mock_open
from datetime import datetime
from django.conf import settings
from myapp.logger import log_action

@pytest.fixture
def mock_log_dir(tmp_path):
    """Fixture to provide a temporary directory for logs."""
    return tmp_path / "logs"

def test_log_action_creates_log_dir(tmp_path):
    """Test that log_action creates the logs directory if it doesn't exist."""
    log_dir = tmp_path / "logs"
    with patch('django.conf.settings.BASE_DIR', str(tmp_path)):
        # Ensure log_dir doesn't exist initially
        assert not os.path.exists(log_dir)
        
        log_action("Test User", "Test Action", "Test Details")
        
        assert os.path.exists(log_dir)
        assert os.path.isdir(log_dir)

def test_log_action_writes_to_file(tmp_path):
    """Test that log_action writes a properly formatted entry to the log file."""
    log_dir = tmp_path / "logs"
    with patch('django.conf.settings.BASE_DIR', str(tmp_path)):
        log_action("Admin: naitik", "Created Brand", "Brand: Apple")
        
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(log_dir, f"{today}.txt")
        
        assert os.path.exists(log_file)
        
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "User: Admin: naitik" in content
            assert "Action: Created Brand" in content
            assert "Details: Brand: Apple" in content
            assert "[" in content  # timestamp part

def test_log_action_handles_exception(capsys):
    """Test that log_action doesn't crash if file writing fails."""
    # We mock 'open' to raise an exception
    with patch('builtins.open', mock_open()) as mocked_file:
        mocked_file.side_effect = Exception("Write Permission Denied")
        
        # This shouldn't raise exception
        log_action("User", "Action", "Details")
        
        captured = capsys.readouterr()
        assert "Logging Error: Write Permission Denied" in captured.out

def test_log_action_multiple_entries(tmp_path):
    """Test that log_action appends to the same file for multiple entries."""
    with patch('django.conf.settings.BASE_DIR', str(tmp_path)):
        log_action("U1", "A1", "D1")
        log_action("U2", "A2", "D2")
        
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(tmp_path, 'logs', f"{today}.txt")
        
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            assert len(lines) == 2
            assert "A1" in lines[0]
            assert "A2" in lines[1]
