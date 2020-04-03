from flask import Flask
from api_example import GreetingV1

app = Flask(__name__)
app.register_blueprint(GreetingV1())
