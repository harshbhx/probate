"""The Sprites exec endpoint answers with a framed stream: 1 stdout, 2 stderr, 3 + exit code."""

import httpx

from probate.adapters.sprites import SpritesAPI, parse_frames

REAL = (
    b"\x02/home/sprite/.bashrc: line 22: bind: warning: line editing not enabled\n"
    b"\x02/home/sprite/.bashrc: line 23: bind: warning: line editing not enabled\n"
    b'\x01{"state": "living", "gen": 1, "name": "Ada", "emails": 0}\n'
    b"\x03\x00"
)


def test_stdout_stderr_and_exit_code_are_separated():
    res = parse_frames(REAL)
    assert res is not None and res.exit_code == 0
    assert res.stdout.strip() == '{"state": "living", "gen": 1, "name": "Ada", "emails": 0}'
    assert res.stderr.count("bind: warning") == 2


def test_a_failing_command_reports_its_exit_code():
    res = parse_frames(b"\x02boom\n\x03\x01")
    assert res is not None and res.exit_code == 1 and res.stderr == "boom\n" and res.stdout == ""


def test_an_exit_code_that_looks_like_a_marker_is_still_an_exit_code():
    res = parse_frames(b"\x01hi\n\x03\x02")
    assert res is not None and res.exit_code == 2 and res.stdout == "hi\n"


def test_plain_text_is_not_framed():
    assert parse_frames(b'{"exit_code": 0}') is None
    assert parse_frames(b"") is None


def test_exec_uses_the_frames():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=REAL, headers={"content-type": "application/octet-stream"}
        )

    api = SpritesAPI("t")
    api.http = httpx.Client(transport=httpx.MockTransport(handler))
    res = api.exec("gen-001-ada", ["bash", "-lc", "true"])
    assert res.exit_code == 0 and res.stdout.strip().startswith('{"state"')


def test_exec_still_accepts_json():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"exit_code": 3, "stdout": "x", "stderr": ""})

    api = SpritesAPI("t")
    api.http = httpx.Client(transport=httpx.MockTransport(handler))
    assert api.exec("s", ["true"]).exit_code == 3
