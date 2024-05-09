import struct
import click
from sqlalchemy import create_engine, event
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base
from azure import identity

SQL_COPT_SS_ACCESS_TOKEN = 1256 # Connection option for access tokens, as defined in msodbcsql.h
TOKEN_URL = "https://database.windows.net/.default" # The token URL for any Azure SQL database

# Should be grabbed from environment variables
connection_string = 'Driver={ODBC Driver 18 for SQL Server};Server=tcp:comp4321-db.database.windows.net,1433;Database=SearchDB;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30'
connection_url = URL.create(
    "mssql+pyodbc",
    query={
        "odbc_connect": connection_string
    }
)

engine = create_engine(connection_url.render_as_string())

azure_credentials = identity.DefaultAzureCredential()

@event.listens_for(engine, "do_connect")
def provide_token(dialect, conn_rec, cargs, cparams):
    # remove the "Trusted_Connection" parameter that SQLAlchemy adds
    cargs[0] = cargs[0].replace(";Trusted_Connection=Yes", "")

    # create token credential
    raw_token = azure_credentials.get_token(TOKEN_URL).token.encode("utf-16-le")
    token_struct = struct.pack(f"<I{len(raw_token)}s", len(raw_token), raw_token)

    # apply it to keyword arguments
    cparams["attrs_before"] = {SQL_COPT_SS_ACCESS_TOKEN: token_struct}

db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))

Base = declarative_base()
Base.query = db_session.query_property()

def init_db() -> None:
    import app.models
    Base.metadata.create_all(bind=engine)

@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

def init_app(app):
    app.teardown_appcontext(shutdown_session)
    app.cli.add_command(init_db_command)

def shutdown_session(e=None):
        db_session.remove()