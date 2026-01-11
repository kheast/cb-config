"""
Django admin configuration for chatbot configurations.
"""
from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from .models import ConfigurationFile


class ConfigurationFileAdminForm(forms.ModelForm):
    """
    Custom form for ConfigurationFile with better JSON editing.
    """
    config_data = forms.JSONField(
        widget=forms.Textarea(attrs={
            'rows': 20,
            'cols': 80,
            'style': 'font-family: monospace; font-size: 12px;'
        }),
        help_text="Complete configuration as JSON. This will be validated against the ChatbotConfig schema."
    )

    class Meta:
        model = ConfigurationFile
        fields = ['name', 'description', 'author', 'config_data']

    def clean(self):
        cleaned_data = super().clean()

        # Ensure metadata.name matches the name field
        config_data = cleaned_data.get('config_data', {})
        name = cleaned_data.get('name', '')

        if config_data:
            if 'metadata' not in config_data:
                config_data['metadata'] = {}
            config_data['metadata']['name'] = name

            # Also sync description and author if provided
            if cleaned_data.get('description'):
                config_data['metadata']['description'] = cleaned_data['description']
            if cleaned_data.get('author'):
                config_data['metadata']['author'] = cleaned_data['author']

            cleaned_data['config_data'] = config_data

        return cleaned_data


@admin.register(ConfigurationFile)
class ConfigurationFileAdmin(admin.ModelAdmin):
    """
    Admin interface for managing chatbot configurations.
    """
    form = ConfigurationFileAdminForm

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
            'fields': ('name', 'description', 'author')
        }),
        ('File Information', {
            'fields': ('filename', 'file_path_display', 'created', 'modified'),
            'classes': ('collapse',)
        }),
        ('Configuration Data', {
            'fields': ('config_data',),
            'description': 'Edit the complete JSON configuration below. Changes will be validated before saving.'
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
        Override save_model to handle validation errors gracefully.
        """
        try:
            super().save_model(request, obj, form, change)
            self.message_user(
                request,
                f"Configuration '{obj.name}' saved successfully to {obj.filename}.json",
                level='success'
            )
        except ValidationError as e:
            self.message_user(
                request,
                f"Validation error: {e}",
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
        Customize the form to provide better help text for new instances.
        """
        form = super().get_form(request, obj, **kwargs)

        if obj is None:
            # New instance
            form.base_fields['config_data'].help_text = (
                "Enter a complete chatbot configuration as JSON. "
                "Make sure to include all required fields: metadata, data_context, and system_prompt. "
                "The metadata.name will be synced with the 'name' field above."
            )

        return form
