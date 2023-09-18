import argparse
import json
import logging
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

from workflow_monitor.Config import Config
from workflow_monitor.Namespace import PlatformNameSpace

logging.basicConfig(
    format="%(name)s: %(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)


class JSONRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length"))
        post_data = self.rfile.read(content_length)
        try:
            json_data = json.loads(post_data.decode("utf-8"))
            repost_with_token(json_data)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"JSON data received and processed.")
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid JSON data.")


def filter_message(message: dict):
    match message["event"]:
        case "started" | "completed" | "error":
            trace = {}
            if "trace" in message:
                trace = {
                    "trace_exit": message["trace"]["exit"],
                    "trace_name": message["trace"]["process"],
                }

            filtered_msg = {
                "run_name": message["runName"],
                "utc_time": message["utcTime"],
                "event": message["event"],
            }

            logger.info(f"Filtered message found: {filtered_msg}")
            yield filtered_msg | trace


def repost_with_token(message: dict):
    namespace = Config.namespace
    token = Config.callback_token

    # use a generator here to simplify ignoring 99% of messages in an infinite stream
    for msg in filter_message(message):
        if "INTP" not in msg["run_name"]:
            logger.critical(f"Invalid workflow ID: {msg['run_name']}")
            logger.critical("Workflow ID must be in the format: INTP00000000408")
            sys.exit(1)
        post_url = (
            f"https://{namespace}.intervenegeneticscores.org/pipeline-manager/csc"
            f"/pipeline/{msg['run_name']}/status"
        )
        header = {"Content-Type": "application/json", "Authorization": f"Basic {token}"}
        response = requests.post(post_url, data=json.dumps(msg), headers=header)

        match response.status_code:
            case 200:
                logger.info("Successfully notified backend")
            case _:
                logger.critical("Backend notification failed, bailing out")
                sys.exit(1)


def run(server_class=HTTPServer, handler_class=JSONRequestHandler):
    server_address = ("", 8000)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--callback_token", help="token to communicate with platform backend"
    )
    parser.add_argument(
        "--namespace", type=PlatformNameSpace.argparse, choices=list(PlatformNameSpace)
    )
    args = parser.parse_args()
    Config.namespace = args.namespace
    Config.callback_token = args.callback_token

    # run a local HTTP server forever (until parent process terminates)
    run()


if __name__ == "__main__":
    main()
