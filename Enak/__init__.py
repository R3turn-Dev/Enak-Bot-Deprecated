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
        super().__init__(command_prefix="2")

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

        self.add_command(self.get_commands)
        self.add_command(self.get_permission)
        self.add_command(self.get_all)
        self.add_command(self.print_if_admin)

    def getRank(self, server, user_id):
        _info = self.getAdmins(server=server, user_id=user_id, rank=True)
        _ranks = [x[1] for x in _info]
        if not _ranks: _ranks.append(1e5)

        return min(_ranks)

    async def is_admin(self, ctx=None, server_id=None, user_id=None):
        if ctx is None:
            admins = self.getAdmins(server=server_id, user_id=user_id)
            roles = [x[0] for x in admins]

            return roles
        else:
            if not server_id: server_id = ctx.message.server.id
            if not user_id: user_id = ctx.message.author.id
            admins = self.getAdmins(server=server_id, user_id=user_id)
            roles = [x[0] for x in admins]
            
            return bool(roles)

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

                return  # End process to avoid duplicated reaction

            # ## Feature Command
            await self.process_commands(msg)

    # 2권한
    @commands.command(name="권한", pass_context=True)
    async def get_permission(self, ctx):
        _RANK = self.getRank(ctx.message.server.id, ctx.message.author.id)
        roles = await self.is_admin(server_id=ctx.message.server.id, user_id=ctx.message.author.id)

        result = ""
        if roles:
            for role in roles:
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

        embed = Embed(title="권한", description="<@{}>님의 으낙봇 사용 권한입니다.".format(ctx.message.author.id))
        embed.add_field(name="Permissions", value=result, inline=False)
        embed.set_footer(text=self.getFooter())

        _out = await self.send_message(ctx.message.channel, embed=embed)
        await self.add_reaction(ctx.message, self.react_emoji)

        await sleep(20)
        await self.delete_message(_out)

    # 2커맨드
    @commands.command(name='커맨드', pass_context=True)
    async def get_commands(self, ctx):
        _SERVER_COMMANDS = self.getCommands(ctx.message.server.id)

        _out = await self.send_message(ctx.message.channel, "<@{}> 이 서버에서 사용가능한 커맨드 목록입니다.\n\n\t".format(ctx.message.author.id) + "\n\t".join(_SERVER_COMMANDS.keys()))
        await self.add_reaction(ctx.message, self.react_emoji)

        await sleep(10)
        await self.delete_message(_out)

    @commands.command(name="관리자", pass_context=True)
    @commands.check(is_admin)
    async def print_if_admin(self, ctx):
        await self.send_message(ctx.message.channel, repr(data))

    # 2정보
    @commands.command(name="정보", pass_context=True)
    async def get_all(self, ctx):
        channels = list(set(list(self.get_all_channels())))
        servers = list(set([x.server for x in channels]))
        members = list(self.get_all_members())

        _out = await self.send_message(ctx.message.channel, """Guilds: {:,}\nChannels: {:,}\nUsers: {:,}\n\n\t{}""".format(len(servers), len(channels), len(members), "\n\t".join([x.name for x in servers])))
        await self.add_reaction(ctx.message, self.react_emoji)

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
            msg_temp = msg_temp.format(gb_nick=member.name, nick=member.nick if member.nick is not None else member.name, name=member.server.name).replace("\\n", "\n").replace("\\t", "\t")

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
