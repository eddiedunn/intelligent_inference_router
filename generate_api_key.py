#!/usr/bin/env python3
"""
API Key Generator for Intelligent Inference Router

- Generates a secure random API key
- Optionally accepts a prefix/label
- Prints the key to stdout
- Optionally sets the key in the server .env and a client env file
"""
import secrets
import string
import argparse
import os
from pathlib import Path
import shutil

DEFAULT_KEY_LENGTH = 40
SERVER_ENV_PATH = Path(".env")
CLIENT_ENV_PATH = Path("client.env")


def generate_key(length=DEFAULT_KEY_LENGTH, prefix=None):
    alphabet = string.ascii_letters + string.digits
    key = ''.join(secrets.choice(alphabet) for _ in range(length))
    if prefix:
        return f"{prefix}_{key}"
    return key


def set_env_key(env_path, api_key, key_name="ROUTER_API_KEY"):
    """Set (or replace) the API key in a .env-style file, preserving all other lines and comments."""
    backup_path = env_path.with_suffix(env_path.suffix + ".bak")
    if env_path.exists():
        shutil.copy(env_path, backup_path)
        with open(env_path, "r") as f:
            lines = f.readlines()
        found = False
        new_lines = []
        for line in lines:
            # Preserve comments and blank lines exactly
            if line.strip().startswith(f"{key_name}="):
                new_lines.append(f"{key_name}={api_key}\n")
                found = True
            else:
                new_lines.append(line)
        if not found:
            # Add API key at the end, but preserve a trailing newline if present
            if new_lines and new_lines[-1] and not new_lines[-1].endswith("\n"):
                new_lines[-1] = new_lines[-1] + "\n"
            new_lines.append(f"{key_name}={api_key}\n")
        with open(env_path, "w") as f:
            f.writelines(new_lines)
    else:
        with open(env_path, "w") as f:
            f.write(f"{key_name}={api_key}\n")
    print(f"Set {key_name} in {env_path} (backup: {backup_path if backup_path.exists() else 'none'})")


def main():
    parser = argparse.ArgumentParser(description="Generate a secure API key.")
    parser.add_argument("--length", type=int, default=DEFAULT_KEY_LENGTH, help="Key length (default: 40)")
    parser.add_argument("--prefix", type=str, default=None, help="Optional prefix/label for the key")
    parser.add_argument("--set-server-env", action="store_true", help="Set key in .env for server")
    parser.add_argument("--set-client-env", action="store_true", help="Set key in client.env for client use")
    parser.add_argument("--client-path", type=str, default=None, help="Custom path for client env file")
    args = parser.parse_args()

    api_key = generate_key(length=args.length, prefix=args.prefix)
    print(f"Generated API key: {api_key}")

    if args.set_server_env:
        set_env_key(SERVER_ENV_PATH, api_key)
    if args.set_client_env:
        client_path = Path(args.client_path) if args.client_path else CLIENT_ENV_PATH
        set_env_key(client_path, api_key)

if __name__ == "__main__":
    main()
