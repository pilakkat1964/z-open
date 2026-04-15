#!/usr/bin/env python3
"""
z-open Release Automation Script

Automates the release process for z-open by updating version numbers across
multiple files and creating a git tag in a synchronized manner.

Usage:
    python3 scripts/release.py 0.6.6
    python3 scripts/release.py 0.6.6 --dry-run
    python3 scripts/release.py 0.6.6 --message "Release notes here"

Files updated:
    1. CMakeLists.txt - project VERSION field
    2. pyproject.toml - [project] version field
    3. debian/changelog - adds new entry with current date
    4. Creates and pushes git tag with version
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class ReleaseAutomation:
    """Automates the z-open release process."""

    def __init__(self, version, message="", dry_run=False, verbose=False):
        """Initialize release automation.
        
        Args:
            version: Version string (e.g., "0.6.5")
            message: Optional release message/changelog entry
            dry_run: If True, show what would be done without doing it
            verbose: If True, print detailed output
        """
        self.version = version
        self.message = message
        self.dry_run = dry_run
        self.verbose = verbose
        self.tag = f"v{version}"
        self.repo_root = Path(__file__).parent.parent
        self.changes = []  # Track changes made

    def log(self, message, level="info"):
        """Print log message with level prefix."""
        if level == "info":
            prefix = "ℹ️ "
        elif level == "success":
            prefix = "✅ "
        elif level == "warning":
            prefix = "⚠️  "
        elif level == "error":
            prefix = "❌ "
        else:
            prefix = "  "

        if level != "verbose" or self.verbose:
            print(f"{prefix}{message}")

    def error(self, message):
        """Print error message and exit."""
        self.log(message, "error")
        sys.exit(1)

    def validate_version(self):
        """Validate version format."""
        if not re.match(r"^\d+\.\d+\.\d+$", self.version):
            self.error(f"Invalid version format: {self.version}")
            self.error("Expected format: X.Y.Z (e.g., 0.6.5)")

    def check_repo_clean(self):
        """Check that working tree is clean."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
            if result.stdout.strip():
                self.error(
                    "Working tree is not clean. Commit or stash changes first:\n"
                    + result.stdout
                )
        except subprocess.CalledProcessError as e:
            self.error(f"Failed to check git status: {e.stderr}")

    def check_tag_exists(self):
        """Check if tag already exists."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", self.tag],
                cwd=self.repo_root,
                capture_output=True,
                check=False,
            )
            if result.returncode == 0:
                self.error(f"Tag {self.tag} already exists. Cannot create release.")
        except subprocess.CalledProcessError:
            pass

    def update_cmakelists(self):
        """Update CMakeLists.txt VERSION field."""
        filepath = self.repo_root / "CMakeLists.txt"
        try:
            content = filepath.read_text()
        except Exception as e:
            self.error(f"Failed to read {filepath}: {e}")

        # Find and replace VERSION field
        pattern = r"project\(\s*zopen\s+VERSION\s+[\d\.]+\s+"
        replacement = f"project(zopen\n    VERSION      {self.version}\n    "
        new_content = re.sub(pattern, replacement, content, count=1)

        if new_content == content:
            self.error(f"Could not find/replace VERSION in {filepath}")

        if not self.dry_run:
            try:
                filepath.write_text(new_content)
                self.log(f"Updated CMakeLists.txt to version {self.version}")
            except Exception as e:
                self.error(f"Failed to write {filepath}: {e}")
        else:
            self.log(f"[DRY-RUN] Would update CMakeLists.txt to version {self.version}")

        self.changes.append(("CMakeLists.txt", "VERSION", self.version))

    def update_pyproject(self):
        """Update pyproject.toml version field."""
        filepath = self.repo_root / "pyproject.toml"
        try:
            content = filepath.read_text()
        except Exception as e:
            self.error(f"Failed to read {filepath}: {e}")

        # Find and replace version field (within [project] section)
        pattern = r'version = "[^"]+"'
        replacement = f'version = "{self.version}"'
        new_content = re.sub(pattern, replacement, content, count=1)

        if new_content == content:
            self.error(f"Could not find/replace version in {filepath}")

        if not self.dry_run:
            try:
                filepath.write_text(new_content)
                self.log(f"Updated pyproject.toml to version {self.version}")
            except Exception as e:
                self.error(f"Failed to write {filepath}: {e}")
        else:
            self.log(f"[DRY-RUN] Would update pyproject.toml to version {self.version}")

        self.changes.append(("pyproject.toml", "version", self.version))

    def update_debian_changelog(self):
        """Update debian/changelog with new version entry."""
        filepath = self.repo_root / "debian" / "changelog"
        try:
            content = filepath.read_text()
        except Exception as e:
            self.error(f"Failed to read {filepath}: {e}")

        # Generate new changelog entry
        now = datetime.now()
        date_str = now.strftime("%a, %d %b %Y %H:%M:%S +0000")
        debian_version = f"{self.version}-1"

        # Use provided message or generate a default one
        if self.message:
            changelog_msg = f"  * {self.message}\n"
        else:
            changelog_msg = f"  * Release {self.version}\n"

        new_entry = (
            f"zopen ({debian_version}) unstable; urgency=low\n"
            f"\n"
            f"{changelog_msg}"
            f"\n"
            f" -- Maintainer <maintainer@example.com>  {date_str}\n"
            f"\n"
        )

        new_content = new_entry + content

        if not self.dry_run:
            try:
                filepath.write_text(new_content)
                self.log(f"Updated debian/changelog with version {debian_version}")
            except Exception as e:
                self.error(f"Failed to write {filepath}: {e}")
        else:
            self.log(f"[DRY-RUN] Would add debian/changelog entry for {debian_version}")
            if self.verbose:
                print("\n" + new_entry)

        self.changes.append(("debian/changelog", "version", debian_version))

    def git_add_and_commit(self):
        """Stage changes and create commit."""
        files_to_add = [
            "CMakeLists.txt",
            "pyproject.toml",
            "debian/changelog",
        ]

        if not self.dry_run:
            try:
                # Add files
                subprocess.run(
                    ["git", "add"] + files_to_add,
                    cwd=self.repo_root,
                    check=True,
                    capture_output=True,
                )

                # Commit
                commit_msg = f"release: bump version to {self.version}"
                subprocess.run(
                    ["git", "commit", "-m", commit_msg],
                    cwd=self.repo_root,
                    check=True,
                    capture_output=True,
                )
                self.log(f"Created commit: {commit_msg}")
            except subprocess.CalledProcessError as e:
                self.error(f"Git commit failed: {e.stderr.decode() if e.stderr else str(e)}")
        else:
            self.log(f"[DRY-RUN] Would commit: release: bump version to {self.version}")

    def git_push_branch(self):
        """Push version commit to remote."""
        if not self.dry_run:
            try:
                subprocess.run(
                    ["git", "push", "origin", "master"],
                    cwd=self.repo_root,
                    check=True,
                    capture_output=True,
                )
                self.log("Pushed version commit to origin/master")
            except subprocess.CalledProcessError as e:
                self.error(f"Git push failed: {e.stderr.decode() if e.stderr else str(e)}")
        else:
            self.log("[DRY-RUN] Would push to origin/master")

    def git_create_tag(self):
        """Create annotated git tag."""
        if not self.dry_run:
            try:
                tag_msg = f"Release {self.version}"
                if self.message:
                    tag_msg += f" - {self.message}"

                subprocess.run(
                    ["git", "tag", "-a", self.tag, "-m", tag_msg],
                    cwd=self.repo_root,
                    check=True,
                    capture_output=True,
                )
                self.log(f"Created tag: {self.tag}")
            except subprocess.CalledProcessError as e:
                self.error(f"Git tag creation failed: {e.stderr.decode() if e.stderr else str(e)}")
        else:
            self.log(f"[DRY-RUN] Would create tag: {self.tag}")

    def git_push_tag(self):
        """Push tag to remote."""
        if not self.dry_run:
            try:
                subprocess.run(
                    ["git", "push", "origin", self.tag],
                    cwd=self.repo_root,
                    check=True,
                    capture_output=True,
                )
                self.log(f"Pushed tag to origin: {self.tag}")
            except subprocess.CalledProcessError as e:
                self.error(f"Git tag push failed: {e.stderr.decode() if e.stderr else str(e)}")
        else:
            self.log(f"[DRY-RUN] Would push tag to origin: {self.tag}")

    def show_summary(self):
        """Show summary of changes."""
        print("\n" + "=" * 60)
        if self.dry_run:
            print("DRY-RUN SUMMARY - No changes made")
        else:
            print("RELEASE SUMMARY")
        print("=" * 60)

        for filepath, field, value in self.changes:
            print(f"  {filepath:25} {field:20} → {value}")

        print("\nNext steps:")
        print(f"  1. GitHub Actions will build release assets")
        print(f"  2. Download from: https://github.com/pilakkat1964/z-open/releases/tag/{self.tag}")
        print(f"  3. Install via: sudo apt install ./zopen-{self.version}-Linux.deb")
        print("=" * 60 + "\n")

    def confirm(self):
        """Ask user to confirm release."""
        print("\n" + "=" * 60)
        print(f"Release Confirmation: z-open {self.version}")
        print("=" * 60)
        print(f"  Version: {self.version}")
        print(f"  Tag: {self.tag}")
        print(f"  Debian revision: {self.version}-1")
        if self.message:
            print(f"  Message: {self.message}")
        print("=" * 60)

        if self.dry_run:
            response = "y"  # Auto-confirm for dry-run
            print("(DRY-RUN MODE - proceeding without confirmation)")
        else:
            response = input("\nProceed with release? (y/n): ").strip().lower()

        if response != "y":
            print("Release cancelled.")
            sys.exit(0)

    def run(self):
        """Execute the full release process."""
        self.log("Starting z-open release automation...")
        self.validate_version()
        self.check_repo_clean()
        self.check_tag_exists()

        self.confirm()

        # Step 1: Update version files
        self.log("\n📝 Updating version files...")
        self.update_cmakelists()
        self.update_pyproject()
        self.update_debian_changelog()

        # Step 2: Commit changes
        self.log("\n💾 Committing changes...")
        self.git_add_and_commit()

        # Step 3: Push commit
        self.log("\n📤 Pushing version commit...")
        self.git_push_branch()

        # Step 4: Create and push tag
        self.log("\n🏷️  Creating and pushing tag...")
        self.git_create_tag()
        self.git_push_tag()

        # Show summary
        self.show_summary()

        self.log("✨ Release process complete!", "success")
        self.log(
            "GitHub Actions will now build the release assets. "
            "Check the Actions tab for progress.",
            "info",
        )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automate z-open release process",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/release.py 0.6.6
  python3 scripts/release.py 0.6.6 --dry-run
  python3 scripts/release.py 0.6.6 --message "New features and bugfixes"
  python3 scripts/release.py 0.6.6 --verbose

The release process:
  1. Updates version in CMakeLists.txt, pyproject.toml, debian/changelog
  2. Creates a git commit with all version updates
  3. Pushes the commit to origin/master
  4. Creates an annotated git tag (v0.6.6)
  5. Pushes the tag to origin, triggering GitHub Actions

GitHub Actions will then automatically:
  - Build the .deb package for amd64
  - Create the install .tar.gz archive
  - Generate the source .tar.gz archive
  - Create a GitHub Release with all assets

Version format must be X.Y.Z (e.g., 0.6.5)
        """,
    )

    parser.add_argument(
        "version",
        help="Release version (e.g., 0.6.6)",
    )

    parser.add_argument(
        "-m",
        "--message",
        default="",
        help="Release message/changelog entry (optional)",
    )

    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print detailed output",
    )

    args = parser.parse_args()

    release = ReleaseAutomation(
        version=args.version,
        message=args.message,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    try:
        release.run()
    except KeyboardInterrupt:
        print("\n\nRelease cancelled by user.")
        sys.exit(1)


if __name__ == "__main__":
    main()
