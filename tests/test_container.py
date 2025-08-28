"""Tests for dependency injection container"""
import pytest
from unittest.mock import Mock
from typing import Optional

from src.container import Container, ServiceDescriptor


class MockService:
    """Mock service for testing"""
    def __init__(self, name: str = "test") -> None:
        self.name = name


class MockDependentService:
    """Mock service with dependency for testing"""
    def __init__(self, mock_service: MockService) -> None:
        self.mock_service = mock_service


class TestContainer:
    """Test cases for dependency injection container"""
    
    def test_register_and_resolve_simple_service(self) -> None:
        """Test basic service registration and resolution"""
        container = Container()
        container.register(MockService)
        
        service = container.resolve(MockService)
        
        assert isinstance(service, MockService)
        assert service.name == "test"
    
    def test_singleton_behavior(self) -> None:
        """Test that singleton services return the same instance"""
        container = Container()
        container.register(MockService, singleton=True)
        
        service1 = container.resolve(MockService)
        service2 = container.resolve(MockService)
        
        assert service1 is service2
    
    def test_non_singleton_behavior(self) -> None:
        """Test that non-singleton services return different instances"""
        container = Container()
        container.register(MockService, singleton=False)
        
        service1 = container.resolve(MockService)
        service2 = container.resolve(MockService)
        
        assert service1 is not service2
        assert isinstance(service1, MockService)
        assert isinstance(service2, MockService)
    
    def test_register_with_factory(self) -> None:
        """Test registration with custom factory function"""
        container = Container()
        
        def create_mock_service() -> MockService:
            return MockService("custom")
        
        container.register(MockService, factory=create_mock_service)
        
        service = container.resolve(MockService)
        
        assert isinstance(service, MockService)
        assert service.name == "custom"
    
    def test_register_instance(self) -> None:
        """Test registration of existing instance"""
        container = Container()
        instance = MockService("instance")
        
        container.register_instance(MockService, instance)
        
        service = container.resolve(MockService)
        
        assert service is instance
        assert service.name == "instance"
    
    def test_dependency_injection(self) -> None:
        """Test automatic dependency injection"""
        container = Container()
        container.register(MockService)
        container.register(MockDependentService)
        
        service = container.resolve(MockDependentService)
        
        assert isinstance(service, MockDependentService)
        assert isinstance(service.mock_service, MockService)
    
    def test_unregistered_service_raises_error(self) -> None:
        """Test that resolving unregistered service raises error"""
        container = Container()
        
        with pytest.raises(ValueError, match="Service MockService is not registered"):
            container.resolve(MockService)
    
    def test_method_chaining(self) -> None:
        """Test that registration methods support chaining"""
        container = Container()
        
        result = container.register(MockService).register(MockDependentService)
        
        assert result is container
        
        # Verify both services are registered
        service1 = container.resolve(MockService)
        service2 = container.resolve(MockDependentService)
        
        assert isinstance(service1, MockService)
        assert isinstance(service2, MockDependentService)


@pytest.fixture
def container() -> Container:
    """Provide a fresh container for each test"""
    return Container()


def test_service_descriptor_creation() -> None:
    """Test ServiceDescriptor creation"""
    def factory() -> MockService:
        return MockService()
    
    descriptor = ServiceDescriptor(
        factory=factory,
        singleton=True,
        dependencies={"dep": "SomeService"}
    )
    
    assert descriptor.factory is factory
    assert descriptor.singleton is True
    assert descriptor.dependencies == {"dep": "SomeService"}