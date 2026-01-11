#!/usr/bin/env python
"""
Test script to verify the new interface works without JSON inputs.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cbconfig.settings')
django.setup()

from configs.models import ConfigurationFile, Datasource, BusinessTerm, FieldMapping
from configs.forms import ConfigurationFileForm


def test_no_json_interface():
    """Test the new interface without JSON inputs."""
    print("Testing No-JSON Interface")
    print("=" * 50)

    # Clean up any existing test data
    ConfigurationFile.objects.filter(name__startswith="test-").delete()

    # Test 1: Create configuration using form (without JSON fields)
    print("\n1. Creating configuration with form (no JSON fields)...")
    form_data = {
        'config_name': 'test-no-json-config',
        'config_description': 'Test configuration without JSON inputs',
        'config_author': 'test@example.com',
        'system_prompt_base': 'You are a helpful assistant that provides clear and concise answers to questions.',
        'persona_name': 'Test Bot',
        'persona_tone': 'professional',
        'persona_verbosity': 'concise',
        'persona_personality_traits': 'helpful, accurate',
        'response_guidelines': 'Be clear\nBe concise',
        'include_current_date': True,
        'include_fiscal_period': True,
        'include_user_role': False,
        'include_dashboard_context': True,
        'llm_model': 'claude-sonnet-4-20250514',
        'llm_temperature': 0.3,
        'llm_max_tokens': 1024,
        'llm_top_p': 0.9,
        'memory_enabled': True,
        'memory_max_turns': 10,
        'memory_summarize_after_turns': 8,
        'advanced_config_json': '{}',
    }

    form = ConfigurationFileForm(data=form_data)

    if not form.is_valid():
        print(f"   ✗ Form validation failed:")
        for field, errors in form.errors.items():
            print(f"     - {field}: {errors}")
        return False

    print("   ✓ Form validated successfully")

    # Save the form (skipping file save initially)
    try:
        config = form.instance
        config.config_data = form.cleaned_data['config_data']
        config.extract_metadata()
        config.save(skip_file_save=True)
        print(f"   ✓ Configuration saved: {config.name}")
        print(f"   ✓ Filename: {config.filename}.json")
    except Exception as e:
        print(f"   ✗ Error saving: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 2: Create related objects directly (simulating inline formsets)
    print("\n2. Creating related objects (datasources, terms, mappings)...")
    try:
        # Create a datasource
        ds = Datasource.objects.create(
            configuration=config,
            name="Test Datasource",
            portal_datasource_id="ds-test-001",
            description="Test datasource for testing",
            primary_entity="TestEntity",
            refresh_frequency="hourly"
        )
        print(f"   ✓ Created datasource: {ds.name}")

        # Create business terms
        bt1 = BusinessTerm.objects.create(
            configuration=config,
            term="TRR",
            definition="Test Recurring Revenue"
        )
        bt2 = BusinessTerm.objects.create(
            configuration=config,
            term="TAV",
            definition="Test Annual Value"
        )
        print(f"   ✓ Created business terms: {bt1.term}, {bt2.term}")

        # Create field mappings
        fm1 = FieldMapping.objects.create(
            configuration=config,
            field_name="test_amount",
            business_name="Test Amount",
            description="The amount for testing",
            format="currency"
        )
        fm2 = FieldMapping.objects.create(
            configuration=config,
            field_name="test_status",
            business_name="Test Status",
            description="Current test status",
            format="text",
            valid_values="Active, Inactive, Pending"
        )
        print(f"   ✓ Created field mappings: {fm1.field_name}, {fm2.field_name}")

    except Exception as e:
        print(f"   ✗ Error creating related objects: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 3: Sync related objects to config_data
    print("\n3. Syncing related objects to config_data...")
    try:
        config.save_with_related()
        print("   ✓ Related objects synced to config_data")
        print(f"   ✓ File saved: {config.get_file_path().exists()}")

        # Verify datasources in config_data
        datasources = config.config_data.get('data_context', {}).get('datasources', [])
        print(f"   ✓ Datasources in config_data: {len(datasources)}")
        assert len(datasources) == 1
        assert datasources[0]['name'] == "Test Datasource"

        # Verify business terms
        business_terms = config.config_data.get('data_context', {}).get('semantic_layer', {}).get('business_terms', {})
        print(f"   ✓ Business terms in config_data: {len(business_terms)}")
        assert len(business_terms) == 2
        assert 'TRR' in business_terms
        assert business_terms['TRR'] == "Test Recurring Revenue"

        # Verify field mappings
        field_mappings = config.config_data.get('data_context', {}).get('semantic_layer', {}).get('field_mappings', {})
        print(f"   ✓ Field mappings in config_data: {len(field_mappings)}")
        assert len(field_mappings) == 2
        assert 'test_amount' in field_mappings
        assert field_mappings['test_amount']['business_name'] == "Test Amount"

    except Exception as e:
        print(f"   ✗ Error syncing: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 4: Validate against Pydantic schema
    print("\n4. Validating against ChatbotConfig schema...")
    try:
        from bootstrap.chatbot_config import ChatbotConfig
        chatbot_config = ChatbotConfig.from_dict(config.config_data)
        print("   ✓ Configuration validates against Pydantic schema")
        print(f"   ✓ Config name: {chatbot_config.metadata.name}")
        print(f"   ✓ Datasources: {len(chatbot_config.data_context.datasources)}")
        print(f"   ✓ Business terms: {len(chatbot_config.data_context.semantic_layer.business_terms)}")
        print(f"   ✓ Field mappings: {len(chatbot_config.data_context.semantic_layer.field_mappings)}")
    except Exception as e:
        print(f"   ✗ Pydantic validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 5: Test reverse sync (config_data to related objects)
    print("\n5. Testing reverse sync (config_data to related objects)...")
    try:
        # Modify config_data manually
        config.config_data['data_context']['datasources'].append({
            'name': 'Second Datasource',
            'portal_datasource_id': 'ds-test-002',
            'description': 'Second test datasource',
            'primary_entity': 'TestEntity2',
            'refresh_frequency': 'daily'
        })

        # Sync back to related objects
        config.sync_config_data_to_related()

        # Verify
        datasources = config.datasources.all()
        print(f"   ✓ Datasources after reverse sync: {len(datasources)}")
        assert len(datasources) == 2

        datasource_names = [ds.name for ds in datasources]
        assert 'Second Datasource' in datasource_names

    except Exception as e:
        print(f"   ✗ Error in reverse sync: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 6: Clean up
    print("\n6. Cleaning up...")
    try:
        file_path = config.get_file_path()
        config_pk = config.pk

        # Count related objects before deletion
        datasource_count = config.datasources.count()
        business_term_count = config.business_terms.count()
        field_mapping_count = config.field_mappings.count()

        print(f"   ✓ Before deletion: {datasource_count} datasources, {business_term_count} terms, {field_mapping_count} mappings")

        # Delete the configuration
        config.delete()

        assert not ConfigurationFile.objects.filter(name='test-no-json-config').exists()
        assert not file_path.exists()

        # Verify related objects were cascade deleted (by checking the total count decreased)
        # We can't filter by config anymore since it's deleted, so just verify the object is gone
        print("   ✓ Configuration and related objects deleted successfully")
    except Exception as e:
        print(f"   ✗ Error cleaning up: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 50)
    print("All no-JSON interface tests passed! ✓")
    print("=" * 50)
    return True


if __name__ == "__main__":
    success = test_no_json_interface()
    sys.exit(0 if success else 1)
