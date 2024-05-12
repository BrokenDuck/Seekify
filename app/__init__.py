import os
from datetime import datetime

import click
from flask import Flask, redirect, render_template, request, url_for
from flask_migrate import Migrate
from sqlalchemy.orm import DeclarativeBase
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

# need to run python3 -m nltk.downloader punkt stopwords

app = Flask(__name__, static_folder='static')
csrf = CSRFProtect(app)

# WEBSITE_HOSTNAME exists only in production environment
if 'WEBSITE_HOSTNAME' not in os.environ:
    # local development, where we'll use environment variables
    print("Loading config.development and environment variables from .env file.")
    app.config.from_object('azureproject.development')
else:
    # production
    print("Loading config.production.")
    app.config.from_object('azureproject.production')

app.config.update(
    SQLALCHEMY_DATABASE_URI=app.config.get('DATABASE_URI'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)

class Base(DeclarativeBase):
    pass

# Initialize the database connection
db = SQLAlchemy(app, model_class=Base)

# Enable Flask-Migrate commands "flask db init/migrate/upgrade" to work
migrate = Migrate(app, db)

# The import must be done after db initialization due to circular import issue
from app.models import Document, TitleTerm, BodyTerm, TitlePostingList, BodyPostingList, TitleCountList, BodyCountList

from app.spider import init_app
init_app(app)

def init_db():
    db.drop_all()
    db.create_all()
    db.session.commit()

@click.command('init-db')
def init_db_command():
    init_db()
    click.echo("Initialized db")

app.cli.add_command(init_db_command)

from app.spider import init_app
init_app(app)

@app.route('/hello')
def hello():
    return 'Hello, World!'

@app.route('/', methods=['GET'])
def base():
    return render_template('base.html')

from app.search import search_db

@app.route('/search', methods=['GET'])
def search():
    if 'q' in request.args:
        search_string = request.args['q']
    else:
        return redirect(url_for('index'))
    
    res = search_db(search_string)

    return render_template('search.html', results = res)