#!/usr/bin/env bash
set -e

BASEDIR=$(dirname "$0")
cd $BASEDIR

echo "=== Flake8 ==="
python -m flake8 ./ --statistics
echo "✓"

echo "=== Pylint ==="
python -m pylint -f colorized ./spark/
echo "✓"

echo "=== MyPy ==="
python -m mypy .

echo "=== ISort ==="
isort .

echo "=== Black ==="
black .
