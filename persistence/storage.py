"""
Storage abstraction layer for Enterprise PM Agent
Supports multiple backends: in-memory, file-based, SQL, NoSQL
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Dict, Any
from datetime import datetime
import json
import uuid
import os
from pydantic import BaseModel as PydanticModel, Field

# Type variable for entity classes
T = TypeVar('T', bound=PydanticModel)


class BaseEntity(PydanticModel):
    """Base entity class with common fields"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1

    def __init__(self, **data):
        if 'id' not in data:
            data['id'] = str(uuid.uuid4())
        if 'created_at' not in data:
            data['created_at'] = datetime.utcnow()
        if 'updated_at' not in data:
            data['updated_at'] = datetime.utcnow()
        super().__init__(**data)


class StorageResult(Generic[T]):
    """Result of a storage operation"""
    def __init__(
        self,
        success: bool,
        data: Optional[T] = None,
        error: Optional[str] = None,
        total_count: Optional[int] = None
    ):
        self.success = success
        self.data = data
        self.error = error
        self.total_count = total_count

    @classmethod
    def success_result(cls, data: T) -> 'StorageResult[T]':
        return cls(success=True, data=data)

    @classmethod
    def error_result(cls, error: str) -> 'StorageResult[T]':
        return cls(success=False, error=error)

    @classmethod
    def list_result(cls, data: List[T], total_count: int) -> 'StorageResult[List[T]]':
        return cls(success=True, data=data, total_count=total_count)


class StorageAdapter(ABC, Generic[T]):
    """Abstract base class for storage adapters"""

    @abstractmethod
    async def create(self, entity: T) -> StorageResult[T]:
        """Create a new entity"""
        pass

    @abstractmethod
    async def get_by_id(self, entity_id: str) -> StorageResult[T]:
        """Get entity by ID"""
        pass

    @abstractmethod
    async def update(self, entity_id: str, entity: T) -> StorageResult[T]:
        """Update an existing entity"""
        pass

    @abstractmethod
    async def delete(self, entity_id: str) -> StorageResult[bool]:
        """Delete an entity by ID"""
        pass

    @abstractmethod
    async def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: Optional[str] = None,
        sort_desc: bool = False
    ) -> StorageResult[List[T]]:
        """List entities with optional filtering and pagination"""
        pass

    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> StorageResult[int]:
        """Count entities matching filters"""
        pass

    @abstractmethod
    async def exists(self, entity_id: str) -> StorageResult[bool]:
        """Check if entity exists"""
        pass

    @abstractmethod
    async def health_check(self) -> StorageResult[bool]:
        """Check storage health"""
        pass


class InMemoryStorageAdapter(StorageAdapter[T]):
    """In-memory storage adapter for development and testing"""

    def __init__(self, entity_type: type[T]):
        self.entity_type = entity_type
        self._storage: Dict[str, T] = {}
        self._indexes: Dict[str, Dict[Any, List[str]]] = {}

    async def create(self, entity: T) -> StorageResult[T]:
        """Create a new entity in memory"""
        try:
            # Ensure ID is set
            if not entity.id:
                entity.id = str(uuid.uuid4())

            # Set timestamps
            now = datetime.utcnow()
            if hasattr(entity, 'created_at') and not entity.created_at:
                entity.created_at = now
            if hasattr(entity, 'updated_at'):
                entity.updated_at = now

            # Store the entity
            self._storage[entity.id] = entity

            # Update indexes
            self._update_indexes(entity.id, entity)

            return StorageResult.success_result(entity)
        except Exception as e:
            return StorageResult.error_result(str(e))

    async def get_by_id(self, entity_id: str) -> StorageResult[T]:
        """Get entity by ID from memory"""
        try:
            entity = self._storage.get(entity_id)
            if entity is None:
                return StorageResult.error_result(f"Entity not found: {entity_id}")
            return StorageResult.success_result(entity)
        except Exception as e:
            return StorageResult.error_result(str(e))

    async def update(self, entity_id: str, entity: T) -> StorageResult[T]:
        """Update an existing entity in memory"""
        try:
            if entity_id not in self._storage:
                return StorageResult.error_result(f"Entity not found: {entity_id}")

            # Ensure ID matches
            entity.id = entity_id

            # Update timestamp
            if hasattr(entity, 'updated_at'):
                entity.updated_at = datetime.utcnow()

            # Remove old indexes
            old_entity = self._storage[entity_id]
            self._remove_indexes(entity_id, old_entity)

            # Store updated entity
            self._storage[entity_id] = entity

            # Update indexes
            self._update_indexes(entity_id, entity)

            return StorageResult.success_result(entity)
        except Exception as e:
            return StorageResult.error_result(str(e))

    async def delete(self, entity_id: str) -> StorageResult[bool]:
        """Delete an entity by ID from memory"""
        try:
            if entity_id not in self._storage:
                return StorageResult.error_result(f"Entity not found: {entity_id}")

            # Remove indexes
            entity = self._storage[entity_id]
            self._remove_indexes(entity_id, entity)

            # Remove entity
            del self._storage[entity_id]

            return StorageResult.success_result(True)
        except Exception as e:
            return StorageResult.error_result(str(e))

    async def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: Optional[str] = None,
        sort_desc: bool = False
    ) -> StorageResult[List[T]]:
        """List entities from memory with filtering and pagination"""
        try:
            # Apply filters
            filtered_entities = list(self._storage.values())
            if filters:
                filtered_entities = [
                    entity for entity in filtered_entities
                    if self._matches_filters(entity, filters)
                ]

            # Apply sorting
            if sort_by and hasattr(filtered_entities[0] if filtered_entities else None, sort_by):
                reverse = sort_desc
                filtered_entities.sort(
                    key=lambda x: getattr(x, sort_by),
                    reverse=reverse
                )

            # Apply pagination
            total_count = len(filtered_entities)
            paginated_entities = filtered_entities[offset:offset + limit]

            return StorageResult.list_result(paginated_entities, total_count)
        except Exception as e:
            return StorageResult.error_result(str(e))

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> StorageResult[int]:
        """Count entities matching filters"""
        try:
            if not filters:
                return StorageResult.success_result(len(self._storage))

            count = sum(
                1 for entity in self._storage.values()
                if self._matches_filters(entity, filters)
            )
            return StorageResult.success_result(count)
        except Exception as e:
            return StorageResult.error_result(str(e))

    async def exists(self, entity_id: str) -> StorageResult[bool]:
        """Check if entity exists in memory"""
        try:
            exists = entity_id in self._storage
            return StorageResult.success_result(exists)
        except Exception as e:
            return StorageResult.error_result(str(e))

    async def health_check(self) -> StorageResult[bool]:
        """Check in-memory storage health"""
        try:
            # Simple check - if we can access the storage, it's healthy
            _ = len(self._storage)
            return StorageResult.success_result(True)
        except Exception as e:
            return StorageResult.error_result(str(e))

    def _matches_filters(self, entity: T, filters: Dict[str, Any]) -> bool:
        """Check if entity matches all filters"""
        for field, value in filters.items():
            if not hasattr(entity, field):
                return False
            if getattr(entity, field) != value:
                return False
        return True

    def _update_indexes(self, entity_id: str, entity: T):
        """Update indexes for an entity"""
        # For simplicity, we're not implementing complex indexing in this example
        pass

    def _remove_indexes(self, entity_id: str, entity: T):
        """Remove indexes for an entity"""
        # For simplicity, we're not implementing complex indexing in this example
        pass


class FileStorageAdapter(StorageAdapter[T]):
    """File-based storage adapter using JSON files"""

    def __init__(self, entity_type: type[T], file_path: str):
        self.entity_type = entity_type
        self.file_path = file_path
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Ensure the storage file exists"""
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                json.dump({}, f)

    def _read_data(self) -> Dict[str, Any]:
        """Read data from file"""
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _write_data(self, data: Dict[str, Any]):
        """Write data to file"""
        with open(self.file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    async def create(self, entity: T) -> StorageResult[T]:
        """Create a new entity in file storage"""
        try:
            data = self._read_data()

            # Ensure ID is set
            if not entity.id:
                entity.id = str(uuid.uuid4())

            # Set timestamps
            now = datetime.utcnow()
            if hasattr(entity, 'created_at') and not entity.created_at:
                entity.created_at = now
            if hasattr(entity, 'updated_at'):
                entity.updated_at = now

            # Store the entity
            data[entity.id] = entity.dict()
            self._write_data(data)

            return StorageResult.success_result(entity)
        except Exception as e:
            return StorageResult.error_result(str(e))

    async def get_by_id(self, entity_id: str) -> StorageResult[T]:
        """Get entity by ID from file storage"""
        try:
            data = self._read_data()
            entity_dict = data.get(entity_id)

            if entity_dict is None:
                return StorageResult.error_result(f"Entity not found: {entity_id}")

            entity = self.entity_type(**entity_dict)
            return StorageResult.success_result(entity)
        except Exception as e:
            return StorageResult.error_result(str(e))

    async def update(self, entity_id: str, entity: T) -> StorageResult[T]:
        """Update an existing entity in file storage"""
        try:
            data = self._read_data()
            if entity_id not in data:
                return StorageResult.error_result(f"Entity not found: {entity_id}")

            # Ensure ID matches
            entity.id = entity_id

            # Update timestamp
            if hasattr(entity, 'updated_at'):
                entity.updated_at = datetime.utcnow()

            # Store the entity
            data[entity_id] = entity.dict()
            self._write_data(data)

            return StorageResult.success_result(entity)
        except Exception as e:
            return StorageResult.error_result(str(e))

    async def delete(self, entity_id: str) -> StorageResult[bool]:
        """Delete an entity by ID from file storage"""
        try:
            data = self._read_data()
            if entity_id not in data:
                return StorageResult.error_result(f"Entity not found: {entity_id}")

            del data[entity_id]
            self._write_data(data)

            return StorageResult.success_result(True)
        except Exception as e:
            return StorageResult.error_result(str(e))

    async def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: Optional[str] = None,
        sort_desc: bool = False
    ) -> StorageResult[List[T]]:
        """List entities from file storage with filtering and pagination"""
        try:
            data = self._read_data()
            entities = [self.entity_type(**entity_dict) for entity_dict in data.values()]

            # Apply filters
            if filters:
                entities = [
                    entity for entity in entities
                    if self._matches_filters(entity, filters)
                ]

            # Apply sorting
            if sort_by and hasattr(entities[0] if entities else None, sort_by):
                reverse = sort_desc
                entities.sort(
                    key=lambda x: getattr(x, sort_by),
                    reverse=reverse
                )

            # Apply pagination
            total_count = len(entities)
            paginated_entities = entities[offset:offset + limit]

            return StorageResult.list_result(paginated_entities, total_count)
        except Exception as e:
            return StorageResult.error_result(str(e))

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> StorageResult[int]:
        """Count entities matching filters"""
        try:
            data = self._read_data()
            if not filters:
                return StorageResult.success_result(len(data))

            entities = [self.entity_type(**entity_dict) for entity_dict in data.values()]
            count = sum(
                1 for entity in entities
                if self._matches_filters(entity, filters)
            )
            return StorageResult.success_result(count)
        except Exception as e:
            return StorageResult.error_result(str(e))

    async def exists(self, entity_id: str) -> StorageResult[bool]:
        """Check if entity exists in file storage"""
        try:
            data = self._read_data()
            exists = entity_id in data
            return StorageResult.success_result(exists)
        except Exception as e:
            return StorageResult.error_result(str(e))

    async def health_check(self) -> StorageResult[bool]:
        """Check file storage health"""
        try:
            # Check if file exists and is readable/writable
            self._ensure_file_exists()
            with open(self.file_path, 'r') as f:
                json.load(f)
            return StorageResult.success_result(True)
        except Exception as e:
            return StorageResult.error_result(str(e))

    def _matches_filters(self, entity: T, filters: Dict[str, Any]) -> bool:
        """Check if entity matches all filters"""
        for field, value in filters.items():
            if not hasattr(entity, field):
                return False
            if getattr(entity, field) != value:
                return False
        return True


class StorageFactory:
    """Factory for creating storage adapters"""

    @staticmethod
    def create_storage(
        storage_type: str,
        entity_type: type[T],
        **kwargs
    ) -> StorageAdapter[T]:
        """Create a storage adapter based on type"""
        if storage_type == "memory":
            return InMemoryStorageAdapter(entity_type)
        elif storage_type == "file":
            file_path = kwargs.get('file_path', './data')
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            return FileStorageAdapter(entity_type, file_path)
        elif storage_type == "sqlite":
            # Would implement SQLite adapter
            raise NotImplementedError("SQLite adapter not yet implemented")
        elif storage_type == "postgresql":
            # Would implement PostgreSQL adapter
            raise NotImplementedError("PostgreSQL adapter not yet implemented")
        elif storage_type == "mongodb":
            # Would implement MongoDB adapter
            raise NotImplementedError("MongoDB adapter not yet implemented")
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")


# Export public interface
__all__ = [
    "BaseEntity",
    "StorageResult",
    "StorageAdapter",
    "InMemoryStorageAdapter",
    "FileStorageAdapter",
    "StorageFactory"
]