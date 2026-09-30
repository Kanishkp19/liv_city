"""Sandbox runner (VERIFIERS S9): hardened docker-py execution, always fail closed."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


class SandboxUnavailable(Exception):
    """Docker missing or daemon down; callers must treat as verifier failure."""


@dataclass
class SandboxResult:
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool = False
    cpu_ms: int = 0
    mem_mb: int = 0


DOCKER_FLAGS = {
    "network_disabled": True,       # --network none
    "read_only": True,              # read-only rootfs
    "user": "65534",                # nobody
    "cap_drop": ["ALL"],
    "security_opt": ["no-new-privileges"],
    "pids_limit": 64,
    "mem_limit": "256m",
    "nano_cpus": int(0.5 * 1e9),
    "tmpfs": {"/work": "rw,size=64m,noexec"},
}


class SandboxRunner:
    """run(image, files, cmd, timeout) -> SandboxResult inside a locked-down container."""

    def __init__(self) -> None:
        try:
            import docker

            self.client: Any = docker.from_env()
            self.client.ping()
        except Exception as e:  # noqa: BLE001
            raise SandboxUnavailable(f"docker unavailable: {e}") from e

    def run(
        self,
        image: str,
        files: dict[str, bytes],
        cmd: list[str],
        *,
        timeout_s: int = 15,
        workdir: str = "/work",
    ) -> SandboxResult:
        """Write files to tmpfs /work, exec cmd, capture <=64KB output, always remove."""
        out_cap = 64 * 1024
        host = self.client.containers.run(
            image,
            command=cmd,
            detach=True,
            working_dir=workdir,
            **DOCKER_FLAGS,
        )
        try:
            # copy files in via exec (tar) - kept minimal: write via sh for tiny fixtures
            for name, content in files.items():
                b64 = __import__("base64").b64encode(content).decode()
                host.exec_run(f"sh -c 'echo {b64} | base64 -d > {workdir}/{name}'")
            started = time.monotonic()
            rc = host.wait(timeout=timeout_s)
            elapsed_ms = int((time.monotonic() - started) * 1000)
            logs = host.logs(stdout=True, stderr=True)
            if isinstance(logs, bytes):
                logs = logs[:out_cap].decode("utf-8", "replace")
            exit_code = rc.get("StatusCode") if isinstance(rc, dict) else getattr(rc, "StatusCode", None)
            return SandboxResult(exit_code=exit_code, stdout=str(logs)[:out_cap], stderr="", cpu_ms=elapsed_ms)
        except Exception as e:  # noqa: BLE001
            name = type(e).__name__
            if "timeout" in name.lower() or "read timed out" in str(e).lower():
                return SandboxResult(exit_code=None, stdout="", stderr="timeout", timed_out=True)
            return SandboxResult(exit_code=None, stdout="", stderr=f"sandbox error: {e}")
        finally:
            import contextlib

            with contextlib.suppress(Exception):
                host.remove(force=True)


def run_or_fail(
    image: str,
    files: dict[str, bytes],
    cmd: list[str],
    *,
    timeout_s: int = 15,
) -> SandboxResult:
    """Convenience: SandboxUnavailable becomes a failed result (fail closed)."""
    try:
        runner = SandboxRunner()
    except SandboxUnavailable as e:
        return SandboxResult(exit_code=None, stdout="", stderr=f"sandbox unavailable: {e}")
    return runner.run(image, files, cmd, timeout_s=timeout_s)
