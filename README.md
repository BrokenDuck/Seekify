# Deploy a Python (Flask) web app with PostgreSQL in Azure

This is a Python web app using the Flask framework and the Azure Database for PostgreSQL relational database service. The Flask app is hosted in a fully managed Azure App Service. This app is designed to be be run locally and then deployed to Azure.

This webapp implements a simple WebEngine in python.

## Requirements

The [requirements.txt](./requirements.txt) has the following packages.

| Package | Description |
| ------- | ----------- |
| [Flask](https://pypi.org/project/Flask/) | Web application framework. |
| [SQLAlchemy](https://pypi.org/project/SQLAlchemy/) | Provides a database abstraction layer to communicate with PostgreSQL. |
| [Flask-SQLAlchemy](https://pypi.org/project/Flask-SQLAlchemy/) | Adds SQLAlchemy support to Flask application by simplifying using SQLAlchemy. Requires SQLAlchemy. |
| [Flask-Migrate](https://pypi.org/project/Flask-Migrate/) | SQLAlchemy database migrations for Flask applications using Alembic. Allows functionality parity with Django version of this sample app.|
| [pyscopg2](https://pypi.org/project/psycopg2/) | PostgreSQL database adapter for Python. |
| [python-dotenv](https://pypi.org/project/python-dotenv/) | Read key-value pairs from .env file and set them as environment variables. In this sample app, those variables describe how to connect to the database locally. <br><br> Flask's [dotenv support](https://flask.palletsprojects.com/en/2.1.x/cli/#environment-variables-from-dotenv) sets environment variables automatically from an `.env` file. |
| [flask_wtf](https://pypi.org/project/Flask-WTF/) | Form rendering, validation, and CSRF protection for Flask with WTForms. Uses CSRFProtect extension. |
| nltk | language processing library |
| lxml | html tree parsing library |
| beautifulsoup4 | interface for html parsing |

## Run the sample

This project has a [dev container configuration](.devcontainer/), which makes it easier to develop apps locally, deploy them to Azure, and monitor them. The easiest way to run this sample application is inside a GitHub codespace. Follow these steps:

1. Fork this repository to your account. For instructions, see [Fork a repo](https://docs.github.com/get-started/quickstart/fork-a-repo).

1. From the repository root of your fork, select **Code** > **Codespaces** > **+**.

1. In the codespace terminal, run the following commands:

    ```shell
    # Install requirements
    python3 -m pip install -r requirements.txt
    # Create .env with environment variables
    cp .env.sample.devcontainer .env
    # Run database migrations
    python3 -m flask db upgrade
    # Run the spider to index the files
    flask --app app init-spider url
    # Start the development server
    flask --app app run
    ```

1. When you see the message `Your application running on port 8000 is available.`, click **Open in Browser**.