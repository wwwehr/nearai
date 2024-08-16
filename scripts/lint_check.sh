#!/usr/bin/env bash
#
# Lint checks the codebase.
#
# Usage: ./scripts/lint_check.sh

set -e
poetry run ruff check . --exclude third_party/,aws_runner/,openapi_client/,agent/ --fix
