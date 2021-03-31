from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from os import path
import glob
import os
import re
from apscheduler.schedulers.blocking import BlockingScheduler
import js_snippets
from datetime import datetime

import time
download_path = path.normpath(path.join(path.dirname(__file__), 'downloads'))

profile = webdriver.FirefoxProfile()

# language stuff
profile.set_preference('intl.accept_languages', 'en-us')

# export saves stuff
profile.set_preference('browser.helperApps.neverAsk.saveToDisk', 'text/plain')
profile.set_preference("browser.download.folderList", 2)
profile.set_preference('browser.download.dir', download_path)

# minimized performance stuff
profile.set_preference('dom.min_background_timeout_value', 5)
profile.set_preference('dom.min_background_timeout_value_without_budget_throttling', 5)
profile.set_preference('dom.timeout.throttling_delay', 0)

# allow pasting?
profile.set_preference('devtools.selfxss.count', 1)
# https://groups.google.com/g/mozilla.dev.platform/c/hcEqovQrBts?pli=1
# maybe disable it with dom.timeout.enable_budget_timer_throttling?
# seems to be not needed
# profile.set_preference('timeout.budget_throttling_max_delay', 5)

profile.update_preferences()
driver = webdriver.Firefox(firefox_profile=profile)


# load game
driver.get("http://kittensgame.com/web/")

# game needs some time to load
time.sleep(10)


def import_save(location):
    with open(location) as fo:
        save = fo.read()

    # open import ui
    driver.find_element_by_id('options-link').click()
    driver.find_element_by_id('importButton').click()

    # do import
    driver.find_element_by_id('importData').send_keys(save)
    time.sleep(1)
    driver.find_element_by_id('doImportButton').click()
    time.sleep(1)
    alert_obj = driver.switch_to.alert
    alert_obj.accept()
    time.sleep(2)


def export_save():
    driver.find_element_by_id('options-link').click()
    driver.find_element_by_id('exportButton').click()
    driver.find_element_by_id('exportToFullFile').click()
    time.sleep(1)
    driver.find_element_by_id('closeButton').click()
    driver.find_element_by_id('optionsDiv').send_keys(Keys.ESCAPE)
    print("saving...")


def auto_hunt():
    catpower = driver.execute_script("return gamePage.resPool.get('manpower');")
    print(f"{datetime.now().strftime('%H:%M:%S')} starthunt [{catpower['value']}].", end=" ")
    example_catpower = {
        'calculatePerTick': True, 'color': '#DBA901', 'isHidden': False, 'isRefundable': {}, 'maxValue': 3906.1,
        'name': 'manpower', 'perTickCached': 2.860868, 'title': 'catpower', 'transient': True, 'type': 'common',
        'unlocked': True, 'value': 3906.1, 'visible': True}

    if catpower["value"] >= catpower["maxValue"] * 0.9:
        # print(f"crafting parchments before hunt...")
        driver.execute_script(f'gamePage.craftAll("parchment")')
        print(f"{datetime.now().strftime('%H:%M:%S')} Hunting, cat power is: ({catpower['value']}/{catpower['maxValue']})", end=" ")
        driver.execute_script("gamePage.village.huntAll();")

    print(f"{datetime.now().strftime('%H:%M:%S')} endhunt")


def auto_craft():
    crafts = {
        'wood': 'beam',
        'minerals': 'slab',
        'coal': 'steel',
        'iron': 'plate',
        'culture': 'manuscript',
        'science': 'compedium'  # this typo is actually part of the game :(
    }

    for resource in crafts:
        res_obj = driver.execute_script(f'return gamePage.resPool.get("{resource}");')
        if res_obj['value'] >= res_obj['maxValue'] * 0.9:
            driver.execute_script(f'gamePage.craftAll("{crafts[resource]}")')
            # print(f'Crafting {crafts[resource]}!')


def auto_build():

    target_buildings = [
        'workshop',

        'hut',
        'logHouse',

        'barn',
        'observatory',
        'mine',
        'lumberMill',
        'quarry',
        'smelter',
        
        'library',
        'academy',

        'pasture',
        'aqueduct',
        'amphitheatre',


    ]
    #'amphitheatre'
    buildable = driver.execute_script(js_snippets.all_buildable)

    for target in target_buildings:

        if target in buildable:
            print(f"{datetime.now().strftime('%H:%M:%S')} building {target}")
            driver.execute_script(js_snippets.build_x.render(x=target))
            buildable = driver.execute_script(js_snippets.all_buildable)


def sorter(save_name):
    base_path = os.path.basename(save_name)
    run, year, day = re.findall(r'\d+', base_path)
    return int(run)*10**6 + int(year)*10**3 + int(day)


if __name__ == '__main__':
    most_recent_save = sorted(glob.glob(download_path + "/*.txt"), key=sorter)[-1]
    print(f"importing most recent save {most_recent_save}...")
    import_save(most_recent_save)

    print('setting up scheduler...')
    scheduler = BlockingScheduler()
    scheduler.add_job(auto_build, 'interval', minutes=1)
    scheduler.add_job(auto_hunt, 'interval', minutes=1)
    scheduler.add_job(auto_craft, 'interval', minutes=2)
    scheduler.add_job(export_save, 'interval', minutes=20)
    scheduler.start()
