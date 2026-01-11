"""
Models for managing chatbot configuration files.
"""
import json
from pathlib import Path
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from pydantic import ValidationError as PydanticValidationError

# Import the ChatbotConfig from bootstrap
import sys
sys.path.insert(0, str(settings.BASE_DIR))
from bootstrap.chatbot_config import ChatbotConfig


class ConfigurationFile(models.Model):
    """
    Django model for managing chatbot configuration files.

    Each instance represents a JSON configuration file stored in the working directory.
    Files are named with 6-digit sequential numbers (000001.json, 000002.json, etc.).
    The metadata.name field must be unique across all configurations.
    """

    # The 6-digit filename (without .json extension)
    filename = models.CharField(
        max_length=6,
        unique=True,
        editable=False,
        help_text="Six-digit filename (e.g., 000001)"
    )

    # Cached metadata from the config file for quick access
    name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Configuration name (from metadata.name)"
    )

    description = models.TextField(
        blank=True,
        help_text="Configuration description"
    )

    author = models.CharField(
        max_length=200,
        blank=True,
        help_text="Configuration author"
    )

    # Full configuration as JSON
    config_data = models.JSONField(
        help_text="Complete configuration as JSON"
    )

    # Timestamps
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Chatbot Configuration'
        verbose_name_plural = 'Chatbot Configurations'

    def __str__(self):
        return f"{self.name} ({self.filename}.json)"

    @classmethod
    def get_next_filename(cls):
        """
        Generate the next available 6-digit filename.
        Finds the highest existing filename and increments by 1.
        """
        existing = cls.objects.all().order_by('-filename').first()
        if existing:
            next_num = int(existing.filename) + 1
        else:
            next_num = 1
        return f"{next_num:06d}"

    @classmethod
    def get_config_directory(cls):
        """Get the directory where config files are stored (working directory)."""
        return settings.WORKING_DIR

    def get_file_path(self):
        """Get the full path to this configuration's JSON file."""
        return self.get_config_directory() / f"{self.filename}.json"

    def validate_config_data(self):
        """
        Validate the config_data using ChatbotConfig pydantic model.
        Raises ValidationError if invalid.
        """
        try:
            ChatbotConfig.from_dict(self.config_data)
        except PydanticValidationError as e:
            raise ValidationError(f"Invalid configuration: {e}")
        except Exception as e:
            raise ValidationError(f"Configuration validation error: {e}")

    def extract_metadata(self):
        """
        Extract metadata fields from config_data and populate model fields.
        """
        metadata = self.config_data.get('metadata', {})
        self.name = metadata.get('name', '')
        self.description = metadata.get('description', '')
        self.author = metadata.get('author', '')

    def load_from_file(self, file_path):
        """
        Load configuration from an existing JSON file.

        Args:
            file_path: Path to the JSON file
        """
        # Load and validate the config
        config = ChatbotConfig.from_file(file_path)

        # Convert to dict, preserving the original structure
        # Use mode='json' to ensure proper serialization of datetime objects
        self.config_data = json.loads(config.model_dump_json(by_alias=True, exclude_none=True))
        self.extract_metadata()

    def save_to_file(self):
        """
        Save the configuration to its JSON file on disk.
        """
        config = ChatbotConfig.from_dict(self.config_data)
        config.to_file(self.get_file_path())

    def clean(self):
        """
        Validate the model before saving.
        """
        # Validate the configuration data
        self.validate_config_data()

        # Extract metadata to ensure sync
        self.extract_metadata()

        # Check for name uniqueness (excluding self)
        if ConfigurationFile.objects.filter(name=self.name).exclude(pk=self.pk).exists():
            raise ValidationError(
                f"A configuration with name '{self.name}' already exists. "
                "Configuration names must be unique."
            )

    def save(self, *args, **kwargs):
        """
        Override save to handle file operations.
        """
        is_new = self.pk is None

        # Generate filename for new instances
        if is_new and not self.filename:
            self.filename = self.get_next_filename()

        # Run validation
        self.full_clean()

        # Save to database
        super().save(*args, **kwargs)

        # Save to file
        try:
            self.save_to_file()
        except Exception as e:
            # If file save fails, delete the database record
            if is_new:
                super().delete(*args, **kwargs)
            raise ValidationError(f"Failed to save configuration file: {e}")

    def delete(self, *args, **kwargs):
        """
        Override delete to remove the file from disk.
        The filename is not reused.
        """
        file_path = self.get_file_path()

        # Delete from database first
        super().delete(*args, **kwargs)

        # Delete the file if it exists
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                # Log but don't fail if file deletion fails
                print(f"Warning: Could not delete file {file_path}: {e}")

    def rename(self, new_name):
        """
        Rename this configuration by updating metadata.name.

        Args:
            new_name: The new name for the configuration

        Raises:
            ValidationError: If the new name is invalid or already exists
        """
        # Check uniqueness
        if ConfigurationFile.objects.filter(name=new_name).exclude(pk=self.pk).exists():
            raise ValidationError(
                f"A configuration with name '{new_name}' already exists. "
                "Configuration names must be unique."
            )

        # Update the config_data
        if 'metadata' not in self.config_data:
            self.config_data['metadata'] = {}
        self.config_data['metadata']['name'] = new_name

        # Update the cached name field
        self.name = new_name

        # Validate and save
        self.save()
