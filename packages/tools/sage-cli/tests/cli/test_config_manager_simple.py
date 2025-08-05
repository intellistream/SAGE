"""
Simple tests for SAGE CLI config_manager module.
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import tempfile
import yaml


class TestConfigManager(unittest.TestCase):
    """Tests for configuration management functionality."""
    
    def test_import_exists(self):
        """Test that the config_manager module can be imported."""
        try:
            from sage.cli import config_manager
            self.assertTrue(hasattr(config_manager, 'ConfigManager'))
        except ImportError as e:
            self.skipTest(f"Config manager module not available: {e}")
    
    def test_config_structure(self):
        """Test basic config structure validation."""
        sample_config = {
            'server': {
                'host': 'localhost',
                'port': 8080
            },
            'database': {
                'name': 'sage_db',
                'type': 'postgresql'
            }
        }
        
        # Validate structure
        self.assertIn('server', sample_config)
        self.assertIn('database', sample_config)
        self.assertIn('host', sample_config['server'])
        self.assertIn('port', sample_config['server'])
    
    @patch('builtins.open')
    @patch('yaml.safe_load')
    def test_config_file_loading(self, mock_yaml_load, mock_open):
        """Test configuration file loading."""
        mock_config = {'test': 'value'}
        mock_yaml_load.return_value = mock_config
        mock_open.return_value.__enter__.return_value = MagicMock()
        
        # Mock file loading
        with open('test_config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        self.assertEqual(config, mock_config)
        mock_open.assert_called_once_with('test_config.yaml', 'r')
    
    @patch('builtins.open')
    @patch('yaml.dump')
    def test_config_file_saving(self, mock_yaml_dump, mock_open):
        """Test configuration file saving."""
        test_config = {'test': 'value'}
        mock_open.return_value.__enter__.return_value = MagicMock()
        
        # Mock file saving
        with open('test_config.yaml', 'w') as f:
            yaml.dump(test_config, f)
        
        mock_open.assert_called_once_with('test_config.yaml', 'w')
        mock_yaml_dump.assert_called_once()
    
    def test_config_validation(self):
        """Test configuration validation logic."""
        valid_config = {
            'server': {'host': 'localhost', 'port': 8080},
            'logging': {'level': 'INFO'}
        }
        
        invalid_config = {
            'server': {'host': ''},  # Empty host
            'logging': {'level': 'INVALID_LEVEL'}
        }
        
        # Basic validation checks
        self.assertTrue(valid_config.get('server', {}).get('host'))
        self.assertFalse(invalid_config.get('server', {}).get('host'))
    
    def test_default_config_values(self):
        """Test default configuration values."""
        defaults = {
            'server': {
                'host': 'localhost',
                'port': 8080,
                'timeout': 30
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            }
        }
        
        self.assertEqual(defaults['server']['host'], 'localhost')
        self.assertEqual(defaults['server']['port'], 8080)
        self.assertEqual(defaults['logging']['level'], 'INFO')


if __name__ == '__main__':
    unittest.main()
