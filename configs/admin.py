"""
Django admin configuration for chatbot configurations.
"""
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from .models import ConfigurationFile, Datasource, BusinessTerm, FieldMapping
from .forms import ConfigurationFileForm


class DatasourceInline(admin.TabularInline):
    """Inline admin for datasources."""
    model = Datasource
    extra = 1
    fields = ['name', 'portal_datasource_id', 'description', 'primary_entity', 'refresh_frequency']


class BusinessTermInline(admin.TabularInline):
    """Inline admin for business terms."""
    model = BusinessTerm
    extra = 1
    fields = ['term', 'definition']


class FieldMappingInline(admin.TabularInline):
    """Inline admin for field mappings."""
    model = FieldMapping
    extra = 1
    fields = ['field_name', 'business_name', 'description', 'format', 'valid_values']


@admin.register(ConfigurationFile)
class ConfigurationFileAdmin(admin.ModelAdmin):
    """
    Admin interface for managing chatbot configurations.
    """
    form = ConfigurationFileForm
    inlines = [DatasourceInline, BusinessTermInline, FieldMappingInline]

    list_display = [
        'name',
        'filename_display',
        'description_short',
        'author',
        'created',
        'modified',
    ]

    list_filter = [
        'created',
        'modified',
    ]

    search_fields = [
        'name',
        'description',
        'author',
        'filename',
    ]

    readonly_fields = [
        'filename',
        'created',
        'modified',
        'file_path_display',
    ]

    fieldsets = (
        ('Configuration Identity', {
            'fields': (
                'config_name',
                'config_description',
                'config_author',
            ),
            'description': 'Basic information about this chatbot configuration.'
        }),
        ('System Prompt', {
            'fields': (
                'system_prompt_base',
            ),
            'description': 'The core system prompt that defines the chatbot\'s behavior.'
        }),
        ('Persona Settings', {
            'fields': (
                'persona_name',
                'persona_tone',
                'persona_verbosity',
                'persona_personality_traits',
            ),
            'classes': ('collapse',),
            'description': 'Customize the chatbot\'s personality and communication style.'
        }),
        ('Response Configuration', {
            'fields': (
                'response_guidelines',
                'include_current_date',
                'include_fiscal_period',
                'include_user_role',
                'include_dashboard_context',
            ),
            'classes': ('collapse',),
            'description': 'Configure response formatting and context injection.'
        }),
        ('Data Sources & Semantic Layer', {
            'fields': (),
            'description': 'Data sources, business terms, and field mappings are managed in the sections below this form.'
        }),
        ('LLM Parameters', {
            'fields': (
                'llm_model',
                'llm_temperature',
                'llm_max_tokens',
                'llm_top_p',
            ),
            'classes': ('collapse',),
            'description': 'Configure the language model parameters.'
        }),
        ('Conversation Memory', {
            'fields': (
                'memory_enabled',
                'memory_max_turns',
                'memory_summarize_after_turns',
            ),
            'classes': ('collapse',),
            'description': 'Configure conversation history and memory settings.'
        }),
        ('Advanced Configuration', {
            'fields': (
                'advanced_config_json',
            ),
            'classes': ('collapse',),
            'description': 'Advanced settings including guardrails, MCP tools, dashboard integration, and logging (JSON object).'
        }),
        ('File Information', {
            'fields': (
                'filename',
                'file_path_display',
                'created',
                'modified',
            ),
            'classes': ('collapse',),
            'description': 'File system information (read-only).'
        }),
    )

    actions = ['rename_configuration']

    def filename_display(self, obj):
        """Display the filename with .json extension."""
        return format_html('<code>{}.json</code>', obj.filename)
    filename_display.short_description = 'Filename'

    def description_short(self, obj):
        """Display a shortened description."""
        if len(obj.description) > 100:
            return obj.description[:100] + '...'
        return obj.description
    description_short.short_description = 'Description'

    def file_path_display(self, obj):
        """Display the full file path."""
        return format_html('<code>{}</code>', obj.get_file_path())
    file_path_display.short_description = 'File Path'

    def rename_configuration(self, request, queryset):
        """
        Custom admin action to rename configurations.
        Note: This is a simplified version. For production, you'd want a proper form.
        """
        if queryset.count() != 1:
            self.message_user(
                request,
                "Please select exactly one configuration to rename.",
                level='warning'
            )
            return

        # For now, just inform the user to use the change form
        self.message_user(
            request,
            "To rename a configuration, edit it and change the 'name' field.",
            level='info'
        )

    rename_configuration.short_description = "Rename selected configuration"

    def save_model(self, request, obj, form, change):
        """
        Override save_model to skip file save initially (related objects haven't been saved yet).
        """
        try:
            # Save to database but skip file save (related objects not yet saved)
            obj.save(skip_file_save=True)
        except ValidationError as e:
            self.message_user(
                request,
                f"Validation error: {e}",
                level='error'
            )
            raise

    def save_related(self, request, form, formsets, change):
        """
        Override save_related to sync related objects to config_data and save to file after inlines are saved.
        """
        # First save the related objects (inlines)
        super().save_related(request, form, formsets, change)

        # Now sync the related objects to config_data and save to file
        try:
            form.instance.save_with_related()
            self.message_user(
                request,
                f"Configuration '{form.instance.name}' saved successfully to {form.instance.filename}.json",
                level='success'
            )
        except ValidationError as e:
            self.message_user(
                request,
                f"Error saving configuration file: {e}",
                level='error'
            )
            raise

    def delete_model(self, request, obj):
        """
        Override delete_model to show confirmation message.
        """
        filename = obj.filename
        name = obj.name
        super().delete_model(request, obj)
        self.message_user(
            request,
            f"Configuration '{name}' ({filename}.json) deleted successfully. "
            f"The filename {filename} will not be reused.",
            level='success'
        )

    def get_form(self, request, obj=None, **kwargs):
        """
        Customize the form for new vs existing instances.
        """
        form = super().get_form(request, obj, **kwargs)

        if obj is None:
            # New instance - provide helpful defaults
            form.base_fields['config_name'].help_text += " (Required: unique, kebab-case)"
            form.base_fields['system_prompt_base'].help_text += " (Minimum 50 characters)"

        return form
