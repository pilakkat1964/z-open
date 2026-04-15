#!/bin/bash
# z-open environment initialization script
# 
# This script ensures a consistent Python virtual environment is set up and used
# for all development, testing, and building tasks.
#
# Usage:
#   source scripts/activate.sh
#   scripts/activate.sh                    # Or run directly
#
# This script will:
#   1. Check if .venv exists
#   2. Create it if needed (using uv or standard venv)
#   3. Install/update dependencies
#   4. Activate the virtual environment
#

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Find project root (works when sourced or run directly)
if [ -n "$BASH_SOURCE" ]; then
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
else
    SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
fi
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

VENV_DIR="$PROJECT_ROOT/.venv"
PYTHON_EXE="$VENV_DIR/bin/python"
PIP_EXE="$VENV_DIR/bin/pip"

# Function to print colored output
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# Function to check if venv exists and is valid
is_venv_valid() {
    if [ ! -e "$PYTHON_EXE" ]; then
        return 1
    fi
    # Check for any pip variant (pip, pip3, pip3.10, etc.)
    if [ ! -e "$VENV_DIR/bin/pip" ] && [ ! -e "$VENV_DIR/bin/pip3" ] && [ ! -e "$VENV_DIR/bin/pip3.10" ]; then
        return 1
    fi
    # Verify python is actually executable
    if [ ! -x "$PYTHON_EXE" ]; then
        return 1
    fi
    return 0
}

# Helper function to get pip executable (use whichever exists)
get_pip() {
    if [ -e "$VENV_DIR/bin/pip" ]; then
        echo "$VENV_DIR/bin/pip"
    elif [ -e "$VENV_DIR/bin/pip3" ]; then
        echo "$VENV_DIR/bin/pip3"
    else
        echo "$VENV_DIR/bin/python -m pip"
    fi
}

# Function to create venv
create_venv() {
    print_info "Creating virtual environment at $VENV_DIR..."
    
    # Check if uv is available
    if command -v uv &> /dev/null; then
        print_info "Using uv to create virtual environment..."
        uv venv "$VENV_DIR" --python 3.10
        
        # uv creates venv without pip, install it
        print_info "Installing pip into virtual environment..."
        "$VENV_DIR/bin/python" -m ensurepip --upgrade
    else
        print_info "Using standard venv to create virtual environment..."
        python3 -m venv "$VENV_DIR"
    fi
    
    if is_venv_valid; then
        print_success "Virtual environment created successfully"
    else
        print_error "Failed to create virtual environment"
        return 1
    fi
}

# Function to install dependencies
install_dependencies() {
    print_info "Installing/updating dependencies..."
    
    PIP=$(get_pip)
    
    if command -v uv &> /dev/null; then
        print_info "Using uv to install dependencies..."
        uv pip install --python "$VENV_DIR/bin/python" --upgrade pip setuptools wheel
        if [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
            uv pip install --python "$VENV_DIR/bin/python" -e "$PROJECT_ROOT[dev]"
        fi
    else
        print_info "Using pip to install dependencies..."
        $PIP install --upgrade pip setuptools wheel
        if [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
            $PIP install -e "$PROJECT_ROOT[dev]"
        fi
    fi
    
    print_success "Dependencies installed"
}

# Main script logic
main() {
    print_info "Z-Open Environment Setup"
    print_info "Project root: $PROJECT_ROOT"
    
    # Check if venv exists
    if ! is_venv_valid; then
        print_warn "Virtual environment not found or invalid"
        create_venv
        install_dependencies
    else
        print_success "Virtual environment found at $VENV_DIR"
        print_info "Dependencies are already installed"
    fi
    
    # Activate venv if this script is sourced
    if [ -n "$BASH_SOURCE" ] && [ "${BASH_SOURCE[0]}" != "$0" ]; then
        source "$VENV_DIR/bin/activate"
        print_success "Virtual environment activated"
        print_info "Python: $(which python)"
        print_info "Pip: $(which pip)"
    else
        # If run directly, print activation instructions
        print_info ""
        print_info "To activate the virtual environment in your current shell, run:"
        echo -e "${BLUE}  source $VENV_DIR/bin/activate${NC}"
        print_info ""
        print_info "Or use this command to activate immediately:"
        echo -e "${BLUE}  source scripts/activate.sh${NC}"
    fi
}

main
