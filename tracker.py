import time

import tradedangerous
from tradedangerous.plugins.eddblink_plug import ImportPlugin as EDDBImportPlugin
from tradedangerous.commands.commandenv import CommandEnv
from tradedangerous import commands
from tradedangerous.commands import exceptions
from tradedangerous import tradedb
from pprint import pprint
from threading import Thread
import sys
from data_manager import DataManager


def get_station_type(station) -> str:
    if station.planetary != "N":
        return "P-" + station.maxPadSize
    elif station.fleet != "N":
        return "FC"
    else:
        return "S-" + station.maxPadSize


class TradeTracker(object):
    def __init__(self, commodity, buy_quantity=12000, sell_quantity=0, pad="L", fc="N"):
        self.commodity = commodity
        self.buy_quantity = buy_quantity
        self.sell_quantity = sell_quantity
        self.pad = pad
        self.buyers = None
        self.sellers = None
        self.fc = fc

    def load(self):
        self.update()

    @property
    def best_buy_location(self):
        return self.buyers.rows[0]

    @property
    def best_sell_location(self):
        return self.sellers.rows[0]

    @property
    def max_profit(self):
        return self.best_sell_location.price - self.best_buy_location.price

    def is_candidate(self):
        return self.max_profit > 22000  # TODO:

    def update(self):
        self.get_best_sellers()
        self.get_best_buyers()

    def get_best_buyers(self):
        def do():
            self.buyers = self.get_best("buy")
            #self.buyers.rows.sort(key=lambda row: row.price, reverse=False)
        Thread(target=do).start()

    def get_best_sellers(self):
        def do():
            self.sellers = self.get_best("sell")
            #self.sellers.rows.sort(key=lambda row: row.price, reverse=True)
        Thread(target=do).start()

    def get_best(self, mode):
        argv = ["trade.py", mode,
                "--near", "Sol",
                "--ly", "1500",
                "--pad-size", self.pad,
                "--price-sort",
                "--fc", self.fc,
                "--quantity", str(self.buy_quantity if mode == "buy" else self.sell_quantity),
                self.commodity]
        cmdenv = commands.CommandIndex().parse(argv)
        tdb = tradedb.TradeDB(tdenv=cmdenv, load=cmdenv.wantsTradeDB)
        try:
            results = cmdenv.run(tdb)
        finally:
            tdb.close()
        return results

    @property
    def is_loaded(self):
        return self.buyers is not None and self.sellers is not None

if __name__ == '__main__':
    from time import sleep







