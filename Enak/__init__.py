from discord import Client, Game, Embed
from .db import PostgreSQL
from .settings import SettingManager
from json import dumps
from time import strftime, time

conf = SettingManager().get().PostgreSQL
DB = PostgreSQL(**conf)

BotConf = dict(DB.get_configuration())


class Bot(Client):
    def __init__(self):
        super().__init__()

        self.token = SettingManager().get().Token
        self.logger = DB.writeLog

        self.getFeedbackChannel = DB.getFeedbackChannel
        self.getTemplateMessage = DB.getTemplateMessage

    async def on_ready(self, *args, **kwargs):
        print(" < Bot Ready >")
        print(self.user.name, self.user.id)
        await self.change_presence(game=Game(name=BotConf['status_message']))

    async def on_message(self, msg):
        await self.logger(msg)
        print(msg.id, msg.server, msg.channel, msg.author, msg.content, msg.attachments)

    async def on_member_join(self, member):
        server_id = member.server.id
        try:
            fb_channel_id = self.getFeedbackChannel(server_id, "welcome")
            if fb_channel_id == "": fb_channel_id = server_id
            fb_channel = self.get_channel(fb_channel_id)

            msg_temp = self.getTemplateMessage(server_id, "welcome")
            msg_temp = msg_temp.format(id=member.id, name=member.server.name)

            await self.send_message(fb_channel, msg_temp)
        except Exception as ex: print(ex)

        try:
            at_channel_id = self.getFeedbackChannel(server_id, "audit")
            at_channel = self.get_channel(at_channel_id)

            embed = Embed(title="User Joined", color=0x16e44a, description="New member has joined now!\nWelcome <@{}> !\n\n".format(member.id))
            embed.set_author(name=member.name, icon_url=member.avatar_url)
            embed.add_field(name="Global Name", value=member.name, inline=False)
            embed.add_field(name="Server Nick", value=member.nick if member.nick is not None else member.name, inline=False)
            embed.add_field(name="Discord ID", value=member.id, inline=False)
            embed.set_footer(text="으낙봇 | 이은학#9299 | Timestamp: {}({})".format(strftime("%Y/%m/%d %H:%M:%S"), time()))

            await self.send_message(at_channel, embed=embed)
        except Exception as ex: print(ex)

    async def on_member_remove(self, member):
        server_id = member.server.id
        try:
            fb_channel_id = self.getFeedbackChannel(server_id, "welcome")
            if fb_channel_id == "": fb_channel_id = server_id
            fb_channel = self.get_channel(fb_channel_id)

            msg_temp = self.getTemplateMessage(server_id, "left")
            msg_temp = msg_temp.format(gb_nick=member.name, nick=member.nick, name=member.server.name)

            await self.send_message(fb_channel, msg_temp)
        except Exception as ex: print(ex)

        try:
            at_channel_id = self.getFeedbackChannel(server_id, "audit")
            at_channel = self.get_channel(at_channel_id)

            embed = Embed(title="User Left", color=0x928f69,
                          description="A member had left now..\nPray for <@{}> !\n\n".format(member.id))
            embed.set_author(name=member.name, icon_url=member.avatar_url)
            embed.add_field(name="Global Name", value=member.name, inline=False)
            embed.add_field(name="Server Nick", value=member.nick if member.nick is not None else member.name, inline=False)
            embed.add_field(name="Discord ID", value=member.id, inline=False)
            embed.set_footer(text="으낙봇 | 이은학#9299 | Timestamp: {}({})".format(strftime("%Y/%m/%d %H:%M:%S"), time()))

            await self.send_message(at_channel, embed=embed)
        except Exception as ex: print(ex)

    async def on_message_edit(self, before, after):
        try:
            server_id = before.server.id
            at_channel_id = self.getFeedbackChannel(server_id, "audit")

            if at_channel_id == before.channel.id: return

            at_channel = self.get_channel(at_channel_id)

            embed = Embed(title="Message Editted", color=0xf57705,
                          description="do`in <@{}> | at <#{}>\n\n".format(before.author.id, before.channel.id))
            embed.set_author(name=before.author.name, icon_url=before.author.avatar_url)
            embed.add_field(name="Before", value="""Message: {}\n\nAttachments: {}\n""".format(before.content, dumps(before.attachments)), inline=False)
            embed.add_field(name="After", value="""Message: {}\n\nAttachments: {}\n""".format(after.content, dumps(after.attachments)), inline=False)
            embed.set_footer(text="으낙봇 | 이은학#9299 | Timestamp: {}({})".format(strftime("%Y/%m/%d %H:%M:%S"), time()))

            await self.send_message(at_channel, embed=embed)
        except Exception as ex: print(ex)

    async def on_message_delete(self, msg):
        try:
            server_id = msg.server.id
            at_channel_id = self.getFeedbackChannel(server_id, "audit")

            if at_channel_id == msg.channel.id: return

            at_channel = self.get_channel(at_channel_id)

            embed = Embed(title="Message Deleted", color=0xf57705,
                          description="author <@{}> | at <#{}>\n\n".format(msg.author.id, msg.channel.id))
            embed.set_author(name=msg.author.name, icon_url=msg.author.avatar_url)
            embed.add_field(name="Before", value="""Message: {}\n\nAttachments: {}\n""".format(msg.content, dumps(msg.attachments)), inline=False)
            embed.set_footer(text="으낙봇 | 이은학#9299 | Timestamp: {}({})".format(strftime("%Y/%m/%d %H:%M:%S"), time()))

            await self.send_message(at_channel, embed=embed)
        except Exception as ex: print(ex)