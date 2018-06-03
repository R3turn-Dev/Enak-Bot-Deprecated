from discord import Client, Game, Embed
from discord.ext import commands
from .db import PostgreSQL
from .settings import SettingManager
from json import dumps
from time import strftime, time
from asyncio import sleep

conf = SettingManager().get().PostgreSQL
DB = PostgreSQL(**conf)

BotConf = dict(DB.get_configuration())


class Bot(commands.Bot):
    def __init__(self):
        # Initialize Parent class
        super().__init__(command_prefix="?")

        # Get token from setting
        self.token = SettingManager().get().Token
        self.logger = DB.writeLog

        self.react_emoji = "👌"

        # Handler for DB Functions
        self.getCommands = DB.getCommands
        self.getChannelInfo = DB.getChannelInfo
        self.getFeedbackChannel = DB.getFeedbackChannel
        self.getTemplateMessage = DB.getTemplateMessage
        self.getAdmins = DB.getAdminInfo
        self.getFooter = DB.getFooter

        self.add_command(self.test)

    @commands.command(name='test')
    async def test(self, ctx):
        await ctx.send("HI")

    def getRank(self, server, user_id):
        _info = self.getAdmins(server=server, user_id=user_id, rank=True)
        _ranks = [x[1] for x in _info]
        if not _ranks: _ranks.append(1e5)

        return min(_ranks)

    async def on_ready(self, *args, **kwargs):
        print(" < Bot Ready >")
        print(self.user.name, self.user.id)
        await self.change_presence(game=Game(name=BotConf['status_message']))

    async def on_message(self, msg):
        # Check channel info
        _CHANNEL_INFO = self.getChannelInfo(msg.channel.id)
        _CHANNEL_TYPE = [x[0] for x in _CHANNEL_INFO]
        _CHANNEL_NO_LOOKING = [x[1] for x in _CHANNEL_INFO]

        # Drop when channel was set not to look
        if True in _CHANNEL_NO_LOOKING:
            return None

        # Logging all the messages
        await self.logger(msg)

        print(msg.id, msg.server, msg.channel, msg.author, msg.content, msg.attachments, msg.embeds)

        # ## No React at bot message
        if msg.author.bot:
            return

        # ## No Direct Messages
        if msg.server is None:
            await self.send_message(msg.channel, "이 봇은 Direct Message 에서 사용하실 수 없습니다.\nThis bot cannot be used in DM.")
            return

        _RANK = self.getRank(msg.server.id, msg.author.id)

        # Command Process
        if "allow_command" in _CHANNEL_TYPE:
            if _RANK > 1e5: return

            # ## Local Command detection
            _SERVER_COMMANDS = self.getCommands(msg.server.id)
            msg_head = msg.content.split(" ")[0]

            # ## Local Command
            if msg_head in _SERVER_COMMANDS.keys():
                f = _SERVER_COMMANDS[msg_head]['feedback'].replace("\\n", "\n").replace("\\t", "\t")
                t = _SERVER_COMMANDS[msg_head]['timeout']
                _out = await self.send_message(msg.channel, f)
                await self.add_reaction(msg, self.react_emoji)

                if t > 0:
                    await sleep(t)
                    await self.delete_message(_out)

            # ## Bot Feature Command Detection
            if msg_head == "2권한":
                print("GO")
                specific_admin = self.getAdmins(server=msg.server.id, user_id=msg.author.id)

                result = ""
                if specific_admin:
                    for role in [x[0] for x in specific_admin]:
                        if role == "global":
                            result += "**Admin (global)**\n" \
                                      "\t*모든 서버에서 봇의 관리자 권한을 얻습니다.\n" \
                                      "\t봇의 주인이거나 주인이 권한을 인가해준 관리자입니다.\n" \
                                      "\t봇의 기능에 대해 __**모든 권한**__이 있습니다.*\n\n"
                        elif role == "server":
                            result += "**Admin (server)**\n" \
                                      "\t*이 서버에 한해서 봇의 관리자 권한을 얻습니다.\n" \
                                      "\t봇의 기능에 대해 이 서버에 대한 내용에 권한이 있습니다.*\n\n"
                        else:
                            result += "**Admin (etc)**\n" \
                                      "\t*봇의 기능에 대해 일부 권한이 있습니다.*\n\n"
                else:
                    if _RANK <= 1e5:
                        result += "**User**\n" \
                                  "\t*봇의 일반 커멘드 사용권한이 있습니다.*\n\n"
                    else:
                        result += "**User**\n"

                embed = Embed(title="권한", description="<@{}>님의 으낙봇 사용 권한입니다.".format(msg.author.id))
                embed.add_field(name="Permissions", value=result, inline=False)
                embed.set_footer(text=self.getFooter())

                await self.send_message(msg.channel, embed=embed)

            elif msg_head == "2명령어" or msg_head == "2커맨드" or msg_head == "2commands":
                if _RANK > 1e5: return

                _out = await self.send_message(
                    msg.channel,
                    "<@{}> 이 서버에서 사용가능한 커맨드 목록입니다.\n\n\t".format(msg.author.id)+"\n\t".join(_SERVER_COMMANDS.keys())
                )
                await self.add_reaction(msg, self.react_emoji)

                await sleep(10)
                await self.delete_message(_out)

    async def on_member_join(self, member):
        server_id = member.server.id
        try:
            fb_channel_id = self.getFeedbackChannel(server_id, "welcome")
            if fb_channel_id == "": fb_channel_id = server_id
            fb_channel = self.get_channel(fb_channel_id)

            msg_temp = self.getTemplateMessage(server_id, "welcome")
            msg_temp = msg_temp.format(id=member.id, name=member.server.name).replace("\\n", "\n").replace("\\t", "\t")

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
            fb_channel_id = self.getFeedbackChannel(server_id, "goodbye")
            if fb_channel_id == "": fb_channel_id = server_id
            fb_channel = self.get_channel(fb_channel_id)

            msg_temp = self.getTemplateMessage(server_id, "left")
            msg_temp = msg_temp.format(gb_nick=member.name, nick=member.nick, name=member.server.name).replace("\\n", "\n").replace("\\t", "\t")

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
            embed.set_footer(text=self.getFooter() + " | Timestamp: {}({})".format(strftime("%Y/%m/%d %H:%M:%S"), time()))

            await self.send_message(at_channel, embed=embed)
        except Exception as ex: print(ex)

    async def on_message_edit(self, before, after):
        if before.author.bot: return None
        try:
            server_id = before.server.id
            at_channel_id = self.getFeedbackChannel(server_id, "audit")

            if at_channel_id == before.channel.id: return

            at_channel = self.get_channel(at_channel_id)

            embed = Embed(title="Message Editted", color=0xf57705,
                          description="do`in <@{}> | at <#{}>\n\n".format(before.author.id, before.channel.id))
            embed.set_author(name=before.author.name, icon_url=before.author.avatar_url)
            embed.add_field(name="Before", value="""Message: {}\n\nAttachments: {}\nEmbeds: {}\n""".format(before.content, dumps(before.attachments), dumps(before.embeds)), inline=False)
            embed.add_field(name="After", value="""Message: {}\n\nAttachments: {}\nEmbeds: {}\n""".format(after.content, dumps(after.attachments), dumps(after.embeds)), inline=False)
            embed.set_footer(text=self.getFooter() + " | Timestamp: {}({})".format(strftime("%Y/%m/%d %H:%M:%S"), time()))

            await self.send_message(at_channel, embed=embed)
        except Exception as ex: print(ex)

    async def on_message_delete(self, msg):
        if msg.author.bot: return None
        try:
            server_id = msg.server.id
            at_channel_id = self.getFeedbackChannel(server_id, "audit")

            if at_channel_id == msg.channel.id: return

            at_channel = self.get_channel(at_channel_id)

            embed = Embed(title="Message Deleted", color=0xf57705,
                          description="author <@{}> | at <#{}>\n\n".format(msg.author.id, msg.channel.id))
            embed.set_author(name=msg.author.name, icon_url=msg.author.avatar_url)
            embed.add_field(name="Before", value="""Message: {}\n\nAttachments: {}\nEmbeds: {}\n""".format(msg.content, dumps(msg.attachments), dumps(msg.embeds)), inline=False)
            embed.set_footer(text=self.getFooter() + " | Timestamp: {}({})".format(strftime("%Y/%m/%d %H:%M:%S"), time()))

            await self.send_message(at_channel, embed=embed)
        except Exception as ex: print(ex)