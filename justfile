# Building Tools task runner (https://github.com/casey/just)

# list available recipes
default:
    @just --list

# create/sync the project venv (uv)
sync:
    uv sync

# run addon tests headless via the bpy module (isolated user config so a
# stale installed addon copy can't interfere)
test:
    #!/usr/bin/env bash
    set -e
    mkdir -p .agent/tools/out/test-user
    BLENDER_USER_RESOURCES="$PWD/.agent/tools/out/test-user" \
        uv run python tests/__main__.py

# run addon tests inside the blender gui (parity)
test-blender:
    blender --window-geometry 0 0 1 1 --no-window-focus -P tests/__main__.py

# format code (ruff)
format:
    uv run ruff format btools tests

# type-check code (mypy)
check:
    uv run mypy btools

# lint code (ruff)
lint:
    uv run ruff check btools

# build the release zip from the latest tag
build:
    uv run python scripts/make-release.py


# dev testing
dev:
    uv run python scripts/make-release.py latest
    blender -P scripts/install-dev-addon.py dev.blend

# serve docs locally (jekyll)
web-serve:
    cd docs && bundle exec jekyll server --watch

# install docs tooling (linux)
web-install-deps-linux:
    sudo apt-get update
    sudo apt-get install ruby ruby-dev rubygems
    sudo gem install bundler github-pages
