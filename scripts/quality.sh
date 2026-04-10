#!/usr/bin/env sh
set -eu

python -m ruff check .
python -m black --check .
python -m flake8 .
