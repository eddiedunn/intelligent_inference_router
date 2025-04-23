import logging
import os
import socket

class UDPSocketHandler(logging.Handler):
    def __init__(self, sink_env_var="REMOTE_LOG_SINK"):
        super().__init__()
        sink = os.getenv(sink_env_var)
        if not sink:
            self.sock = None
            return
        host, port = sink.split(":")
        self.address = (host, int(port))
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def emit(self, record):
        if not self.sock:
            return
        try:
            msg = self.format(record)
            self.sock.sendto(msg.encode("utf-8"), self.address)
        except Exception:
            self.handleError(record)
