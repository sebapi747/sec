''' ---------------------------------------------------------------------------------------------
 Initialize table schema for perf.db
'''
import os
import sqlite3

DATABASE= "sec.db"

''' ---------------------------------------------------------------------------------------------
 SQLite utils
'''
class DBObj(object):
    def __init__(self):
        self.db = sqlite3.connect(DATABASE)

g = DBObj()

def init_sql_schema():
    print("init sql tables")
    f = open("sql/schema.sql", mode='r') 
    g.db.cursor().executescript(f.read())
    f.close()
    g.db.commit()


''' ---------------------------------------------------------------------------------------------
 main
 '''
if __name__ == '__main__':
    init_sql_schema()
