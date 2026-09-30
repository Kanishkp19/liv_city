"""T0.1: scaffold sanity - package imports and tooling baseline."""

import agentville


def test_package_imports() -> None:
    assert agentville.__version__ == "0.1.0"
