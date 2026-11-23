<div align="center">

# 🧹 Discord Friend Remover

**Remove all your Discord friends automatically, with a safe dry run first.**

[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Selenium](https://img.shields.io/badge/selenium-4.11%2B-43B02A?logo=selenium&logoColor=white)](https://www.selenium.dev/)
[![License: MIT](https://img.shields.io/github/license/Tygovanommen/discord-friend-remover?color=yellow)](LICENSE)

</div>

---

## 🚀 Usage

Requires Python 3.9+ and Google Chrome. Selenium downloads the matching chromedriver for you.

```bash
pip install -r requirements.txt

python -m src            # dry run: opens and cancels the remove dialog for each friend
python -m src --remove   # removes them for real, after you confirm
```

The first time you run it, Chrome opens on the Discord login page and waits up to 5 minutes for you to log in. Your session is saved in `~/.discord-friend-remover/chrome-profile`, so you only have to log in once.

Before removing anything, the script reads your whole friends list and shows who it will remove. If it stops partway (for example because Discord rate-limits you), run it again to continue.

## 🛡️ Keeping some friends

To keep a friend, pass their username, user ID or display name. Matching ignores case and a leading `@`.

```bash
python -m src --remove --exclude bob_42 123456789012345678
```

You can also list them in an `exclude.txt` in the project folder, one per line, with `#` for comments. The script reads it automatically, or you can point to another file with `--exclude-file path/to/file.txt`. `exclude.txt` is in `.gitignore`, so your list won't be committed.

- Use usernames or user IDs where you can. A display name keeps *every* friend who has that name.
- To copy a user ID, turn on *Developer Mode* in Discord's settings, then right-click the user and choose *Copy User ID*.
- The script lists the friends it keeps and warns about exclude entries that don't match anyone, so check for typos before you confirm.

## ⚠️ Disclaimer

> [!WARNING]
> **USE AT YOUR OWN RISK.** Automating your account may violate the [Discord Terms of Service](https://discord.com/terms), and removed friends can't be restored.

## 📄 License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for details.
