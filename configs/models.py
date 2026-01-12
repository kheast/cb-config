"""
Models for managing chatbot configuration files.
"""
import json
import yaml
from pathlib import Path
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from pydantic import ValidationError as PydanticValidationError

# Import the ChatbotConfig from bootstrap
import sys
sys.path.insert(0, str(settings.BASE_DIR))
from bootstrap.chatbot_config import ChatbotConfig, FileFormat


class BedrockCredentials(models.Model):
    """AWS Bedrock credentials for Anthropic models."""
    aws_access_key_id = models.CharField(max_length=200, help_text="AWS Access Key ID")
    aws_secret_access_key = models.CharField(max_length=200, help_text="AWS Secret Access Key")
    aws_region = models.CharField(max_length=50, default="us-east-1", help_text="AWS Region")

    class Meta:
        verbose_name = 'Bedrock Credentials'
        verbose_name_plural = 'Bedrock Credentials'

    def __str__(self):
        return f"Bedrock ({self.aws_region})"


class OpenAICredentials(models.Model):
    """OpenAI API credentials."""
    api_key = models.CharField(max_length=200, help_text="OpenAI API Key")
    organization_id = models.CharField(max_length=200, blank=True, null=True, help_text="OpenAI Organization ID (optional)")

    class Meta:
        verbose_name = 'OpenAI Credentials'
        verbose_name_plural = 'OpenAI Credentials'

    def __str__(self):
        return f"OpenAI (org: {self.organization_id or 'default'})"


class LLMCredentials(models.Model):
    """
    LLM provider credentials. Exactly one of anthropic_bedrock or openai must be set.
    """
    # Provider choice
    PROVIDER_CHOICES = [
        ('anthropic_bedrock', 'Anthropic Bedrock'),
        ('openai', 'OpenAI'),
    ]
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, help_text="LLM Provider")

    # Credentials (exactly one should be set based on provider)
    anthropic_bedrock = models.OneToOneField(
        BedrockCredentials,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='llm_credentials'
    )
    openai = models.OneToOneField(
        OpenAICredentials,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='llm_credentials'
    )

    class Meta:
        verbose_name = 'LLM Credentials'
        verbose_name_plural = 'LLM Credentials'

    def __str__(self):
        return f"LLM Credentials ({self.get_provider_display()})"

    def clean(self):
        """Validate that exactly one credential type is set based on provider."""
        super().clean()
        if self.provider == 'anthropic_bedrock' and not self.anthropic_bedrock:
            raise ValidationError("Bedrock credentials are required when provider is Anthropic Bedrock")
        if self.provider == 'openai' and not self.openai:
            raise ValidationError("OpenAI credentials are required when provider is OpenAI")
        if self.provider == 'anthropic_bedrock' and self.openai:
            raise ValidationError("Cannot have OpenAI credentials when provider is Anthropic Bedrock")
        if self.provider == 'openai' and self.anthropic_bedrock:
            raise ValidationError("Cannot have Bedrock credentials when provider is OpenAI")


class ConfigurationFile(models.Model):
    """
    Django model for managing chatbot configuration files.

    Each instance represents a configuration file (JSON or YAML) stored in the working directory.
    Files are named with 6-digit sequential numbers (000001.json, 000001.yaml, etc.).
    The metadata.name field must be unique across all configurations.
    """

    # The 6-digit filename (without extension)
    filename = models.CharField(
        max_length=6,
        unique=True,
        editable=False,
        help_text="Six-digit filename (e.g., 000001)"
    )

    # File format (json or yaml)
    FORMAT_CHOICES = [
        ('json', 'JSON'),
        ('yaml', 'YAML'),
    ]
    file_format = models.CharField(
        max_length=4,
        choices=FORMAT_CHOICES,
        default='json',
        help_text="File format (JSON or YAML)"
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

    # LLM credentials (required)
    llm_credentials = models.OneToOneField(
        LLMCredentials,
        on_delete=models.CASCADE,
        related_name='configuration',
        null=True,
        blank=True,
        help_text="LLM provider credentials"
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
        return f"{self.name} ({self.filename}.{self.file_format})"

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
        """Get the full path to this configuration's file."""
        return self.get_config_directory() / f"{self.filename}.{self.file_format}"

    def validate_config_data(self, skip_datasource_check=False):
        """
        Validate the config_data using ChatbotConfig pydantic model.

        Args:
            skip_datasource_check: If True, temporarily add a dummy datasource for validation
                                   (used when datasources will be added via inline formsets)

        Raises ValidationError if invalid.
        """
        try:
            config_to_validate = self.config_data

            # If skipping datasource check and no datasources exist, add a temporary one for validation
            if skip_datasource_check:
                data_context = config_to_validate.get('data_context', {})
                if not data_context.get('datasources'):
                    # Create a copy to avoid modifying the original
                    import copy
                    config_to_validate = copy.deepcopy(self.config_data)
                    config_to_validate['data_context']['datasources'] = [{
                        'name': 'Temporary',
                        'portal_datasource_id': 'temp',
                        'description': 'Temporary datasource for validation',
                        'primary_entity': 'Temp'
                    }]

            ChatbotConfig.from_dict(config_to_validate)
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
        Load configuration from an existing JSON or YAML file.

        Args:
            file_path: Path to the configuration file
        """
        # Load and validate the config
        config = ChatbotConfig.from_file(file_path)

        # Detect and set the file format
        file_path_obj = Path(file_path)
        if file_path_obj.suffix.lower() in ['.yaml', '.yml']:
            self.file_format = 'yaml'
        else:
            self.file_format = 'json'

        # Convert to dict, preserving the original structure
        # Use mode='json' to ensure proper serialization of datetime objects
        self.config_data = json.loads(config.model_dump_json(by_alias=True, exclude_none=True))
        self.extract_metadata()

        # Extract and sync LLM credentials
        self.sync_llm_credentials_from_config_data()

        # Note: sync_config_data_to_related() should be called after the instance is saved to the database
        # (so it has a pk). The caller should call it explicitly if needed.

    def save_to_file(self):
        """
        Save the configuration to its file on disk (JSON or YAML based on file_format).
        """
        config = ChatbotConfig.from_dict(self.config_data)
        # Convert file_format to FileFormat enum
        format_enum = FileFormat.JSON if self.file_format == 'json' else FileFormat.YAML
        config.to_file(self.get_file_path(), format=format_enum)

    def clean(self):
        """
        Validate the model before saving.
        """
        # Validate the configuration data
        # Skip datasource check if datasources will be added via inline formsets
        self.validate_config_data(skip_datasource_check=True)

        # Extract metadata to ensure sync
        self.extract_metadata()

        # Check for name uniqueness (excluding self)
        if ConfigurationFile.objects.filter(name=self.name).exclude(pk=self.pk).exists():
            raise ValidationError(
                f"A configuration with name '{self.name}' already exists. "
                "Configuration names must be unique."
            )

    def save(self, *args, skip_file_save=False, **kwargs):
        """
        Override save to handle file operations.

        Args:
            skip_file_save: If True, don't save to file (used during initial save before related objects exist)
        """
        is_new = self.pk is None

        # Generate filename for new instances
        if is_new and not self.filename:
            self.filename = self.get_next_filename()

        # Run validation
        self.full_clean()

        # Save to database
        super().save(*args, **kwargs)

        # Save to file unless explicitly skipped
        if not skip_file_save:
            # Sync related objects to config_data
            self.sync_related_to_config_data()

            # Save to file
            try:
                self.save_to_file()
            except Exception as e:
                # If file save fails, delete the database record
                if is_new:
                    super().delete(*args, **kwargs)
                raise ValidationError(f"Failed to save configuration file: {e}")

    def save_with_related(self):
        """
        Save configuration file after syncing related objects.
        This should be called after all related objects (datasources, terms, mappings) have been saved.
        """
        self.sync_related_to_config_data()

        # Do a full validation now that datasources are populated
        self.validate_config_data(skip_datasource_check=False)

        self.save_to_file()

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

    def sync_related_to_config_data(self):
        """
        Synchronize related objects (LLM credentials, datasources, business terms, field mappings)
        into the config_data JSON structure.
        """
        if not self.config_data:
            return

        # Sync LLM credentials
        self.sync_llm_credentials_to_config_data()

        # Sync datasources
        datasources = []
        for ds in self.datasources.all():
            datasources.append({
                'name': ds.name,
                'portal_datasource_id': ds.portal_datasource_id,
                'description': ds.description,
                'primary_entity': ds.primary_entity,
                'refresh_frequency': ds.refresh_frequency,
            })

        if 'data_context' not in self.config_data:
            self.config_data['data_context'] = {}
        self.config_data['data_context']['datasources'] = datasources

        # Sync business terms
        business_terms = {}
        for bt in self.business_terms.all():
            business_terms[bt.term] = bt.definition

        if 'semantic_layer' not in self.config_data.get('data_context', {}):
            self.config_data['data_context']['semantic_layer'] = {}
        self.config_data['data_context']['semantic_layer']['business_terms'] = business_terms

        # Sync field mappings
        field_mappings = {}
        for fm in self.field_mappings.all():
            mapping = {
                'business_name': fm.business_name,
                'description': fm.description,
                'format': fm.format,
            }
            if fm.valid_values:
                mapping['valid_values'] = [v.strip() for v in fm.valid_values.split(',') if v.strip()]
            field_mappings[fm.field_name] = mapping

        self.config_data['data_context']['semantic_layer']['field_mappings'] = field_mappings

    def sync_config_data_to_related(self):
        """
        Synchronize config_data JSON to related objects (datasources, business terms, field mappings).
        This is called when loading from file.
        """
        if not self.pk or not self.config_data:
            return

        data_context = self.config_data.get('data_context', {})

        # Sync datasources
        datasources_data = data_context.get('datasources', [])
        # Clear existing
        self.datasources.all().delete()
        # Create new
        for ds_data in datasources_data:
            Datasource.objects.create(
                configuration=self,
                name=ds_data.get('name', ''),
                portal_datasource_id=ds_data.get('portal_datasource_id', ''),
                description=ds_data.get('description', ''),
                primary_entity=ds_data.get('primary_entity', ''),
                refresh_frequency=ds_data.get('refresh_frequency', 'daily'),
            )

        # Sync business terms
        semantic_layer = data_context.get('semantic_layer', {})
        business_terms_data = semantic_layer.get('business_terms', {})
        # Clear existing
        self.business_terms.all().delete()
        # Create new
        for term, definition in business_terms_data.items():
            BusinessTerm.objects.create(
                configuration=self,
                term=term,
                definition=definition,
            )

        # Sync field mappings
        field_mappings_data = semantic_layer.get('field_mappings', {})
        # Clear existing
        self.field_mappings.all().delete()
        # Create new
        for field_name, mapping in field_mappings_data.items():
            valid_values_list = mapping.get('valid_values', [])
            valid_values_str = ', '.join(valid_values_list) if valid_values_list else ''

            FieldMapping.objects.create(
                configuration=self,
                field_name=field_name,
                business_name=mapping.get('business_name', ''),
                description=mapping.get('description', ''),
                format=mapping.get('format', 'text'),
                valid_values=valid_values_str,
            )

    def sync_llm_credentials_to_config_data(self):
        """
        Synchronize LLM credentials model to config_data JSON structure.
        """
        if not self.llm_credentials or not self.config_data:
            return

        llm_creds = self.llm_credentials
        creds_data = {}

        if llm_creds.provider == 'anthropic_bedrock' and llm_creds.anthropic_bedrock:
            creds_data['anthropic_bedrock'] = {
                'aws_access_key_id': llm_creds.anthropic_bedrock.aws_access_key_id,
                'aws_secret_access_key': llm_creds.anthropic_bedrock.aws_secret_access_key,
                'aws_region': llm_creds.anthropic_bedrock.aws_region,
            }
        elif llm_creds.provider == 'openai' and llm_creds.openai:
            creds_data['openai'] = {
                'api_key': llm_creds.openai.api_key,
            }
            if llm_creds.openai.organization_id:
                creds_data['openai']['organization_id'] = llm_creds.openai.organization_id

        self.config_data['llm_credentials'] = creds_data

    def sync_llm_credentials_from_config_data(self):
        """
        Synchronize config_data JSON to LLM credentials model.
        This is called when loading from file.
        """
        if not self.config_data:
            return

        creds_data = self.config_data.get('llm_credentials', {})
        if not creds_data:
            return

        # Determine provider
        if 'anthropic_bedrock' in creds_data and creds_data['anthropic_bedrock']:
            provider = 'anthropic_bedrock'
            bedrock_data = creds_data['anthropic_bedrock']

            # Create Bedrock credentials
            bedrock_creds = BedrockCredentials.objects.create(
                aws_access_key_id=bedrock_data.get('aws_access_key_id', ''),
                aws_secret_access_key=bedrock_data.get('aws_secret_access_key', ''),
                aws_region=bedrock_data.get('aws_region', 'us-east-1'),
            )

            # Create LLM credentials
            self.llm_credentials = LLMCredentials.objects.create(
                provider=provider,
                anthropic_bedrock=bedrock_creds,
            )

        elif 'openai' in creds_data and creds_data['openai']:
            provider = 'openai'
            openai_data = creds_data['openai']

            # Create OpenAI credentials
            openai_creds = OpenAICredentials.objects.create(
                api_key=openai_data.get('api_key', ''),
                organization_id=openai_data.get('organization_id'),
            )

            # Create LLM credentials
            self.llm_credentials = LLMCredentials.objects.create(
                provider=provider,
                openai=openai_creds,
            )


class Datasource(models.Model):
    """
    A datasource referenced by a chatbot configuration.
    """
    configuration = models.ForeignKey(
        ConfigurationFile,
        on_delete=models.CASCADE,
        related_name='datasources'
    )

    name = models.CharField(
        max_length=200,
        help_text="Friendly name for this datasource"
    )

    portal_datasource_id = models.CharField(
        max_length=200,
        help_text="Portal's internal datasource identifier"
    )

    description = models.TextField(
        help_text="What data this datasource provides"
    )

    primary_entity = models.CharField(
        max_length=100,
        help_text="The main entity type (e.g., Opportunity, Account)"
    )

    refresh_frequency = models.CharField(
        max_length=50,
        default='daily',
        help_text="How often the underlying data refreshes"
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Datasource'
        verbose_name_plural = 'Datasources'

    def __str__(self):
        return f"{self.name} ({self.portal_datasource_id})"


class BusinessTerm(models.Model):
    """
    A business term definition for the semantic layer.
    """
    configuration = models.ForeignKey(
        ConfigurationFile,
        on_delete=models.CASCADE,
        related_name='business_terms'
    )

    term = models.CharField(
        max_length=100,
        help_text="Business term (e.g., ARR, MRR)"
    )

    definition = models.TextField(
        help_text="Definition of the term"
    )

    class Meta:
        ordering = ['term']
        verbose_name = 'Business Term'
        verbose_name_plural = 'Business Terms'
        unique_together = [['configuration', 'term']]

    def __str__(self):
        return f"{self.term}: {self.definition[:50]}"


class FieldMapping(models.Model):
    """
    A field mapping from technical field name to business terminology.
    """
    configuration = models.ForeignKey(
        ConfigurationFile,
        on_delete=models.CASCADE,
        related_name='field_mappings'
    )

    field_name = models.CharField(
        max_length=100,
        help_text="Technical field name (e.g., 'amount', 'stage')"
    )

    business_name = models.CharField(
        max_length=200,
        help_text="User-friendly name for this field"
    )

    description = models.TextField(
        help_text="What this field represents"
    )

    format = models.CharField(
        max_length=50,
        default='text',
        help_text="Data format: currency, text, date, number, percentage, etc."
    )

    valid_values = models.TextField(
        blank=True,
        help_text="Comma-separated list of valid values (if applicable)"
    )

    class Meta:
        ordering = ['field_name']
        verbose_name = 'Field Mapping'
        verbose_name_plural = 'Field Mappings'
        unique_together = [['configuration', 'field_name']]

    def __str__(self):
        return f"{self.field_name} → {self.business_name}"
