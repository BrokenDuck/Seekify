import os
from flask import Flask

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    
    # Initial config for flask application
    app.config.from_mapping(
        SECRET_KEY='dev',
    )

    # Load in test configuration if available
    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # Database connection initialisation
    from . import db
    db.init_app(app)

    # Spider initialization
    from . import spider
    spider.init_app(app)

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    return app