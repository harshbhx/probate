"""BoxArchive against the connector's real URL layout: /2.0 for the API, /upload for uploads."""

import httpx

from probate.adapters.archive import BoxArchive

GATEWAY = "https://api.sprites.dev/v1/gateway/box/CONN"


class FakeBox:
    """Just enough of Box, keyed by the paths the connector exposes."""

    def __init__(self) -> None:
        self.folders: dict[str, dict] = {}  # id -> {name, parent}
        self.files: dict[str, dict] = {}  # id -> {name, parent, data}
        self.calls: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path.removeprefix("/v1/gateway/box/CONN")
        self.calls.append(f"{request.method} {path}")
        if request.method == "POST" and path == "/2.0/folders":
            import json

            body = json.loads(request.content)
            for fid, f in self.folders.items():
                if f["name"] == body["name"] and f["parent"] == body["parent"]["id"]:
                    return httpx.Response(409, json={"context_info": {"conflicts": [{"id": fid}]}})
            fid = f"d{len(self.folders) + 1}"
            self.folders[fid] = {"name": body["name"], "parent": body["parent"]["id"]}
            return httpx.Response(201, json={"id": fid})
        if request.method == "GET" and path.startswith("/2.0/folders/") and path.endswith("/items"):
            parent = path.split("/")[3]
            entries = [
                {"type": "file", "id": fid, "name": f["name"]}
                for fid, f in self.files.items()
                if f["parent"] == parent
            ]
            return httpx.Response(200, json={"entries": entries, "total_count": len(entries)})
        if request.method == "POST" and path == "/upload/files/content":
            raw = request.content.decode(errors="replace")
            import re

            name = re.search(r'"name": "([^"]+)"', raw).group(1)
            parent = re.search(r'"id": "([^"]+)"', raw).group(1)
            data = raw.split("\r\n\r\n")[-1].split("\r\n--")[0]
            fid = f"f{len(self.files) + 1}"
            self.files[fid] = {"name": name, "parent": parent, "data": data}
            return httpx.Response(201, json={"entries": [{"id": fid}]})
        if (
            request.method == "POST"
            and path.startswith("/upload/files/")
            and path.endswith("/content")
            and path != "/upload/files/content"
        ):
            fid = path.split("/")[3]
            raw = request.content.decode(errors="replace")
            self.files[fid]["data"] = raw.split("\r\n\r\n")[-1].split("\r\n--")[0]
            return httpx.Response(201, json={"entries": [{"id": fid}]})
        if request.method == "GET" and path.startswith("/2.0/files/") and path.endswith("/content"):
            fid = path.split("/")[3]
            return httpx.Response(200, text=self.files[fid]["data"])
        return httpx.Response(404, json={"path": path})


def _archive(box: FakeBox) -> BoxArchive:
    a = BoxArchive(GATEWAY)
    a.http = httpx.Client(transport=httpx.MockTransport(box.handler))
    return a


def test_urls_use_2_0_and_upload():
    a = BoxArchive(GATEWAY)
    assert a.base == GATEWAY + "/2.0" and a.upload == GATEWAY + "/upload"
    assert BoxArchive(GATEWAY + "/2.0").base == GATEWAY + "/2.0"


def test_a_file_written_by_one_process_is_found_by_another():
    box = FakeBox()
    writer, reader = _archive(box), _archive(box)  # two processes: separate caches
    writer.put_text("wills/WILL-gen-002.json", '[{"id": "m1"}]')
    assert reader.get_text("wills/WILL-gen-002.json") == '[{"id": "m1"}]'
    assert reader.get_text("wills/WILL-gen-009.json") is None
    assert not any(c.startswith("POST /folders") for c in box.calls)  # the 2.0 prefix is used


def test_append_text_works():
    box = FakeBox()
    a = _archive(box)
    a.put_text("log/a.md", "one")
    a.append_text("log/a.md", " two")
    assert a.get_text("log/a.md") == "one two"
