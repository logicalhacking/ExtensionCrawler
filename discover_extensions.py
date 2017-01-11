#!/bin/env python3
from selenium import webdriver
import time
import os
import re
import time
import sys
import datetime

def scroll(driver):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

def click_more(driver):
    more_btn = driver.find_element_by_xpath("//div[text()='See More']")
    if more_btn and more_btn.is_displayed():
        more_btn.click()
        #print("More Button found, seen and clicked")

def save_ids(driver, savefile):
    #This does not give is the complete source, unfortunately:
    #content = driver.page_source

    content = driver.execute_script("return document.body.innerHTML")
    ids = sorted(set(re.findall("""[a-z]{32}""", content)))

    oldids = []
    try:
        with open(savefile, "r") as f:
            for line in f:
                oldids.append(line.strip())
        oldids = sorted(set(oldids))
    except:
        pass
    if ids == oldids:
        return False

    with open(savefile, "w") as f:
        f.write("\n".join(ids))
        #print("IDs written")
    return True

savedir = "."
if len(sys.argv) > 1:
    savedir = sys.argv[1]
    os.makedirs(savedir)
savefile = os.path.join(savedir, "ids-{}.txt".format(datetime.datetime.now().isoformat()))

driver = webdriver.PhantomJS() 
content = driver.get('https://chrome.google.com/webstore/category/extensions')

last_save = 0
while True:
    scroll(driver)
    click_more(driver)

    if time.time() - last_save > 30.0:
        if not save_ids(driver, savefile):
            #print("No new extension ids since last save, exiting...")
            sys.exit(0)
        last_save = time.time()

    time.sleep(0.5)
