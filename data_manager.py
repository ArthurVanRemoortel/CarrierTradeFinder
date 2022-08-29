from pprint import pprint
from datetime import datetime

import tradedangerous.tradedb
from database_tools import DBConnection
from tradedangerous import tradedb, tradeenv, commands, tradeexcept, tradecalc, prices
from tradedangerous.commands import exceptions
from tradedangerous.commands import buy_cmd, sell_cmd, local_cmd, trade_cmd, market_cmd
import time


class DataManager:
    _instance = None
    database_connection: DBConnection = DBConnection()
    tdb = tradedb.TradeDB()

    def __new__(cls):
        if cls._instance is None:
            print("Creating DataManager instance...")
            cls._instance = super(DataManager, cls).__new__(cls)
            # Setup here
        return cls._instance

    def get_item_history_min_max(self):
        ...

    def get_item_history(self, station_id):
        ...

    def insert_item_record(self, item_id: int, station_id: int, buy: int, sell: int, supply: int, demand: int, last_update: datetime):
        self.database_connection.insert_item_record(item_id=item_id, station_id=station_id, buy=buy, sell=sell, supply=supply, demand=demand, last_update=last_update)

    def batch_insert_item_records(self, rows):
        self.database_connection.batch_execute(fn=self.insert_item_record, rows=rows)

    def update_database(self):
        trade_data = self.check_db()
        if trade_data is not None:
            print("Updating price data...")
            argv = ["trade.py", "import", "--merge", "-P", "eddblink", "-O", "skipvend"]
        else:
            # Update all.
            print("Updating all data. ")
            argv = ["trade.py", "import", "-P", "eddblink"]
        cmdenv = commands.CommandIndex().parse(argv)
        tdb = tradedb.TradeDB(cmdenv, load=cmdenv.wantsTradeDB)
        try:
            results = cmdenv.run(tdb)
        finally:
            # always close tdb
            tdb.close()
        if results:
            results.render()

    def check_db(self):
        tdb = tradedb.TradeDB()
        tsc = tdb.tradingStationCount
        cmdenv = commands.commandenv
        if tsc == 0:
            raise exceptions.NoDataError(
                "There is no trading data for ANY station in "
                "the local database. Please enter or import "
                "price data."
            )
        elif tsc == 1:
            raise exceptions.NoDataError(
                "The local database only contains trading data "
                "for one station. Please enter or import data "
                "for additional stations."
            )
        elif tsc < 8:
            cmdenv.NOTE(
                "The local database only contains trading data "
                "for {} stations. Please enter or import data "
                "for additional stations.".format(
                    tsc
                )
            )
        else:
            print(tsc, "trading data found.")
        tdb.close()
        return tsc if tsc > 0 else None

    def load_trade_dangerous_items_prices(self):
        tdb = self.tdb
        history_rows = []

        cur = tdb.query("""
                SELECT  station_id, item_id,
                        demand_price, demand_units, demand_level,
                        supply_price, supply_units, supply_level,
                        modified
                FROM  StationItem """)

        for row in cur:
            history_rows.append((row[1], row[0], row[2], row[5], row[4], row[6], row[8]))

        self.batch_insert_item_records(rows=history_rows)

    def find_trade_candidates(self, tdb=None):
        use_tdb = tdb if tdb is not None else self.tdb
        result_demand = use_tdb.query(
            """ SELECT item_id, max(demand_price) FROM StationItem GROUP BY item_id""", ()).fetchall()
        result_supply = use_tdb.query(
            """ SELECT item_id, min(supply_price) FROM StationItem WHERE supply_price > 0 AND supply_units > 10000 GROUP BY item_id""",
            ()).fetchall()

        candidates = []
        for item in use_tdb.items():
            item_id = item.ID
            best_supply = list(filter(lambda row: row[0] == item_id, result_supply))
            best_demand = list(filter(lambda row: row[0] == item_id, result_demand))

            if len(best_supply) > 1 or len(best_demand) > 1:
                raise Exception(best_demand, best_supply)

            if len(best_supply) == 0 or len(best_demand) == 0:
                continue

            best_demand = best_demand[0]
            best_supply = best_supply[0]
            max_profit = best_demand[1] - best_supply[1]
            if max_profit > 22000:
                candidates.append((item, max_profit))
        candidates.sort(key=lambda p: p[1], reverse=True)
        return candidates


if __name__ == '__main__':
    DataManager()
    # DataManager().database_connection.execute_query(""" DELETE FROM ItemHistory WHERE 1 """)
    DataManager().update_database()
    start_time = time.time()
    DataManager().load_trade_dangerous_items_prices()

    #for can in DataManager().find_trade_candidates():
    #    print(can[0].dbname, can[1])

    print(time.time() - start_time)
