import re
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

APP_URL = "https://discord.com/app"
FRIENDS_URL = "https://discord.com/channels/@me"

# Chrome 136+ refuses to automate the default Chrome profile, so the script keeps
# its own profile. You log in once and the session is remembered for next runs.
PROFILE_DIR = Path.home() / ".discord-friend-remover" / "chrome-profile"

# Discord hashes its class names (e.g. "peopleListItem_a1b2c3"), so match on the
# stable prefix with *= and prefer data/aria attributes where they exist.
FRIEND_ROW_SELECTORS = [
    "div[class*='peopleListItem']",
    "[role='listitem']:has([data-list-item-id^='people___'])",
]
MORE_BUTTON_SELECTORS = [
    "[aria-label^='More options']",
    "div[class*='actions'] > div:nth-child(2)",
]
REMOVE_MENU_ITEM = "#friend-row-remove-friend"
CONFIRM_BUTTON = "[role='dialog'] button[class*='critical-primary'], [role='dialog'] button[type='submit']"
DIALOG = "div[class*='layerContainer'] [role='dialog']"

# Reads user ID, display name and username from a friend row. The username span
# is only visible on hover, so use textContent instead of Selenium's .text.
FRIEND_INFO_JS = """
const row = arguments[0];
const text = sel => {
    const el = row.querySelector(sel);
    return el ? el.textContent.trim() : null;
};
const item = row.querySelector("[data-list-item-id^='people___']");
return {
    id: item ? item.getAttribute("data-list-item-id").replace("people___", "") : null,
    name: text("[class*='username']"),
    username: text("[class*='infoSpacing']"),
};
"""

# Scrolls the friend list's scroll container one page (or to the top).
SCROLL_JS = """
let el = arguments[0];
while (el && !(el.scrollHeight > el.clientHeight
               && /(auto|scroll)/.test(getComputedStyle(el).overflowY))) {
    el = el.parentElement;
}
if (!el) return false;
const before = el.scrollTop;
el.scrollTop = arguments[1] ? 0 : before + el.clientHeight * 0.8;
return el.scrollTop !== before;
"""


def describe(friend):
    if friend["username"] and friend["username"] != friend["name"]:
        return f"{friend['name']} (@{friend['username']})"
    return friend["name"] or friend["key"]


class Discord:

    def __init__(self, dry_run=True, exclude=()):
        self.dry_run = dry_run
        # Usernames, display names or user IDs, compared case-insensitively.
        self.exclude = {e.strip().lstrip("@").lower() for e in exclude if e.strip()}

        options = webdriver.ChromeOptions()
        options.add_argument("--user-data-dir=" + str(PROFILE_DIR))
        options.add_argument("--disable-extensions")

        # Selenium Manager (built into Selenium >= 4.6) downloads a matching
        # chromedriver automatically, no webdriver-manager needed.
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 15)

    def is_logged_in(self):
        self.driver.get(APP_URL)
        try:
            WebDriverWait(self.driver, 15).until(
                lambda d: "/login" in d.current_url or "/channels/" in d.current_url
            )
        except TimeoutException:
            pass
        return "/login" not in self.driver.current_url

    def wait_for_login(self, timeout=300):
        """Give the user time to log in manually in the opened browser window."""
        print("Please log in to Discord in the opened browser window "
              f"(waiting up to {timeout} seconds)...")
        try:
            WebDriverWait(self.driver, timeout, poll_frequency=1).until(
                lambda d: "/channels/" in d.current_url
            )
            return True
        except TimeoutException:
            return False

    def dismiss_popups(self, attempts=5):
        """Close promo/what's-new dialogs (e.g. Nitro offers) that block clicks."""
        for _ in range(attempts):
            if not self.driver.find_elements(By.CSS_SELECTOR, DIALOG):
                return
            self._close_layers()
            try:
                WebDriverWait(self.driver, 3).until_not(
                    lambda d: d.find_elements(By.CSS_SELECTOR, DIALOG))
            except TimeoutException:
                pass

    def open_all_friends(self):
        self.driver.get(FRIENDS_URL)
        tabs = self.wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[role='tab']"))
        )
        # Popups tend to appear a moment after the page loads.
        time.sleep(2)
        self.dismiss_popups()

        # Never pick the "Add Friend" tab.
        tabs = [t for t in tabs if "addFriend" not in (t.get_attribute("class") or "")]
        all_tab = next(
            (t for t in tabs
             if (t.get_attribute("textContent") or "").strip().lower() == "all"),
            None,
        )
        if all_tab is None:
            # Non-English client: "All" is the second tab after "Online", or the
            # only one when Discord hides "Online"/"Pending".
            all_tab = tabs[1] if len(tabs) > 1 else tabs[0]
        all_tab.click()

    def _find_any(self, root, selectors):
        for selector in selectors:
            elements = root.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                return elements
        return []

    def friend_rows(self):
        return self._find_any(self.driver, FRIEND_ROW_SELECTORS)

    def rendered_friends(self):
        """Info for every friend row currently rendered (Discord virtualizes the list)."""
        friends = []
        for row in self.friend_rows():
            try:
                info = self.driver.execute_script(FRIEND_INFO_JS, row)
            except StaleElementReferenceException:
                continue
            info["row"] = row
            info["key"] = info["id"] or info["username"] or info["name"]
            friends.append(info)
        return friends

    def is_excluded(self, friend):
        return any(
            value and value.lower() in self.exclude
            for value in (friend["id"], friend["username"], friend["name"])
        )

    def _scroll_list(self, to_top=False):
        """Scroll the friend list one page down (or to the top). Returns True if it moved."""
        rows = self.friend_rows()
        if not rows:
            return False
        moved = self.driver.execute_script(SCROLL_JS, rows[0], to_top)
        if moved:
            time.sleep(0.5)  # give Discord time to render the next rows
        return moved

    def collect_friends(self):
        """Scroll through the whole list once to get every friend, in list order."""
        self._scroll_list(to_top=True)
        friends = {}
        while True:
            for friend in self.rendered_friends():
                friends.setdefault(friend["key"], friend)
            if not self._scroll_list():
                break
        self._scroll_list(to_top=True)
        return list(friends.values())

    def friend_count(self):
        """Read the 'ALL FRIENDS — 42' header, or None if it can't be found."""
        for header in self.driver.find_elements(
                By.CSS_SELECTOR, "[class*='peopleColumn'] h2, [class*='peopleColumn'] [class*='title']"):
            match = re.search(r"(\d+)\s*$", header.text.strip())
            if match:
                return int(match.group(1))
        # Don't fall back to counting rows: the list is virtualized, so only
        # part of it is rendered and the count would be wrong.
        return None

    def _close_layers(self):
        ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()

    def remove_friend(self, row):
        ActionChains(self.driver).move_to_element(row).perform()
        more = self._find_any(row, MORE_BUTTON_SELECTORS)
        if not more:
            raise NoSuchElementException("Could not find the 'More' button on a friend row")
        more[0].click()

        self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, REMOVE_MENU_ITEM))).click()
        confirm = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, CONFIRM_BUTTON)))

        if self.dry_run:
            # Close the confirmation dialog without removing anyone.
            self._close_layers()
            self.wait.until(EC.staleness_of(confirm))
        else:
            confirm.click()
            self.wait.until(EC.staleness_of(row))

    def search_users(self):
        self.open_all_friends()
        try:
            self.wait.until(lambda d: self.friend_rows())
        except TimeoutException:
            print("No friends found.")
            return

        friends = self.collect_friends()
        expected = self.friend_count()
        print(f"{len(friends)} friends were found")
        if expected is not None and len(friends) != expected:
            print(f"Warning: Discord says you have {expected} friends, "
                  "but not all of them could be read from the list.")

        kept = [f for f in friends if self.is_excluded(f)]
        targets = [f for f in friends if not self.is_excluded(f)]

        if kept:
            print(f"\nKeeping {len(kept)} excluded friends:")
            for friend in kept:
                print("  - " + describe(friend))

        matched = {v.lower() for f in kept for v in (f["id"], f["username"], f["name"]) if v}
        unmatched = sorted(self.exclude - matched)
        if unmatched:
            print("\nWarning: these exclude entries did not match any friend: "
                  + ", ".join(unmatched))

        if not targets:
            print("\nNothing to remove.")
            return

        if self.dry_run:
            print(f"\nDry run: {len(targets)} friends would be removed. Opening the remove "
                  "dialog for each and cancelling it.")
        else:
            print(f"\n{len(targets)} friends will be removed:")
            for friend in targets:
                print("  - " + describe(friend))
            answer = input(f"Are you sure you want to remove these {len(targets)} friends? [y/n]\n")
            if not answer or answer[0].lower() != "y":
                print("You did not indicate approval")
                return

        done, missing = self._process(targets)
        if missing:
            print(f"Warning: {len(missing)} friends were not processed: "
                  + ", ".join(describe(f) for f in missing))
        if self.dry_run:
            print(f"Dry run finished: {done} friends checked, nobody was removed.")
            print("Run again with --remove to actually remove them.")
        else:
            print(f"Done: removed {done} friends.")

    def _process(self, targets):
        """Remove (or in a dry run, cancel removing) exactly the given friends."""
        pending = {f["key"]: f for f in targets}
        done = 0
        self._scroll_list(to_top=True)
        while pending:
            visible = [f for f in self.rendered_friends() if f["key"] in pending]
            if not visible:
                if self._scroll_list():
                    continue
                break
            friend = visible[0]
            try:
                self.remove_friend(friend["row"])
            except StaleElementReferenceException:
                continue
            except TimeoutException:
                # Usually Discord rate limiting or a changed UI. Stop instead of
                # crashing so the summary below is still printed.
                self._close_layers()
                print(f"Timed out on {describe(friend)}, stopping. "
                      "Wait a bit and run the script again to continue.")
                break
            del pending[friend["key"]]
            done += 1
            verb = "Checked" if self.dry_run else "Removed"
            print(f"{verb} {done}/{len(targets)}: {describe(friend)}")
        return done, list(pending.values())

    def exit(self):
        print("Exiting program...")
        self.driver.quit()
