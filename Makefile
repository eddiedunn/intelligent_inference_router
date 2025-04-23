# Intelligent Inference Router Makefile

# Default log sink for remote UDP log forwarding
REMOTE_LOG_SINK ?=

.PHONY: all deploy-test up down test logs

all: deploy-test

# Build and run stack, run tests, forward logs if REMOTE_LOG_SINK is set, then tear down

deploy-test: build up logs test down

build:
	docker compose build

up:
	docker compose up -d

# Run tests inside the router container
# Will fail the make if tests fail

test:
	docker compose run --rm router pytest --disable-warnings -q

# Forward logs to REMOTE_LOG_SINK if set (runs in background)
logs:
	@if [ "$(REMOTE_LOG_SINK)" != "" ]; then \
		python forward_logs_udp.py --sink $(REMOTE_LOG_SINK) & \
	fi

down:
	docker compose down
