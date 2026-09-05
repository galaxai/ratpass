import http.client
import http.server
import unittest

from ratpass.providers.base import start_callback_server


class _TestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(204)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass


class CallbackServerTests(unittest.TestCase):
    def test_starts_server_on_background_thread(self) -> None:
        server, thread = start_callback_server(_TestHandler, port=0)
        connection = http.client.HTTPConnection(
            "localhost", server.server_port, timeout=2
        )

        try:
            connection.request("GET", "/auth/callback")
            response = connection.getresponse()
            response.read()
        finally:
            connection.close()
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        self.assertEqual(response.status, 204)
        self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
