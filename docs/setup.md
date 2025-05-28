# Setup Guide

Follow these steps to prepare a local development environment.

1. Create a Python 3.10 virtual environment and activate it.
2. Install project dependencies using:
   ```bash
   pip install -e .
   pip install -r requirements-dev.txt
   ```
3. Initialize the model registry:
   ```bash
   make migrate
   make seed
   ```
4. Start the development server:
   ```bash
   make dev
   ```

See [README](../README.md) for additional details.
