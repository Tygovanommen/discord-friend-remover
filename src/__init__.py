import subprocess

from src.Discord import Discord


# Kill any existing chrome windows
def kill_chrome():
    try:
        subprocess.check_output('taskkill /im chrome.exe 2>NUL', shell=True)
    except subprocess.CalledProcessError:
        pass


discord = None
try:
    print("Starting process...")
    kill_chrome()
    discord = Discord()

    print("Attempting to open dashboard...")
    if discord.is_logged_in():
        discord.search_users()
    else:
        print("You are not logged in. Log in before executing!")
finally:
    # Close browser when everything is done
    try:
        discord.exit()
    except:
        kill_chrome()
