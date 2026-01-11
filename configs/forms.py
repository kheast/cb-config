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

    # Data Context - Datasources (as JSON for now, can be improved with inline formsets)
    datasources_json = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 10,
            'cols': 80,
            'style': 'font-family: monospace; font-size: 12px;'
        }),
        label="Datasources",
        help_text="JSON array of datasource objects. Must have at least one datasource."
    )

    # Semantic Layer
    business_terms_json = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 8,
            'cols': 80,
            'style': 'font-family: monospace; font-size: 12px;'
        }),
        required=False,
        label="Business Terms",
        help_text="JSON object mapping terms to definitions (e.g., {\"ARR\": \"Annual Recurring Revenue\"})"
    )

    field_mappings_json = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 8,
            'cols': 80,
            'style': 'font-family: monospace; font-size: 12px;'
        }),
        required=False,
        label="Field Mappings",
        help_text="JSON object mapping technical fields to business terminology"
    )

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

    class Meta:
        model = ConfigurationFile
        fields = ['config_name', 'config_description', 'config_author']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If editing existing instance, populate form fields from config_data
        if self.instance and self.instance.pk and self.instance.config_data:
            self._populate_from_config_data()

    def _populate_from_config_data(self):
        """Populate form fields from existing config_data."""
        config = self.instance.config_data

        # Metadata
        metadata = config.get('metadata', {})
        self.fields['config_name'].initial = metadata.get('name', '')
        self.fields['config_description'].initial = metadata.get('description', '')
        self.fields['config_author'].initial = metadata.get('author', '')

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

        # Data Context
        data_context = config.get('data_context', {})
        datasources = data_context.get('datasources', [])
        self.fields['datasources_json'].initial = json.dumps(datasources, indent=2)

        # Semantic Layer
        semantic_layer = data_context.get('semantic_layer', {})
        business_terms = semantic_layer.get('business_terms', {})
        self.fields['business_terms_json'].initial = json.dumps(business_terms, indent=2) if business_terms else '{}'

        field_mappings = semantic_layer.get('field_mappings', {})
        self.fields['field_mappings_json'].initial = json.dumps(field_mappings, indent=2) if field_mappings else '{}'

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
            'mcp_elicitation': config.get('mcp_elicitation', {}),
            'dashboard_integration': config.get('dashboard_integration', {}),
            'logging': config.get('logging', {}),
        }
        # Remove empty sections
        advanced = {k: v for k, v in advanced.items() if v}
        self.fields['advanced_config_json'].initial = json.dumps(advanced, indent=2) if advanced else '{}'

    def clean_datasources_json(self):
        """Validate datasources JSON."""
        data = self.cleaned_data['datasources_json']
        try:
            datasources = json.loads(data)
            if not isinstance(datasources, list):
                raise ValidationError("Datasources must be a JSON array")
            if len(datasources) == 0:
                raise ValidationError("At least one datasource is required")
            return data
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {e}")

    def clean_business_terms_json(self):
        """Validate business terms JSON."""
        data = self.cleaned_data['business_terms_json']
        if not data or data.strip() == '':
            return '{}'
        try:
            terms = json.loads(data)
            if not isinstance(terms, dict):
                raise ValidationError("Business terms must be a JSON object")
            return data
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {e}")

    def clean_field_mappings_json(self):
        """Validate field mappings JSON."""
        data = self.cleaned_data['field_mappings_json']
        if not data or data.strip() == '':
            return '{}'
        try:
            mappings = json.loads(data)
            if not isinstance(mappings, dict):
                raise ValidationError("Field mappings must be a JSON object")
            return data
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {e}")

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

        # Build the complete configuration
        from datetime import datetime

        # Parse JSON fields
        datasources = json.loads(cleaned_data.get('datasources_json', '[]'))
        business_terms = json.loads(cleaned_data.get('business_terms_json', '{}'))
        field_mappings = json.loads(cleaned_data.get('field_mappings_json', '{}'))
        advanced_config = json.loads(cleaned_data.get('advanced_config_json', '{}'))

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

        # Build complete config_data
        config_data = {
            "version": "1.0.0",
            "metadata": {
                "name": cleaned_data.get('config_name', ''),
                "description": cleaned_data.get('config_description', ''),
                "created": created,
                "modified": now,
                "author": cleaned_data.get('config_author', ''),
            },
            "data_context": {
                "datasources": datasources,
                "semantic_layer": {
                    "business_terms": business_terms,
                    "field_mappings": field_mappings,
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
        # Don't call super().save() yet - we need to set config_data first
        instance = self.instance

        # Set config_data from cleaned_data BEFORE validation
        instance.config_data = self.cleaned_data['config_data']

        # Extract metadata to model fields
        instance.extract_metadata()

        # Now validate and save
        if commit:
            instance.save()

        return instance
