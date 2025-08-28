"""Dependency injection container for nano-banana application"""
from typing import TypeVar, Type, Dict, Any, Callable, Optional
from dataclasses import dataclass
import inspect


T = TypeVar('T')


@dataclass
class ServiceDescriptor:
    """Describes how a service should be created and managed"""
    factory: Callable[..., Any]
    singleton: bool = True
    dependencies: Optional[Dict[str, str]] = None


class Container:
    """Simple dependency injection container"""
    
    def __init__(self) -> None:
        self._services: Dict[str, ServiceDescriptor] = {}
        self._instances: Dict[str, Any] = {}
    
    def register(
        self,
        service_type: Type[T],
        factory: Optional[Callable[..., T]] = None,
        singleton: bool = True,
        **kwargs: Any
    ) -> 'Container':
        """Register a service with the container
        
        Args:
            service_type: The type/interface of the service
            factory: Factory function to create the service (defaults to constructor)
            singleton: Whether to create only one instance (default: True)
            **kwargs: Additional dependencies to inject
            
        Returns:
            Self for method chaining
        """
        service_name = service_type.__name__
        
        if factory is None:
            factory = service_type
        
        # Extract constructor dependencies from type hints
        sig = inspect.signature(factory)
        dependencies = {}
        
        for param_name, param in sig.parameters.items():
            if param_name != 'self' and param.annotation != param.empty:
                # Use parameter annotation as service name
                if hasattr(param.annotation, '__name__'):
                    dependencies[param_name] = param.annotation.__name__
                else:
                    # For complex types like Optional[SomeType], try to extract
                    origin = getattr(param.annotation, '__origin__', None)
                    args = getattr(param.annotation, '__args__', ())
                    if origin is not None and args:
                        # Handle Optional[T] -> T
                        if origin is type(Optional[str]):
                            dependencies[param_name] = args[0].__name__
        
        # Override with explicitly provided dependencies
        dependencies.update(kwargs)
        
        self._services[service_name] = ServiceDescriptor(
            factory=factory,
            singleton=singleton,
            dependencies=dependencies or None
        )
        
        return self
    
    def register_instance(self, service_type: Type[T], instance: T) -> 'Container':
        """Register an existing instance as a service
        
        Args:
            service_type: The type of the service
            instance: The instance to register
            
        Returns:
            Self for method chaining
        """
        service_name = service_type.__name__
        self._instances[service_name] = instance
        return self
    
    def resolve(self, service_type: Type[T]) -> T:
        """Resolve a service from the container
        
        Args:
            service_type: The type of service to resolve
            
        Returns:
            An instance of the requested service
        """
        service_name = service_type.__name__
        
        # Return existing instance if singleton
        if service_name in self._instances:
            return self._instances[service_name]
        
        # Get service descriptor
        if service_name not in self._services:
            raise ValueError(f"Service {service_name} is not registered")
        
        descriptor = self._services[service_name]
        
        # Build dependencies
        kwargs = {}
        if descriptor.dependencies:
            for param_name, dep_type_name in descriptor.dependencies.items():
                # Recursively resolve dependencies
                dep_type = self._find_type_by_name(dep_type_name)
                if dep_type:
                    kwargs[param_name] = self.resolve(dep_type)
        
        # Create instance
        instance = descriptor.factory(**kwargs)
        
        # Cache if singleton
        if descriptor.singleton:
            self._instances[service_name] = instance
        
        return instance
    
    def _find_type_by_name(self, type_name: str) -> Optional[Type]:
        """Find a registered type by its name"""
        for service_name, descriptor in self._services.items():
            if service_name == type_name:
                # Try to extract the actual type from the factory
                factory = descriptor.factory
                if hasattr(factory, '__annotations__'):
                    return_annotation = factory.__annotations__.get('return')
                    if return_annotation and hasattr(return_annotation, '__name__'):
                        if return_annotation.__name__ == type_name:
                            return return_annotation
                
                # Fallback: assume factory is the constructor
                if hasattr(factory, '__name__') and factory.__name__ == type_name:
                    return factory
        
        return None


# Global container instance
container = Container()


def get_container() -> Container:
    """Get the global container instance"""
    return container


def configure_container() -> Container:
    """Configure the container with default services"""
    from .config import Config
    from .storage import StorageManager  
    from .database import DatabaseManager
    from .fal_wrapper import FALWrapper
    from .image_preview import ImagePreview
    
    # Register core services
    container.register(Config)
    container.register(StorageManager)
    container.register(DatabaseManager)
    container.register(ImagePreview)
    
    # FALWrapper needs special handling for optional parameters
    container.register(
        FALWrapper,
        lambda: FALWrapper(db_manager=container.resolve(DatabaseManager))
    )
    
    return container