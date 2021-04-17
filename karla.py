"""
    Karla Kolumna handles all the reporting.

"""

from datetime import datetime


class History:
    """This just handles the reports"""
    def __init__(self):
        self.constructed_buildings = {}  # building -> count
        self.researched_technologies = []
        self.researched_upgrades = []
        self.crafts = {}  # resource -> count
        self.hunts = 0
        self.praise = 0
        self.start = datetime.now()

    def build(self, building):
        if building in self.constructed_buildings:
            self.constructed_buildings[building] += 1
        else:
            self.constructed_buildings[building] = 1

    def research(self, tech):
        self.researched_technologies.append(tech)

    def upgrade(self, upgrade):
        self.researched_upgrades.append(upgrade)

    def craft(self, name):
        if name in self.crafts:
            self.crafts[name] += 1
        else:
            self.crafts[name] = 1

    def clean(self):
        self.__init__()

    def do_report(self):

        # title
        duration = datetime.now() - self.start
        minutes = duration.seconds // 60
        seconds = duration.seconds - 60*minutes
        title = f'In the last {minutes} minutes and {seconds} seconds'
        print(title)
        print("="*len(title))

        # buildings
        if self.constructed_buildings:
            print('Constructed: ')
            for building, count in self.constructed_buildings.items():
                print(f'{count:2}x {building}')

        # research
        if self.researched_technologies:
            print(f'Researched: {", ".join(self.researched_technologies)}')

        # upgrades
        if self.researched_upgrades:
            print(f'Bought upgrades: {", ".join(self.researched_upgrades)}')

        # crafts
        if self.crafts:
            print('Crafted: ')
            for craft, count in self.crafts.items():
                print(f'{count:2}x {craft}')

        # hunts & praises
        if self.hunts:
            print(f'Hunted {self.hunts} times.')
        if self.praise:
            print(f'Praised the sun {self.praise} times.')

    # todo add trading and upgrading embassies?


if __name__ == '__main__':
    hist = History()

    # add some buildings
    blds = ['logHouse', 'mine', 'library', 'smelter', 'smelter', 'smelter', 'aqueduct', 'aqueduct', 'aqueduct', 'aqueduct', 'aqueduct', 'aqueduct']
    for bld in blds:
        hist.build(bld)

    # research some stuff
    techs = ["currency", "rocketry"]
    for t in techs:
        hist.research(t)

    # upgrade some stuff
    hist.upgrade("geodesy")
    hist.upgrade("LHC")

    # todo not crafting atm

    # hunt
    hist.hunts += 12

    hist.do_report()
