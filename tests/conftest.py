import pytest


def pytest_addoption(parser):
    parser.addoption("--runslow", action="store_true", default=False, help="run slow tests")


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")


def pytest_collection_modifyitems(config, items):
    if all("slow" in item.keywords for item in items):
        # If all tests are marked slow (like when starting tests explicitly through their IDE), the user has purposely
        # started the slow tests and we should not care about the --runslow flag
        return
    if config.getoption("--runslow"):
        # --runslow given in cli: run all tests
        return
    else:
        # --runslow not given in cli: skip slow tests, but run all other tests
        skip_slow = pytest.mark.skip(reason="need --runslow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
