import os
import subprocess


def get_git_revision_short_hash_or_latest(dir: str = "tmp") -> str:
    path = f"{dir}/wagers_{get_git_revision_short_hash()}.csv"
    if os.path.exists(path):
        return get_git_revision_short_hash()
    else:
        files = [
            f for f in os.listdir(dir) if f.startswith("wagers_") and f.endswith(".csv")
        ]
        if not files:
            return "latest"
        return sorted(files)[-1].replace("wagers_", "").replace(".csv", "")


def get_git_revision_short_hash() -> str:
    return (
        subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
        .decode("ascii")
        .strip()
    )
