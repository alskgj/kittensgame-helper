from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from os import path
import glob
import os
import re
from apscheduler.schedulers.blocking import BlockingScheduler
import js_snippets
from datetime import datetime
from random import randint
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
time.sleep(7)

constructed_buildings = []

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
    print(f"{datetime.now().strftime('%H:%M:%S')} saving...")
    do_report()


def auto_hunt():
    catpower = driver.execute_script("return gamePage.resPool.get('manpower');")
    # print(f"{datetime.now().strftime('%H:%M:%S')} starthunt [{catpower['value']}].", end=" ")
    example_catpower = {
        'calculatePerTick': True, 'color': '#DBA901', 'isHidden': False, 'isRefundable': {}, 'maxValue': 3906.1,
        'name': 'manpower', 'perTickCached': 2.860868, 'title': 'catpower', 'transient': True, 'type': 'common',
        'unlocked': True, 'value': 3906.1, 'visible': True}

    # prioritize trading over hunting
    gold_obj = driver.execute_script(f'return gamePage.resPool.get("gold");')
    if gold_obj['value'] >= gold_obj['maxValue'] * 0.8:
        auto_trade()

    if catpower["value"] >= catpower["maxValue"] * 0.8:
        # print(f"crafting parchments before hunt...")
        driver.execute_script(f'gamePage.craftAll("parchment")')
        # print(f"{datetime.now().strftime('%H:%M:%S')} Hunting, cat power is: ({catpower['value']}/{catpower['maxValue']})")
        driver.execute_script("gamePage.village.huntAll();")

    # print(f"{datetime.now().strftime('%H:%M:%S')} endhunt")


def is_researched(tech):
    science = driver.execute_script('return gamePage.science.meta[0]["meta"];')
    # science is a list of dicts, containing the key 'researched' and 'unlocked'
    # and many others

    # there is also 'label'
    filtered = [t for t in science if t['name'] == tech]
    if len(filtered) != 1:
        print(f'Searched for {tech}, but couldn\'t find it. Filtered is {filtered}.')
        raise NotImplementedError

    return filtered[0]['researched']


def auto_craft():
    crafts = {
        'wood': 'beam',
        'minerals': 'slab',
        'coal': 'steel',
        'iron': 'plate',
        'culture': 'manuscript',
    }

    if is_researched('navigation'):
        crafts['science'] = 'compedium'
    if is_researched('genetics'):
        if randint(0, 1) == 0:
            crafts['science'] = 'compedium'
        else:
            crafts['science'] = 'blueprint'


    for resource in crafts:
        res_obj = driver.execute_script(f'return gamePage.resPool.get("{resource}");')
        if res_obj['value'] >= res_obj['maxValue'] * 0.9:
            driver.execute_script(f'gamePage.craftAll("{crafts[resource]}")')
            # print(f'Crafting {crafts[resource]}!')


def auto_trade():
    # todo send explorers to find griffins
    gold_obj = driver.execute_script(f'return gamePage.resPool.get("gold");')
    iron_obj = driver.execute_script(f'return gamePage.resPool.get("iron");')
    titanium_obj = driver.execute_script(f'return gamePage.resPool.get("titanium");')

    zebras_unlocked = driver.execute_script(f'return gamePage.diplomacy.get("zebras").unlocked;')
    griffins_unlocked = driver.execute_script(f'return gamePage.diplomacy.get("griffins").unlocked;')

    # auto level embassies
    driver.execute_script(js_snippets.upgrade_embassies)

    # enough gold to trade
    if gold_obj['value'] >= gold_obj['maxValue'] * 0.8:

        # make space for iron
        if iron_obj['value'] >= iron_obj['maxValue'] * 0.5 and (zebras_unlocked or griffins_unlocked):
            driver.execute_script(f'gamePage.craftAll("plate")')

        if titanium_obj['value'] <= titanium_obj['maxValue'] * 0.5 and zebras_unlocked:
            print(f'{datetime.now().strftime("%H:%M:%S")} trading with zebras')
            # create slabs if not available
            slabs = driver.execute_script(f'return gamePage.resPool.get("slab");')['value']
            if slabs < 100:
                driver.execute_script(f'gamePage.craftAll("slab")')
            driver.execute_script('gamePage.diplomacy.tradeAll(game.diplomacy.get("zebras"));')

        elif griffins_unlocked:
            driver.execute_script('gamePage.diplomacy.tradeAll(game.diplomacy.get("griffins"));')
            print(f'{datetime.now().strftime("%H:%M:%S")} trading with griffins')


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

        'chapel'
    ]

    # manuscripts and gold should be available now
    if is_researched('genetics'):
        target_buildings.append('temple')
        target_buildings.append('tradepost')

    # titanium shouldn't be a problem anymore
    if is_researched('rocketry'):
        target_buildings.append('mansion')


    # todo add conditional buildings, maybe
    # temple, after reaching space?
    # mansion, if we have 2k+ ships
    # harbour? need to craft scaffold

    # todo library - datacenter


    buildable = driver.execute_script(js_snippets.all_buildable)

    built = []
    for target in target_buildings:

        if target in buildable:
            built.append(target)
            constructed_buildings.append(target)
            driver.execute_script(js_snippets.build_x.render(x=target))
            buildable = driver.execute_script(js_snippets.all_buildable)
    if built:
        print(f"{datetime.now().strftime('%H:%M:%S')} built {built}")
    # if not built:
    #     print(f"{datetime.now().strftime('%H:%M:%S')} built nothing, buildable: {buildable}")


def do_report():
    counts = {}
    global constructed_buildings
    for building in constructed_buildings:
        if building not in counts:
            counts[building] = 1
        else:
            counts[building] += 1
    counts['mansion'] += 10

    print('Constructed the following buildings since last time saving: ')
    for building, count in counts.items():
        print(f'{count:2}x {building}')

    constructed_buildings = []


def switch_to_build_tab():
    """Can't build without this - but disrupts user from playing
    manually - so this is meant to be invoked infrequently, to prevent
    long phases of inactivity in a tab that prevents building"""
    driver.execute_script('gamePage.bldTab.domNode.click();')


def sorter(save_name):
    base_path = os.path.basename(save_name)
    run, year, day = re.findall(r'\d+', base_path)
    return int(run)*10**6 + int(year)*10**3 + int(day)


if __name__ == '__main__':
    most_recent_save = sorted(glob.glob(download_path + "/*.txt"), key=sorter)[-1]
    print(f"{datetime.now().strftime('%H:%M:%S')} importing most recent save {most_recent_save}...")
    import_save(most_recent_save)

    print(f'{datetime.now().strftime("%H:%M:%S")} setting up scheduler...')
    scheduler = BlockingScheduler()

    scheduler.add_job(auto_hunt, 'interval', seconds=30)
    scheduler.add_job(auto_build, 'interval', seconds=31)
    time.sleep(1)
    scheduler.add_job(auto_craft, 'interval', minutes=2)
    scheduler.add_job(auto_trade, 'interval', minutes=1, seconds=1)
    scheduler.add_job(switch_to_build_tab, 'interval', minutes=10)
    time.sleep(3)
    scheduler.add_job(export_save, 'interval', minutes=20)


    scheduler.start()
    input()

