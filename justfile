# Task runner. Run `just` with no arguments to list the recipes.
set shell := ["bash", "-euo", "pipefail", "-c"]

# mkdocs-gen-files and mkdocs-literate-nav print a long notice about MkDocs 2.0
# on every build. It is a notice, not an error.
export DISABLE_MKDOCS_2_WARNING := "true"

# List the recipes
default:
    @just --list --unsorted

# Install every dependency group
install:
    uv sync --all-groups

# Run the unit tests
test:
    uv run pytest

# Lint and format-check the Python code
lint:
    uv run ruff check .
    uv run ruff format --check .

# Check the repository layout rules
layout:
    uv run python scripts/check_layout.py

# Validate every plugin.json against the stored Agent Plugins 1.0.0 schema
manifests:
    uv run check-jsonschema --schemafile schemas/agent-plugins/1.0.0/plugin.schema.json plugins/*/plugin.json
