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
    
    assert result.returncode == 0
    assert "Redirecting to new SAGE CLI" in result.stdout
    # The actual help output from the new CLI should be present
    assert "Usage: sage [OPTIONS] COMMAND [ARGS]..." in result.stdout
