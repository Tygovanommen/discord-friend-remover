from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from os import path
import os
import time


class Discord:

    isTest = True
    driver = None

    def __init__(self):
        os.environ['WDM_LOG_LEVEL'] = '0'

        options = webdriver.ChromeOptions()
        # Get relative path
        dumps_dir = path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data')
        options.add_argument(r"--user-data-dir=" + dumps_dir)

        options.add_argument('--disable-extensions')
        self.driver = webdriver.Chrome(
            executable_path=ChromeDriverManager().install(),
            options=options
        )

    def is_logged_in(self):
        self.driver.get("https://discord.com/app")
        current_url = self.driver.current_url
        if current_url == "https://discord.com/login":
            return False

        return True

    def search_users(self):
        time.sleep(1)
        self.driver.find_element("div[class^='tabBar'] div:nth-child(2)").click()

        # Get user tags
        users_blocks = self.driver.find_element(
            "div[class^='peopleColumn'] div[class^='peopleListItem']")

        # Ask for confirmation
        print(str(len(users_blocks)) + " users were found")
        answer = input("Are you sure you want to deleted them? [y/n]\n")
        if not answer or answer[0].lower() != 'y':
            print('You did not indicate approval')
            self.exit()

        # Loop through users blocks
        for userBlock in users_blocks:
            userBlock.find_element("div[class^='actions'] div:nth-child(2)").click()
            time.sleep(0.1)
            self.driver.find_element("#friend-row-remove-friend").click()
            time.sleep(0.1)

            # Set isTest variable to test the code
            if self.isTest:
                self.driver.find_element("div[class^='layerContainer'] button[type='button']").click()
            else:
                self.driver.find_element("div[class^='layerContainer'] button[type='submit']").click()

            time.sleep(0.1)

    def exit(self):
        print("Exiting program...")
        self.driver.quit()
        exit(1)
