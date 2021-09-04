from . import app
from semoxy.io.config import Config


def test_status_endpoint(app):
    _, resp = app.test_client.get("/")

    assert resp.status == 200
    assert resp.json["software"] == "Semoxy"
    assert resp.json["repository"]
    assert resp.json["version"]
    assert resp.json["description"]
    assert resp.json["issueTracker"]


def test_info_endpoint(app):
    pass
