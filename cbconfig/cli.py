"""
Command-line interface for the Chatbot Configuration Manager.

This module provides the entry point for running the Django development server
when the package is installed via pip/uv.
"""

import os
import sys
from pathlib import Path


def main():
    """Launch the Django development server for chatbot configuration management."""

    print("=" * 50)
    print("  Chatbot Configuration Editor")
    print("=" * 50)
    print()

    # Set up Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cbconfig.settings')

    # Import Django
    try:
        import django
        from django.core.management import execute_from_command_line
    except ImportError as e:
        print(f"Error: Failed to import Django: {e}")
        print()
        print("This should not happen. Please ensure Django is installed correctly.")
        sys.exit(1)

    # Setup Django
    django.setup()

    print("Initializing application...")
    print()

    # Run migrations
    print("Setting up database...")
    try:
        execute_from_command_line(['cbc-server', 'migrate', '--no-input'])
    except SystemExit:
        pass  # Django calls sys.exit, which we need to catch

    # Check if a superuser exists, if not create one
    print()
    print("Checking for admin user...")

    from django.contrib.auth import get_user_model
    User = get_user_model()

    try:
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin')
            print("Created admin user: admin/admin")
        else:
            print("Admin user already exists")
    except Exception as e:
        print(f"Note: {e}")

    print()
    print("=" * 50)
    print("  Starting Development Server")
    print("=" * 50)
    print()
    print("Admin interface will be available at:")
    print("  http://127.0.0.1:8000/admin/")
    print()
    print("Login credentials:")
    print("  Username: admin")
    print("  Password: admin")
    print()
    print("Configuration files will be stored in:")
    print(f"  {Path.cwd()}")
    print()
    print("Press Ctrl+C to stop the server")
    print()

    # Start the Django development server
    execute_from_command_line(['cbc-server', 'runserver'])


if __name__ == '__main__':
    main()
