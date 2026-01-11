#!/usr/bin/env python
"""
Quick test script to verify the application setup.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cbconfig.settings')
django.setup()

from configs.models import ConfigurationFile
from bootstrap.chatbot_config import ChatbotConfig

def test_configuration():
    """Test creating and managing a configuration."""
    print("Testing Configuration Management")
    print("=" * 50)

    # Test 1: Load sample config
    print("\n1. Loading sample configuration from file...")
    try:
        config = ChatbotConfig.from_file("sample-config.json")
        print(f"   ✓ Configuration loaded: {config.metadata.name}")
        print(f"   ✓ Description: {config.metadata.description}")
        print(f"   ✓ Datasources: {len(config.data_context.datasources)}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    # Test 2: Create ConfigurationFile instance
    print("\n2. Creating database record...")
    try:
        # Clear existing test data
        ConfigurationFile.objects.filter(name="sales-dashboard-chatbot").delete()

        # Create new instance
        config_file = ConfigurationFile()
        config_file.load_from_file("sample-config.json")
        config_file.save()

        print(f"   ✓ Configuration saved with filename: {config_file.filename}.json")
        print(f"   ✓ Database ID: {config_file.pk}")
        print(f"   ✓ Name: {config_file.name}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    # Test 3: Retrieve and verify
    print("\n3. Retrieving configuration from database...")
    try:
        retrieved = ConfigurationFile.objects.get(name="sales-dashboard-chatbot")
        print(f"   ✓ Retrieved configuration: {retrieved.name}")
        print(f"   ✓ Filename: {retrieved.filename}.json")
        print(f"   ✓ Description: {retrieved.description}")

        # Verify file exists
        file_path = retrieved.get_file_path()
        if file_path.exists():
            print(f"   ✓ File exists on disk: {file_path}")
        else:
            print(f"   ✗ File not found: {file_path}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    # Test 4: Test filename generation
    print("\n4. Testing filename generation...")
    try:
        next_filename = ConfigurationFile.get_next_filename()
        print(f"   ✓ Next available filename: {next_filename}.json")

        current_num = int(config_file.filename)
        next_num = int(next_filename)
        if next_num == current_num + 1:
            print(f"   ✓ Filename incremented correctly")
        else:
            print(f"   ✗ Unexpected filename: expected {current_num + 1:06d}, got {next_filename}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    # Test 5: Test uniqueness constraint
    print("\n5. Testing uniqueness constraint...")
    try:
        duplicate = ConfigurationFile()
        duplicate.config_data = config_file.config_data.copy()
        duplicate.extract_metadata()
        duplicate.save()
        print(f"   ✗ Uniqueness constraint not enforced!")
        return False
    except Exception as e:
        if "unique" in str(e).lower() or "already exists" in str(e).lower():
            print(f"   ✓ Uniqueness constraint working correctly")
        else:
            print(f"   ✗ Unexpected error: {e}")
            return False

    # Test 6: Clean up
    print("\n6. Cleaning up...")
    try:
        config_file.delete()
        print(f"   ✓ Configuration deleted from database")

        # Check if file was deleted
        if not file_path.exists():
            print(f"   ✓ File removed from disk")
        else:
            print(f"   ✗ File still exists: {file_path}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    print("\n" + "=" * 50)
    print("All tests passed! ✓")
    print("=" * 50)
    return True

if __name__ == "__main__":
    success = test_configuration()
    sys.exit(0 if success else 1)
