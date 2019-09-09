import pytest

from usim.py import Environment


@pytest.fixture
def env():
    return Environment()
