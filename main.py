import subprocess

from Discord import Discord


# Kill any existing chrome windows
def killChrome():
    try:
        subprocess.check_output('taskkill /im chrome.exe 2>NUL', shell=True)
    except:
        pass


discord = None
try:
    print("Starting process...")
    killChrome()
    discord = Discord()

    print("Attempting to open dashboard...")
    if discord.isLoggedIn():
        discord.searchUsers()
    else:
        print("You are not logged in. Log in before executing!")
finally:
    # Close browser when everything is done
    try:
        discord.exit()
    except:
        killChrome()
