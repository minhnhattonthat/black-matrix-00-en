"""clean.py: free disk space in a published project by deleting what can be rebuilt or downloaded again.

Deletes build/, out/, output*/, work/ except work/states/, .pytest_cache/, .venv/, __pycache__/, and emulator downloads
(a tools/ subdirectory with an .exe or .dll at its top). Only paths git ignores and doesn't track; a tools/ subdirectory
holding a BIOS or Firmware folder is kept. rom/, release/, saves and savestates are never touched.
Skips a project with no git tag, local or on origin (not published), unless --force. Dry run unless --yes.

    python -X utf8 tools/clean.py                      # this project, dry run
    python -X utf8 tools/clean.py H:/translation/* --yes"""
import argparse
import os
import shutil
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAVES = {".sav", ".srm", ".state", ".mss", ".sstate", ".ppst", *(f".ds{i}" for i in range(10))}  # as in .gitignore


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def is_emulator(d):
    names = {p.name.lower() for p in d.iterdir()}
    if names & {"bios", "firmware"}:
        return False  # user-supplied BIOS lives here; not downloadable
    return any(n.endswith((".exe", ".dll")) for n in names)


def candidates(repo):
    picked = [repo / n for n in ("build", "out", ".pytest_cache", ".venv")] + list(repo.glob("output*"))
    if (repo / "work").is_dir():
        picked += [p for p in (repo / "work").iterdir() if p.name not in ("states", "saves") and p.suffix not in SAVES]
    if (repo / "tools").is_dir():
        picked += [p for p in (repo / "tools").iterdir() if p.is_dir() and is_emulator(p)]
    skip = set(picked) | {repo / ".git", repo / "rom"}
    for dirpath, dirs, _ in os.walk(repo):
        if "__pycache__" in dirs:
            picked.append(Path(dirpath, "__pycache__"))
        dirs[:] = [d for d in dirs if d != "__pycache__" and Path(dirpath, d) not in skip]
    return [p for p in picked if p.exists()
            and git(repo, "check-ignore", "-q", str(p)).returncode == 0
            and not git(repo, "ls-files", "--", str(p)).stdout]


def size(p):
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def make_writable(func, path, _):  # git objects in nested clones are read-only on Windows
    os.chmod(path, stat.S_IWRITE)
    func(path)


def clean(repo, yes, force):
    if not (repo / ".git").exists():
        print(f"{repo}: not a git repo, skipped")
        return 0
    published = git(repo, "tag").stdout.strip() or git(repo, "ls-remote", "--tags", "origin").stdout.strip()
    if not published and not force:
        print(f"{repo}: no git tag here or on origin (not published?), skipped; --force to clean anyway")
        return 0
    print(repo)
    total = 0
    for p in candidates(repo):
        n = size(p)
        total += n
        print(f"  {n / 2**20:9.1f} MB  {p.relative_to(repo)}")
        if yes:
            shutil.rmtree(p, onexc=make_writable) if p.is_dir() else p.unlink()
    print(f"  {total / 2**20:.1f} MB {'freed' if yes else 'to free (dry run; --yes to delete)'}")
    return total


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repos", nargs="*", type=Path, default=[ROOT], help="project directories (default: this one)")
    ap.add_argument("--yes", action="store_true", help="delete; without it, only list")
    ap.add_argument("--force", action="store_true", help="clean projects with no git tag too")
    args = ap.parse_args()
    total = sum(clean(r.resolve(), args.yes, args.force) for r in args.repos if r.is_dir())
    if len(args.repos) > 1:
        print(f"total: {total / 2**30:.2f} GB")
