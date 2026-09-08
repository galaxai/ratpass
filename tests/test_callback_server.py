import http.client
import http.server

from ratpass.providers.base import start_callback_server


class _TestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(204)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass


def test_starts_server_on_background_thread() -> None:
    server, thread = start_callback_server(_TestHandler, port=0)
    connection = http.client.HTTPConnection("localhost", server.server_port, timeout=2)

    try:
        connection.request("GET", "/auth/callback")
        response = connection.getresponse()
        response.read()
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert response.status == 204
    assert not thread.is_alive()
