from flask import Flask
from api_v1 import GreetingV1

app = Flask(__name__)
app.register_blueprint(GreetingV1(), url_prefix='/v1')