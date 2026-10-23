import inspect
import os

import pytest

# Environment needed to run against a real Zabbix server, see docker/test/seed.py
INTEGRATION_ENV = ["ZABBIX_URL", "ZABBIX_TOKEN", "REMOTE"]


def _is_integration(item: pytest.Item) -> bool:
    """
    Integration tests are built on one of the shared `base_*` test classes,
    which connect to Zabbix and the git remote.
    """
    if item.get_closest_marker("integration"):
        return True

    cls = getattr(item, "cls", None)

    if cls is None:
        return False

    return any(
        (module := inspect.getmodule(base))
        and module.__name__.split(".")[-1].startswith("base_")
        and module.__name__.split(".")[-1] != "base_test"
        for base in inspect.getmro(cls)
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]):
    missing = [key for key in INTEGRATION_ENV if not os.getenv(key)]
    skip = pytest.mark.skip(reason=f"Integration test, {', '.join(missing)} not set")

    for item in items:
        if not _is_integration(item):
            continue

        item.add_marker(pytest.mark.integration)

        if missing:
            item.add_marker(skip)
