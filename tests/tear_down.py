import shutil
import pytest
from pathlib import Path

@pytest.fixture(scope='session', autouse=True)
def teardown():
    """
    removes the policy config file after each test
    """
    path = Path.joinpath(Path.cwd(), "policyConfig")
    yield
    shutil.rmtree(path)