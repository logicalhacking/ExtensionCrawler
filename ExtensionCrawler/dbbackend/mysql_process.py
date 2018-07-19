#
# Copyright (C) 2017 The University of Sheffield, UK
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from multiprocessing import Process, Manager

from ExtensionCrawler.dbbackend.mysql_backend import MysqlBackend
from ExtensionCrawler.util import setup_logger, log_exception

class MysqlProxy:
    def __init__(self, q):
        self.q = q

    def insertmany(self, table, arglist):
        self.q.put((MysqlProcessBackend.INSERT, (table, arglist)))

    def insert(self, table, **kwargs):
        self.insertmany(table, [kwargs])

    def get_cdnjs_info(self, md5):
        return None


def run(mysql_kwargs, q):
    setup_logger(True)
    finished = False

    try:
        with MysqlBackend(None, **mysql_kwargs) as db:
            while True:
                cmd, data = q.get()
                if cmd == MysqlProcessBackend.STOP:
                    finished = True
                    break
                if cmd == MysqlProcessBackend.INSERT:
                    db.insertmany(*data)
    except:
        log_exception("Stopping Mysql backend and emptying queue...")
        if not finished:
            while True:
                cmd, data = q.get()
                if cmd == MysqlProcessBackend.STOP:
                    break
                if cmd == MysqlProcessBackend.INSERT:
                    pass


class MysqlProcessBackend:
    STOP = "stop"
    INSERT = "insert"

    def __init__(self, ext_id, **mysql_kwargs):
        self.mysql_kwargs = mysql_kwargs
        self.m = Manager()
        self.queue = self.m.Queue(1000)

    def __enter__(self):
        self.p = Process(target=run, args=(self.mysql_kwargs, self.queue))
        self.p.start()
        return MysqlProxy(self.queue)

    def __exit__(self, *args):
        self.queue.put((MysqlProcessBackend.STOP, None))
        self.p.join()
