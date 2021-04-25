from os import path
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.job import Job
from datetime import datetime
from random import randint
import time
import api

import logging
import random
import configparser
import typing
config = configparser.ConfigParser()
config.read('config.ini')

download_path = path.normpath(path.join(path.dirname(__file__), 'downloads'))
constructed_buildings = []


def setup_logging():
    logging.basicConfig(
        filename='super_kitten.log',
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(message)s',
        filemode='w'
    )

    # found third party loggers with
    # loggers = [logging.getLogger(e) for e in logging.root.manager.loggerDict]
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('apscheduler').setLevel(logging.WARNING)
    logging.getLogger('concurrent').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(
        filename='super_kitten.log',
        mode='w'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

"""
def do_report():
    counts = {}
    global constructed_buildings
    for building in constructed_buildings:
        if building not in counts:
            counts[building] = 1
        else:
            counts[building] += 1

    print(f'{datetime.now().strftime("%H:%M:%S")} Constructed the following buildings since last time saving: ')
    for building, count in counts.items():
        print(f'{count:2}x {building}')

    constructed_buildings = []
"""


def export_save():
    logger.info('saving...')
    game.export_save()
    game.report()


def auto_hunt():
    catpower = game.get_resource_obj('manpower')

    # prioritize trading over hunting
    gold_obj = game.get_resource_obj('gold')
    if gold_obj['value'] >= gold_obj['maxValue'] * 0.8:
        auto_trade()

    if catpower["value"] >= catpower["maxValue"] * 0.8:
        game.craft_all('parchment')
        logger.debug(f"Hunting, cat power is: ({round(catpower['value'])}/{round(catpower['maxValue'])})")
        game.hunt()


def auto_craft():
    game.update_resources()

    # beam and slabs if they are full
    if game.resources.wood.almost_full:
        game.craft_all('beam')
    if game.resources.minerals.almost_full:
        game.craft_all('slab')

    # plates and steel, try to keep them balanced
    if game.resources.iron.almost_full and game.resources.plate < game.resources.steel:
        game.craft_all('plate')
    if game.resources.coal.almost_full and game.resources.steel < game.resources.plate:
        game.craft_all('steel')

    # furs -> parchment -> manuscript -> compendium -> blueprint
    # furs -> parchment is handled by the hunt function
    # parchment -> manuscript is done iff we have enough culture and
    # iff it doesn't block chapel construction
    chapel = game.get_building_obj('chapel')
    parchment_chapel_price = chapel['prices'][2]['val'] * game.get_price_ratio('chapel') ** chapel['on']

    if game.resources.culture.almost_full and (
            not chapel['unlocked'] or
            (parchment_chapel_price > 5000 and not game.is_researched('thorium')) or
            game.resources.parchment.value >= parchment_chapel_price * 2
    ):
            game.craft_all('manuscript')

    # manuscript -> compendium -> blueprint
    if game.resources.science.almost_full:

        if game.is_researched('biochemistry'):
            if game.resources.compendium < game.resources.blueprint:
                game.craft_all('compedium')
            else:
                game.craft_all('blueprint')

        elif game.is_researched('navigation'):
            game.craft_all('compedium')

    # scaffold
    if game.is_researched('navigation') and game.resources.beam > game.resources.scaffold:
        game.craft_all('scaffold')

    # late game crafting - uses crafted materials as ingredients
    if game.is_researched('particlePhysics'):

        # gear and alloy
        if game.resources.steel > game.resources.gear and game.resources.gear <= game.resources.alloy:
            game.craft_all('gear')
        elif game.resources.steel > game.resources.alloy and game.resources.alloy < game.resources.gear:
            if game.resources.titanium > game.resources.alloy:
                game.craft_all('alloy')

        # concrete
        if game.resources.slab.value > game.resources.concrete.value * 1000 and \
                game.resources.steel > game.resources.concrete:
            game.craft_all('concrate')

        # eludium
        if game.resources.unobtainium.almost_full:
            game.craft_all('eludium')

        # kerosene?
        # thorium?
        if (
                game.resources.megalith < game.resources.beam and
                game.resources.megalith < game.resources.slab and
                game.resources.megalith < game.resources.plate
        ):
            game.craft_all('megalith')


def auto_embassies():
    # this is fairly disruptive since it switches tab
    # auto level embassies - only if there are some temples, to ensure there is at least some culture production
    if game.get_building_obj('temple')['on'] >= 10:
        # game.switch_to_trade_tab()
        game.update_diplomacy_tab()
        time.sleep(1)
        game.upgrade_embassies()

    # this is useful, since we want to be on the build tab often, if we are on another tab,
    # prices don't get updated and nothing gets built
    game.update_build_tab()
    #game.switch_to_build_tab()


def auto_upgrade():
    if config['auto']['upgrade'] == 'True':
        upgraded = game.buy_first_workshop_upgrade()
        if upgraded:
            logger.info(f"bought upgrade: {upgraded}")


def auto_research():
    if config['auto']['research'] == 'True':
        researched = game.research_something()
        if researched:
            logger.info(f"researched: {researched}")


def auto_trade():
    # todo send explorers to find griffins
    # todo add trading to report
    gold_obj = game.get_resource_obj('gold')
    iron_obj = game.get_resource_obj('iron')
    titanium_obj = game.get_resource_obj('titanium')

    zebras_unlocked = game.get_race_obj('zebras')['unlocked']
    griffins_unlocked = game.get_race_obj('griffins')['unlocked']

    # enough gold to trade
    if gold_obj['value'] >= gold_obj['maxValue'] * 0.8:

        # make space for iron
        if iron_obj['value'] >= iron_obj['maxValue'] * 0.5 and (zebras_unlocked or griffins_unlocked):
            game.craft_all('plate')

        if titanium_obj['value'] <= titanium_obj['maxValue'] * 0.5 and zebras_unlocked:
            logger.debug('trading with zebras')
            slabs = game.get_resource_obj('slab')['value']
            if slabs < 100:
                game.craft_all('slab')
            game.trade_all('zebras')

        elif griffins_unlocked:
            game.trade_all('griffins')
            logger.debug('trading with griffins')


def auto_praise():
    faith_obj = game.get_resource_obj('faith')
    if faith_obj['value'] >= faith_obj['maxValue'] * 0.9:
        logger.debug('Praising the sun!')
        game.praise_the_sun()


def constraint_satisfied(constraint):
    if constraint == 'always':
        return True
    elif constraint == 'never':
        return False
    else:
        return game.is_researched(constraint)


def config_build(log=False):
    config.read('config.ini')  # refresh view, to reflect user changes
    build_any_of_those = []

    buildings_with_unsatisfied_constraints = set()
    constraints_not_satisfied = set()

    buildable_with_prices = game.get_buildable_with_prices()
    for building in buildable_with_prices:
        game.update_build_tab()
        name = building["name"]            # ie 'mansion'
        resources = building["resources"]  # ie ['titanium', 'slab', 'steel']

        all_constraints_satisfied = True

        for res in resources:
            try:
                constraint = config['Auto Build Prerequisites'][res]
            except KeyError:
                print(f"Resource {res} not in Auto Build Prerequisites...")
                logger.critical(f"Resource {res} not in Auto Build Prerequisites...")
                raise NotImplementedError
            if not constraint_satisfied(constraint):
                buildings_with_unsatisfied_constraints.add(name)
                constraints_not_satisfied.add(f'{res}:{constraint}')
                all_constraints_satisfied = False

        if all_constraints_satisfied:
            build_any_of_those.append(name)

    if log:
        logger.debug(f'Buildings with unsatisfied constraints: {buildings_with_unsatisfied_constraints}')
        logger.debug(f'Unsatisfied constraints: {constraints_not_satisfied}')
    return build_any_of_those


def constraint_build():
    buildable = config_build(log=True)
    built = []
    while buildable:

        building = random.choice(buildable)
        game.build(building)

        # log stuff
        constructed_buildings.append(building)
        built.append(building)

        # check if we can build more stuff
        buildable = config_build()

    if built:
        logger.info(f"built {built}")
    if not built:
        logger.debug(f"Built nothing!")

    # reset cache
    game.is_researched.cache_clear()


def watchdog(jobs: typing.List[Job]):
    pause_everything = game.is_paused()
    jobs_are_paused = jobs[0].next_run_time is None

    if jobs_are_paused and not pause_everything:
        logger.info("Resuming all jobs!")
        for job in jobs:
            job.resume()

    elif not jobs_are_paused and pause_everything:
        logger.info("Pausing all jobs!")
        for job in jobs:
            job.pause()


logger = setup_logging()
if __name__ == '__main__':
    game = api.Game()

    print(f'{datetime.now().strftime("%H:%M:%S")} setting up scheduler...')
    scheduler = BlockingScheduler()

    jobs = [scheduler.add_job(auto_hunt, 'interval', seconds=30),
            scheduler.add_job(constraint_build, 'interval', minutes=2),
            scheduler.add_job(auto_craft, 'interval', seconds=30),
            scheduler.add_job(auto_trade, 'interval', minutes=2),
            scheduler.add_job(auto_embassies, 'interval', minutes=2, seconds=5),
            scheduler.add_job(auto_praise, 'interval', minutes=1),
            scheduler.add_job(auto_upgrade, 'interval', minutes=2, seconds=3),
            scheduler.add_job(auto_research, 'interval', minutes=2, seconds=2)]

    time.sleep(3)
    save_job = scheduler.add_job(export_save, 'interval', minutes=20)

    watchdog_job = scheduler.add_job(watchdog, 'interval', args=(jobs,), seconds=10)

    scheduler.start()
    input()

