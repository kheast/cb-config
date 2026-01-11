#!/usr/bin/env python
"""
Test script to verify the new form-based configuration interface.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cbconfig.settings')
django.setup()

from configs.models import ConfigurationFile
from configs.forms import ConfigurationFileForm


def test_form():
    """Test the new form interface."""
    print("Testing Form-Based Configuration Interface")
    print("=" * 50)

    # Clean up any existing test data
    ConfigurationFile.objects.filter(name__startswith="test-").delete()

    # Test 1: Create configuration using form data
    print("\n1. Testing form creation with individual fields...")
    form_data = {
        'config_name': 'test-sales-assistant',
        'config_description': 'Test sales assistant configuration',
        'config_author': 'test@example.com',
        'system_prompt_base': 'You are a helpful sales assistant that helps users analyze their sales data and answer questions about opportunities, pipeline, and revenue.',
        'persona_name': 'Sales Bot',
        'persona_tone': 'professional',
        'persona_verbosity': 'concise',
        'persona_personality_traits': 'data-driven, helpful, analytical',
        'response_guidelines': 'Always cite data sources\nUse business terminology\nFormat numbers clearly',
        'include_current_date': True,
        'include_fiscal_period': True,
        'include_user_role': False,
        'include_dashboard_context': True,
        'datasources_json': '''[
            {
                "name": "Sales Data",
                "portal_datasource_id": "ds-001",
                "description": "Salesforce opportunities",
                "primary_entity": "Opportunity",
                "refresh_frequency": "hourly"
            }
        ]''',
        'business_terms_json': '''{
            "ARR": "Annual Recurring Revenue",
            "MRR": "Monthly Recurring Revenue"
        }''',
        'field_mappings_json': '{}',
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

    # Save the form
    try:
        config = form.save()
        print(f"   ✓ Configuration saved: {config.name}")
        print(f"   ✓ Filename: {config.filename}.json")
        print(f"   ✓ File exists: {config.get_file_path().exists()}")
    except Exception as e:
        print(f"   ✗ Error saving: {e}")
        return False

    # Test 2: Verify the config_data was built correctly
    print("\n2. Verifying config_data structure...")
    try:
        assert 'metadata' in config.config_data
        assert 'data_context' in config.config_data
        assert 'system_prompt' in config.config_data
        assert 'llm_parameters' in config.config_data
        assert 'conversation_memory' in config.config_data

        assert config.config_data['metadata']['name'] == 'test-sales-assistant'
        assert config.config_data['system_prompt']['base_prompt'].startswith('You are a helpful')
        assert config.config_data['system_prompt']['persona']['name'] == 'Sales Bot'
        assert len(config.config_data['system_prompt']['persona']['personality_traits']) == 3
        assert len(config.config_data['system_prompt']['response_guidelines']) == 3
        assert len(config.config_data['data_context']['datasources']) == 1
        assert config.config_data['llm_parameters']['model'] == 'claude-sonnet-4-20250514'

        print("   ✓ Config data structure is correct")
        print(f"   ✓ Metadata: {config.config_data['metadata']['name']}")
        print(f"   ✓ Persona name: {config.config_data['system_prompt']['persona']['name']}")
        print(f"   ✓ Datasources: {len(config.config_data['data_context']['datasources'])}")
        print(f"   ✓ Model: {config.config_data['llm_parameters']['model']}")
    except AssertionError as e:
        print(f"   ✗ Structure validation failed: {e}")
        return False
    except KeyError as e:
        print(f"   ✗ Missing key in config_data: {e}")
        return False

    # Test 3: Edit the configuration
    print("\n3. Testing form editing...")
    try:
        # Load the config into a form for editing
        edit_form = ConfigurationFileForm(instance=config)

        # Verify fields are populated from config_data
        assert edit_form.fields['config_name'].initial == 'test-sales-assistant'
        assert edit_form.fields['persona_name'].initial == 'Sales Bot'
        assert 'data-driven' in edit_form.fields['persona_personality_traits'].initial

        print("   ✓ Form populated from existing config_data")

        # Update some fields
        edit_data = form_data.copy()
        edit_data['persona_name'] = 'Sales Assistant Pro'
        edit_data['llm_temperature'] = 0.5

        edit_form = ConfigurationFileForm(data=edit_data, instance=config)
        if not edit_form.is_valid():
            print(f"   ✗ Edit form validation failed: {edit_form.errors}")
            return False

        updated_config = edit_form.save()
        assert updated_config.config_data['system_prompt']['persona']['name'] == 'Sales Assistant Pro'
        assert updated_config.config_data['llm_parameters']['temperature'] == 0.5

        print("   ✓ Configuration updated successfully")
        print(f"   ✓ New persona name: {updated_config.config_data['system_prompt']['persona']['name']}")
        print(f"   ✓ New temperature: {updated_config.config_data['llm_parameters']['temperature']}")
    except Exception as e:
        print(f"   ✗ Error editing: {e}")
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
        print(f"   ✓ System prompt: {chatbot_config.system_prompt.base_prompt[:50]}...")
    except Exception as e:
        print(f"   ✗ Pydantic validation failed: {e}")
        return False

    # Test 5: Clean up
    print("\n5. Cleaning up...")
    try:
        file_path = config.get_file_path()
        config.delete()

        assert not ConfigurationFile.objects.filter(name='test-sales-assistant').exists()
        assert not file_path.exists()

        print("   ✓ Configuration deleted successfully")
    except Exception as e:
        print(f"   ✗ Error cleaning up: {e}")
        return False

    print("\n" + "=" * 50)
    print("All form tests passed! ✓")
    print("=" * 50)
    return True


if __name__ == "__main__":
    success = test_form()
    sys.exit(0 if success else 1)
