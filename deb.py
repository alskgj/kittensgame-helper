from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from os import path
import glob
import os
import re
from apscheduler.schedulers.blocking import BlockingScheduler
import js_snippets
from datetime import datetime
import configparser
config = configparser.ConfigParser()
config.read('config.ini')

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


def sorter(save_name):
    base_path = os.path.basename(save_name)
    run, year, day = re.findall(r'\d+', base_path)
    return int(run)*10**6 + int(year)*10**3 + int(day)


def constraint_satisfied(constraint):
    if constraint == 'always':
        return True
    elif constraint == 'never':
        return False
    else:
        return is_researched(constraint)


def config_build():
    config.read('config.ini')  # refresh view, to reflect user changes
    build_any_of_those = []

    buildable_with_prices = driver.execute_script(js_snippets.buildable_with_prices)
    for building in buildable_with_prices:
        name = building["name"]            # ie 'mansion'
        resources = building["resources"]  # ie ['titanium', 'slab', 'steel']

        all_constraints_satisfied = True
        for res in resources:
            try:
                constraint = config['Auto Build Prerequisites'][res]
            except KeyError:
                print(f"Resource {res} not in Auto Build Prerequisites...")
                raise NotImplementedError
            if not constraint_satisfied(constraint):
                print(f"{name} does not satisfy constraint {constraint} from res {res}")
                all_constraints_satisfied = False

        if all_constraints_satisfied:
            build_any_of_those.append(name)

    return build_any_of_those

the_button_func = """
window.script_paused = false;
window.theButton = function() {
if (document.getElementById("toggleScript").style.color == "black") {
    document.getElementById("toggleScript").style.color = 'red';
    gamePage.msg('Script is now paused!');
    window.script_paused = true;
} else {
    document.getElementById("toggleScript").style.color = 'black';
    gamePage.msg('Script is now running!');
    window.script_paused = false;
}
}
"""


def setup():
    driver.execute_script(the_button_func)
    driver.execute_script("$(\"#footerLinks\").append('<div><button id=\"toggleScript\" style=\"color:black\" onclick=\"theButton()\"> Pause script... </button></br></div>');")



if __name__ == '__main__':
    most_recent_save = sorted(glob.glob(download_path + "/*.txt"), key=sorter)[-1]
    print(f"{datetime.now().strftime('%H:%M:%S')} importing most recent save {most_recent_save}...")
    import_save(most_recent_save)
    setup()