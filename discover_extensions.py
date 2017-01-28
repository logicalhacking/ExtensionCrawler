#!/usr/bin/env python3
#
# Copyright (C) 2017 The University of Sheffield, UK
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from selenium import webdriver
import time
import os
import re
import time
import sys
import datetime
import argparse

class ExtensionExplorer:
    def scroll(self, driver):
        driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')

    def click_more(self, driver):
        more_btn = driver.find_element_by_xpath("//div[text()='See More']")
        if more_btn and more_btn.is_displayed():
            more_btn.click()

    def save_ids(self, driver, savefile):
        #This does not give us the complete source, unfortunately:
        #content = driver.page_source

        content = driver.execute_script('return document.body.innerHTML')
        ids = sorted(set(re.findall('\/([a-z]{32})"', content)))

        oldids = []
        try:
            with open(savefile, 'r') as f:
                for line in f:
                    oldids.append(line.strip())
            oldids = sorted(set(oldids))
        except:
            pass
        if ids == oldids:
            return False

        with open(savefile, 'w') as f:
            f.write('\n'.join(ids))
        return True
    def run(self, outdir, interval):
        os.makedirs(outdir, exist_ok=True)
        savefile = os.path.join(outdir, 'ids-{}.txt'.format(datetime.datetime.now().isoformat()))

        driver = webdriver.PhantomJS(service_log_path=os.path.devnull)
        content = driver.get('https://chrome.google.com/webstore/category/extensions')

        last_save = 0
        while True:
            try:
                self.scroll(driver)
                self.click_more(driver)
            except Exception as e:
                print(e, file=sys.stderr)

            if time.time() - last_save > interval:
                if not self.save_ids(driver, savefile):
                    driver.quit()
                    sys.exit(0)
                last_save = time.time()

            time.sleep(0.5)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description='Crawls the Google Play Store for new extension ids.')
    parser.add_argument('out', help='The directory where the files with new ids should be stored.')
    parser.add_argument('-t', '--interval', help='Saves the found ids to file every X seconds. If no new ids have been found within these X seconds, the crawler quits.', default=30.0, type=float)
    args = parser.parse_args()
    ExtensionExplorer().run(args.out, args.interval)
