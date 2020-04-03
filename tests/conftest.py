import pytest, logging


@pytest.fixture
def app():
    import flask
    app = flask.Flask(__name__)
    app.debug = True
    app.testing = True
    return app


@pytest.fixture
def client(app):
    yield app.test_client()