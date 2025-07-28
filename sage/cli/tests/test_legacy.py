"""
Tests for sage.cli.legacy
"""
from unittest.mock import patch
import subprocess
import sys

def test_legacy_script_redirects():
    """Test that the legacy script redirects to the new CLI."""
    
    # We need to run this in a separate process to simulate the `if __name__ == "__main__"` block
    result = subprocess.run(
        [sys.executable, "-m", "sage.cli.legacy"],
        capture_output=True,
        text=True
    )
    
    # The command exits with code 2 (missing command), which is expected behavior
    assert result.returncode in [0, 2]  # Accept both success and "missing command" 
    assert "Redirecting to new SAGE CLI" in result.stdout
