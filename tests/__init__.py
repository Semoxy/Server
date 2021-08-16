from sanic_testing import TestManager
from semoxy import Semoxy
import pytest


@pytest.fixture
def app():
    semoxy_app = Semoxy()
    TestManager(semoxy_app)

    return semoxy_app
