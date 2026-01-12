"""
Zuar Portal Chatbot Configuration Models

This module defines Pydantic models for validating and loading chatbot configurations.
Use ChatbotConfig.from_file() to load a configuration from disk.

Supports both JSON and YAML formats. When reading, the format is auto-detected
from the file contents. When writing, JSON is used by default.

Example:
    config = ChatbotConfig.from_file("path/to/config.yaml")
    config.to_file("path/to/config.json")  # Writes as JSON (default)
    config.to_file("path/to/config.yaml", format="yaml")  # Writes as YAML
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    ConfigDict,
)


# =============================================================================
# Enums
# =============================================================================

class LLMProvider(str, Enum):
    """Supported LLM providers."""
    ANTHROPIC_BEDROCK = "anthropic_bedrock"
    OPENAI = "openai"


class Verbosity(str, Enum):
    """Response verbosity levels."""
    CONCISE = "concise"
    MODERATE = "moderate"
    DETAILED = "detailed"


class Tone(str, Enum):
    """Persona tone options."""
    FORMAL = "formal"
    PROFESSIONAL = "professional but approachable"
    CASUAL = "casual"
    TECHNICAL = "technical"


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class TrendDirection(str, Enum):
    """Trend direction indicators."""
    UP = "up"
    DOWN = "down"
    FLAT = "flat"


class DefaultFormat(str, Enum):
    """Default response format options."""
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"
    JSON = "json"


class PanelPosition(str, Enum):
    """Dashboard panel position options."""
    RIGHT_PANEL = "right_panel"
    LEFT_PANEL = "left_panel"
    BOTTOM_PANEL = "bottom_panel"
    MODAL = "modal"
    FLOATING = "floating"


class PanelState(str, Enum):
    """Initial panel state options."""
    COLLAPSED = "collapsed"
    EXPANDED = "expanded"


class PIIAction(str, Enum):
    """Actions to take when PII is detected."""
    REDACT = "redact"
    BLOCK = "block"
    WARN = "warn"


class FileFormat(str, Enum):
    """Supported configuration file formats."""
    JSON = "json"
    YAML = "yaml"


# =============================================================================
# Format Detection Utilities
# =============================================================================

def detect_format(content: str) -> FileFormat:
    """
    Detect whether content is JSON or YAML based on its structure.
    
    Args:
        content: The file content as a string.
        
    Returns:
        FileFormat.JSON or FileFormat.YAML
    """
    stripped = content.strip()
    
    # JSON objects start with { and JSON arrays start with [
    if stripped.startswith('{') or stripped.startswith('['):
        # Try to parse as JSON to confirm
        try:
            json.loads(content)
            return FileFormat.JSON
        except json.JSONDecodeError:
            pass
    
    # If not valid JSON, assume YAML
    return FileFormat.YAML


def parse_content(content: str) -> dict[str, Any]:
    """
    Parse content as either JSON or YAML based on auto-detection.
    
    Args:
        content: The file content as a string.
        
    Returns:
        Parsed dictionary.
        
    Raises:
        ValueError: If content cannot be parsed as either format.
    """
    detected_format = detect_format(content)
    
    if detected_format == FileFormat.JSON:
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse as JSON: {e}")
    else:
        try:
            result = yaml.safe_load(content)
            if result is None:
                return {}
            if not isinstance(result, dict):
                raise ValueError("YAML content must be a mapping/dictionary at the root level")
            return result
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse as YAML: {e}")


def serialize_content(data: dict[str, Any], format: FileFormat = FileFormat.JSON) -> str:
    """
    Serialize data to JSON or YAML format.
    
    Args:
        data: The data dictionary to serialize.
        format: The output format (default: JSON).
        
    Returns:
        Serialized string.
    """
    # Convert datetime objects to ISO format strings
    def convert_datetimes(obj):
        if isinstance(obj, dict):
            return {k: convert_datetimes(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_datetimes(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return obj
    
    data = convert_datetimes(data)
    
    if format == FileFormat.JSON:
        return json.dumps(data, indent=2, ensure_ascii=False)
    else:
        return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)


# =============================================================================
# Metadata Models
# =============================================================================

class ConfigMetadata(BaseModel):
    """Configuration metadata for versioning and audit."""
    
    model_config = ConfigDict(extra="forbid")
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$",
        description="Unique identifier for this configuration (kebab-case)"
    )
    description: str = Field(
        ...,
        max_length=500,
        description="Human-readable description of what this config is for"
    )
    created: datetime = Field(
        ...,
        description="ISO 8601 timestamp of creation"
    )
    modified: datetime = Field(
        ...,
        description="ISO 8601 timestamp of last modification"
    )
    author: str = Field(
        ...,
        description="Email or identifier of the configuration author"
    )


# =============================================================================
# LLM Provider and Credentials Models (Priority 1)
# =============================================================================

class BedrockCredentials(BaseModel):
    """AWS Bedrock credentials for Anthropic models."""
    
    model_config = ConfigDict(extra="forbid")
    
    aws_access_key_id: str = Field(
        ...,
        min_length=16,
        max_length=128,
        description="AWS access key ID"
    )
    aws_secret_access_key: str = Field(
        ...,
        min_length=1,
        description="AWS secret access key"
    )
    aws_region: str = Field(
        default="us-east-1",
        pattern=r"^[a-z]{2}-[a-z]+-\d+$",
        description="AWS region for Bedrock (e.g., us-east-1, us-west-2)"
    )


class OpenAICredentials(BaseModel):
    """OpenAI API credentials."""
    
    model_config = ConfigDict(extra="forbid")
    
    api_key: str = Field(
        ...,
        min_length=1,
        description="OpenAI API key"
    )
    organization_id: str | None = Field(
        default=None,
        description="Optional OpenAI organization ID"
    )


class LLMCredentials(BaseModel):
    """LLM provider credentials - exactly one provider must be configured."""
    
    model_config = ConfigDict(extra="forbid")
    
    anthropic_bedrock: BedrockCredentials | None = Field(
        default=None,
        description="AWS Bedrock credentials for Anthropic models"
    )
    openai: OpenAICredentials | None = Field(
        default=None,
        description="OpenAI API credentials"
    )

    @model_validator(mode="after")
    def validate_exactly_one_provider(self) -> "LLMCredentials":
        """Ensure exactly one provider is configured."""
        providers_set = sum([
            self.anthropic_bedrock is not None,
            self.openai is not None,
        ])
        if providers_set == 0:
            raise ValueError(
                "At least one LLM provider must be configured "
                "(anthropic_bedrock or openai)"
            )
        if providers_set > 1:
            raise ValueError(
                "Only one LLM provider can be configured at a time"
            )
        return self

    @property
    def provider(self) -> LLMProvider:
        """Return the configured provider type."""
        if self.anthropic_bedrock is not None:
            return LLMProvider.ANTHROPIC_BEDROCK
        return LLMProvider.OPENAI


# =============================================================================
# LLM Parameters Models (Priority 1)
# =============================================================================

class RetryPolicy(BaseModel):
    """LLM API retry policy."""
    
    model_config = ConfigDict(extra="forbid")
    
    max_retries: int = Field(default=3, ge=0, le=10)
    initial_delay_ms: int = Field(default=1000, ge=100, le=30000)
    backoff_multiplier: float = Field(default=2.0, ge=1.0, le=5.0)
    max_delay_ms: int = Field(default=10000, ge=1000, le=60000)


class LLMParameters(BaseModel):
    """LLM configuration parameters."""
    
    model_config = ConfigDict(extra="forbid")
    
    model: str = Field(
        ...,
        description="Model identifier (e.g., anthropic.claude-3-sonnet-20240229-v1:0, gpt-4)"
    )
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Sampling temperature"
    )
    max_tokens: int = Field(
        default=1024,
        ge=100,
        le=8192,
        description="Maximum tokens in response"
    )
    top_p: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter"
    )
    stop_sequences: list[str] = Field(
        default_factory=list,
        description="Sequences that stop generation"
    )
    retry_policy: RetryPolicy = Field(
        default_factory=RetryPolicy,
        description="Retry configuration"
    )
    timeout_ms: int = Field(
        default=30000,
        ge=5000,
        le=120000,
        description="Request timeout in milliseconds"
    )


# =============================================================================
# Data Context Models (Priority 1)
# =============================================================================

class Datasource(BaseModel):
    """Reference to a Portal datasource."""
    
    model_config = ConfigDict(extra="forbid")
    
    name: str = Field(
        ...,
        description="Friendly name for this datasource within the chatbot"
    )
    portal_datasource_id: str = Field(
        ...,
        description="Portal's internal datasource identifier"
    )
    description: str = Field(
        ...,
        description="What data this datasource provides"
    )
    primary_entity: str = Field(
        ...,
        description="The main Salesforce object type (e.g., Opportunity, Account)"
    )
    refresh_frequency: str = Field(
        default="daily",
        description="How often the underlying data refreshes"
    )


class FieldMapping(BaseModel):
    """Mapping from technical field name to business terminology."""
    
    model_config = ConfigDict(extra="forbid")
    
    business_name: str = Field(
        ...,
        description="User-friendly name for this field"
    )
    description: str = Field(
        ...,
        description="What this field represents"
    )
    format: str = Field(
        ...,
        description="Data format: currency, text, date, number, percentage, etc."
    )
    valid_values: list[str] | None = Field(
        default=None,
        description="Enumerated valid values, if applicable"
    )


class EntityRelationship(BaseModel):
    """Describes relationships between entities."""
    
    model_config = ConfigDict(extra="forbid")
    
    from_entity: str = Field(
        ...,
        alias="from",
        description="Source entity"
    )
    to: str = Field(
        ...,
        description="Target entity"
    )
    relationship: Literal["belongs_to", "has_many", "has_one", "many_to_many"] = Field(
        ...,
        description="Type of relationship"
    )
    description: str = Field(
        ...,
        description="Human-readable description of the relationship"
    )


class CalculatedMetric(BaseModel):
    """Definition of a calculated/derived metric."""
    
    model_config = ConfigDict(extra="forbid")
    
    name: str = Field(
        ...,
        description="Metric identifier"
    )
    formula: str = Field(
        ...,
        description="Calculation formula or expression"
    )
    description: str = Field(
        ...,
        description="What this metric represents"
    )


class FiscalQuarters(BaseModel):
    """Fiscal quarter definitions."""
    
    model_config = ConfigDict(extra="forbid")
    
    Q1: str = Field(..., description="Q1 date range")
    Q2: str = Field(..., description="Q2 date range")
    Q3: str = Field(..., description="Q3 date range")
    Q4: str = Field(..., description="Q4 date range")


class TimeConventions(BaseModel):
    """Time and date interpretation rules."""
    
    model_config = ConfigDict(extra="forbid")
    
    fiscal_year_start: str = Field(
        ...,
        description="When the fiscal year begins (e.g., 'February 1')"
    )
    fiscal_quarters: FiscalQuarters = Field(
        ...,
        description="Fiscal quarter date ranges"
    )
    default_timezone: str = Field(
        default="UTC",
        description="Default timezone for date interpretations"
    )
    when_user_says_this_quarter: str = Field(
        default="current fiscal quarter based on today's date",
        description="How to interpret 'this quarter'"
    )
    when_user_says_this_year: str = Field(
        default="current fiscal year based on today's date",
        description="How to interpret 'this year'"
    )


class SegmentDefinition(BaseModel):
    """Definition of a segment with optional min/max bounds."""
    
    model_config = ConfigDict(extra="allow")
    
    description: str = Field(
        ...,
        description="What this segment represents"
    )
    min: float | None = Field(
        default=None,
        description="Minimum value (inclusive)"
    )
    max: float | None = Field(
        default=None,
        description="Maximum value (inclusive)"
    )


class SegmentationRules(BaseModel):
    """Rules for segmenting data."""
    
    model_config = ConfigDict(extra="allow")
    
    deal_size: dict[str, SegmentDefinition | str] | None = Field(
        default=None,
        description="Deal size segmentation rules"
    )
    account_tier: dict[str, str] | None = Field(
        default=None,
        description="Account tier definitions"
    )


class SampleQuestion(BaseModel):
    """Example question with interpretation guidance."""
    
    model_config = ConfigDict(extra="forbid")
    
    question: str = Field(
        ...,
        description="Example user question"
    )
    interpretation: str = Field(
        ...,
        description="How the chatbot should interpret this question"
    )
    datasource: str = Field(
        ...,
        description="Which datasource to query"
    )


class SemanticLayer(BaseModel):
    """Business terminology and data interpretation rules."""
    
    model_config = ConfigDict(extra="forbid")
    
    business_terms: dict[str, str] = Field(
        default_factory=dict,
        description="Glossary of business terms and their definitions"
    )
    field_mappings: dict[str, FieldMapping] = Field(
        default_factory=dict,
        description="Technical field name to business term mappings"
    )
    entity_relationships: list[EntityRelationship] = Field(
        default_factory=list,
        description="Relationships between data entities"
    )
    calculated_metrics: list[CalculatedMetric] = Field(
        default_factory=list,
        description="Derived metrics and their formulas"
    )
    time_conventions: TimeConventions | None = Field(
        default=None,
        description="Time and date interpretation rules"
    )
    segmentation_rules: SegmentationRules | None = Field(
        default=None,
        description="Rules for categorizing data into segments"
    )


class DataContext(BaseModel):
    """Complete data context configuration."""
    
    model_config = ConfigDict(extra="forbid")
    
    datasources: list[Datasource] = Field(
        ...,
        min_length=1,
        description="Available Portal datasources"
    )
    semantic_layer: SemanticLayer = Field(
        default_factory=SemanticLayer,
        description="Business terminology and interpretation rules"
    )
    sample_questions: list[SampleQuestion] = Field(
        default_factory=list,
        description="Example questions to guide interpretation"
    )


# =============================================================================
# System Prompt Models (Priority 1)
# =============================================================================

class Persona(BaseModel):
    """Chatbot persona configuration."""
    
    model_config = ConfigDict(extra="forbid")
    
    name: str = Field(
        default="Assistant",
        description="Display name for the chatbot"
    )
    tone: str = Field(
        default="professional but approachable",
        description="Communication tone"
    )
    verbosity: Verbosity = Field(
        default=Verbosity.CONCISE,
        description="Response length preference"
    )
    personality_traits: list[str] = Field(
        default_factory=list,
        description="Behavioral characteristics"
    )


class ContextInjection(BaseModel):
    """What context to automatically include in prompts."""
    
    model_config = ConfigDict(extra="forbid")
    
    include_current_date: bool = Field(
        default=True,
        description="Include today's date in context"
    )
    include_fiscal_period: bool = Field(
        default=True,
        description="Include current fiscal period info"
    )
    include_user_role: bool = Field(
        default=False,
        description="Include user's role/permissions context"
    )
    include_dashboard_context: bool = Field(
        default=True,
        description="Include information about the current dashboard"
    )


class FewShotExample(BaseModel):
    """Example conversation turn for few-shot prompting."""
    
    model_config = ConfigDict(extra="forbid")
    
    user: str = Field(
        ...,
        description="Example user message"
    )
    assistant: str = Field(
        ...,
        description="Example assistant response"
    )


class SystemPrompt(BaseModel):
    """System prompt configuration."""
    
    model_config = ConfigDict(extra="forbid")
    
    base_prompt: str = Field(
        ...,
        min_length=50,
        max_length=10000,
        description="The core system prompt text"
    )
    persona: Persona = Field(
        default_factory=Persona,
        description="Chatbot persona settings"
    )
    response_guidelines: list[str] = Field(
        default_factory=list,
        description="Rules for how to format and structure responses"
    )
    context_injection: ContextInjection = Field(
        default_factory=ContextInjection,
        description="What context to automatically include"
    )
    few_shot_examples: list[FewShotExample] = Field(
        default_factory=list,
        max_length=10,
        description="Example conversations for few-shot learning"
    )


# =============================================================================
# Guardrails Models (Priority 1)
# =============================================================================

class TopicRestrictions(BaseModel):
    """Topic-based content restrictions."""
    
    model_config = ConfigDict(extra="forbid")
    
    blocked_topics: list[str] = Field(
        default_factory=list,
        description="Topics the chatbot should not discuss"
    )
    redirect_message: str = Field(
        default="I'm not able to discuss that topic. How else can I help?",
        description="Message shown when a blocked topic is detected"
    )


class AggregationRequirement(BaseModel):
    """Require aggregation when record count is below threshold."""
    
    model_config = ConfigDict(extra="forbid")
    
    individual_compensation: int | None = Field(
        default=None,
        ge=1,
        description="Minimum records before showing individual compensation data"
    )
    description: str = Field(
        default="",
        description="Explanation of the aggregation requirement"
    )


class DataRestrictions(BaseModel):
    """Data-level access restrictions."""
    
    model_config = ConfigDict(extra="forbid")
    
    never_expose_fields: list[str] = Field(
        default_factory=list,
        description="Fields that should never be shown to users"
    )
    require_aggregation_above: AggregationRequirement | None = Field(
        default=None,
        description="Aggregation requirements for sensitive data"
    )


class BehavioralRestrictions(BaseModel):
    """Behavioral rules for the chatbot."""
    
    model_config = ConfigDict(extra="forbid")
    
    never_actions: list[str] = Field(
        default_factory=list,
        description="Actions the chatbot must never take"
    )
    always_actions: list[str] = Field(
        default_factory=list,
        description="Actions the chatbot must always take"
    )


class InputValidation(BaseModel):
    """Input validation rules."""
    
    model_config = ConfigDict(extra="forbid")
    
    max_question_length: int = Field(
        default=2000,
        ge=100,
        le=10000,
        description="Maximum allowed question length in characters"
    )
    reject_patterns: list[str] = Field(
        default_factory=list,
        description="Regex patterns or strings to reject"
    )
    rejection_message: str = Field(
        default="I didn't understand that request. Could you rephrase?",
        description="Message shown when input is rejected"
    )


class PIIDetection(BaseModel):
    """PII detection settings."""
    
    model_config = ConfigDict(extra="forbid")
    
    enabled: bool = Field(
        default=True,
        description="Whether PII detection is enabled"
    )
    action: PIIAction = Field(
        default=PIIAction.REDACT,
        description="Action to take when PII is detected"
    )


class OutputValidation(BaseModel):
    """Output validation rules."""
    
    model_config = ConfigDict(extra="forbid")
    
    max_response_length: int = Field(
        default=4000,
        ge=100,
        le=20000,
        description="Maximum response length in characters"
    )
    require_data_attribution: bool = Field(
        default=True,
        description="Require responses to cite data sources"
    )
    pii_detection: PIIDetection = Field(
        default_factory=PIIDetection,
        description="PII detection configuration"
    )


class RateLimits(BaseModel):
    """Rate limiting configuration."""
    
    model_config = ConfigDict(extra="forbid")
    
    max_questions_per_minute: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum questions allowed per minute"
    )
    max_questions_per_session: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Maximum questions allowed per session"
    )
    cooldown_message: str = Field(
        default="Please wait a moment before continuing.",
        description="Message shown when rate limit is hit"
    )


class Guardrails(BaseModel):
    """Complete guardrails configuration."""
    
    model_config = ConfigDict(extra="forbid")
    
    topic_restrictions: TopicRestrictions = Field(
        default_factory=TopicRestrictions,
        description="Topic-based restrictions"
    )
    data_restrictions: DataRestrictions = Field(
        default_factory=DataRestrictions,
        description="Data access restrictions"
    )
    behavioral_restrictions: BehavioralRestrictions = Field(
        default_factory=BehavioralRestrictions,
        description="Behavioral rules"
    )
    input_validation: InputValidation = Field(
        default_factory=InputValidation,
        description="Input validation rules"
    )
    output_validation: OutputValidation = Field(
        default_factory=OutputValidation,
        description="Output validation rules"
    )
    rate_limits: RateLimits = Field(
        default_factory=RateLimits,
        description="Rate limiting settings"
    )


# =============================================================================
# Structured Output Models (Priority 2)
# =============================================================================

class CurrencyFormatting(BaseModel):
    """Currency formatting rules."""
    
    model_config = ConfigDict(extra="forbid")
    
    symbol: str = Field(default="$", description="Currency symbol")
    thousands_separator: str = Field(default=",", description="Thousands separator")
    abbreviate_above: int = Field(
        default=1000000,
        description="Abbreviate values above this threshold"
    )
    abbreviation_style: str = Field(
        default="1.2M",
        description="How to abbreviate large numbers"
    )


class PercentageFormatting(BaseModel):
    """Percentage formatting rules."""
    
    model_config = ConfigDict(extra="forbid")
    
    decimal_places: int = Field(default=1, ge=0, le=4)
    include_symbol: bool = Field(default=True)


class DateFormatting(BaseModel):
    """Date formatting rules."""
    
    model_config = ConfigDict(extra="forbid")
    
    format: str = Field(
        default="MMM D, YYYY",
        description="Date format pattern"
    )
    relative_within_days: int = Field(
        default=7,
        ge=0,
        description="Use relative dates for dates within this many days"
    )


class TableFormatting(BaseModel):
    """Table display formatting rules."""
    
    model_config = ConfigDict(extra="forbid")
    
    max_rows_before_summary: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Summarize if more rows than this"
    )
    sort_by_default: str = Field(
        default="amount_desc",
        description="Default sort order"
    )


class FormattingRules(BaseModel):
    """Complete formatting rules."""
    
    model_config = ConfigDict(extra="forbid")
    
    currency: CurrencyFormatting = Field(default_factory=CurrencyFormatting)
    percentage: PercentageFormatting = Field(default_factory=PercentageFormatting)
    dates: DateFormatting = Field(default_factory=DateFormatting)
    tables: TableFormatting = Field(default_factory=TableFormatting)


class StructuredOutput(BaseModel):
    """Structured output configuration."""
    
    model_config = ConfigDict(extra="forbid")
    
    default_format: DefaultFormat = Field(
        default=DefaultFormat.MARKDOWN,
        description="Default response format"
    )
    response_schemas: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="JSON schemas for structured response types"
    )
    formatting_rules: FormattingRules = Field(
        default_factory=FormattingRules,
        description="Formatting rules for values"
    )


# =============================================================================
# Conversation Memory Models (Priority 2)
# =============================================================================

class ConversationMemory(BaseModel):
    """Conversation memory configuration."""
    
    model_config = ConfigDict(extra="forbid")
    
    enabled: bool = Field(
        default=True,
        description="Whether conversation memory is enabled"
    )
    max_turns: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum conversation turns to retain"
    )
    summarize_after_turns: int = Field(
        default=8,
        ge=1,
        le=50,
        description="Summarize context after this many turns"
    )
    session_timeout_minutes: int = Field(
        default=30,
        ge=5,
        le=1440,
        description="Session timeout in minutes"
    )
    context_to_preserve: list[str] = Field(
        default_factory=list,
        description="Types of context to preserve across turns"
    )
    context_to_forget: list[str] = Field(
        default_factory=list,
        description="Types of context to discard"
    )

    @model_validator(mode="after")
    def validate_summarize_before_max(self) -> "ConversationMemory":
        """Ensure summarize_after_turns <= max_turns."""
        if self.summarize_after_turns > self.max_turns:
            raise ValueError(
                f"summarize_after_turns ({self.summarize_after_turns}) "
                f"must be <= max_turns ({self.max_turns})"
            )
        return self


# =============================================================================
# Elicitation Models (Priority 2)
# =============================================================================

class ElicitationPattern(BaseModel):
    """Elicitation pattern for handling ambiguous requests."""
    
    model_config = ConfigDict(extra="forbid")
    
    trigger: str = Field(..., description="Pattern identifier")
    condition: str = Field(..., description="When this pattern applies")
    prompt: str = Field(..., description="Clarification prompt to show user")
    default_if_skipped: str | None = Field(
        default=None,
        description="Default value if user doesn't respond"
    )


class Elicitation(BaseModel):
    """Elicitation configuration."""
    
    model_config = ConfigDict(extra="forbid")
    
    enabled: bool = Field(
        default=True,
        description="Whether elicitation is enabled"
    )
    patterns: list[ElicitationPattern] = Field(
        default_factory=list,
        description="Elicitation patterns"
    )


# =============================================================================
# MCP Models (Priority 3)
# =============================================================================

class MCPToolParameter(BaseModel):
    """MCP tool parameter definition."""
    
    model_config = ConfigDict(extra="allow")


class MCPTool(BaseModel):
    """MCP tool definition."""
    
    model_config = ConfigDict(extra="forbid")
    
    name: str = Field(..., description="Tool identifier")
    description: str = Field(..., description="What this tool does")
    enabled: bool = Field(default=False, description="Whether tool is enabled")
    parameters: dict[str, str] = Field(
        default_factory=dict,
        description="Parameter name to type mapping"
    )
    requires_approval: bool = Field(
        default=False,
        description="Whether this tool requires user approval"
    )


class RunnerMCP(BaseModel):
    """Runner MCP connection configuration."""
    
    model_config = ConfigDict(extra="forbid")
    
    enabled: bool = Field(default=False)
    endpoint: str | None = Field(default=None)
    description: str = Field(default="")


class MCPTools(BaseModel):
    """MCP tools configuration."""
    
    model_config = ConfigDict(extra="forbid")
    
    enabled: bool = Field(
        default=False,
        description="Whether MCP tools are enabled globally"
    )
    available_tools: list[MCPTool] = Field(
        default_factory=list,
        description="Available tool definitions"
    )
    runner_mcp: RunnerMCP = Field(
        default_factory=RunnerMCP,
        description="Runner MCP configuration"
    )


class MCPResource(BaseModel):
    """MCP resource definition."""
    
    model_config = ConfigDict(extra="forbid")
    
    name: str = Field(..., description="Resource identifier")
    description: str = Field(..., description="What this resource contains")
    uri: str = Field(..., description="Resource URI")
    enabled: bool = Field(default=False, description="Whether resource is enabled")


class MCPResources(BaseModel):
    """MCP resources configuration."""
    
    model_config = ConfigDict(extra="forbid")
    
    enabled: bool = Field(
        default=False,
        description="Whether MCP resources are enabled globally"
    )
    available_resources: list[MCPResource] = Field(
        default_factory=list,
        description="Available resource definitions"
    )


# =============================================================================
# Dashboard Integration Models
# =============================================================================

class VisualizationAwareness(BaseModel):
    """Configuration for dashboard visualization awareness."""
    
    model_config = ConfigDict(extra="forbid")
    
    enabled: bool = Field(
        default=True,
        description="Whether the chatbot is aware of dashboard visualizations"
    )
    can_reference_charts: bool = Field(
        default=True,
        description="Whether the chatbot can reference specific charts"
    )
    context_includes: list[str] = Field(
        default_factory=list,
        description="What visualization context to include"
    )


class DashboardIntegration(BaseModel):
    """Dashboard integration configuration."""
    
    model_config = ConfigDict(extra="forbid")
    
    position: PanelPosition = Field(
        default=PanelPosition.RIGHT_PANEL,
        description="Where the chatbot panel appears"
    )
    initial_state: PanelState = Field(
        default=PanelState.COLLAPSED,
        description="Initial panel state"
    )
    width_px: int = Field(
        default=400,
        ge=200,
        le=800,
        description="Panel width in pixels"
    )
    welcome_message: str = Field(
        default="Hello! How can I help you understand this data?",
        description="Initial message shown to users"
    )
    suggested_questions: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Suggested questions to show users"
    )
    visualization_awareness: VisualizationAwareness = Field(
        default_factory=VisualizationAwareness,
        description="Visualization awareness settings"
    )


# =============================================================================
# Logging Models
# =============================================================================

class Logging(BaseModel):
    """Logging configuration."""
    
    model_config = ConfigDict(extra="forbid")
    
    log_conversations: bool = Field(
        default=True,
        description="Whether to log conversations"
    )
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Logging level"
    )
    include_in_logs: list[str] = Field(
        default_factory=lambda: [
            "session_id",
            "user_id",
            "dashboard_id",
            "question",
            "latency_ms",
        ],
        description="Fields to include in logs"
    )
    exclude_from_logs: list[str] = Field(
        default_factory=lambda: [
            "full_response_text",
        ],
        description="Fields to exclude from logs"
    )
    retention_days: int = Field(
        default=90,
        ge=1,
        le=365,
        description="Log retention period in days"
    )


# =============================================================================
# Root Configuration Model
# =============================================================================

class ChatbotConfig(BaseModel):
    """
    Complete chatbot configuration.
    
    This is the root model that contains all configuration sections.
    Use ChatbotConfig.from_file() to load from disk.
    
    Supports both JSON and YAML formats. Format is auto-detected when reading.
    JSON is used by default when writing.
    """
    
    model_config = ConfigDict(extra="forbid")
    
    version: str = Field(
        default="1.0.0",
        pattern=r"^\d+\.\d+\.\d+$",
        description="Configuration schema version"
    )
    metadata: ConfigMetadata = Field(
        ...,
        description="Configuration metadata"
    )
    
    # Priority 1: Foundation (MVP Required)
    llm_credentials: LLMCredentials = Field(
        ...,
        description="LLM provider credentials (Anthropic via Bedrock or OpenAI)"
    )
    llm_parameters: LLMParameters = Field(
        ...,
        description="LLM parameters (temperature, max_tokens, etc.)"
    )
    data_context: DataContext = Field(
        ...,
        description="Data context and semantic layer"
    )
    system_prompt: SystemPrompt = Field(
        ...,
        description="System prompt configuration"
    )
    guardrails: Guardrails = Field(
        default_factory=Guardrails,
        description="Safety guardrails"
    )
    
    # Priority 2: Enhanced Functionality
    structured_output: StructuredOutput = Field(
        default_factory=StructuredOutput,
        description="Structured output configuration"
    )
    conversation_memory: ConversationMemory = Field(
        default_factory=ConversationMemory,
        description="Conversation memory settings"
    )
    elicitation: Elicitation = Field(
        default_factory=Elicitation,
        description="Elicitation configuration for disambiguation"
    )
    
    # Priority 3: Advanced Capabilities
    mcp_tools: MCPTools = Field(
        default_factory=MCPTools,
        description="MCP tools configuration"
    )
    mcp_resources: MCPResources = Field(
        default_factory=MCPResources,
        description="MCP resources configuration"
    )
    
    # Dashboard Integration
    dashboard_integration: DashboardIntegration = Field(
        default_factory=DashboardIntegration,
        description="Dashboard integration settings"
    )
    
    # Logging
    logging: Logging = Field(
        default_factory=Logging,
        description="Logging configuration"
    )

    @classmethod
    def from_file(cls, path: str | Path) -> "ChatbotConfig":
        """
        Load and validate a configuration from a JSON or YAML file.
        
        The format is auto-detected from the file contents, not the extension.
        
        Args:
            path: Path to the configuration file.
            
        Returns:
            Validated ChatbotConfig instance.
            
        Raises:
            FileNotFoundError: If the file doesn't exist.
            ValueError: If the file cannot be parsed.
            pydantic.ValidationError: If the configuration is invalid.
            
        Example:
            config = ChatbotConfig.from_file("configs/sales-dashboard.yaml")
            config = ChatbotConfig.from_file("configs/sales-dashboard.json")
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        data = parse_content(content)
        return cls.model_validate(data)

    @classmethod
    def from_string(cls, content: str) -> "ChatbotConfig":
        """
        Load and validate a configuration from a JSON or YAML string.
        
        The format is auto-detected from the content.
        
        Args:
            content: Configuration content as a string.
            
        Returns:
            Validated ChatbotConfig instance.
        """
        data = parse_content(content)
        return cls.model_validate(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChatbotConfig":
        """
        Load and validate a configuration from a dictionary.
        
        Args:
            data: Configuration dictionary.
            
        Returns:
            Validated ChatbotConfig instance.
        """
        return cls.model_validate(data)

    def to_file(
        self, 
        path: str | Path, 
        format: FileFormat | str = FileFormat.JSON
    ) -> None:
        """
        Save the configuration to a file.
        
        Args:
            path: Path to save the configuration to.
            format: Output format - "json" (default) or "yaml".
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        if isinstance(format, str):
            format = FileFormat(format.lower())
        
        data = self.model_dump(by_alias=True, exclude_none=True)
        content = serialize_content(data, format)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def to_json(self) -> str:
        """
        Serialize the configuration to a JSON string.
        
        Returns:
            JSON string.
        """
        data = self.model_dump(by_alias=True, exclude_none=True)
        return serialize_content(data, FileFormat.JSON)

    def to_yaml(self) -> str:
        """
        Serialize the configuration to a YAML string.
        
        Returns:
            YAML string.
        """
        data = self.model_dump(by_alias=True, exclude_none=True)
        return serialize_content(data, FileFormat.YAML)

    def get_system_prompt_text(self) -> str:
        """
        Build the complete system prompt including persona and guidelines.
        
        Returns:
            Complete system prompt string ready for LLM.
        """
        parts = [self.system_prompt.base_prompt]
        
        if self.system_prompt.persona.personality_traits:
            traits = ", ".join(self.system_prompt.persona.personality_traits)
            parts.append(f"\nPersonality: {traits}")
        
        if self.system_prompt.response_guidelines:
            guidelines = "\n".join(
                f"- {g}" for g in self.system_prompt.response_guidelines
            )
            parts.append(f"\nResponse guidelines:\n{guidelines}")
        
        if self.data_context.semantic_layer.business_terms:
            terms = "\n".join(
                f"- {term}: {definition}"
                for term, definition in self.data_context.semantic_layer.business_terms.items()
            )
            parts.append(f"\nBusiness terminology:\n{terms}")
        
        return "\n".join(parts)

    def get_datasource_ids(self) -> list[str]:
        """
        Get list of Portal datasource IDs referenced by this config.
        
        Returns:
            List of datasource IDs.
        """
        return [ds.portal_datasource_id for ds in self.data_context.datasources]

    def get_llm_provider(self) -> LLMProvider:
        """
        Get the configured LLM provider.
        
        Returns:
            The LLM provider enum value.
        """
        return self.llm_credentials.provider


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python chatbot_config.py <config_file>")
        print("\nThis will validate the configuration and print a summary.")
        print("Supports both JSON and YAML formats (auto-detected).")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    try:
        config = ChatbotConfig.from_file(config_path)
        print(f"[OK] Configuration '{config.metadata.name}' loaded successfully!")
        print(f"\n  Description: {config.metadata.description}")
        print(f"  Version: {config.version}")
        print(f"  Author: {config.metadata.author}")
        print(f"  LLM Provider: {config.get_llm_provider().value}")
        print(f"  LLM Model: {config.llm_parameters.model}")
        print(f"  Datasources: {len(config.data_context.datasources)}")
        print(f"  Business terms: {len(config.data_context.semantic_layer.business_terms)}")
        print(f"  Field mappings: {len(config.data_context.semantic_layer.field_mappings)}")
        print(f"  Sample questions: {len(config.data_context.sample_questions)}")
        print(f"  Guardrails enabled: Yes")
        print(f"  MCP tools enabled: {config.mcp_tools.enabled}")
        print(f"  MCP resources enabled: {config.mcp_resources.enabled}")
        
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"[ERROR] Parse error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Validation error: {e}")
        sys.exit(1)
