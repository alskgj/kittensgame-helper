from os import path

from selenium import webdriver
import logging
import time
import os
import glob
import re
import js_snippets
from functools import lru_cache
from selenium.webdriver.common.keys import Keys


def sorter(save_name):
    base_path = os.path.basename(save_name)
    run, year, day = re.findall(r'\d+', base_path)
    return int(run)*10**6 + int(year)*10**3 + int(day)


class Game:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

        self.download_path = path.normpath(path.join(path.dirname(__file__), 'downloads'))

        # browser config
        profile = webdriver.FirefoxProfile()

        # language stuff
        profile.set_preference('intl.accept_languages', 'en-us')

        # export saves stuff
        profile.set_preference('browser.helperApps.neverAsk.saveToDisk', 'text/plain')
        profile.set_preference("browser.download.folderList", 2)
        profile.set_preference('browser.download.dir', self.download_path)

        # minimized performance stuff
        profile.set_preference('dom.min_background_timeout_value', 5)
        profile.set_preference('dom.min_background_timeout_value_without_budget_throttling', 5)
        profile.set_preference('dom.timeout.throttling_delay', 0)

        # allow pasting
        profile.set_preference('devtools.selfxss.count', 100)

        profile.update_preferences()
        self.driver = webdriver.Firefox(firefox_profile=profile)
        self.logger.info('game api ready')

    def start_game(self):
        """ Loads the game and imports the most recent save
        """
        self.driver.get("http://kittensgame.com/web/")
        # game needs some time to load
        time.sleep(10)

        most_recent_save = sorted(glob.glob(self.download_path + "/*.txt"), key=sorter)[-1]
        self.logger.info(f'Loading save {most_recent_save}')
        with open(most_recent_save) as fo:
            save = fo.read()

        # open import ui
        self.driver.find_element_by_id('options-link').click()
        self.driver.find_element_by_id('importButton').click()

        # do import
        self.driver.find_element_by_id('importData').send_keys(save)
        time.sleep(1)
        self.driver.find_element_by_id('doImportButton').click()
        time.sleep(1)
        alert_obj = self.driver.switch_to.alert
        alert_obj.accept()
        time.sleep(2)
        self.logger.debug(f'Loaded save {most_recent_save}')

    def switch_to_trade_tab(self):
        """Can't build embassies without this - but disrupts user from playing
        manually - so this is meant to be invoked infrequently, to prevent
        long phases of inactivity in a tab that prevents building"""
        self.driver.execute_script('gamePage.diplomacyTab.domNode.click();')

    def switch_to_build_tab(self):
        """Can't construct buildings without this - but disrupts user from playing
        manually - so this is meant to be invoked infrequently, to prevent
        long phases of inactivity in a tab that prevents building"""
        self.driver.execute_script('gamePage.bldTab.domNode.click();')

    def build(self, building_name):
        self.driver.execute_script(js_snippets.build_x.render(x=building_name))

    def get_buildable_with_prices(self):
        # todo parse the result into python objects
        return self.driver.execute_script(js_snippets.buildable_with_prices)

    def craft_all(self, resource):
        self.driver.execute_script(f'gamePage.craftAll("{resource}")')

    def get_resource_obj(self, resource):
        # todo parse the result into python objects
        return self.driver.execute_script(f'return gamePage.resPool.get("{resource}");')

    def get_race_obj(self, race):
        return self.driver.execute_script(f'return gamePage.diplomacy.get("{race}")')

    @lru_cache
    def is_researched(self, tech):
        """ Checks if something is researched already
        ATTENTION THIS IS CACHED - don't forget to clear the cache of this occasionally

        :param tech: name of a tech - i.e. 'rocketry'
        :return: boolean indicating if tech is researched
        """
        science = self.driver.execute_script('return gamePage.science.meta[0]["meta"];')
        # science is a list of dicts, containing the key 'researched' and 'unlocked'
        # and many others

        # there is also 'label'
        filtered = [t for t in science if t['name'] == tech]
        if len(filtered) != 1:
            self.logger.warning(f'Searched for {tech}, but couldn\'t find it. Filtered is {filtered}.')
            raise NotImplementedError

        return filtered[0]['researched']

    def geodesy_researched(self):
        """
        not used at the moment - however this snippet shows how to check if a policy is researched
        geodesy researched snippet

        gamePage.workshop.meta[0].meta[55].researched
        wu = gamePage.workshop.meta[0].meta
        geodesy = [element for element in wu if element["name"] == "geodesy"][0]
        geodesy_researched = geodesy["researched"]
        """
        workshop_upgrades = self.driver.execute_script('return gamePage.workshop.meta[0].meta')
        geodesy = [element for element in workshop_upgrades if element["name"] == "geodesy"][0]
        self.logger.debug(f'geodesy research status: {geodesy["researched"]}')
        return geodesy["researched"]

    def get_building_obj(self, building):
        # todo parse into python obj
        return self.driver.execute_script(f'return gamePage.bld.get("{building}")')

    def get_price_ratio(self, building) -> float:
        return self.driver.execute_script(f'return game.bld.getPriceRatio("{building}")')

    def upgrade_embassies(self):
        self.driver.execute_script(js_snippets.upgrade_embassies)

    def trade_all(self, race):
        self.driver.execute_script(f'gamePage.diplomacy.tradeAll(game.diplomacy.get("{race}"));')

    def hunt(self):
        self.driver.execute_script("gamePage.village.huntAll();")

    def export_save(self):
        self.driver.find_element_by_id('options-link').click()
        self.driver.find_element_by_id('exportButton').click()
        self.driver.find_element_by_id('exportToFullFile').click()
        time.sleep(1)
        self.driver.find_element_by_id('closeButton').click()
        self.driver.find_element_by_id('optionsDiv').send_keys(Keys.ESCAPE)
