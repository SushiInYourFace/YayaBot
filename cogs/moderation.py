import datetime
import io
import json
import sqlite3
import time

import discord
from discord import errors
from discord.ext import commands, tasks

import functions

#sets up SQLite
connection = sqlite3.connect("database.db")
cursor = connection.cursor()

class Moderation(commands.Cog):
    """Cog for moderators to help them moderate!"""

    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.timedRoleCheck.start()
        self.bot.cooldowns = {}
        self.bot.pending_cooldowns = {}
        self.bot.before_invoke(self.before_invoke)

    @commands.group(help="Purge command.")
    @commands.check(functions.has_modrole)
    async def purge(self,ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    #purge command
    @purge.command(help="Purges a specified amount of messages from the chat",name="number",aliases=["n"])
    async def purge_number(self, ctx, arg:int):
        arg += 1 # adding one to ignore the command invoking message
        await ctx.channel.purge(limit=arg)
    
    #purge match command, only purges messages that contain a certain string
    @purge.command(help="Purges messages containing a certain string", name="match", aliases=["m"])
    async def purge_match(self, ctx, limit:int, *, filtered):
        limit += 1
        def filter_check(message):
            return filtered in message.content
        await ctx.channel.purge(limit=limit, check=filter_check)

    #ban
    @commands.command(help="bans a user")
    @commands.check(functions.has_modrole)
    async def ban(self, ctx, member : discord.Member, *, reason=None):
        if not ctx.guild.me.guild_permissions.ban_members:
            await ctx.send("I don't have permissions to ban people.")
            return
        elif ctx.guild.me.top_role <= member.top_role:
            await ctx.send("I don't have permission to ban that member.")
            return
        if reason is None:
            reason = "No reason specified"
        await ctx.guild.ban(member, reason=reason)
        bantime = time.time()
        banEmbed = discord.Embed(title="You have been banned from "+ ctx.guild.name, color=0xFF0000)
        banEmbed.add_field(name="Ban reason:", value=reason)
        try:
            await member.send(embed=banEmbed)
            unsent = False
        except errors.HTTPException:
            unsent = True
        successEmbed = discord.Embed(title="Banned " + str(member), color=0xFF0000)
        if unsent:
            successEmbed.set_footer(text="Failed to send a message to the user " + str(member))
        await ctx.send(embed=successEmbed)
        SqlCommands.new_case(member.id, ctx.guild.id, "ban", reason, bantime, -1, str(ctx.author))

    @commands.command(help="kicks a user")
    @commands.check(functions.has_modrole)
    async def kick(self, ctx, member : discord.Member, *, reason=None):
        if not ctx.guild.me.guild_permissions.kick_members:
            await ctx.send("I don't have permissions to kick people.")
            return
        elif ctx.guild.me.top_role <= member.top_role:
            await ctx.send("I don't have permission to kick that member.")
            return
        if reason == None:
            reason = "No reason specified"
        kicktime = time.time()
        kickEmbed = discord.Embed(title="You have been kicked from "+ ctx.guild.name, color=0xFF0000)
        kickEmbed.add_field(name="Kick reason:", value=reason)
        await ctx.guild.kick(member, reason=reason)
        try:
            await member.send(embed=kickEmbed)
            unsent = False
        except errors.HTTPException:
            unsent = True
        successEmbed = discord.Embed(title="Kicked " + str(member), color=0xFF0000)
        if unsent:
            successEmbed.set_footer(text="Failed to send a message to the user " + str(member))
        await ctx.send(embed=successEmbed)
        SqlCommands.new_case(member.id, ctx.guild.id, "kick", reason, kicktime, -1, str(ctx.author))

    #unban
    @commands.command(help="unbans a user")
    @commands.check(functions.has_modrole)
    async def unban(self, ctx, user : discord.User):
        unbanTime = time.time()
        try:
            await ctx.guild.fetch_ban(user)
        except discord.NotFound:
            notBannedEmbed = discord.Embed(title = "This user is not banned", color = 0xFF0000)
            await ctx.send(embed = notBannedEmbed)
            return
        await ctx.guild.unban(user)
        successEmbed = discord.Embed(title = "Unbanned " + str(user), color = 0x00FF00)
        await ctx.send(embed=successEmbed)
        SqlCommands.new_case(user.id, ctx.guild.id, "unban", "N/A", unbanTime, -1, str(ctx.author))

    #gravel
    @commands.command(help="Gravels a user")
    @commands.check(functions.has_modrole)
    async def gravel(self, ctx, member : discord.Member, graveltime, *, reason=None):
        now = time.time()    
        if graveltime[-1] == "m" or graveltime[-1] == "h" or graveltime[-1] == "d" or graveltime[-1] == "s":
            timeformat = graveltime[-1]
            timevalue = graveltime[:-1]
        else:
            timeformat = "m"
            timevalue = graveltime
        try:
            timevalue = int(timevalue)
        except ValueError:
            await ctx.send("Oops! That's not a valid time format")
            return
        if reason == None:
            reason = "No reason specified"
        totalsecs = TimeConversions.secondsconverter(timevalue, timeformat)
        roleid = SqlCommands.get_role(ctx.guild.id, "gravel")
        converter = commands.RoleConverter()
        role = await converter.convert(ctx,str(roleid))
        await member.add_roles(role)
        end = now + totalsecs
        gravelEmbed = discord.Embed(title=f"You have been graveled in {ctx.guild.name} for  {TimeConversions.fromseconds(totalsecs)}", color=0xFF0000)
        gravelEmbed.add_field(name="Reason:", value=reason)
        try:
            await member.send(embed=gravelEmbed)
            unsent = False
        except errors.HTTPException:
            unsent = True
        SqlCommands.new_case(member.id, ctx.guild.id, "gravel", reason, now, end, str(ctx.author))
        successEmbed = discord.Embed(title = "Gravelled  " + str(member), color = 0x808080)
        if unsent:
            successEmbed.set_footer(text="Failed to send a message to this user")
        await ctx.send(embed=successEmbed)

    @commands.command(help="Mutes a user")
    @commands.check(functions.has_modrole)
    async def mute(self, ctx, member : discord.Member, mutetime, *, reason=None):
        now = time.time()    
        if mutetime[-1] == "m" or mutetime[-1] == "h" or mutetime[-1] == "d" or mutetime[-1] == "s":
            timeformat = mutetime[-1]
            timevalue = mutetime[:-1]
        else:
            timeformat = "m"
            timevalue = mutetime
        try:
            timevalue = int(timevalue)
        except ValueError:
            await ctx.send("Oops! That's not a valid time format")
            return
        if reason == None:
            reason = "No reason specified"
        totalsecs = TimeConversions.secondsconverter(timevalue, timeformat)
        roleid = SqlCommands.get_role(ctx.guild.id, "muted")
        roleid = str(roleid)
        converter = commands.RoleConverter()
        role = await converter.convert(ctx,roleid)
        await member.add_roles(role)
        end = now + totalsecs
        muteEmbed = discord.Embed(title="You have been muted in "+ ctx.guild.name + " for " + TimeConversions.fromseconds(totalsecs), color=0xFF0000)
        muteEmbed.add_field(name="Reason:", value=reason)
        try:
            await member.send(embed=muteEmbed)
            unsent = False
        except errors.HTTPException:
            unsent = True
        SqlCommands.new_case(member.id, ctx.guild.id, "mute", reason, now, end, str(ctx.author))
        successEmbed = discord.Embed(title = "Muted " + str(member), color = 0xFFFFFF)
        if unsent:
            successEmbed.set_footer(text="Failed to send a message to this user")
        await ctx.send(embed=successEmbed)

    @commands.command(help="warns a user")
    @commands.check(functions.has_modrole)
    async def warn(self, ctx, member : discord.Member, *, reason):
        warnEmbed = discord.Embed(title="You have been warned in "+ ctx.guild.name, color=0xFF0000)
        warnEmbed.add_field(name="Reason:", value=reason)
        SqlCommands.new_case(member.id, ctx.guild.id, "warn", reason, time.time(), -1, str(ctx.author))
        try:
            await member.send(embed=warnEmbed)
            successEmbed = discord.Embed(title="Successfully warned "+ str(member), color = 0x00FF00)
            await ctx.send(embed=successEmbed)
        except errors.HTTPException:
            failEmbed = discord.Embed(title="Could not warn user "+ str(member), color = 0x00FF00)
            await ctx.send(embed=failEmbed)

    @commands.command(help="Shows a user's modlogs")
    @commands.check(functions.has_modrole)
    async def modlogs(self, ctx, member : discord.User):
        logEmbed = discord.Embed(title = str(member) + "'s Modlogs", color=0x000080)
        logs = cursor.execute("SELECT id_in_guild, guild, user, type, reason, started, expires, moderator FROM caselog WHERE user = ? AND guild = ?", (member.id, ctx.guild.id)).fetchall()
        for log in logs:
            start = datetime.datetime.fromtimestamp(int(log[5])).strftime('%Y-%m-%d %H:%M:%S')
            if int(log[6]) != -1:
                totaltime = TimeConversions.fromseconds(int(int(log[6])) - int(log[5]))
            else:
                totaltime = "N/A"
            logEmbed.add_field(name="__**Case " + str(log[0]) + "**__", value="**Type- **" + log[3] + "\n**Reason- **" + log[4] + "\n**Time- **" + start + "\n**Length- **" + totaltime + "\n**Moderator- **" + log[7], inline=True)
        logEmbed.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed = logEmbed)

    @commands.command(help="Shows information on a case")
    @commands.check(functions.has_modrole)
    async def case(self, ctx, case:int):
        caseinfo = cursor.execute("SELECT id_in_guild, guild, user, type, reason, started, expires, moderator FROM caselog WHERE id = ?", (case,)).fetchone()
        try:
            start = datetime.datetime.fromtimestamp(int(caseinfo[5])).strftime('%Y-%m-%d %H:%M:%S')
        except TypeError:
            await ctx.send("Could not find that case number")
            return
        if int(caseinfo[6]) != -1:
            totaltime = TimeConversions.fromseconds(int(int(caseinfo[6])) - int(caseinfo[5]))
        else:
            totaltime = "N/A"
        logEmbed = discord.Embed(title="Case " + str(case), color=0x000080)
        user = await self.bot.fetch_user(caseinfo[2])
        logEmbed.add_field(name=user, value="**Type- **" + caseinfo[3] + "\n**Reason- **" + caseinfo[4] + "\n**Time- **" + start + "\n**Length- **" + totaltime + "\n**Moderator- **" + caseinfo[7], inline=True)
        logEmbed.set_thumbnail(url=user.avatar_url)
        await ctx.send(embed = logEmbed)


    @commands.command(help="Unmutes a User")
    @commands.check(functions.has_modrole)
    async def unmute(self, ctx, member : discord.Member):
        mod = str(ctx.author)
        unmutetime = time.time()
        muted = SqlCommands.get_role(ctx.guild.id, "muted")
        mutedRole = ctx.guild.get_role(muted)
        await member.remove_roles(mutedRole,)
        successEmbed = discord.Embed(title="Unmuted " + str(member), color=0x00FF00)
        await ctx.send(embed=successEmbed)
        SqlCommands.new_case(member.id, ctx.guild.id, "unmute", "N/A", unmutetime, -1, mod)

    @commands.command(help="Ungravels a User")
    @commands.check(functions.has_modrole)
    async def ungravel(self, ctx, member : discord.Member):
        mod = str(ctx.author)
        ungraveltime = time.time()
        gravel = SqlCommands.get_role(ctx.guild.id, "gravel")
        mutedRole = ctx.guild.get_role(gravel)
        await member.remove_roles(mutedRole,)
        successEmbed = discord.Embed(title="Removed Gravel from " + str(member), color=0x00FF00)
        await ctx.send(embed=successEmbed)
        SqlCommands.new_case(member.id, ctx.guild.id, "ungravel", "N/A", ungraveltime, -1, mod)

    #checks if a role needs to be removed
    @tasks.loop(seconds=5.0)
    async def timedRoleCheck(self):
        now = time.time()
        expired = cursor.execute("SELECT id FROM active_cases WHERE expiration <= " + str(now)).fetchall()
        for item in expired:
            case = cursor.execute("SELECT guild, user, type FROM caselog WHERE id = ?", (item[0],)).fetchone()
            guild = self.bot.get_guild(int(case[0]))
            if case[2] == "gravel":
                roleid = SqlCommands.get_role(case[0], "gravel")
                role = guild.get_role(roleid)
                member = guild.get_member(case[1])
                try:
                    await member.remove_roles(role)
                except:
                    pass
            elif case[2] == "mute":
                roleid = SqlCommands.get_role(case[0], "muted")
                role = guild.get_role(roleid)
                member = guild.get_member(case[1])
                try:
                    await member.remove_roles(role)
                except:
                    pass
            cursor.execute("DELETE FROM active_cases WHERE id = ?", (item[0],))
            connection.commit()
         
    async def bot_check_once(self,ctx):
        if isinstance(ctx.channel,discord.DMChannel):
            return True
        if ctx.guild.id not in self.bot.cooldowns.keys():
            self.bot.cooldowns[ctx.guild.id] = {}
        if ctx.guild.id not in self.bot.pending_cooldowns.keys():
            self.bot.pending_cooldowns[ctx.guild.id] = {}
        if functions.has_modrole(ctx) or functions.has_adminrole(ctx):
            return True
        now = datetime.datetime.now()
        if now < self.bot.cooldowns[ctx.guild.id].get(ctx.author.id,now):
            await ctx.message.add_reaction("🕐")
            return False
        cmd = cursor.execute("SELECT command_usage, command_cooldown FROM role_ids WHERE guild = ?", (ctx.guild.id,)).fetchone()
        if cmd:
            commandRole, commandCooldown = cmd
        else:
            return True
        member_roles = [role.id for role in ctx.author.roles]
        if not commandRole:
            if commandCooldown and not (ctx.invoked_with == "help" and ctx.command.name != "help"):
                self.bot.pending_cooldowns[ctx.guild.id][ctx.author.id] = (ctx.command,datetime.datetime.now() + datetime.timedelta(milliseconds=commandCooldown))
            return True
        elif (commandRole in member_roles):
            if commandCooldown and not (ctx.invoked_with == "help" and ctx.command.name != "help"):
                self.bot.pending_cooldowns[ctx.guild.id][ctx.author.id] = (ctx.command,datetime.datetime.now() + datetime.timedelta(milliseconds=commandCooldown))
            return True
        else:
            return False

    async def before_invoke(self,ctx): # There is no way to put a global check behind local checks so cooldowns were being added even if the command was not ran and before_invoke cannot stop a command from being run, this stops that by adding the cooldowns when the command is invoked rather than during the global check.
        if ctx.author.id in self.bot.pending_cooldowns[ctx.guild.id].keys():
            cooldown = [(user,self.bot.pending_cooldowns[ctx.guild.id][user][1]) for user in self.bot.pending_cooldowns[ctx.guild.id] if (self.bot.pending_cooldowns[ctx.guild.id][user][0] == ctx.command and user == ctx.author.id)]
            if cooldown:
                self.bot.cooldowns[ctx.guild.id][cooldown[0][0]] = cooldown[0][1]

SqlCommands = functions.Sql()
TimeConversions = functions.timeconverters()

def setup(bot):
    bot.add_cog(Moderation(bot))
