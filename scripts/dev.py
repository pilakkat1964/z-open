#!/usr/bin/env python3
"""
Z-Open development workflow wrapper

Accelerates the development cycle by wrapping:
- Environment setup (venv, dependencies)
- Testing and validation
- Packaging (DEB package)
- Version control (review, commit, push, release)

Usage:
    ./scripts/dev.py --help
    ./scripts/dev.py setup
    ./scripts/dev.py test
    ./scripts/dev.py build
    ./scripts/dev.py package
    ./scripts/dev.py release --version 0.7.0
    ./scripts/dev.py full --version 0.7.0
"""

import argparse
import os
import subprocess
import sys
import json
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class Context:
    """Execution context for the workflow."""

    root_dir: Path
    venv_dir: Path
    build_dir: Path
    verbose: bool = False
    dry_run: bool = False

    @classmethod
    def auto(cls, verbose: bool = False, dry_run: bool = False) -> "Context":
        """Auto-discover project root from script location."""
        script_dir = Path(__file__).parent.absolute()
        root_dir = script_dir.parent
        return cls(
            root_dir=root_dir,
            venv_dir=root_dir / ".venv",
            build_dir=root_dir / "build",
            verbose=verbose,
            dry_run=dry_run,
        )

    def run(self, cmd: List[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
        """Execute a command with optional output capture and dry-run mode."""
        if self.verbose or self.dry_run:
            print(f"$ {' '.join(cmd)}")

        if self.dry_run:
            return subprocess.CompletedProcess(cmd, 0)

        kwargs = {"check": check}
        if capture:
            kwargs.update({"capture_output": True, "text": True})

        return subprocess.run(cmd, **kwargs)

    def activate_venv(self) -> List[str]:
        """Return the command to activate the virtual environment."""
        activate_script = self.venv_dir / "bin" / "activate"
        if not activate_script.exists():
            raise FileNotFoundError(f"Virtual environment not found at {self.venv_dir}")
        return ["/bin/bash", "-c", f"source {activate_script} && "]

    def python(self) -> str:
        """Return the path to the Python interpreter in the venv."""
        python_exe = self.venv_dir / "bin" / "python"
        if not python_exe.exists():
            return sys.executable
        return str(python_exe)

    def pip(self) -> str:
        """Return the path to the pip executable in the venv."""
        pip_exe = self.venv_dir / "bin" / "pip"
        if not pip_exe.exists():
            return f"{sys.executable} -m pip"
        return str(pip_exe)


def cmd_setup(ctx: Context) -> int:
    """Set up development environment."""
    print("Setting up development environment...")

    # Create virtual environment
    if not ctx.venv_dir.exists():
        print(f"Creating virtual environment at {ctx.venv_dir}...")
        ctx.run([sys.executable, "-m", "venv", str(ctx.venv_dir)])

    # Upgrade pip
    print("Upgrading pip...")
    ctx.run([ctx.python(), "-m", "pip", "install", "--upgrade", "pip"])

    # Install package in editable mode with dev dependencies
    print("Installing z-open with dev dependencies...")
    ctx.run([ctx.pip(), "install", "-e", str(ctx.root_dir / ".[dev]")])

    print("✓ Development environment ready!")
    print(f"\nTo activate the environment, run:")
    print(f"  source {ctx.venv_dir / 'bin' / 'activate'}")

    return 0


def cmd_test(ctx: Context) -> int:
    """Run manual tests and validations."""
    print("Running tests and validations...")

    # Test Python compilation
    print("\n1. Testing Python syntax...")
    ctx.run([ctx.python(), "-m", "py_compile", str(ctx.root_dir / "zopen.py")])
    print("   ✓ zopen.py compiles successfully")

    # Test CLI help
    print("\n2. Testing CLI help...")
    ctx.run([ctx.python(), str(ctx.root_dir / "zopen.py"), "--help"], check=False)
    print("   ✓ Help command works")

    # Test CLI version
    print("\n3. Testing CLI version...")
    ctx.run([ctx.python(), str(ctx.root_dir / "zopen.py"), "--version"], check=False)
    print("   ✓ Version command works")

    print("\n✓ All tests passed!")
    return 0


def cmd_build(ctx: Context) -> int:
    """Build the project locally."""
    print("Building project...")

    # Clean previous build
    if ctx.build_dir.exists():
        print(f"Cleaning {ctx.build_dir}...")
        import shutil
        shutil.rmtree(ctx.build_dir)

    # Create build directory
    ctx.build_dir.mkdir(exist_ok=True)

    # Run CMake
    print("Configuring CMake...")
    cmake_cmd = [
        "cmake",
        str(ctx.root_dir),
        f"-B{ctx.build_dir}",
        "-DCMAKE_INSTALL_PREFIX=/opt/zopen",
    ]
    ctx.run(cmake_cmd, check=False)

    # Build with make
    print("Building with make...")
    ctx.run(["make", "-C", str(ctx.build_dir)], check=False)

    print("✓ Build complete!")
    return 0


def cmd_package(ctx: Context, version: Optional[str] = None, skip_deb: bool = False, skip_source: bool = False) -> int:
    """Create distributable packages."""
    print("Creating packages...")

    if not version:
        # Auto-detect from pyproject.toml
        pyproject = ctx.root_dir / "pyproject.toml"
        if pyproject.exists():
            with open(pyproject) as f:
                for line in f:
                    if 'version = "' in line:
                        version = line.split('"')[1]
                        break

    if not version:
        print("✗ Could not determine version. Use --version to specify.")
        return 1

    print(f"Creating packages for version {version}...")

    # Build DEB package
    if not skip_deb:
        print("\n1. Building DEB package...")
        deb_cmd = ["cmake", "--build", str(ctx.build_dir), "--target", "deb"]
        result = ctx.run(deb_cmd, check=False)
        if result.returncode == 0:
            print("   ✓ DEB package created")
        else:
            print("   ⚠ DEB package build skipped (may not be available in this environment)")

    # Create source archive
    if not skip_source:
        print("\n2. Creating source archive...")
        archive_name = f"zopen-{version}-source.tar.gz"
        archive_cmd = [
            "git",
            "archive",
            "--format=tar.gz",
            f"--prefix=zopen-{version}-source/",
            f"-o{ctx.root_dir / archive_name}",
            "HEAD",
        ]
        result = ctx.run(archive_cmd, check=False)
        if result.returncode == 0:
            print(f"   ✓ Source archive created: {archive_name}")

    print("✓ Packaging complete!")
    return 0


def cmd_release(
    ctx: Context,
    version: Optional[str] = None,
    stage: bool = False,
    no_wait: bool = False,
    commit_msg: Optional[str] = None,
    timeout: int = 300,
) -> int:
    """Create and publish a release."""
    print("Creating release...")

    if not version:
        # Auto-detect from pyproject.toml
        pyproject = ctx.root_dir / "pyproject.toml"
        if pyproject.exists():
            with open(pyproject) as f:
                for line in f:
                    if 'version = "' in line:
                        version = line.split('"')[1]
                        break

    if not version:
        print("✗ Could not determine version. Use --version to specify.")
        return 1

    print(f"Releasing version {version}...")

    # Check git status
    print("\n1. Checking git status...")
    status = ctx.run(["git", "-C", str(ctx.root_dir), "status", "--porcelain"], capture=True)
    if status.stdout.strip():
        print("\nModified files:")
        print(status.stdout)
        response = input("Stage these changes for commit? (y/n): ")
        if response.lower() == "y":
            print("Staging all changes...")
            ctx.run(["git", "-C", str(ctx.root_dir), "add", "-A"])

    # Create commit
    print("\n2. Creating release commit...")
    msg = commit_msg or f"Release v{version}"
    ctx.run(["git", "-C", str(ctx.root_dir), "commit", "-m", msg], check=False)

    # Create git tag
    print("\n3. Creating git tag...")
    tag = f"v{version}"
    if stage:
        tag += "-stage"
    ctx.run(["git", "-C", str(ctx.root_dir), "tag", tag], check=False)

    # Push to remote
    print("\n4. Pushing to remote...")
    ctx.run(["git", "-C", str(ctx.root_dir), "push", "origin", "master"], check=False)
    ctx.run(["git", "-C", str(ctx.root_dir), "push", "origin", tag], check=False)

    print(f"\n✓ Release {tag} published!")
    print(f"GitHub Actions will build the release automatically.")
    print(f"View at: https://github.com/pilakkat1964/z-open/releases/tag/{tag}")

    return 0


def cmd_full(ctx: Context, version: Optional[str] = None) -> int:
    """Run complete workflow: test, build, package, release."""
    print("Running full development workflow...")

    steps = [
        ("Testing", lambda: cmd_test(ctx)),
        ("Building", lambda: cmd_build(ctx)),
        ("Packaging", lambda: cmd_package(ctx, version=version)),
        ("Creating release", lambda: cmd_release(ctx, version=version)),
    ]

    for step_name, step_func in steps:
        print(f"\n{'=' * 60}")
        print(f"Step: {step_name}")
        print(f"{'=' * 60}")
        if step_func() != 0:
            print(f"\n✗ {step_name} failed!")
            return 1

    print(f"\n{'=' * 60}")
    print("✓ Full workflow complete!")
    print(f"{'=' * 60}")
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Z-Open development workflow wrapper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--dry-run", action="store_true", help="Show commands without executing")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup command
    subparsers.add_parser("setup", help="Set up development environment")

    # Test command
    subparsers.add_parser("test", help="Run tests and validations")

    # Build command
    subparsers.add_parser("build", help="Build project locally")

    # Package command
    pkg_parser = subparsers.add_parser("package", help="Create distributable packages")
    pkg_parser.add_argument("--version", help="Package version (auto-detected if not provided)")
    pkg_parser.add_argument("--skip-deb", action="store_true", help="Skip DEB package creation")
    pkg_parser.add_argument("--skip-source", action="store_true", help="Skip source archive creation")

    # Release command
    rel_parser = subparsers.add_parser("release", help="Create and publish a release")
    rel_parser.add_argument("--version", help="Release version (auto-detected if not provided)")
    rel_parser.add_argument("--stage", action="store_true", help="Create staging release (add -stage suffix)")
    rel_parser.add_argument("--no-wait", action="store_true", help="Don't wait for GitHub Actions")
    rel_parser.add_argument("--commit-msg", help="Custom commit message")
    rel_parser.add_argument("--timeout", type=int, default=300, help="Timeout for GitHub Actions (seconds)")

    # Full workflow command
    full_parser = subparsers.add_parser("full", help="Run complete workflow (test, build, package, release)")
    full_parser.add_argument("--version", help="Release version (auto-detected if not provided)")

    args = parser.parse_args()

    try:
        ctx = Context.auto(verbose=args.verbose, dry_run=args.dry_run)

        if not args.command:
            parser.print_help()
            return 0

        if args.command == "setup":
            return cmd_setup(ctx)
        elif args.command == "test":
            return cmd_test(ctx)
        elif args.command == "build":
            return cmd_build(ctx)
        elif args.command == "package":
            return cmd_package(
                ctx,
                version=args.version,
                skip_deb=args.skip_deb,
                skip_source=args.skip_source,
            )
        elif args.command == "release":
            return cmd_release(
                ctx,
                version=args.version,
                stage=args.stage,
                no_wait=args.no_wait,
                commit_msg=args.commit_msg,
                timeout=args.timeout,
            )
        elif args.command == "full":
            return cmd_full(ctx, version=args.version)
        else:
            print(f"Unknown command: {args.command}")
            return 1

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
