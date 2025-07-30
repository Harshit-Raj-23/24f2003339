from flask import Flask

app = Flask(__name__)

from config import *

from models import *

from routes import register_blueprints
register_blueprints(app)

if __name__ == "__main__":
    app.run(debug=True)