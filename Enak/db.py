from psycopg2 import connect
from threading import get_ident
from json import dumps
from re import escape


class PostgreSQL:
    def __init__(self, initial_connect=True, **kwargs):
        self.__dict__ = kwargs

        self.conn = None
        self.cursor = None

        self.connDict = {}
        self.curDict = {}

        self.escaper = escape

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
        content = self.escaper(msg.content)
        attachments = self.escaper(dumps(msg.attachments))
        embeds = self.escaper(dumps(msg.embeds))

        cur = self.getCursor()

        cur.execute("INSERT INTO messages (msg_id, server, channel, author, content, attachments, embeds) VALUES ('{}', '{}', '{}', '{}', E'{}', E'{}', E'{}');".format(
            msg.id, server_id, channel_id, author_id, content, attachments, embeds
        ))

    def getChannelInfo(self, channel):
        cur = self.getCursor()

        cur.execute("SELECT type, no_looking FROM channels WHERE channel='{}' and enabled=TRUE ;".format(channel))

        data = cur.fetchall()
        return data

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

    def getCommands(self, server):
        cur = self.getCursor()

        cur.execute("SELECT name, feedback, timeout FROM commands WHERE server='{}' or server = '0';".format(
            server
        ))

        data = cur.fetchall()
        return dict([(k, {'feedback': f, 'timeout': t}) for k, f, t in data])

    def getAdminInfo(self, server="", user_id="", overlap=False, rank=False):
        cur = self.getCursor()

        cur.execute("SELECT {}{} FROM administrators WHERE (server='{}' or server='0') {};".format(
            "type" if user_id else "user_id, type", ", rank" if rank else "", server, """and user_id='{}'""".format(user_id) if user_id else ""
        ))

        data = cur.fetchall()
        return data

    def getFooter(self):
        cur = self.getCursor()

        cur.execute("SELECT content FROM templates WHERE type='footer' LIMIT 1;")

        data = cur.fetchall()
        return data[0][0] if data else ""

    def getUserAudit(self, server="", user=""):
        cur = self.getCursor()

        cur.execute("SELECT * FROM user_audit WHERE type='footer';")

        data = cur.fetchall()
        return data
