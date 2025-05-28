# llm-d Cluster Setup

This guide explains how to launch a local k3s cluster with `k3d` and install the
sample `llm-d` Helm chart.

## Prerequisites

- Docker
- `k3d`
- `helm`

## Steps

1. Activate the project virtual environment:

   ```bash
   source .venv/bin/activate
   ```

2. Create the cluster and install the chart:

   ```bash
   make k3s-up
   ```

   The command spins up a single-node k3s cluster and installs the chart from
   `worker_cluster/chart`.

3. Retrieve the service endpoint and set `LLMD_ENDPOINT` for the router. For
   example:

   ```bash
   kubectl get svc -n llmd llm-d
   export LLMD_ENDPOINT=http://localhost:8000
   ```

The router will forward any registry entry with type `llm-d` to this endpoint.
