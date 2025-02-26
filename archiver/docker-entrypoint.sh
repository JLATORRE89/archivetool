#!/bin/bash
set -e

# Function to run CLI version
run_cli() {
    exec python -m archiver.cli "$@"
}

# Function to run GUI version
run_gui() {
    exec python -m archiver.gui
}

# Check first argument for version selection
case "$1" in
    cli)
        shift
        run_cli "$@"
        ;;
    gui)
        run_gui
        ;;
    *)
        echo "Usage: $0 {cli|gui} [arguments]"
        echo "For CLI: $0 cli [url] [-o output_dir] [-t threads] [-q]"
        echo "For GUI: $0 gui"
        exit 1
        ;;
esac