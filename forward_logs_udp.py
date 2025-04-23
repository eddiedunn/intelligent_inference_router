#!/usr/bin/env python3
"""
Forward Docker Compose logs to a remote UDP sink.
Usage: python forward_logs_udp.py --sink host:port
"""
import argparse
import socket
import subprocess
import sys

def main():
    parser = argparse.ArgumentParser(description="Forward docker compose logs to UDP.")
    parser.add_argument('--sink', required=True, help='host:port of remote log sink')
    args = parser.parse_args()
    host, port = args.sink.split(":")
    port = int(port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    proc = subprocess.Popen(['docker', 'compose', 'logs', '-f'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        for line in proc.stdout:
            sock.sendto(line, (host, port))
            sys.stdout.buffer.write(line)
            sys.stdout.buffer.flush()
    except KeyboardInterrupt:
        proc.terminate()
    finally:
        sock.close()

if __name__ == "__main__":
    main()
