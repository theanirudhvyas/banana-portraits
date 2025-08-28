"""Tests for storage manager"""
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
import requests

from src.storage import StorageManager


@pytest.fixture
def temp_storage():
    """Create temporary storage directory for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Mock the config to use temp directory
        with patch('src.storage.Config') as mock_config:
            config_instance = Mock()
            config_instance.models_dir = temp_path / "models"
            config_instance.outputs_dir = temp_path / "outputs" 
            config_instance.temp_dir = temp_path / "temp"
            config_instance.storage_dir = temp_path
            
            # Create directories
            config_instance.models_dir.mkdir(parents=True, exist_ok=True)
            config_instance.outputs_dir.mkdir(parents=True, exist_ok=True)
            config_instance.temp_dir.mkdir(parents=True, exist_ok=True)
            
            mock_config.return_value = config_instance
            
            yield StorageManager()


class TestStorageManager:
    """Test cases for StorageManager"""
    
    def test_initialization(self, temp_storage):
        """Test that storage manager initializes correctly"""
        storage = temp_storage
        
        assert storage.config is not None
        assert storage.models_file.name == 'models.json'
        assert isinstance(storage._models, dict)
    
    def test_save_and_load_model(self, temp_storage):
        """Test saving and loading model information"""
        storage = temp_storage
        
        model_info = {
            "lora_url": "https://example.com/model.safetensors",
            "trigger_word": "NANO",
            "created": "2024-01-01"
        }
        
        storage.save_model("test_model", model_info)
        loaded_info = storage.load_model("test_model")
        
        assert loaded_info == model_info
    
    def test_load_nonexistent_model(self, temp_storage):
        """Test loading model that doesn't exist"""
        storage = temp_storage
        
        result = storage.load_model("nonexistent")
        
        assert result is None
    
    def test_list_models(self, temp_storage):
        """Test listing all models"""
        storage = temp_storage
        
        # Initially empty
        models = storage.list_models()
        assert models == {}
        
        # Add some models
        storage.save_model("model1", {"url": "url1"})
        storage.save_model("model2", {"url": "url2"})
        
        models = storage.list_models()
        assert len(models) == 2
        assert "model1" in models
        assert "model2" in models
    
    def test_delete_model(self, temp_storage):
        """Test deleting a model"""
        storage = temp_storage
        
        storage.save_model("test_model", {"url": "test"})
        
        # Model exists
        assert storage.load_model("test_model") is not None
        
        # Delete model
        result = storage.delete_model("test_model")
        assert result is True
        
        # Model no longer exists
        assert storage.load_model("test_model") is None
        
        # Delete nonexistent model
        result = storage.delete_model("nonexistent")
        assert result is False
    
    @patch('src.storage.requests.get')
    def test_save_generated_image(self, mock_get, temp_storage):
        """Test downloading and saving generated images"""
        storage = temp_storage
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.raw = MagicMock()
        mock_get.return_value = mock_response
        
        with patch('src.storage.shutil.copyfileobj') as mock_copyfile:
            image_path = storage.save_generated_image(
                "https://example.com/image.jpg", 
                "test_image.jpg"
            )
            
            expected_path = str(storage.outputs_dir / "test_image.jpg")
            assert image_path == expected_path
            
            mock_get.assert_called_once_with("https://example.com/image.jpg", stream=True)
            mock_response.raise_for_status.assert_called_once()
            mock_copyfile.assert_called_once()
    
    def test_create_temp_file(self, temp_storage):
        """Test creating temporary files"""
        storage = temp_storage
        
        temp_path = storage.create_temp_file('.jpg')
        
        assert temp_path is not None
        assert Path(temp_path).suffix == '.jpg'
        assert Path(temp_path).parent == storage.temp_dir
    
    def test_cleanup_temp_files(self, temp_storage):
        """Test cleaning up temporary files"""
        storage = temp_storage
        
        # Create some temp files
        temp_file1 = storage.create_temp_file('.jpg')
        temp_file2 = storage.create_temp_file('.png')
        
        # Files exist
        assert Path(temp_file1).exists() is False  # NamedTemporaryFile with delete=False
        assert Path(temp_file2).exists() is False
        
        # Create actual files for testing cleanup
        test_file = storage.temp_dir / "test.txt"
        test_file.write_text("test")
        assert test_file.exists()
        
        # Cleanup
        storage.cleanup_temp_files()
        
        # Temp directory still exists but is empty
        assert storage.temp_dir.exists()
        assert not test_file.exists()
    
    def test_get_timestamp(self, temp_storage):
        """Test timestamp generation"""
        storage = temp_storage
        
        timestamp = storage.get_timestamp()
        
        assert isinstance(timestamp, str)
        assert len(timestamp) == 15  # YYYYMMDD_HHMMSS format
        assert '_' in timestamp
    
    def test_get_storage_stats(self, temp_storage):
        """Test storage statistics"""
        storage = temp_storage
        
        # Create some test files
        (storage.outputs_dir / "test.jpg").write_bytes(b"fake image data")
        storage.save_model("test", {"data": "test"})
        
        stats = storage.get_storage_stats()
        
        assert isinstance(stats, dict)
        assert 'models_count' in stats
        assert 'outputs_size_mb' in stats
        assert 'temp_size_mb' in stats
        assert 'total_size_mb' in stats
        
        assert stats['models_count'] == 1
        assert stats['outputs_size_mb'] >= 0
    
    def test_models_registry_persistence(self, temp_storage):
        """Test that model registry persists to disk"""
        storage = temp_storage
        
        # Save a model
        storage.save_model("persistent_model", {"url": "test"})
        
        # Registry file should exist
        assert storage.models_file.exists()
        
        # Read registry file directly
        with open(storage.models_file, 'r') as f:
            registry_data = json.load(f)
        
        assert "persistent_model" in registry_data
        assert registry_data["persistent_model"]["url"] == "test"
    
    def test_corrupted_registry_handling(self, temp_storage):
        """Test handling of corrupted registry file"""
        storage = temp_storage
        
        # Create corrupted JSON file
        storage.models_file.write_text("invalid json {")
        
        # Should handle corruption gracefully
        new_storage = StorageManager.__new__(StorageManager)
        new_storage.config = storage.config
        new_storage.models_file = storage.models_file
        new_storage.outputs_dir = storage.outputs_dir
        new_storage.temp_dir = storage.temp_dir
        new_storage._models = new_storage._load_models_registry()
        
        assert new_storage._models == {}  # Should start with empty registry