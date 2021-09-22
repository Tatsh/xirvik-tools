#!/usr/bin/env bash
type="$1"
shift
if [ -z "$type" ]; then
    sphinx-build -M help doc build
else
    sphinx-build -M "${type}" doc build "$@"
fi
