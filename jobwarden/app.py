from flask import Flask

app = Flask(__name__)
app.config.from_pyfile("../config.py")

# Import the views module to register the routes
from jobwarden.views import *  # noqa
