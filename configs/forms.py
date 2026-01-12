"""
Custom forms for chatbot configuration management.
"""
from django import forms
from django.core.exceptions import ValidationError
from .models import ConfigurationFile
import json


class ConfigurationFileForm(forms.ModelForm):
    """
    Custom form that breaks out individual configuration fields for editing.
    """

    # Metadata fields
    config_name = forms.CharField(
        max_length=100,
        label="Configuration Name",
        help_text="Unique identifier (kebab-case, e.g., 'sales-dashboard')"
    )
    config_description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'cols': 80}),
        label="Description",
        help_text="What this configuration is for"
    )
    config_author = forms.CharField(
        max_length=200,
        label="Author",
        help_text="Your name or email"
    )

    # LLM Credentials
    llm_provider = forms.ChoiceField(
        choices=[
            ('anthropic_bedrock', 'Anthropic Bedrock (AWS)'),
            ('openai', 'OpenAI'),
        ],
        initial='anthropic_bedrock',
        label="LLM Provider",
        help_text="Select the LLM provider"
    )

    # AWS Bedrock credentials (shown when provider is anthropic_bedrock)
    aws_access_key_id = forms.CharField(
        max_length=200,
        required=False,
        label="AWS Access Key ID",
        help_text="AWS Access Key ID for Bedrock"
    )
    aws_secret_access_key = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.PasswordInput(render_value=True),
        label="AWS Secret Access Key",
        help_text="AWS Secret Access Key for Bedrock"
    )
    aws_region = forms.CharField(
        max_length=50,
        initial="us-east-1",
        required=False,
        label="AWS Region",
        help_text="AWS Region for Bedrock"
    )

    # OpenAI credentials (shown when provider is openai)
    openai_api_key = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.PasswordInput(render_value=True),
        label="OpenAI API Key",
        help_text="OpenAI API Key"
    )
    openai_organization_id = forms.CharField(
        max_length=200,
        required=False,
        label="OpenAI Organization ID",
        help_text="OpenAI Organization ID (optional)"
    )

    # System Prompt - Base
    system_prompt_base = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 10, 'cols': 80}),
        label="System Prompt",
        help_text="The core system prompt text (50-10000 characters)"
    )

    # System Prompt - Persona
    persona_name = forms.CharField(
        max_length=100,
        initial="Assistant",
        label="Persona Name",
        help_text="Display name for the chatbot"
    )
    persona_tone = forms.CharField(
        max_length=200,
        initial="professional but approachable",
        label="Persona Tone",
        help_text="Communication tone"
    )
    persona_verbosity = forms.ChoiceField(
        choices=[
            ('concise', 'Concise'),
            ('moderate', 'Moderate'),
            ('detailed', 'Detailed'),
        ],
        initial='concise',
        label="Verbosity",
        help_text="Response length preference"
    )
    persona_personality_traits = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'cols': 80}),
        required=False,
        label="Personality Traits",
        help_text="Comma-separated list of behavioral characteristics"
    )

    # Response guidelines
    response_guidelines = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5, 'cols': 80}),
        required=False,
        label="Response Guidelines",
        help_text="One guideline per line - rules for formatting and structuring responses"
    )

    # Context Injection
    include_current_date = forms.BooleanField(
        initial=True,
        required=False,
        label="Include Current Date",
        help_text="Include today's date in context"
    )
    include_fiscal_period = forms.BooleanField(
        initial=True,
        required=False,
        label="Include Fiscal Period",
        help_text="Include current fiscal period info"
    )
    include_user_role = forms.BooleanField(
        initial=False,
        required=False,
        label="Include User Role",
        help_text="Include user's role/permissions context"
    )
    include_dashboard_context = forms.BooleanField(
        initial=True,
        required=False,
        label="Include Dashboard Context",
        help_text="Include information about the current dashboard"
    )

    # Note: Datasources, Business Terms, and Field Mappings are now managed via inline formsets
    # in the admin interface, so no form fields are needed for them here.

    # LLM Parameters
    llm_model = forms.CharField(
        max_length=100,
        initial="claude-sonnet-4-20250514",
        label="LLM Model",
        help_text="Model identifier (e.g., claude-sonnet-4-20250514)"
    )
    llm_temperature = forms.FloatField(
        min_value=0.0,
        max_value=1.0,
        initial=0.3,
        label="Temperature",
        help_text="Sampling temperature (0.0-1.0)"
    )
    llm_max_tokens = forms.IntegerField(
        min_value=100,
        max_value=8192,
        initial=1024,
        label="Max Tokens",
        help_text="Maximum tokens in response"
    )
    llm_top_p = forms.FloatField(
        min_value=0.0,
        max_value=1.0,
        initial=0.9,
        label="Top P",
        help_text="Nucleus sampling parameter"
    )

    # Conversation Memory
    memory_enabled = forms.BooleanField(
        initial=True,
        required=False,
        label="Memory Enabled",
        help_text="Whether conversation memory is enabled"
    )
    memory_max_turns = forms.IntegerField(
        min_value=1,
        max_value=50,
        initial=10,
        label="Max Turns",
        help_text="Maximum conversation turns to retain"
    )
    memory_summarize_after_turns = forms.IntegerField(
        min_value=1,
        max_value=50,
        initial=8,
        label="Summarize After Turns",
        help_text="Summarize context after this many turns"
    )

    # Advanced Configuration (JSON for complex nested structures)
    advanced_config_json = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 15,
            'cols': 80,
            'style': 'font-family: monospace; font-size: 12px;'
        }),
        required=False,
        label="Advanced Configuration",
        help_text="JSON for advanced settings: guardrails, MCP tools, dashboard integration, etc."
    )

    # File format field
    file_format = forms.ChoiceField(
        choices=[
            ('json', 'JSON'),
            ('yaml', 'YAML'),
        ],
        initial='json',
        label="File Format",
        help_text="Choose JSON or YAML format for the configuration file"
    )

    class Meta:
        model = ConfigurationFile
        fields = ['config_name', 'config_description', 'config_author', 'file_format']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If editing existing instance, populate form fields from config_data
        if self.instance and self.instance.pk and self.instance.config_data:
            self._populate_from_config_data()
            # Also populate file_format
            self.fields['file_format'].initial = self.instance.file_format

    def _populate_from_config_data(self):
        """Populate form fields from existing config_data."""
        config = self.instance.config_data

        # Metadata
        metadata = config.get('metadata', {})
        self.fields['config_name'].initial = metadata.get('name', '')
        self.fields['config_description'].initial = metadata.get('description', '')
        self.fields['config_author'].initial = metadata.get('author', '')

        # LLM Credentials
        llm_credentials = config.get('llm_credentials', {})
        if 'anthropic_bedrock' in llm_credentials and llm_credentials['anthropic_bedrock']:
            self.fields['llm_provider'].initial = 'anthropic_bedrock'
            bedrock = llm_credentials['anthropic_bedrock']
            self.fields['aws_access_key_id'].initial = bedrock.get('aws_access_key_id', '')
            self.fields['aws_secret_access_key'].initial = bedrock.get('aws_secret_access_key', '')
            self.fields['aws_region'].initial = bedrock.get('aws_region', 'us-east-1')
        elif 'openai' in llm_credentials and llm_credentials['openai']:
            self.fields['llm_provider'].initial = 'openai'
            openai = llm_credentials['openai']
            self.fields['openai_api_key'].initial = openai.get('api_key', '')
            self.fields['openai_organization_id'].initial = openai.get('organization_id', '')

        # System Prompt
        system_prompt = config.get('system_prompt', {})
        self.fields['system_prompt_base'].initial = system_prompt.get('base_prompt', '')

        # Persona
        persona = system_prompt.get('persona', {})
        self.fields['persona_name'].initial = persona.get('name', 'Assistant')
        self.fields['persona_tone'].initial = persona.get('tone', 'professional but approachable')
        self.fields['persona_verbosity'].initial = persona.get('verbosity', 'concise')
        traits = persona.get('personality_traits', [])
        self.fields['persona_personality_traits'].initial = ', '.join(traits) if traits else ''

        # Response Guidelines
        guidelines = system_prompt.get('response_guidelines', [])
        self.fields['response_guidelines'].initial = '\n'.join(guidelines) if guidelines else ''

        # Context Injection
        context_injection = system_prompt.get('context_injection', {})
        self.fields['include_current_date'].initial = context_injection.get('include_current_date', True)
        self.fields['include_fiscal_period'].initial = context_injection.get('include_fiscal_period', True)
        self.fields['include_user_role'].initial = context_injection.get('include_user_role', False)
        self.fields['include_dashboard_context'].initial = context_injection.get('include_dashboard_context', True)

        # Note: Datasources, Business Terms, and Field Mappings are now managed via inline formsets,
        # so we don't populate form fields for them.

        # LLM Parameters
        llm_params = config.get('llm_parameters', {})
        self.fields['llm_model'].initial = llm_params.get('model', 'claude-sonnet-4-20250514')
        self.fields['llm_temperature'].initial = llm_params.get('temperature', 0.3)
        self.fields['llm_max_tokens'].initial = llm_params.get('max_tokens', 1024)
        self.fields['llm_top_p'].initial = llm_params.get('top_p', 0.9)

        # Conversation Memory
        memory = config.get('conversation_memory', {})
        self.fields['memory_enabled'].initial = memory.get('enabled', True)
        self.fields['memory_max_turns'].initial = memory.get('max_turns', 10)
        self.fields['memory_summarize_after_turns'].initial = memory.get('summarize_after_turns', 8)

        # Advanced config (everything else)
        advanced = {
            'guardrails': config.get('guardrails', {}),
            'structured_output': config.get('structured_output', {}),
            'mcp_tools': config.get('mcp_tools', {}),
            'mcp_resources': config.get('mcp_resources', {}),
            'elicitation': config.get('elicitation', {}),  # Changed from mcp_elicitation
            'dashboard_integration': config.get('dashboard_integration', {}),
            'logging': config.get('logging', {}),
        }
        # Remove empty sections
        advanced = {k: v for k, v in advanced.items() if v}
        self.fields['advanced_config_json'].initial = json.dumps(advanced, indent=2) if advanced else '{}'

    # Note: Datasources, Business Terms, and Field Mappings validation removed
    # since they're now managed via inline formsets

    def clean_advanced_config_json(self):
        """Validate advanced config JSON."""
        data = self.cleaned_data['advanced_config_json']
        if not data or data.strip() == '':
            return '{}'
        try:
            config = json.loads(data)
            if not isinstance(config, dict):
                raise ValidationError("Advanced config must be a JSON object")
            return data
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {e}")

    def _post_clean(self):
        """
        Override _post_clean to set config_data on instance before model validation.
        This is called after form.clean() but before model.full_clean().
        """
        # Set config_data on the instance so model validation can use it
        if hasattr(self, 'cleaned_data') and 'config_data' in self.cleaned_data:
            self.instance.config_data = self.cleaned_data['config_data']
            self.instance.extract_metadata()

        # Now call parent _post_clean which will trigger model.full_clean()
        super()._post_clean()

    def clean(self):
        """Build the complete config_data from individual fields."""
        cleaned_data = super().clean()

        # Validate LLM credentials based on provider
        provider = cleaned_data.get('llm_provider')
        if provider == 'anthropic_bedrock':
            if not cleaned_data.get('aws_access_key_id'):
                self.add_error('aws_access_key_id', 'AWS Access Key ID is required for Bedrock')
            if not cleaned_data.get('aws_secret_access_key'):
                self.add_error('aws_secret_access_key', 'AWS Secret Access Key is required for Bedrock')
            if not cleaned_data.get('aws_region'):
                self.add_error('aws_region', 'AWS Region is required for Bedrock')
        elif provider == 'openai':
            if not cleaned_data.get('openai_api_key'):
                self.add_error('openai_api_key', 'OpenAI API Key is required for OpenAI')

        # Build the complete configuration
        from datetime import datetime

        # Parse JSON fields (only advanced config now)
        advanced_config = json.loads(cleaned_data.get('advanced_config_json', '{}'))

        # Note: datasources, business_terms, and field_mappings are handled by inline formsets
        # and will be synced to config_data separately via sync_related_to_config_data()

        # Parse personality traits and guidelines
        traits_text = cleaned_data.get('persona_personality_traits', '')
        personality_traits = [t.strip() for t in traits_text.split(',') if t.strip()] if traits_text else []

        guidelines_text = cleaned_data.get('response_guidelines', '')
        response_guidelines = [g.strip() for g in guidelines_text.split('\n') if g.strip()] if guidelines_text else []

        # Get existing timestamps if editing, otherwise create new ones
        now = datetime.utcnow().isoformat() + 'Z'
        if self.instance and self.instance.pk and self.instance.config_data:
            created = self.instance.config_data.get('metadata', {}).get('created', now)
        else:
            created = now

        # Build LLM credentials section
        llm_credentials = {}
        provider = cleaned_data.get('llm_provider')
        if provider == 'anthropic_bedrock':
            llm_credentials['anthropic_bedrock'] = {
                'aws_access_key_id': cleaned_data.get('aws_access_key_id', ''),
                'aws_secret_access_key': cleaned_data.get('aws_secret_access_key', ''),
                'aws_region': cleaned_data.get('aws_region', 'us-east-1'),
            }
        elif provider == 'openai':
            openai_creds = {
                'api_key': cleaned_data.get('openai_api_key', ''),
            }
            if cleaned_data.get('openai_organization_id'):
                openai_creds['organization_id'] = cleaned_data.get('openai_organization_id')
            llm_credentials['openai'] = openai_creds

        # Build complete config_data
        # Note: datasources, business_terms, and field_mappings will be populated
        # by sync_related_to_config_data() after the related objects are saved
        config_data = {
            "version": "1.0.0",
            "metadata": {
                "name": cleaned_data.get('config_name', ''),
                "description": cleaned_data.get('config_description', ''),
                "created": created,
                "modified": now,
                "author": cleaned_data.get('config_author', ''),
            },
            "llm_credentials": llm_credentials,
            "data_context": {
                "datasources": [],  # Will be populated from inline formset
                "semantic_layer": {
                    "business_terms": {},  # Will be populated from inline formset
                    "field_mappings": {},  # Will be populated from inline formset
                },
            },
            "system_prompt": {
                "base_prompt": cleaned_data.get('system_prompt_base', ''),
                "persona": {
                    "name": cleaned_data.get('persona_name', 'Assistant'),
                    "tone": cleaned_data.get('persona_tone', 'professional but approachable'),
                    "verbosity": cleaned_data.get('persona_verbosity', 'concise'),
                    "personality_traits": personality_traits,
                },
                "response_guidelines": response_guidelines,
                "context_injection": {
                    "include_current_date": cleaned_data.get('include_current_date', True),
                    "include_fiscal_period": cleaned_data.get('include_fiscal_period', True),
                    "include_user_role": cleaned_data.get('include_user_role', False),
                    "include_dashboard_context": cleaned_data.get('include_dashboard_context', True),
                },
            },
            "llm_parameters": {
                "model": cleaned_data.get('llm_model', 'claude-sonnet-4-20250514'),
                "temperature": cleaned_data.get('llm_temperature', 0.3),
                "max_tokens": cleaned_data.get('llm_max_tokens', 1024),
                "top_p": cleaned_data.get('llm_top_p', 0.9),
            },
            "conversation_memory": {
                "enabled": cleaned_data.get('memory_enabled', True),
                "max_turns": cleaned_data.get('memory_max_turns', 10),
                "summarize_after_turns": cleaned_data.get('memory_summarize_after_turns', 8),
            },
        }

        # Merge advanced config
        config_data.update(advanced_config)

        # Store in cleaned_data for the model
        cleaned_data['config_data'] = config_data

        # Also update the visible fields for consistency
        cleaned_data['name'] = cleaned_data.get('config_name', '')
        cleaned_data['description'] = cleaned_data.get('config_description', '')
        cleaned_data['author'] = cleaned_data.get('config_author', '')

        return cleaned_data

    def save(self, commit=True):
        """Save the configuration with the built config_data."""
        from .models import BedrockCredentials, OpenAICredentials, LLMCredentials

        # Don't call super().save() yet - we need to set config_data first
        instance = self.instance

        # Set config_data from cleaned_data BEFORE validation
        instance.config_data = self.cleaned_data['config_data']

        # Set file format
        instance.file_format = self.cleaned_data.get('file_format', 'json')

        # Extract metadata to model fields
        instance.extract_metadata()

        # Handle LLM credentials - create or update the LLM credentials objects
        provider = self.cleaned_data.get('llm_provider')

        # If editing existing config with llm_credentials, delete old ones
        if instance.pk and instance.llm_credentials:
            old_creds = instance.llm_credentials
            instance.llm_credentials = None
            instance.save(skip_file_save=True)
            if old_creds.anthropic_bedrock:
                old_creds.anthropic_bedrock.delete()
            if old_creds.openai:
                old_creds.openai.delete()
            old_creds.delete()

        # Create new LLM credentials
        if provider == 'anthropic_bedrock':
            bedrock_creds = BedrockCredentials.objects.create(
                aws_access_key_id=self.cleaned_data.get('aws_access_key_id', ''),
                aws_secret_access_key=self.cleaned_data.get('aws_secret_access_key', ''),
                aws_region=self.cleaned_data.get('aws_region', 'us-east-1'),
            )
            llm_creds = LLMCredentials.objects.create(
                provider='anthropic_bedrock',
                anthropic_bedrock=bedrock_creds,
            )
            instance.llm_credentials = llm_creds
        elif provider == 'openai':
            openai_creds = OpenAICredentials.objects.create(
                api_key=self.cleaned_data.get('openai_api_key', ''),
                organization_id=self.cleaned_data.get('openai_organization_id') or None,
            )
            llm_creds = LLMCredentials.objects.create(
                provider='openai',
                openai=openai_creds,
            )
            instance.llm_credentials = llm_creds

        # Now validate and save
        if commit:
            instance.save()

        return instance
