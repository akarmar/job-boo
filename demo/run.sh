#!/usr/bin/env bash
# Launcher script for job-boo demo containers.
# Usage: ./demo/run.sh [OPTIONS]
#
# Options:
#   --env FILE       Path to .env file with API keys
#   --mount PATH     Mount a directory (e.g., your project) into /work
#   --demo           Run the non-interactive narrated demo
#   --build          Force rebuild the Docker image
#   -h, --help       Show help

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
IMAGE_NAME="job-boo-interactive"
ENV_FILE=""
MOUNT_DIR=""
RUN_DEMO=false
FORCE_BUILD=false

usage() {
  echo "Usage: ./demo/run.sh [OPTIONS]"
  echo ""
  echo "Options:"
  echo "  --env FILE       .env file with API keys (auto-detects common paths)"
  echo "  --mount PATH     Mount a directory into /work"
  echo "  --demo           Run non-interactive narrated demo"
  echo "  --build          Force rebuild Docker image"
  echo "  -h, --help       Show this help"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)    ENV_FILE="$2"; shift 2 ;;
    --mount)  MOUNT_DIR="$2"; shift 2 ;;
    --demo)   RUN_DEMO=true; shift ;;
    --build)  FORCE_BUILD=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1"; usage; exit 1 ;;
  esac
done

# Auto-detect .env file
if [ -z "$ENV_FILE" ]; then
  for candidate in \
    "$REPO_DIR/.env" \
    "$HOME/.job-boo.env" \
    "$HOME/.job-boo/config.env"; do
    if [ -f "$candidate" ]; then
      ENV_FILE="$candidate"
      echo "Auto-detected env: $ENV_FILE"
      break
    fi
  done
fi

# Decide which image to use
if $RUN_DEMO; then
  IMAGE_NAME="job-boo-demo"
  DOCKERFILE="$SCRIPT_DIR/Dockerfile"
else
  IMAGE_NAME="job-boo-interactive"
  DOCKERFILE="$SCRIPT_DIR/Dockerfile.interactive"
fi

# Build if needed
if $FORCE_BUILD || ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
  echo "Building $IMAGE_NAME..."
  docker build -t "$IMAGE_NAME" -f "$DOCKERFILE" "$REPO_DIR"
fi

# Assemble docker run args
DOCKER_ARGS=(-it --rm)

if [ -n "$ENV_FILE" ]; then
  DOCKER_ARGS+=(-v "$ENV_FILE:/root/job-boo.env:ro")
fi

if [ -n "$MOUNT_DIR" ]; then
  DOCKER_ARGS+=(-v "$MOUNT_DIR:/work" -w /work)
fi

# Run
if $RUN_DEMO; then
  docker run "${DOCKER_ARGS[@]}" "$IMAGE_NAME"
else
  docker run "${DOCKER_ARGS[@]}" "$IMAGE_NAME" bash
fi
