Create a standalone Django application intended to be run locally by a single person on
a laptop.  The Django "runserver" django-admin command should be used to run the
application -- there is no need to use a standalone webserver such as nginx.

The application is intended to perform CRUD operations on "chatbot configuration files".
The contents of each chatbot configuration file is JSON that can be read and validated
by calling the `ChatbotConfig.from_file` function (located in the
`bootstrap/chatbot_config.py` file).  Similarly, the `ChatbotConfig.to_file` function
can be used to write a configuration file to disk.

1. Configuration files (as well as any necessary application state) should be stored in
   the directory in which the application is started.

2. Configuration file names should be a six digit number starting at 1 and sequentially
   increasing.  If a configuration is deleted, the file name associated with the
   configuration should not be reused.

3. Within the configuration, "metadata.name" is the name of the specific
   configuration.  Configuration names must be unique -- there can be no duplicates.

Minimally, the user interface should support the following:

1. Scrollable list of existing configurations in increasing alphanumeric order of
   configuration name.  The name of the file should be displayed as well.
2. Delete configurations.
3. Rename configurations.
4. Create a new configuration.
5. Edit a configuration.

It is fine to use the Django admin interface for this purpose if it simplifies the code.
If the admin interface is used, please also use pleasing styling such as Django
Grappelli.

Additional requirements:

The application should be stored in an existing github repository:
github.com/kheast/cb-config.  The repository is public and is readable by anyone.

The user of the application should not have to install the application or deal with
Python virtualenvironments.  Instead, create a bash script named `cbc-edit`.  `cbc-edit`
will contain a shebang that uses `uv run` to download and the application and run it.
All that a user should need to run this application is a copy of the `cbc-edit`.

## ADDENDUM 2

Currently, the contents of the configuration file must be provided as a json blob.
Instead of this, make each field of the configuration editable in the user interface.

## ADDENDUM 3

The user of the application should never have to write JSON.  For example, in "Semantic
Layer", "Business Terms", they are currently expected to provide a JSON object mapping
terms to definitions.  Instead, update the interface to allow the user to define this
mapping without JSON.  For example, they should be able to perform CRUD operations on a
list of mappings for term to definition.  The same thing for "Field Mappings".

## ADDENDUM 4

I note that `cbc-edit` requires that the github repo be present on disk.  The idea was
that the user would not have to know about git or have the source code present on disk.
Instead, the desire was that the bash script have a `[tool.uv.sources]` section that
specified the application is taken directly from the public repo
`github.com/kheast/cb-config`.

**Implementation**: The `cbc-edit` script is now a standalone Python script that uses
PEP 723 inline script metadata with `[tool.uv.sources]` to pull the cb-config package
directly from GitHub. Users can download just the `cbc-edit` script and run it from
any directory. The application code is automatically downloaded from GitHub and cached
by uv. No cloning or local source code required.

