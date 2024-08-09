#!/bin/bash

cd "$(dirname "$0")"/.. || exit

if command -v pyenv 1>/dev/null 2>&1; then
  export PYENV_ROOT="$HOME/.pyenv"
  export PATH="$PYENV_ROOT/bin:$PATH"
  eval "$(pyenv init --path)"
  eval "$(pyenv init -)"
fi

pyenv shell 3.10.14

if [ ! -d "venv" ]; then
    python -m venv venv
fi

. venv/bin/activate

pip3.10 install -e .[hub]

echo "Setup complete"