#!/usr/bin/env sh
set -eu

python -m compileall \
  main.py \
  main_window.py \
  importcsv.py \
  inportcsv.py \
  logic \
  services \
  styles \
  ui \
  tests \
  database/init_db.py

python -m unittest discover -s tests -p 'test_*.py' -v
