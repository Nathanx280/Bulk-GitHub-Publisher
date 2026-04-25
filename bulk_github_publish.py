#!/usr/bin/env python3
"""
bulk_github_publish.py

Scans a parent folder for project subfolders, creates GitHub repos for them
if needed, initializes Git if needed, commits files if there are changes,
and pushes them to GitHub.

Requirements:
    pip install requests

Environment variables:
    GITHUB_USER   = your GitHub username
    GITHUB_TOKEN  = your GitHub personal access token

Example:
    set GITHUB_USER=Nathanx280
    set GITHUB_TOKEN=YOUR_NEW_TOKEN
    python bulk_github_publish.py "C:\\Users\\natha\\OneDrive\\Desktop\\Programs\\Full Collection" --private
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import requests

API_BASE = "https://api.github.com"

IGNORED_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".idea",
    ".vs",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    "out",
    "target",
    ".next",
    ".nuxt",
    ".cache",
}

IGNORED_FILES = {
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
}

SKIP_EXACT_NAMES = {
    "Zip_Backups",
}

DEFAULT_GITIGNORE = """# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.venv/
venv/
.pytest_cache/
.mypy_cache/

# Node
node_modules/
npm-debug.log*
yarn-error.log*
pnpm-debug.log*

# Build/output
dist/
build/
out/
target/
.cache/

# Archives
*.zip
*.rar
*.7z
*.tar
*.gz

# Environment
.env
.env.*
!.env.example

# Logs
*.log

# OS/editor
Thumbs.db
.DS_Store
.idea/
.vscode/
.vs/

# Coverage
.coverage
htmlcov/
"""

LARGE_BINARY_EXTENSIONS = {
    ".zip", ".rar", ".7z", ".iso", ".exe", ".dll", ".msi",
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv",
    ".mp3", ".wav", ".flac", ".ogg",
    ".psd", ".ai", ".blend",
}


def now() -> str:
    return time.strftime("%H:%M:%S")


def log(msg: str) -> None:
    print(f"[{now()}] {msg}", flush=True)


def github_headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def run_git(args: list[str], cwd: Path) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        raise RuntimeError("Git is not installed or not available in PATH.")


def run_git_live(args: list[str], cwd: Path) -> int:
    cmd = ["git", *args]
    log(f"[GIT] {' '.join(cmd)}")
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        raise RuntimeError("Git is not installed or not available in PATH.")

    assert proc.stdout is not None
    for line in proc.stdout:
        print(line.rstrip(), flush=True)

    return proc.wait()


def sanitize_repo_name(name: str) -> str:
    cleaned = re.sub(r"[^\w.\- ]+", "-", name.strip())
    cleaned = cleaned.replace(" ", "-")
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned[:100] or "project"


def is_empty_folder(folder: Path) -> bool:
    try:
        next(folder.iterdir())
        return False
    except StopIteration:
        return True


def has_meaningful_files(folder: Path) -> bool:
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
        for filename in files:
            if filename in IGNORED_FILES:
                continue
            return True
    return False


def folder_size_mb(folder: Path) -> float:
    total = 0
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file_name in files:
            fp = Path(root) / file_name
            try:
                total += fp.stat().st_size
            except OSError:
                pass
    return total / (1024 * 1024)


def count_files(folder: Path) -> int:
    total = 0
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        total += len(files)
    return total


def list_large_binaries(folder: Path, limit: int = 20) -> list[Path]:
    found: list[Path] = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file_name in files:
            fp = Path(root) / file_name
            if fp.suffix.lower() in LARGE_BINARY_EXTENSIONS:
                found.append(fp)
                if len(found) >= limit:
                    return found
    return found


def list_candidate_projects(parent: Path) -> list[Path]:
    projects: list[Path] = []
    for item in parent.iterdir():
        if not item.is_dir():
            continue
        if item.name.startswith("."):
            continue
        if item.name in SKIP_EXACT_NAMES:
            continue
        if is_empty_folder(item):
            continue
        if not has_meaningful_files(item):
            continue
        projects.append(item)
    return sorted(projects, key=lambda p: p.name.lower())


def verify_github_identity(expected_user: str, token: str) -> None:
    log("Verifying GitHub token...")
    resp = requests.get(f"{API_BASE}/user", headers=github_headers(token), timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"GitHub token check failed: {resp.status_code} {resp.text}")

    data = resp.json()
    login = (data.get("login") or "").strip()
    if login.lower() != expected_user.lower():
        raise RuntimeError(
            f"Token belongs to '{login}' but GITHUB_USER is '{expected_user}'."
        )
    log(f"Authenticated as GitHub user: {login}")


def repo_exists(user: str, repo: str, token: str) -> bool:
    resp = requests.get(
        f"{API_BASE}/repos/{user}/{repo}",
        headers=github_headers(token),
        timeout=30,
    )
    if resp.status_code == 200:
        return True
    if resp.status_code == 404:
        return False
    raise RuntimeError(f"Failed checking repo {user}/{repo}: {resp.status_code} {resp.text}")


def create_repo(token: str, repo_name: str, private: bool, description: str = "") -> dict:
    payload = {
        "name": repo_name,
        "private": private,
        "auto_init": False,
        "description": description,
    }
    resp = requests.post(
        f"{API_BASE}/user/repos",
        headers=github_headers(token),
        json=payload,
        timeout=30,
    )
    if resp.status_code == 201:
        return resp.json()
    raise RuntimeError(f"Failed creating repo '{repo_name}': {resp.status_code} {resp.text}")


def verify_repo_exists_after_create(user: str, repo: str, token: str) -> dict:
    resp = requests.get(
        f"{API_BASE}/repos/{user}/{repo}",
        headers=github_headers(token),
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Repo verification failed for {user}/{repo}: {resp.status_code} {resp.text}")
    return resp.json()


def write_gitignore_if_missing(project_dir: Path) -> None:
    gitignore = project_dir / ".gitignore"
    if gitignore.exists():
        return
    gitignore.write_text(DEFAULT_GITIGNORE, encoding="utf-8")
    log(f"[INFO] Wrote default .gitignore in {project_dir.name}")


def ensure_git_identity(project_dir: Path) -> None:
    code_name, out_name, _ = run_git(["config", "--get", "user.name"], cwd=project_dir)
    code_email, out_email, _ = run_git(["config", "--get", "user.email"], cwd=project_dir)

    if code_name != 0 or not out_name:
        log(f"[WARN] git user.name is not set for {project_dir.name}")
    if code_email != 0 or not out_email:
        log(f"[WARN] git user.email is not set for {project_dir.name}")


def ensure_git_repo(project_dir: Path, default_branch: str) -> None:
    if not (project_dir / ".git").exists():
        log("[FIX] Initializing new git repo...")
        if run_git_live(["init"], project_dir) != 0:
            raise RuntimeError(f"git init failed in {project_dir}")

    # Try to detect current branch
    code, out, err = run_git(["branch", "--show-current"], cwd=project_dir)
    if code != 0:
        raise RuntimeError(f"Could not detect current branch in {project_dir}: {err}")

    current = out.strip()

    # If there is already a branch, rename if needed
    if current:
        if current != default_branch:
            log(f"[FIX] Renaming branch {current} -> {default_branch}")
            if run_git_live(["branch", "-M", default_branch], project_dir) != 0:
                raise RuntimeError(f"Could not rename branch in {project_dir}")
        return

    # No current branch means probably no commits yet; that is fine.
    log(f"[INFO] Repo has no current branch yet; branch will be finalized on first commit.")


def has_any_commit(project_dir: Path) -> bool:
    code, _, _ = run_git(["rev-parse", "--verify", "HEAD"], cwd=project_dir)
    return code == 0


def commit_all(project_dir: Path, message: str, default_branch: str) -> bool:
    log("[INFO] Staging files...")
    if run_git_live(["add", "."], project_dir) != 0:
        raise RuntimeError(f"git add failed in {project_dir}")

    code, out, err = run_git(["status", "--porcelain"], cwd=project_dir)
    if code != 0:
        raise RuntimeError(f"git status failed in {project_dir}: {err}")

    if out.strip():
        log("[INFO] Creating commit...")
        if run_git_live(["commit", "-m", message], project_dir) != 0:
            raise RuntimeError(f"git commit failed in {project_dir}")

        # After first commit, ensure branch name is right
        code, current_branch, err = run_git(["branch", "--show-current"], cwd=project_dir)
        if code != 0:
            raise RuntimeError(f"Could not detect current branch after commit in {project_dir}: {err}")

        if current_branch.strip() != default_branch:
            log(f"[FIX] Renaming branch {current_branch.strip() or '<unknown>'} -> {default_branch}")
            if run_git_live(["branch", "-M", default_branch], project_dir) != 0:
                raise RuntimeError(f"Could not rename branch in {project_dir}")

        return True

    # No staged changes
    if not has_any_commit(project_dir):
        log("[WARN] No changes detected and no commits exist yet. Skipping commit.")
        return False

    return False


def set_or_update_remote(project_dir: Path, remote_name: str, remote_url: str) -> None:
    code, out, _ = run_git(["remote"], cwd=project_dir)
    if code != 0:
        raise RuntimeError(f"Could not list remotes in {project_dir}")

    remotes = {line.strip() for line in out.splitlines() if line.strip()}
    if remote_name in remotes:
        code, _, err = run_git(["remote", "set-url", remote_name, remote_url], cwd=project_dir)
        if code != 0:
            raise RuntimeError(f"Could not set remote URL in {project_dir}: {err}")
    else:
        code, _, err = run_git(["remote", "add", remote_name, remote_url], cwd=project_dir)
        if code != 0:
            raise RuntimeError(f"Could not add remote in {project_dir}: {err}")


def push_branch(project_dir: Path, branch: str, remote_name: str) -> None:
    log("[INFO] Pushing to GitHub...")
    if run_git_live(["push", "-u", remote_name, branch], project_dir) != 0:
        raise RuntimeError(f"git push failed in {project_dir}")


def get_upstream(project_dir: Path) -> str | None:
    code, out, _ = run_git(
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        cwd=project_dir,
    )
    if code == 0 and out.strip():
        return out.strip()
    return None


def process_project(
    project_dir: Path,
    user: str,
    token: str,
    private: bool,
    default_branch: str,
    remote_name: str,
    commit_message: str,
    dry_run: bool,
    max_folder_mb: float,
) -> str:
    repo_name = sanitize_repo_name(project_dir.name)
    repo_https = f"https://github.com/{user}/{repo_name}.git"

    print()
    log(f"=== {project_dir.name} ===")
    log(f"Repo name: {repo_name}")

    size_mb = folder_size_mb(project_dir)
    file_count = count_files(project_dir)
    log(f"[INFO] Folder size: {size_mb:.1f} MB")
    log(f"[INFO] File count: {file_count}")

    if size_mb > max_folder_mb:
        log(f"[SKIP] Folder exceeds max size limit ({max_folder_mb:.1f} MB).")
        binaries = list_large_binaries(project_dir)
        if binaries:
            log("[INFO] Example large/binary-type files found:")
            for path in binaries[:10]:
                try:
                    rel = path.relative_to(project_dir)
                except ValueError:
                    rel = path
                log(f"  - {rel}")
        return "skipped"

    if dry_run:
        log("[DRY RUN] Would check/create repo, commit changes, and push project.")
        return "success"

    exists = repo_exists(user, repo_name, token)
    if exists:
        log("[INFO] Repo already exists on GitHub.")
    else:
        log("[INFO] Creating GitHub repo...")
        create_repo(
            token=token,
            repo_name=repo_name,
            private=private,
            description=f"Imported from local folder: {project_dir.name}",
        )
        repo_data = verify_repo_exists_after_create(user, repo_name, token)
        log(f"[OK] Repo created: {repo_data.get('html_url', repo_https)}")

    write_gitignore_if_missing(project_dir)
    ensure_git_identity(project_dir)
    ensure_git_repo(project_dir, default_branch)

    committed = commit_all(project_dir, commit_message, default_branch)
    if committed:
        log("[OK] Commit created.")
    else:
        log("[INFO] No local changes to commit.")

    set_or_update_remote(project_dir, remote_name, repo_https)

    # Only push if there is at least one commit
    if has_any_commit(project_dir):
        push_branch(project_dir, default_branch, remote_name)

        upstream = get_upstream(project_dir)
        if upstream:
            log(f"[OK] Upstream set: {upstream}")
        else:
            log("[WARN] Could not confirm upstream branch.")

        log(f"[OK] Pushed to {repo_https}")
    else:
        log("[WARN] No commits exist, so nothing was pushed.")

    return "success"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan a folder for project subfolders, create GitHub repos, and push them."
    )
    parser.add_argument("parent_folder", help="Folder containing project subfolders")
    parser.add_argument("--private", action="store_true", help="Create private repos")
    parser.add_argument("--public", action="store_true", help="Create public repos")
    parser.add_argument("--branch", default="main", help="Default branch name (default: main)")
    parser.add_argument("--remote", default="origin", help="Git remote name (default: origin)")
    parser.add_argument(
        "--commit-message",
        default="Initial import",
        help="Commit message to use (default: Initial import)",
    )
    parser.add_argument(
        "--max-folder-mb",
        type=float,
        default=500.0,
        help="Skip folders larger than this many MB (default: 500)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without pushing")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.private and args.public:
        print("Choose only one of --private or --public.", file=sys.stderr)
        return 1

    private = True if args.private else False

    token = os.getenv("GITHUB_TOKEN", "").strip()
    user = os.getenv("GITHUB_USER", "").strip()

    if not token:
        print("Missing GITHUB_TOKEN environment variable.", file=sys.stderr)
        return 1
    if not user:
        print("Missing GITHUB_USER environment variable.", file=sys.stderr)
        return 1

    parent = Path(args.parent_folder).expanduser().resolve()
    if not parent.exists() or not parent.is_dir():
        print(f"Invalid folder: {parent}", file=sys.stderr)
        return 1

    verify_github_identity(user, token)

    projects = list_candidate_projects(parent)
    if not projects:
        print("No project subfolders found.")
        return 0

    log(f"Found {len(projects)} project(s) in: {parent}")

    success_count = 0
    error_count = 0
    skip_count = 0

    for project in projects:
        try:
            result = process_project(
                project_dir=project,
                user=user,
                token=token,
                private=private,
                default_branch=args.branch,
                remote_name=args.remote,
                commit_message=args.commit_message,
                dry_run=args.dry_run,
                max_folder_mb=args.max_folder_mb,
            )
            if result == "skipped":
                skip_count += 1
            else:
                success_count += 1
        except KeyboardInterrupt:
            log("[ABORTED] Stopped by user.")
            return 130
        except Exception as exc:
            error_count += 1
            log(f"[ERROR] {project.name}: {exc}")

    print()
    log("Done.")
    log(f"Successful: {success_count}")
    log(f"Errors: {error_count}")
    log(f"Skipped: {skip_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())