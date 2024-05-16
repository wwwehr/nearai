#!/bin/bash
set -e

CLI_CMD="/home/setup/.local/bin/jasnah-cli"

"$CLI_CMD" version
"$CLI_CMD" supervisor install
"$CLI_CMD" supervisor start
