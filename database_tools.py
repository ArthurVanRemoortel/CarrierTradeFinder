import sqlite3
from datetime import datetime

INSERT_ITEM_RECORD_Q = """ INSERT INTO ItemHistory (item_id, station_id, buy, sell, supply, demand, last_update)  VALUES (?, ?, ?, ?, ?, ?, ?) """

# Select items that should be treated as identical.
SELECT_ITEM_RECORD_IDENTICAL_Q = """ SELECT * FROM ItemHistory WHERE item_id = ? AND station_id = ? """ #  AND buy == ? AND sell == ? AND supply == ? AND demand == ? """


class DBConnection(object):
    # def __new__(cls, path):
    #     if not hasattr(cls, 'instance'):
    #         cls.instance = super(DBConnection, cls).__new__(cls)
    #     return cls.instance

    def __init__(self, path='mydatabase.sqlite'):
        self.db_file_path = path
        self.current_transaction = None
        self.test = False
        # self.db_connection = sqlite3.connect(self.db_file)

    def begin_transaction(self):
        if not self.current_transaction:
            con = sqlite3.connect(self.db_file_path, check_same_thread=False)
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute('BEGIN TRANSACTION')
            self.current_transaction = cur
            self.test = True
        else:
            print("Transaction already exists. Ignoring")

    def end_transaction(self):
        self.current_transaction.execute('COMMIT')
        self.current_transaction.close()
        self.current_transaction = None
        self.test = False

    def execute_query(self, query, args=(), cursor=None):
        existing_cursor = self.current_transaction if self.current_transaction is not None else cursor
        if existing_cursor is not None:
            try:
                existing_cursor.execute(query, args)
                return existing_cursor
            except sqlite3.Error as e:
                print(query)
                print(args)
                raise e

        else:
            print("new cursor:", query, args)
            try:
                with sqlite3.connect(self.db_file_path, check_same_thread=False) as con:
                    con.row_factory = sqlite3.Row
                    new_cursor = con.cursor()
                    new_cursor.execute(query, args)
                    return new_cursor
            except sqlite3.Error as e:
                print(query)
                print(args)
                raise e

    def batch_execute(self, fn, rows):
        self.begin_transaction()
        for row in rows:
            fn(*row)
        self.end_transaction()

    def insert_item_record(self, item_id: int, station_id: int, buy: int, sell: int, supply: int, demand: int, last_update: datetime, cursor=None):

        # Select older items with those exact values. If they exist, no new data should be inserted.
        existing_identical = self.execute_query(SELECT_ITEM_RECORD_IDENTICAL_Q, (item_id, station_id), cursor=cursor).fetchall()
        if len(existing_identical) == 0:
            # No entries for item at station. Always insert.
            #print("NEW ITEM: ", item_id, station_id, buy, sell, supply, demand, last_update)
            self.execute_query(INSERT_ITEM_RECORD_Q, (item_id, station_id, buy, sell, supply, demand, last_update), cursor)
        else:
            # Other entries for item at station. Only insert if the most recent one is different.
            latest: sqlite3.Row = max(existing_identical, key=lambda row: row['last_update'])
            if latest['last_update'] == last_update:
                # Latest has same data so is same data.
                # print("same")
                return
            elif latest['supply'] != supply or latest['demand'] != demand or latest['buy'] != buy or latest['sell'] != sell:
                # for k in latest.keys():
                #     print("Update: ", f"{k}={latest[k]}", end=", ")
                self.execute_query(INSERT_ITEM_RECORD_Q, (item_id, station_id, buy, sell, supply, demand, last_update), cursor)


if __name__ == '__main__':
    dbc = DBConnection()
    # dbc.insert_item_record(284, 25261, 1768, 0, 2, 0, "2021-06-11 13:33:03")






