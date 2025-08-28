"""Tests for simplified service locator"""
import pytest
from unittest.mock import Mock, patch

from src.services import (
    register_service, get_service, clear_services, 
    initialize_services, is_initialized, get_fal_client, require_fal_client
)


class MockService:
    """Mock service for testing"""
    def __init__(self, name: str = "test") -> None:
        self.name = name


class TestServiceLocator:
    """Test cases for service locator"""
    
    def setUp(self) -> None:
        """Clear services before each test"""
        clear_services()
    
    def test_register_and_get_service(self) -> None:
        """Test basic service registration and retrieval"""
        clear_services()
        service = MockService("test")
        
        register_service(MockService, service)
        retrieved = get_service(MockService)
        
        assert retrieved is service
        assert retrieved.name == "test"
    
    def test_get_unregistered_service_raises_error(self) -> None:
        """Test that getting unregistered service raises error"""
        clear_services()
        
        with pytest.raises(ValueError, match="Service MockService not registered"):
            get_service(MockService)
    
    def test_clear_services(self) -> None:
        """Test clearing all services"""
        clear_services()
        service = MockService()
        register_service(MockService, service)
        
        # Service is registered
        assert get_service(MockService) is service
        
        # Clear services
        clear_services()
        
        # Service is no longer available
        with pytest.raises(ValueError):
            get_service(MockService)
    
    @patch('src.config.Config')
    @patch('src.storage.StorageManager')  
    @patch('src.database.DatabaseManager')
    @patch('src.image_preview.ImagePreview')
    @patch('src.fal_wrapper.FALWrapper')
    def test_initialize_services_success(self, mock_fal, mock_image, mock_db, mock_storage, mock_config):
        """Test successful service initialization"""
        clear_services()
        
        # Mock successful FAL client creation
        mock_config.return_value = Mock()
        mock_storage.return_value = Mock()
        mock_db.return_value = Mock()  
        mock_image.return_value = Mock()
        mock_fal.return_value = Mock()
        
        initialize_services(verbose=True)
        
        assert is_initialized()
        
        # Verify services are registered
        from src.config import Config
        from src.storage import StorageManager
        from src.database import DatabaseManager
        from src.image_preview import ImagePreview
        
        assert get_service(Config) is not None
        assert get_service(StorageManager) is not None
        assert get_service(DatabaseManager) is not None
        assert get_service(ImagePreview) is not None
    
    @patch('src.config.Config')
    @patch('src.storage.StorageManager')
    @patch('src.database.DatabaseManager') 
    @patch('src.image_preview.ImagePreview')
    @patch('src.fal_wrapper.FALWrapper')
    def test_initialize_services_no_fal_key(self, mock_fal, mock_image, mock_db, mock_storage, mock_config):
        """Test service initialization without FAL key"""
        clear_services()
        
        # Mock FAL client creation failure
        mock_config.return_value = Mock()
        mock_storage.return_value = Mock()
        mock_db.return_value = Mock()
        mock_image.return_value = Mock()
        mock_fal.side_effect = ValueError("No FAL key")
        
        initialize_services()
        
        assert is_initialized()
        assert get_fal_client() is None
    
    def test_initialize_services_idempotent(self) -> None:
        """Test that initialize_services can be called multiple times safely"""
        clear_services()
        
        with patch('src.config.Config'), \
             patch('src.storage.StorageManager'), \
             patch('src.database.DatabaseManager'), \
             patch('src.image_preview.ImagePreview'), \
             patch('src.fal_wrapper.FALWrapper', side_effect=ValueError):
            
            # Initialize twice
            initialize_services()
            initialize_services()
            
            # Should still be initialized
            assert is_initialized()
    
    def test_get_fal_client_available(self) -> None:
        """Test getting FAL client when available"""
        clear_services()
        mock_fal = Mock()
        
        from src.fal_wrapper import FALWrapper
        register_service(FALWrapper, mock_fal)
        
        client = get_fal_client()
        assert client is mock_fal
    
    def test_get_fal_client_unavailable(self) -> None:
        """Test getting FAL client when not available"""
        clear_services()
        
        client = get_fal_client()
        assert client is None
    
    def test_require_fal_client_available(self) -> None:
        """Test requiring FAL client when available"""
        clear_services()
        mock_fal = Mock()
        
        from src.fal_wrapper import FALWrapper
        register_service(FALWrapper, mock_fal)
        
        client = require_fal_client()
        assert client is mock_fal
    
    def test_require_fal_client_unavailable(self) -> None:
        """Test requiring FAL client when not available"""
        clear_services()
        
        with pytest.raises(ValueError, match="FAL_KEY is required"):
            require_fal_client()
    
    def test_is_initialized_states(self) -> None:
        """Test initialization state tracking"""
        clear_services()
        assert not is_initialized()
        
        with patch('src.config.Config'), \
             patch('src.storage.StorageManager'), \
             patch('src.database.DatabaseManager'), \
             patch('src.image_preview.ImagePreview'), \
             patch('src.fal_wrapper.FALWrapper', side_effect=ValueError):
            
            initialize_services()
            assert is_initialized()
            
            clear_services()
            assert not is_initialized()


# Fixtures for service testing
@pytest.fixture(autouse=True)
def setup_test_services():
    """Automatically clear services before each test"""
    clear_services()
    yield
    clear_services()


@pytest.fixture
def mock_services():
    """Provide mock services for testing"""
    services = {
        'config': Mock(),
        'storage': Mock(), 
        'database': Mock(),
        'fal': Mock()
    }
    return services