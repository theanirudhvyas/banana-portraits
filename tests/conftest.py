"""Pytest configuration and shared fixtures"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.services import clear_services
from src.config import Config
from src.storage import StorageManager
from src.database import DatabaseManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_config(temp_dir):
    """Mock configuration with temporary directories"""
    config = Mock(spec=Config)
    config.storage_dir = temp_dir / "storage"
    config.models_dir = temp_dir / "models"  
    config.outputs_dir = temp_dir / "outputs"
    config.temp_dir = temp_dir / "temp"
    
    # Create directories
    config.storage_dir.mkdir(parents=True, exist_ok=True)
    config.models_dir.mkdir(parents=True, exist_ok=True)
    config.outputs_dir.mkdir(parents=True, exist_ok=True)
    config.temp_dir.mkdir(parents=True, exist_ok=True)
    
    return config


@pytest.fixture(autouse=True)
def clean_services():
    """Clear services before and after each test"""
    clear_services()
    yield
    clear_services()


@pytest.fixture
def mock_fal_client():
    """Mock FAL client for testing"""
    with patch('src.fal_wrapper.fal') as mock_fal:
        mock_client = Mock()
        mock_fal.subscribe.return_value = {
            'images': [{'url': 'https://example.com/test.jpg'}],
            'seed': 12345,
            'timings': {'inference': 2.5}
        }
        mock_fal.upload_file.return_value = 'https://example.com/uploaded.jpg'
        yield mock_fal


@pytest.fixture
def sample_generation_data():
    """Sample generation data for testing"""
    return {
        'id': 1,
        'timestamp': '2024-01-01T12:00:00',
        'prompt': 'a robot in a city',
        'base_model': 'flux-dev',
        'finetuned_model': None,
        'steps': 28,
        'image_size': 'landscape_16_9',
        'num_images': 1,
        'seed': 12345,
        'image_paths': ['/path/to/image.jpg'],
        'image_urls': ['https://example.com/image.jpg'],
        'generation_time': 2.5,
        'success': True,
        'error_message': None,
        'metadata': None
    }


@pytest.fixture
def sample_session_data():
    """Sample session data for testing"""
    return {
        'id': 1,
        'name': 'Test Session',
        'created_timestamp': '2024-01-01T12:00:00',
        'updated_timestamp': '2024-01-01T12:30:00',
        'initial_image_path': '/path/to/initial.jpg',
        'description': 'Test session description',
        'step_count': 3
    }


@pytest.fixture 
def sample_step_data():
    """Sample step data for testing"""
    return {
        'id': 1,
        'session_id': 1,
        'step_number': 1,
        'prompt': 'make it more colorful',
        'image_path': '/path/to/step1.jpg',
        'timestamp': '2024-01-01T12:15:00',
        'success': True,
        'error_message': None,
        'generation_time': 1.8
    }


# Test markers for different test categories
pytest_plugins = []

def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "functional: mark test as a functional test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )