from http.server import HTTPServer, BaseHTTPRequestHandler
import os


PORT = int(os.environ.get("PORT", 10000))


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Celery Worker Alive")


server = HTTPServer(("0.0.0.0", PORT), Handler)

print(f"Keep-alive server running on port {PORT}")

server.serve_forever()