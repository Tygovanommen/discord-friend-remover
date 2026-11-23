import argparse
from pathlib import Path

from src.Discord import Discord

DEFAULT_EXCLUDE_FILE = Path("exclude.txt")


def read_exclude_file(path):
    """One username, display name or user ID per line. '#' starts a comment."""
    entries = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            entries.append(line)
    return entries


def main():
    parser = argparse.ArgumentParser(description="Remove all your Discord friends.")
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Actually remove friends. Without this flag the script only does a dry run.",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        action="extend",
        default=[],
        metavar="USER",
        help="Friends to keep: username, display name or user ID (case-insensitive).",
    )
    parser.add_argument(
        "--exclude-file",
        metavar="PATH",
        help="File with friends to keep, one per line "
             f"(default: {DEFAULT_EXCLUDE_FILE} if it exists).",
    )
    args = parser.parse_args()

    exclude = list(args.exclude)
    exclude_file = args.exclude_file or (DEFAULT_EXCLUDE_FILE if DEFAULT_EXCLUDE_FILE.exists() else None)
    if exclude_file:
        exclude += read_exclude_file(exclude_file)
        print(f"Loaded exclude list from {exclude_file}")

    print("Starting process...")
    discord = Discord(dry_run=not args.remove, exclude=exclude)
    try:
        print("Attempting to open dashboard...")
        if not discord.is_logged_in() and not discord.wait_for_login():
            print("You are not logged in. Log in before executing!")
            return
        discord.search_users()
    finally:
        # Close browser when everything is done
        discord.exit()


if __name__ == "__main__":
    main()
