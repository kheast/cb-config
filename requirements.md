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

