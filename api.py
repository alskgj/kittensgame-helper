from os import path

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
from selenium import webdriver
import logging
import time
import os
import glob
import re
import js_snippets
from functools import lru_cache
from selenium.webdriver.common.keys import Keys
from karla import History


def sorter(save_name):
    base_path = os.path.basename(save_name)
    run, year, day = re.findall(r'\d+', base_path)
    return int(run)*10**8 + int(year)*10**3 + int(day)


class ResourceContainer:
    def __init__(self, resource_map_obj):
        self.alloy = Resource(resource_map_obj['alloy'])
        self.beam = Resource(resource_map_obj['beam'])
        self.blueprint = Resource(resource_map_obj['blueprint'])
        self.catnip = Resource(resource_map_obj['catnip'])
        self.coal = Resource(resource_map_obj['coal'])
        self.compendium = Resource(resource_map_obj['compedium'])
        self.concrete = Resource(resource_map_obj['concrate'])
        self.culture = Resource(resource_map_obj['culture'])
        self.eludium = Resource(resource_map_obj['eludium'])
        self.furs = Resource(resource_map_obj['furs'])
        self.gear = Resource(resource_map_obj['gear'])
        self.gold = Resource(resource_map_obj['gold'])
        self.iron = Resource(resource_map_obj['iron'])
        self.kerosene = Resource(resource_map_obj['kerosene'])
        self.catpower = Resource(resource_map_obj['manpower'])
        self.manuscript = Resource(resource_map_obj['manuscript'])
        self.megalith = Resource(resource_map_obj['megalith'])
        self.minerals = Resource(resource_map_obj['minerals'])
        self.oil = Resource(resource_map_obj['oil'])
        self.parchment = Resource(resource_map_obj['parchment'])
        self.plate = Resource(resource_map_obj['plate'])
        self.scaffold = Resource(resource_map_obj['scaffold'])
        self.science = Resource(resource_map_obj['science'])
        self.ship = Resource(resource_map_obj['ship'])
        self.slab = Resource(resource_map_obj['slab'])
        self.starchart = Resource(resource_map_obj['starchart'])
        self.steel = Resource(resource_map_obj['steel'])
        self.tanker = Resource(resource_map_obj['tanker'])
        self.time_crystal = Resource(resource_map_obj['timeCrystal'])
        self.titanium = Resource(resource_map_obj['titanium'])
        self.unicorns = Resource(resource_map_obj['unicorns'])
        self.unobtainium = Resource(resource_map_obj['unobtainium'])
        self.uranium = Resource(resource_map_obj['uranium'])
        self.wood = Resource(resource_map_obj['wood'])
        self.thorium = Resource(resource_map_obj['thorium'])


class Resource:
    def __init__(self, resource_obj):
        self.name = resource_obj['name']
        if 'craftable' in resource_obj:
            self.craftable = resource_obj['craftable']
        else:
            self.craftable = False

        # 0 means not maxValue
        self.max_value = resource_obj['maxValue']
        if self.max_value == 0:
            self.max_value = 999_999_999_999_999

        self.perTick = resource_obj['perTickCached']
        self.unlocked = resource_obj['unlocked']
        self.value = resource_obj['value']

        if self.value >= self.max_value * 0.8:
            self.almost_full = True
        else:
            self.almost_full = False

    def __lt__(self, other):
        return self.value < other.value

    def __gt__(self, other):
        return self.value > other.value

    def __le__(self, other):
        return self.value <= other.value

    def __ge__(self, other):
        return self.value >= other.value


class Game:
    def __init__(self):
        self.history = History()

        self.logger = logging.getLogger(__name__)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(console_handler)

        file_handler = logging.FileHandler(
            filename='super_kitten.log',
            mode='w'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

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

        self._start_game()
        self._setup_additional_buttons()

        self._res_container = self.update_resources()

    def _start_game(self):
        """ Loads the game and imports the most recent save
        """
        self.driver.get("http://kittensgame.com/web/")

        # wait until page is loaded
        WebDriverWait(driver=self.driver, timeout=100).until(
            expected_conditions.element_to_be_clickable((By.ID, 'logLink'))
        )

        most_recent_save = sorted(glob.glob(self.download_path + "/*.txt"), key=sorter)[-1]
        self.logger.info(f'Loading save {most_recent_save}')
        with open(most_recent_save) as fo:
            save = fo.read()

        # open import ui
        self.driver.find_element_by_id('options-link').click()
        self.driver.find_element_by_id('importButton').click()

        # do import
        self.driver.find_element_by_id('importData').send_keys(save)
        self.driver.find_element_by_id('doImportButton').click()
        alert_obj = self.driver.switch_to.alert

        alert_obj.accept()
        self.logger.debug(f'Loaded save {most_recent_save}')

    @property
    def resources(self):
        return self._res_container

    def get_jobs(self):
        return self.driver.execute_script('return game.village.jobs;')

    @property
    def available_kittens(self):
        return self.driver.execute_script('return game.village.getFreeKittens();')

    def assign_jobs(self, name: str, amount: int):
        self.driver.execute_script(f"game.village.assignJob(game.village.getJob('{name}'), {amount})")

    def update_resources(self):
        """Refreshes the view of the Game.resources property"""
        res_obj = self.driver.execute_script('return gamePage.resPool.resourceMap;')
        self._res_container = ResourceContainer(res_obj)
        return self._res_container

    def get_energy_surplus(self):
        return self.driver.execute_script('return game.resPool.energyWinterProd - game.resPool.energyCons')

    def _setup_additional_buttons(self):
        self.driver.execute_script(js_snippets.function_button_pause_all)
        self.driver.execute_script(js_snippets.add_pause_all_button)

    def is_paused(self):
        return self.driver.execute_script('return script_paused;')

    def update_build_tab(self):
        self.driver.execute_script('gamePage.bldTab.render();')
        self.driver.execute_script('gamePage.bldTab.update();')

    def update_space_tab(self):
        self.driver.execute_script('gamePage.spaceTab.render();')
        self.driver.execute_script('gamePage.spaceTab.update();')

    def update_diplomacy_tab(self):
        self.driver.execute_script('gamePage.diplomacyTab.render();')
        self.driver.execute_script('gamePage.diplomacyTab.update();')

    def update_religion_tab(self):
        self.driver.execute_script('gamePage.religionTab.render();')

    def update_workshop_tab(self):
        self.driver.execute_script('gamePage.workshopTab.render();')
        self.driver.execute_script('gamePage.workshopTab.update();')

    def upgrade_solar_revolution(self):
        self.driver.execute_script('gamePage.religionTab.rUpgradeButtons[5].buttonContent.click();')

    def buy_first_workshop_upgrade(self):
        self.update_workshop_tab()
        upgrade = self.driver.execute_script(js_snippets.buy_first_workshop_upgrade)
        if upgrade:
            self.history.upgrade(upgrade)
        return upgrade

    def update_science_tab(self):
        self.driver.execute_script('gamePage.libraryTab.render();')
        self.driver.execute_script('gamePage.libraryTab.update();')

    def research_something(self):
        self.update_science_tab()
        tech = self.driver.execute_script(js_snippets.research_first)
        if tech:
            self.history.research(tech)
        return tech

    def build(self, building_name):
        self.driver.execute_script(js_snippets.build_x.render(x=building_name))
        self.history.build(building_name)

    def build_space(self, building_name):
        self.driver.execute_script(js_snippets.build_x_space.render(x=building_name))
        self.history.build(building_name)

    def get_buildable_with_prices(self):
        # todo parse the result into python objects
        return self.driver.execute_script(js_snippets.buildable_with_prices_and_effects)

    def get_space_buildable_with_prices(self):
        return self.driver.execute_script(js_snippets.space_buildable_with_prices_and_effects)

    def craft_all(self, resource):
        self.driver.execute_script(f'gamePage.craftAll("{resource}")')
        self.history.craft(resource)

    def praise_the_sun(self):
        self.driver.execute_script('gamePage.religion.praise();')
        self.history.praise += 1

    def get_resource_obj(self, resource):
        # todo parse the result into python objects
        return self.driver.execute_script(f'return gamePage.resPool.get("{resource}");')

    def get_race_obj(self, race):
        return self.driver.execute_script(f'return gamePage.diplomacy.get("{race}")')

    def send_explorers(self):
        return self.driver.execute_script(js_snippets.explore)

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
            self.logger.warning(f'Searched for [{tech}], but couldn\'t find it. Filtered is {filtered}.')
            self.logger.warning(f'unfiltered: {[t["name"] for t in science]}')
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
        self.update_diplomacy_tab()
        self.driver.execute_script(js_snippets.upgrade_embassies)

    def trade_all(self, race):
        if self.is_paused():
            self.logger.info("Not trading - script is paused.")
        else:
            self.driver.execute_script(f'gamePage.diplomacy.tradeAll(game.diplomacy.get("{race}"));')

    def on_pacifism_challenge(self):
        return self.driver.execute_script('return game.challenges.getChallenge("pacifism").active')

    def hunt(self):
        # dont cheat
        if not self.on_pacifism_challenge():
            self.driver.execute_script("gamePage.village.huntAll();")
            self.history.hunts += 1

    def report(self):
        self.history.do_report()
        self.history.clean()

    def export_save(self):
        self.driver.find_element_by_id('options-link').click()
        self.driver.find_element_by_id('exportButton').click()
        self.driver.find_element_by_id('exportToFullFile').click()
        time.sleep(1)
        self.driver.find_element_by_id('closeButton').click()
        self.driver.find_element_by_id('optionsDiv').send_keys(Keys.ESCAPE)

    def render_tabs(self):
        pass
        # def switch_to_trade_tab(self):
        #     """Can't build embassies without this - but disrupts user from playing
        #     manually - so this is meant to be invoked infrequently, to prevent
        #     long phases of inactivity in a tab that prevents building"""
        # self.driver.execute_script('gamePage.diplomacyTab.domNode.click();')

