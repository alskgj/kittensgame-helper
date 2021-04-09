from os import path
from apscheduler.schedulers.blocking import BlockingScheduler

from datetime import datetime
from random import randint
import time
import api

import logging
import random
import configparser
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


def export_save():
    logger.info('saving...')
    game.export_save()
    do_report()


def auto_hunt():
    catpower = game.get_resource_obj('manpower')

    # prioritize trading over hunting
    gold_obj = game.get_resource_obj('gold')
    if gold_obj['value'] >= gold_obj['maxValue'] * 0.8:
        auto_trade()

    if catpower["value"] >= catpower["maxValue"] * 0.8:
        game.craft_all('parchment')
        logger.info(f"Hunting, cat power is: ({round(catpower['value'])}/{round(catpower['maxValue'])})")
        game.hunt()


def auto_craft():
    # todo only craft steel in the early game if we have more plates, so that we can build
    # some ships
    # if this isn't implemented it might be hard to buy the first few calciners, because early titanite is hard to find

    crafts = {
        'wood': 'beam',
        'minerals': 'slab',
        'coal': 'steel',
        'iron': 'plate',
        'culture': 'manuscript',
    }

    if game.is_researched('navigation'):
        crafts['science'] = 'compedium'
    if game.is_researched('genetics'):
        if randint(0, 1) == 0:
            crafts['science'] = 'compedium'
        else:
            crafts['science'] = 'blueprint'

    # remove parchment -> compendium if we don't have a lot of parchment
    # this is to ensure chapel can be built
    chapel = game.get_building_obj('chapel')
    parchment_chapel_price = chapel['prices'][2]['val'] * game.get_price_ratio('chapel') ** chapel['on']
    parchment_held = game.get_resource_obj('parchment')['value']
    if parchment_held < parchment_chapel_price*2 and chapel['unlocked']:
        del crafts['culture']
        logger.debug(f'removed culture since {parchment_chapel_price}*2 is higher than {parchment_held}')

    crafted = []
    for resource in crafts:
        res_obj = game.get_resource_obj(resource)
        if res_obj['value'] >= res_obj['maxValue'] * 0.9:
            game.craft_all(crafts[resource])
            crafted.append(crafts[resource])

    if crafted:
        logger.info(f'Crafting {crafted}!')


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
            logger.info('trading with zebras')
            slabs = game.get_resource_obj('slab')['value']
            if slabs < 100:
                game.craft_all('slab')
            game.trade_all('zebras')

        elif griffins_unlocked:
            game.trade_all('griffins')
            logger.info('trading with griffins')


def constraint_satisfied(constraint):
    if constraint == 'always':
        return True
    elif constraint == 'never':
        return False
    else:
        return game.is_researched(constraint)


def config_build():
    config.read('config.ini')  # refresh view, to reflect user changes
    build_any_of_those = []

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
                logger.debug(f"{name} does not satisfy constraint {constraint} from res {res}")
                all_constraints_satisfied = False

        if all_constraints_satisfied:
            build_any_of_those.append(name)

    return build_any_of_those


def constraint_build():
    buildable = config_build()
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


logger = setup_logging()
if __name__ == '__main__':
    game = api.Game()
    game.start_game()

    print(f'{datetime.now().strftime("%H:%M:%S")} setting up scheduler...')
    scheduler = BlockingScheduler()

    scheduler.add_job(auto_hunt, 'interval', seconds=30)
    scheduler.add_job(constraint_build, 'interval', seconds=31)
    time.sleep(1)
    scheduler.add_job(auto_craft, 'interval', minutes=2)
    scheduler.add_job(auto_trade, 'interval', minutes=1, seconds=1)

    # fairly disruptive, since this switches tab
    scheduler.add_job(auto_embassies, 'interval', minutes=10, seconds=5)
    time.sleep(3)
    scheduler.add_job(export_save, 'interval', minutes=20)

    scheduler.start()
    input()

