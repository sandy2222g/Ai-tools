"""End-to-end isolation tests against a real Docker daemon and the sandbox image.

Run with:  make docker && pytest -m docker
Skipped automatically when Docker or the sandbox image is not available.
"""

import pytest

from tools._common import isolation
from tools.run_code.tool import run_code

pytestmark = pytest.mark.docker

requires_docker = pytest.mark.skipif(
    not isolation._docker_ready(),
    reason="Docker daemon or sandbox image unavailable (run `make docker`)",
)


@requires_docker
def test_container_has_no_network():
    code = (
        "import socket\n"
        "try:\n"
        "    socket.create_connection(('1.1.1.1', 53), timeout=3)\n"
        "    print('CONNECTED')\n"
        "except OSError as e:\n"
        "    print('BLOCKED', type(e).__name__)\n"
    )
    result = run_code(code, timeout=20, isolation="docker")
    assert result["isolation"] == "docker"
    assert "CONNECTED" not in result["stdout"]
    assert "BLOCKED" in result["stdout"]


@requires_docker
def test_root_filesystem_is_read_only():
    code = (
        "try:\n"
        "    open('/etc/ai-tools-write-test', 'w')\n"
        "    print('WRITABLE')\n"
        "except OSError:\n"
        "    print('READONLY')\n"
    )
    result = run_code(code, timeout=20, isolation="docker")
    assert "READONLY" in result["stdout"]


@requires_docker
def test_container_runs_unprivileged():
    result = run_code("import os; print(os.getuid())", timeout=20, isolation="docker")
    assert result["stdout"].strip() != "0"


@requires_docker
def test_host_environment_is_not_visible(monkeypatch):
    monkeypatch.setenv("AI_TOOLS_TEST_SECRET", "must-not-leak")
    result = run_code(
        "import os; print(os.environ.get('AI_TOOLS_TEST_SECRET', 'absent'))",
        timeout=20,
        isolation="docker",
    )
    assert result["stdout"].strip() == "absent"


@requires_docker
def test_runaway_container_is_killed_on_timeout():
    result = run_code("while True:\n    pass", timeout=3, isolation="docker")
    assert result["timed_out"] is True
