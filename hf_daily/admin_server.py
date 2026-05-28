from __future__ import annotations

import json
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .site_builder import SiteBuilder
from .storage import ProjectPaths, read_json, write_json


class AdminHTTPServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[SimpleHTTPRequestHandler],
        paths: ProjectPaths,
    ) -> None:
        super().__init__(server_address, handler_class)
        self.paths = paths


def create_admin_server(
    paths: ProjectPaths,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> AdminHTTPServer:
    handler = partial(AdminRequestHandler, directory=str(paths.site_dir))
    return AdminHTTPServer((host, port), handler, paths)


class AdminRequestHandler(SimpleHTTPRequestHandler):
    server: AdminHTTPServer

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_POST(self) -> None:
        if self.path != "/api/tag-overrides":
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown admin endpoint")
            return

        try:
            payload = self._read_json_body()
            paper_id = str(payload.get("paper_id", "")).strip()
            if not paper_id:
                self._send_json({"error": "paper_id is required"}, HTTPStatus.BAD_REQUEST)
                return
            overrides = _update_tag_override(self.server.paths, paper_id, payload)
            SiteBuilder(self.server.paths).build()
            self._send_json({"status": "saved", "paper_overrides": overrides["paper_overrides"]})
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body"}, HTTPStatus.BAD_REQUEST)
        except OSError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8")
        payload = json.loads(raw_body or "{}")
        if not isinstance(payload, dict):
            raise json.JSONDecodeError("JSON body must be an object", raw_body, 0)
        return payload

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _update_tag_override(
    paths: ProjectPaths,
    paper_id: str,
    payload: dict[str, Any],
) -> dict[str, dict[str, dict[str, str]]]:
    overrides = read_json(paths.tag_overrides, {"paper_overrides": {}})
    paper_overrides = overrides.get("paper_overrides", {})
    if not isinstance(paper_overrides, dict):
        paper_overrides = {}

    fields = {
        field: str(payload.get(field, "")).strip()
        for field in ["institution_tag", "topic_tag"]
        if str(payload.get(field, "")).strip()
    }
    if fields:
        paper_overrides[paper_id] = fields
    else:
        paper_overrides.pop(paper_id, None)

    cleaned = {"paper_overrides": dict(sorted(paper_overrides.items()))}
    write_json(paths.tag_overrides, cleaned)
    return cleaned
