# Setup Guide: IIR MVP Phase 1a

## Prerequisites
- Debian 12 (or compatible Linux)
- NVIDIA RTX 4090 with drivers (≥535) for GPU inference
- NVIDIA Container Toolkit
- Docker & Docker Compose
- Git
- Python 3.7+ for utility scripts

---

## Step-by-Step Setup

1. **Clone the repository**
   ```sh
   git clone https://github.com/eddiedunn/intelligent_inference_router.git
   cd intelligent_inference_router
   ```

2. **Copy and configure your environment**
   ```sh
   cp .env.example .env
   ```

3. **Generate a secure API key for both server and client**
   ```sh
   python generate_api_key.py --set-server-env --set-client-env
   # Optionally, add --prefix myproject or --client-path path/to/client.env
   ```

4. **[Optional] Enable remote log forwarding for debugging**
   - Edit `.env` and set:
     ```
     REMOTE_LOG_SINK=host:port  # e.g., 1.2.3.4:9999
     ```
   - **All logs will be sent to your REMOTE_LOG_SINK** ("tee" style):
     - Application logs (from all Python logging calls) are forwarded to the remote sink as well as stdout.
     - Docker Compose logs (from all containers) are also forwarded if you use `make logs` or `make deploy-test`.
   - **Recommended:** Use [logflow](https://github.com/eddiedunn/logflow) as your log destination.
     1. Clone and run logflow on your destination server:
        ```sh
        git clone https://github.com/eddiedunn/logflow.git
        cd logflow
        pip install -r requirements.txt
        python logflow.py --listen 0.0.0.0:9999
        # Or use Docker:
        docker run --rm -p 9999:9999/udp ghcr.io/eddiedunn/logflow:latest --listen 0.0.0.0:9999
        ```
     2. Set your `REMOTE_LOG_SINK` to the IP and port where logflow is running (e.g., `REMOTE_LOG_SINK=your.server.ip:9999`).
   - (Alternative: For quick debugging, you can use the simple Python UDP listener below.)
     ```python
     import socket
     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
     sock.bind(("0.0.0.0", 9999))
     while True:
         data, addr = sock.recvfrom(4096)
         print(data.decode(), end="")
     ```
   - Then run:
     ```sh
     make logs
     # or as part of
     make deploy-test
     ```

## Hugging Face Token for Gated Models

Some models (such as Meta Llama 3) are gated on Hugging Face and require authentication to download.

If you see errors like `401 Unauthorized` or `Cannot access gated repo` in your logs, you must:

1. **Request access** to the model at: https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct
2. **Get your Hugging Face access token**: https://huggingface.co/settings/tokens
3. **Add your token to the `.env` file**:
   ```sh
   HF_TOKEN=your_huggingface_token_here
   ```
4. **Restart the stack**:
   ```sh
   make deploy-test
   # or
   docker compose up -d
   ```

If you do not add this token, the vLLM container will fail to start and you will see repeated authentication errors in the logs.

---

5. **Build and start the stack**
   ```sh
   docker compose build
   docker compose up -d
   ```

6. **Check service status and logs**
   ```sh
   docker compose ps
   docker compose logs -f router
   ```

7. **Test the API**
   - Health check: [http://localhost:8000/health](http://localhost:8000/health)
   - OpenAPI docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Running Multiple Stacks (Dev/Test)

To run a second stack on the same host (e.g., for parallel dev/testing):

1. Copy and edit the override file:
   ```sh
   cp docker-compose.override-sample.yml docker-compose.override-stack2.yml
   # Edit ports as needed in the new file
   ```

2. Start with a unique project name:
   ```sh
   COMPOSE_PROJECT_NAME=stack2 docker compose -f docker-compose.yml -f docker-compose.override-stack2.yml up -d
   ```

---

## Troubleshooting

- See `docs/TROUBLESHOOTING.md` for common issues.
- For authentication errors, double-check your API key in `.env` and client config.
- For port conflicts, use the override file and unique `COMPOSE_PROJECT_NAME`.

---

**For more details, see:**
- [docs/API.md](docs/API.md) for endpoint and usage details
- [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for environment/config options
- [docs/MONITORING.md](docs/MONITORING.md) for metrics setup
