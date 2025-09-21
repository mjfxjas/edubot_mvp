#!/usr/bin/env python3
import json, subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8080

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")        # CORS
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        if self.path not in ("/creds", "/creds.json", "/"):
            return self._send(404, {"error":"not found"})
        try:
            # Use your current AWS CLI creds/profile; set AWS_PROFILE if needed
            out = subprocess.check_output([
                "aws","sts","get-session-token",
                "--duration-seconds","900",
                "--query","Credentials","--output","json"
            ], stderr=subprocess.STDOUT)
            creds = json.loads(out.decode())
            return self._send(200, creds)
        except subprocess.CalledProcessError as e:
            return self._send(500, {"error":"sts_failed","details":e.output.decode()})

if __name__ == "__main__":
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
