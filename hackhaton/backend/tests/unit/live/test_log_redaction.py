"""T050 — log-redaction regression.

The candump runner must not surface user@, port, identity files,
ProxyJump targets, or any other argv detail into log lines. The
contract (`contracts/websocket.md` §"Implementation notes") is that
the redacted form is `ssh <host> candump <iface>`, with override
presence collapsed to a `+overrides` token when the operator passed
any override(s).

This test pins both halves: the redacted form is correct, AND none
of the sensitive ssh argv ever leaks through the redacted property.
"""

from __future__ import annotations

from vayobd.live.candump_runner import CandumpRunner, _redacted_command


def test_redacted_command_default_form() -> None:
    assert (
        _redacted_command("ts-de-ber-zeus", "can0")
        == "ssh ts-de-ber-zeus candump can0"
    )


def test_redacted_command_collapses_user_override() -> None:
    redacted = _redacted_command(
        "ts-de-ber-zeus", "can0", user="someone-secret"
    )
    assert "someone-secret" not in redacted
    assert "+overrides" in redacted


def test_redacted_command_collapses_port_override() -> None:
    redacted = _redacted_command("ts-de-ber-zeus", "can0", port=2222)
    assert "2222" not in redacted
    assert "+overrides" in redacted


def test_redacted_command_collapses_both_overrides() -> None:
    redacted = _redacted_command(
        "ts-de-ber-zeus", "can0", user="alice", port=4242
    )
    assert "alice" not in redacted
    assert "4242" not in redacted
    assert redacted.count("+overrides") == 1


def test_runner_property_omits_sensitive_argv() -> None:
    """The CandumpRunner's `redacted_command` property is the single
    source of truth for log lines. Confirm it doesn't expose the ssh
    argv flags (BatchMode, ServerAliveInterval, etc.) or the override
    values.
    """
    runner = CandumpRunner(
        host_address="ts-de-ber-zeus",
        iface="can0",
        user="alice@vay",
        port=2222,
    )
    redacted = runner.redacted_command
    forbidden = [
        "BatchMode",
        "ServerAliveInterval",
        "ServerAliveCountMax",
        "ConnectTimeout",
        "alice@vay",
        "2222",
        "ProxyJump",
        "-i",
        "-o",
    ]
    for needle in forbidden:
        assert needle not in redacted, (
            f"redacted log line leaked {needle!r}: {redacted!r}"
        )
    # Positive: must include host + iface + overrides marker.
    assert "ts-de-ber-zeus" in redacted
    assert "can0" in redacted
    assert "+overrides" in redacted


def test_runner_property_no_overrides_marker_when_clean() -> None:
    runner = CandumpRunner(host_address="ts-de-ber-zeus", iface="can0")
    assert runner.redacted_command == "ssh ts-de-ber-zeus candump can0"


# --------------------------------------------------------------------------
# T055 — TOFU host-key policy ratification (FR-025).
#
# The 2026-05-07 clarification session pinned `accept-new` (TOFU) as the
# canonical host-key trust model. This test asserts that the ssh argv
# built by `CandumpRunner.start()` carries the right `-o` flag and
# never the bypass flags — the latter would silently disable MITM
# detection.
# --------------------------------------------------------------------------


def _capture_argv(monkeypatch, runner: CandumpRunner) -> list[str]:
    """Run `runner.start()` against a recording stub instead of a real
    ssh subprocess. Returns the argv that *would have been* passed to
    `asyncio.create_subprocess_exec`.
    """
    import asyncio

    captured: list[str] = []

    async def _fake_create_subprocess_exec(*argv, **_kwargs):
        captured.extend(argv)
        # Return a minimal awaitable that mimics the bits `start()`
        # touches. We never await `lines()` so streams can be None.

        class _Stub:
            stdout = None
            stderr = None
            returncode = None

            def terminate(self) -> None:  # pragma: no cover
                pass

            async def wait(self) -> int:  # pragma: no cover
                return 0

        return _Stub()

    monkeypatch.setattr(
        asyncio, "create_subprocess_exec", _fake_create_subprocess_exec
    )
    asyncio.run(runner.start())
    return captured


def test_ssh_argv_includes_accept_new_tofu_flag(monkeypatch) -> None:
    """FR-025: the spawned ssh MUST set StrictHostKeyChecking=accept-new
    so first-contact host keys auto-add to ~/.ssh/known_hosts and
    *changed* keys still fail.
    """
    runner = CandumpRunner(host_address="ts-de-ber-zeus", iface="can0")
    argv = _capture_argv(monkeypatch, runner)

    # Pair every `-o` flag with its value so we can assert on the kv set.
    pairs: list[tuple[str, str]] = []
    i = 0
    while i < len(argv) - 1:
        if argv[i] == "-o":
            pairs.append(("-o", argv[i + 1]))
            i += 2
        else:
            i += 1
    options = {kv for _, kv in pairs}

    assert "StrictHostKeyChecking=accept-new" in options


def test_ssh_argv_does_not_bypass_host_key_check(monkeypatch) -> None:
    """FR-025: the backend MUST NOT use `StrictHostKeyChecking=no` or
    redirect known_hosts to /dev/null — both bypass MITM detection.
    """
    runner = CandumpRunner(host_address="ts-de-ber-zeus", iface="can0")
    argv = _capture_argv(monkeypatch, runner)
    flat = " ".join(argv)

    forbidden = [
        "StrictHostKeyChecking=no",
        "UserKnownHostsFile=/dev/null",
    ]
    for needle in forbidden:
        assert needle not in flat, (
            f"ssh argv contained MITM-bypass option: {needle!r}"
        )
