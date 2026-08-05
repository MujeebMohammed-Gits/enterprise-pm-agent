"""
Tests for the storage abstraction layer
"""
import asyncio
import tempfile
import os
from datetime import datetime
from pydantic import Field

from persistence.storage import (
    BaseEntity,
    StorageFactory,
    StorageResult
)


class TestItem(BaseEntity):
    """Test entity for storage tests"""
    name: str = Field(...)
    description: Optional[str] = None
    is_active: bool = True


async def test_in_memory_storage():
    """Test in-memory storage adapter"""
    print("Testing in-memory storage...")

    # Create storage adapter
    storage = StorageFactory.create_storage(
        "memory",
        TestItem
    )

    # Test health check
    health = await storage.health_check()
    assert health.success, f"Health check failed: {health.error}"
    assert health.data == True, "Health check should return True"
    print("✅ Health check passed")

    # Test create
    item = TestItem(name="Test Item", description="A test item")
    create_result = await storage.create(item)
    assert create_result.success, f"Create failed: {create_result.error}"
    assert create_result.data is not None, "Created item should not be None"
    assert create_result.data.name == "Test Item", "Name should match"
    assert create_result.data.id is not None, "ID should be generated"
    item_id = create_result.data.id
    print("✅ Create test passed")

    # Test get by ID
    get_result = await storage.get_by_id(item_id)
    assert get_result.success, f"Get failed: {get_result.error}"
    assert get_result.data is not None, "Retrieved item should not be None"
    assert get_result.data.name == "Test Item", "Name should match"
    assert get_result.data.id == item_id, "ID should match"
    print("✅ Get by ID test passed")

    # Test update
    update_item = TestItem(
        id=item_id,
        name="Updated Item",
        description="An updated item"
    )
    update_result = await storage.update(item_id, update_item)
    assert update_result.success, f"Update failed: {update_result.error}"
    assert update_result.data is not None, "Updated item should not be None"
    assert update_result.data.name == "Updated Item", "Name should be updated"
    print("✅ Update test passed")

    # Test list
    list_result = await storage.list()
    assert list_result.success, f"List failed: {list_result.error}"
    assert list_result.data is not None, "List data should not be None"
    assert len(list_result.data) == 1, "Should have one item"
    assert list_result.total_count == 1, "Total count should be 1"
    print("✅ List test passed")

    # Test count
    count_result = await storage.count()
    assert count_result.success, f"Count failed: {count_result.error}"
    assert count_result.data == 1, "Count should be 1"
    print("✅ Count test passed")

    # Test exists
    exists_result = await storage.exists(item_id)
    assert exists_result.success, f"Exists failed: {exists_result.error}"
    assert exists_result.data == True, "Should exist"
    print("✅ Exists test passed")

    # Test delete
    delete_result = await storage.delete(item_id)
    assert delete_result.success, f"Delete failed: {delete_result.error}"
    assert delete_result.data == True, "Delete should return True"
    print("✅ Delete test passed")

    # Verify deletion
    get_after_delete = await storage.get_by_id(item_id)
    assert not get_after_delete.success, "Should not find deleted item"
    assert "not found" in get_after_delete.error.lower(), "Error should indicate not found"
    print("✅ Delete verification passed")


async def test_file_storage():
    """Test file-based storage adapter"""
    print("\nTesting file storage...")

    # Create temporary file for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = f.name

    try:
        # Create storage adapter
        storage = StorageFactory.create_storage(
            "file",
            TestItem,
            file_path=temp_file
        )

        # Test health check
        health = await storage.health_check()
        assert health.success, f"Health check failed: {health.error}"
        assert health.data == True, "Health check should return True"
        print("✅ Health check passed")

        # Test create
        item = TestItem(name="File Test Item", description="A file test item")
        create_result = await storage.create(item)
        assert create_result.success, f"Create failed: {create_result.error}"
        assert create_result.data is not None, "Created item should not be None"
        item_id = create_result.data.id
        print("✅ Create test passed")

        # Test get by ID
        get_result = await storage.get_by_id(item_id)
        assert get_result.success, f"Get failed: {get_result.error}"
        assert get_result.data is not None, "Retrieved item should not be None"
        assert get_result.data.name == "File Test Item", "Name should match"
        assert get_result.data.id == item_id, "ID should match"
        print("✅ Get by ID test passed")

        # Test file persistence by creating new storage instance
        storage2 = StorageFactory.create_storage(
            "file",
            TestItem,
            file_path=temp_file
        )

        get_result2 = await storage2.get_by_id(item_id)
        assert get_result2.success, f"Get from new instance failed: {get_result2.error}"
        assert get_result2.data is not None, "Retrieved item should not be None"
        assert get_result2.data.name == "File Test Item", "Name should persist"
        print("✅ File persistence test passed")

    finally:
        # Clean up temporary file
        if os.path.exists(temp_file):
            os.unlink(temp_file)

    print("✅ File storage tests completed")


async def run_storage_tests():
    """Run all storage tests"""
    print("Running storage tests...\n")

    await test_in_memory_storage()
    await test_file_storage()

    print("\n🎉 All storage tests passed!")


if __name__ == "__main__":
    asyncio.run(run_storage_tests())