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

# Check that the catalogs match the plugin.json files
catalogs:
    uv run python scripts/sync_catalogs.py --check

# Rewrite the catalogs from the plugin.json files
sync:
    uv run python scripts/sync_catalogs.py

# Create a plugin: just new-plugin emad-jobs "Job search skills."
new-plugin name description:
    uv run python scripts/new_plugin.py "{{name}}" --description "{{description}}"

# Create a skill in a plugin: just new-skill emad-jobs cover-letter
new-skill plugin name:
    uv run python scripts/new_skill.py "{{plugin}}" "{{name}}"

# Validate every SKILL.md against the Agent Skills specification
skills:
    for dir in plugins/*/skills/*/; do uv run agentskills validate "$dir"; done

# Check that every eval file is valid, without calling a model
evals-list:
    uv run skill-lens list plugins

# Check the marketplace, each plugin and each manifest the way Claude Code reads them
claude-validate:
    #!/usr/bin/env bash
    set -euo pipefail
    if ! command -v claude >/dev/null 2>&1; then
        if [ -n "${CI:-}" ]; then
            echo "error: claude is not installed, and CI must run this check" >&2
            exit 1
        fi
        echo "warning: claude is not installed; skipping 'claude plugin validate'. CI runs it." >&2
        exit 0
    fi
    claude plugin validate --strict .
    for dir in plugins/*/; do
        claude plugin validate --strict "$dir"
        claude plugin validate --strict "${dir}plugin.json"
    done

# Serve the site on http://127.0.0.1:8000, rebuilding on save
docs:
    uv run mkdocs serve

# Build the site exactly as CI does; any warning fails the build
docs-build:
    uv run mkdocs build --strict
