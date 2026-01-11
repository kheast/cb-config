# Chatbot Configuration Manager

A standalone Django application for managing chatbot configuration files locally. This tool provides a user-friendly web interface for performing CRUD operations on JSON-based chatbot configurations.

## Features

- **Web-based Admin Interface**: Clean, intuitive interface powered by Django Admin and Grappelli
- **File Management**: Automatic management of configuration files with sequential 6-digit naming (000001.json, 000002.json, etc.)
- **Validation**: Built-in validation using Pydantic models to ensure configuration correctness
- **Unique Names**: Enforces uniqueness of configuration names (metadata.name field)
- **Local Storage**: All configurations stored in your current working directory
- **No Installation Required**: Uses `uv` to automatically manage dependencies

## Requirements

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer

### Installing uv

If you don't have `uv` installed:

```bash
# macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Quick Start

1. Download the `cbc-edit` script:
```bash
curl -O https://raw.githubusercontent.com/kheast/cb-config/main/cbc-edit
chmod +x cbc-edit
```

2. Run the application:
```bash
./cbc-edit
```

3. Open your browser to: http://127.0.0.1:8000/admin/

4. Login with default credentials:
   - Username: `admin`
   - Password: `admin`

That's it! The application will automatically:
- Download the latest version from GitHub
- Install all required dependencies
- Set up the database
- Create an admin user
- Start the development server

**Note**: You don't need to clone the repository or have the source code locally. The `cbc-edit` script automatically installs the `cb-config` package from GitHub using uv, which handles all dependencies and caching.

## Usage

### Creating a Configuration

1. Click "Chatbot Configurations" in the admin interface
2. Click "Add Chatbot Configuration" button
3. Fill in:
   - **Name**: Unique identifier (kebab-case, e.g., "sales-dashboard")
   - **Description**: What this configuration is for
   - **Author**: Your name or email
   - **Config Data**: Complete JSON configuration
4. Click "Save"

The configuration will be:
- Validated against the ChatbotConfig schema
- Assigned the next available 6-digit filename
- Saved to disk in your current directory

### Listing Configurations

The main admin page displays all configurations in a sortable, searchable table showing:
- Configuration name
- Filename (e.g., 000001.json)
- Description (truncated)
- Author
- Created and modified timestamps

### Editing a Configuration

1. Click on any configuration in the list
2. Modify the fields or JSON data
3. Click "Save"

The file will be updated on disk and validated before saving.

### Renaming a Configuration

1. Click on the configuration to edit
2. Change the "Name" field
3. Click "Save"

The metadata.name in the JSON will be automatically updated to match.

### Deleting a Configuration

1. Select one or more configurations using checkboxes
2. Choose "Delete selected chatbot configurations" from the action dropdown
3. Click "Go" and confirm

The files will be removed from disk. **Note**: Deleted filenames are not reused.

## File Structure

```
your-working-directory/
├── cbc-edit             # The launcher script (download once)
├── 000001.json          # Configuration files
├── 000002.json
├── 000003.json
├── ...
└── cbconfig.db          # SQLite database
```

Configuration files are stored as JSON in the directory where you run `./cbc-edit`. The application code is automatically downloaded and cached by `uv` in your system cache directory, so you don't need the source code locally.

## Configuration File Format

Each configuration file must follow the ChatbotConfig schema defined in `bootstrap/chatbot_config.py`. At minimum, it requires:

```json
{
  "version": "1.0.0",
  "metadata": {
    "name": "example-config",
    "description": "Example configuration",
    "created": "2024-01-01T00:00:00Z",
    "modified": "2024-01-01T00:00:00Z",
    "author": "user@example.com"
  },
  "data_context": {
    "datasources": [
      {
        "name": "Example Data",
        "portal_datasource_id": "ds-123",
        "description": "Example datasource",
        "primary_entity": "Account"
      }
    ]
  },
  "system_prompt": {
    "base_prompt": "You are a helpful assistant..."
  }
}
```

Refer to `bootstrap/chatbot_config.py` for the complete schema definition.

## Architecture

### Components

- **Django**: Web framework providing the admin interface
- **Grappelli**: Admin interface styling
- **Pydantic**: Configuration validation via ChatbotConfig model
- **SQLite**: Local database for tracking configurations
- **uv**: Dependency management

### How It Works

1. **Models** (`configs/models.py`):
   - `ConfigurationFile` model wraps JSON files
   - Manages file I/O using ChatbotConfig.from_file() and to_file()
   - Enforces sequential naming and uniqueness constraints

2. **Admin** (`configs/admin.py`):
   - Custom admin interface with JSON editor
   - List view with filtering and search
   - Validation messages and error handling

3. **File Naming**:
   - Files named as 6-digit zero-padded numbers (000001-999999)
   - Sequential: finds highest existing number and adds 1
   - Deleted numbers are never reused

4. **Validation**:
   - All configs validated with Pydantic before saving
   - Ensures metadata.name uniqueness
   - Prevents invalid configurations from being saved

## Development

**Note**: This section is for developers who want to contribute to the project. End users don't need to clone the repository - just download and run the `cbc-edit` script as described in Quick Start above.

### For Contributors: Setting Up Development Environment

If you want to contribute to this project:

1. Clone the repository:
```bash
git clone https://github.com/kheast/cb-config.git
cd cb-config
```

2. Install dependencies:
```bash
uv sync
```

3. Run the development server:
```bash
uv run python manage.py runserver
```

### Project Structure

```
cb-config/
├── bootstrap/
│   └── chatbot_config.py      # Pydantic models
├── cbconfig/
│   ├── settings.py             # Django settings
│   ├── urls.py                 # URL routing
│   └── wsgi.py                 # WSGI config
├── configs/
│   ├── models.py               # ConfigurationFile model
│   ├── admin.py                # Admin interface
│   └── apps.py                 # App configuration
├── manage.py                   # Django management
├── cbc-edit                    # Standalone launcher script
├── pyproject.toml              # Dependencies
└── README.md                   # This file
```

### Running Management Commands

You can use `uv run` to execute any Django management command:

```bash
# Create migrations
uv run python manage.py makemigrations

# Run migrations
uv run python manage.py migrate

# Create a superuser
uv run python manage.py createsuperuser

# Open Django shell
uv run python manage.py shell
```

### Customization

To modify the admin interface, edit `configs/admin.py`. To change the data model, edit `configs/models.py` and create migrations.

## Troubleshooting

### "Configuration with name already exists"

Each configuration must have a unique name. Choose a different name or delete the existing configuration with that name.

### "Invalid configuration" error

The JSON data must conform to the ChatbotConfig schema. Check the error message for details about which fields are missing or invalid.

### Port already in use

If port 8000 is already in use, you can specify a different port:

```bash
uv run python manage.py runserver 8001
```

### Database issues

If you encounter database errors, you can reset by deleting `cbconfig.db` and restarting:

```bash
rm cbconfig.db
./cbc-edit
```

## License

This project is available for use under standard open source terms.

## Support

For issues or questions, please file an issue on the GitHub repository.
