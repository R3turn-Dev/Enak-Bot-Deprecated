from psycopg2 import connect
from threading import get_ident
from json import dumps


class PostgreSQL:
    def __init__(self, initial_connect=True, **kwargs):
        self.__dict__ = kwargs

        self.conn = None
        self.cursor = None

        self.connDict = {}
        self.curDict = {}

        if initial_connect:
            self.getConn()
            self.getCursor()

    def getConn(self):
        self.conn = connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.pw,
            database=self.db
        )

        self.conn.autocommit = True
        return self.conn

    def getCursor(self):
        thread_id = get_ident().__int__()

        if thread_id not in self.connDict.keys():
            self.connDict[thread_id] = self.getConn()

        if thread_id not in self.curDict.keys():
            self.curDict[thread_id] = self.connDict[thread_id].cursor()

        return self.curDict[thread_id]

    def execute(self, query):
        return self.getConn().execute(query)

    def get_configuration(self):
        cur = self.getCursor()

        cur.execute("SELECT * FROM configurations;")
        return cur.fetchall()

    def checkTable(self, table_name):
        conn = self.getConn()
        cur = conn.cursor()

        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name = '{}';".format(table_name))
        data = cur.fetchall()
        return bool(data)

    async def writeLog(self, msg):
        server_id = "0" if msg.server is None else msg.server.id
        channel_id = msg.channel.id
        author_id = msg.author.id
        attachments = dumps(msg.attachments)

        cur = self.getCursor()

        cur.execute("INSERT INTO messages VALUES ('{}', '{}', '{}', '{}', '{}', '{}');".format(
            msg.id, server_id, channel_id, author_id, msg.content, attachments
        ))

    def getFeedbackChannel(self, server, type):
        cur = self.getCursor()

        cur.execute("SELECT channel FROM feedbacks WHERE server='{}' and type='{}';".format(
            server, type
        ))

        data = cur.fetchall()
        return data[0][0] if len(data) else ""

    def getTemplateMessage(self, server, type):
        cur = self.getCursor()

        cur.execute("SELECT content FROM templates WHERE server='{}' and type='{}';".format(
            server, type
        ))

        data = cur.fetchall()
        if len(data): return data[0][0]
        else:
            cur.execute("SELECT content FROM templates WHERE server='0' and type='{}';".format(type))

            data = cur.fetchall()

            if len(data): return data[0][0]
            else: return "설정된 메세지가 없습니다. 한 번 설정해보세요!"
