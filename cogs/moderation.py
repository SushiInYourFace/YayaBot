import discord
from discord import errors
from discord.ext import commands, tasks
import sqlite3
import time
import datetime
import requests
import io

#sets up SQLite
connection = sqlite3.connect("database.db")
cursor = connection.cursor()

async def filter_check(ctx):
    inDb = cursor.execute("SELECT * FROM message_filter WHERE guild = ?", (ctx.guild.id,)).fetchone()
    if (inDb is None): # Guild filter doesn't exist
        cursor.execute("INSERT INTO message_filter(guild,enabled,filter) VALUES(?,?,?)",(ctx.guild.id,1,""))
        connection.commit()
        await ctx.send("Filter created and enabled.")
    return True

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.timedRoleCheck.start()
        self.bot.wordWarnCooldown = {}

    @commands.group(help="Purge command.")
    @commands.has_permissions(manage_messages=True)
    async def purge(self,ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_help(ctx)

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
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member : discord.Member, *, reason):
        mod = str(ctx.author)
        guild = ctx.guild
        username = member.name
        userid = member.id
        bantime = time.time()
        banEmbed = discord.Embed(title="You have been banned from "+ ctx.guild.name, color=0xFF0000)
        banEmbed.add_field(name="Ban reason:", value=reason)
        try:
            await member.send(embed=banEmbed)
            unsent = False
        except errors.HTTPException:
            unsent = True
        await guild.ban(member, reason=reason)
        successEmbed = discord.Embed(title="Banned " + username, color=0xFF0000)
        if unsent:
            successEmbed.set_footer(text="Failed to send a message to this user")
        await ctx.send(embed=successEmbed)
        SqlCommands.new_case(userid, guild.id, "ban", reason, bantime, -1, mod)

    #unban
    @commands.command(help="unbans a user")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user : discord.User):
        guild = ctx.guild
        mod = str(ctx.author)
        userid = user.id
        unbanTime = time.time()
        try:
            await guild.fetch_ban(user)
        except discord.NotFound:
            notBannedEmbed = discord.Embed(title = "This user is not banned", color = 0xFF0000)
            await ctx.send(embed = notBannedEmbed)
            return
        await guild.unban(user)
        successEmbed = discord.Embed(title = "Unbanned " + user.name, color = 0x00FF00)
        await ctx.send(embed=successEmbed)
        SqlCommands.new_case(userid, guild.id, "unban", "N/A", unbanTime, -1, mod)

    #gravel
    @commands.command(help="Gravels a user")
    @commands.has_permissions(ban_members=True)
    async def gravel(self, ctx, member : discord.Member, graveltime, *, reason):
        guild = ctx.guild
        mod = str(ctx.author)
        now = time.time()    
        if graveltime[-1] == "m" or graveltime[-1] == "h" or graveltime[-1] == "d" or graveltime[-1] == "s":
            timeformat = graveltime[-1]
            timevalue = graveltime[:-1]
        else:
            await ctx.send("Oops! That's not a valid time format")
            return
        try:
            timevalue = int(timevalue)
        except ValueError:
            await ctx.send("Oops! That's not a valid time format")
            return
        totalsecs = TimeConversions.secondsconverter(timevalue, timeformat)
        roleid = SqlCommands.get_role(ctx.guild.id, "gravel")
        roleid = str(roleid)
        converter = commands.RoleConverter()
        role = await converter.convert(ctx,roleid)
        await member.add_roles(role)
        end = now + totalsecs
        SqlCommands.new_case(member.id, guild.id, "gravel", reason, now, end, mod)
        successEmbed = discord.Embed(title = "Gravelled  " + member.name, color = 0x808080)
        await ctx.send(embed=successEmbed)

    @commands.command(help="Mutes a user")
    @commands.has_permissions(ban_members=True)
    async def mute(self, ctx, member : discord.Member, mutetime, *, reason):
        guild = ctx.guild
        mod = str(ctx.author)
        now = time.time()    
        if mutetime[-1] == "m" or mutetime[-1] == "h" or mutetime[-1] == "d" or mutetime[-1] == "s":
            timeformat = mutetime[-1]
            timevalue = mutetime[:-1]
        else:
            await ctx.send("Oops! That's not a valid time format")
            return
        try:
            timevalue = int(timevalue)
        except ValueError:
            await ctx.send("Oops! That's not a valid time format")
            return
        totalsecs = TimeConversions.secondsconverter(timevalue, timeformat)
        roleid = SqlCommands.get_role(ctx.guild.id, "muted")
        roleid = str(roleid)
        converter = commands.RoleConverter()
        role = await converter.convert(ctx,roleid)
        await member.add_roles(role)
        end = now + totalsecs
        SqlCommands.new_case(member.id, guild.id, "mute", reason, now, end, mod)
        successEmbed = discord.Embed(title = "Muted " + member.name, color = 0xFFFFFF)
        await ctx.send(embed=successEmbed)

    @commands.command(help="Shows a user's modlogs")
    @commands.has_permissions(ban_members=True)
    async def modlogs(self, ctx, member : discord.User):
        avatar = member.avatar_url
        logEmbed = discord.Embed(title = member.name + "'s Modlogs", color=0x000080)
        logs = cursor.execute("SELECT id, guild, user, type, reason, started, expires, moderator FROM caselog WHERE user = ? AND guild = ?", (member.id, ctx.guild.id)).fetchall()
        for log in logs:
            start = datetime.datetime.fromtimestamp(int(log[5])).strftime('%Y-%m-%d %H:%M:%S')
            if int(log[6]) != -1:
                totaltime = TimeConversions.fromseconds(int(int(log[6])) - int(log[5]))
            else:
                totaltime = "Permanent"
            logEmbed.add_field(name="__**Case " + str(log[0]) + "**__", value="**Type- **" + log[3] + "\n**Reason- **" + log[4] + "\n**Time- **" + start + "\n**Length- **" + totaltime + "\n**Moderator- **" + log[7], inline=True)
        logEmbed.set_thumbnail(url=avatar)
        await ctx.send(embed = logEmbed)

    @commands.command(help="Unmutes a User")
    @commands.has_permissions(ban_members=True)
    async def unmute(self, ctx, member : discord.Member):
        mod = str(ctx.author)
        unmutetime = time.time()
        muted = SqlCommands.get_role(ctx.guild.id, "muted")
        mutedRole = ctx.guild.get_role(muted)
        await member.remove_roles(mutedRole,)
        successEmbed = discord.Embed(title="Unmuted " + member.name, color=0x00FF00)
        await ctx.send(embed=successEmbed)
        SqlCommands.new_case(member.id, ctx.guild.id, "unmute", "N/A", unmutetime, -1, mod)

    @commands.command(help="Ungravels a User")
    @commands.has_permissions(ban_members=True)
    async def ungravel(self, ctx, member : discord.Member):
        mod = str(ctx.author)
        ungraveltime = time.time()
        gravel = SqlCommands.get_role(ctx.guild.id, "gravel")
        mutedRole = ctx.guild.get_role(gravel)
        await member.remove_roles(mutedRole,)
        successEmbed = discord.Embed(title="Removed Gravel from " + member.name, color=0x00FF00)
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

    @commands.group(name="filter",aliases=["messageFilter","message_filter"])
    @commands.has_permissions(manage_guild=True)
    @commands.check(filter_check)
    async def messageFilter(self,ctx):
        """Modifies the server message word filter."""
        if ctx.invoked_subcommand is None:
            await self.bot.send_help(ctx)

    @messageFilter.command(name="set")
    async def messageFilter_set(self,ctx,*,mFilter=None):
        """Sets the server message filter to the specified string or contents of a supplied text file if the desired filter is longer than 2000 characters.
        Each word/phrase to be filtered should be separated by ;
        For exmaple to filter both mark and john you'd put `mark;john`
        Put nothing for filter to be reset to nothing."""
        if (mFilter is None and ctx.message.attachments):
            response = requests.get(ctx.message.attachments[0].url)
            response.raise_for_status()
            mFilter = response.text
        elif (not ctx.message.attachments and mFilter is None):
            mFilter = ""
        if mFilter.endswith(";"):
            mFilter = mFilter[:-1]
        if mFilter.startswith(";"):
            mFilter = mFilter[1:]
        cursor.execute("UPDATE message_filter SET filter=? WHERE guild=?",(mFilter,ctx.guild.id))
        connection.commit()
        await ctx.send("Filter set.")

    @messageFilter.command(name="add")
    async def messageFilter_add(self,ctx,*words):
        """Adds specified words/phrases to filter.
        You can specify multiple words with spaces, to add something that includes a space you must encase it in ".
        For example `[p]filter add "mario and luigi"` would filter `mario and luigi` only and not `mario`, `and` or `luigi` separately"""
        guildFilter = cursor.execute("SELECT * FROM message_filter WHERE guild = ?",(ctx.guild.id,)).fetchone()[2]
        guildFilter = guildFilter.split(";")
        if "" in guildFilter:
            guildFilter.remove("")
        if not guildFilter:
            guildFilter = []
        for word in words:
            guildFilter.append(word)
        guildFilter = ";".join(guildFilter)
        cursor.execute("UPDATE message_filter SET filter=? WHERE guild=?",(guildFilter,ctx.guild.id))
        connection.commit()
        await ctx.send("Added to filter.")
   

    @messageFilter.command(name="remove",aliases=["del","delete"])
    async def messageFilter_remove(self,ctx,*words):
        """Removes specified words/phrases from filter.
        You can specify multiple words with spaces, to remove something that includes a space you must encase it in ".
        For example `[p]filter add "mario and luigi"` would remove `mario and luigi`"""
        guildFilter = cursor.execute("SELECT * FROM message_filter WHERE guild = ?",(ctx.guild.id,)).fetchone()[2]
        guildFilter = guildFilter.split(";")
        if "" in guildFilter:
            guildFilter.remove("")
        notFoundWords = []
        for word in words:
            try:
                guildFilter.remove(word)
            except:
                notFoundWords.append(word)
        guildFilter = ";".join(guildFilter)
        cursor.execute("UPDATE message_filter SET filter=? WHERE guild=?",(guildFilter,ctx.guild.id))
        connection.commit()
        await ctx.send(f"Removed from filter. {'The following words were not found so not removed: ' if notFoundWords else ''}{' '.join(notFoundWords) if notFoundWords else ''}")

    @messageFilter.command(name="get",aliases=["list"])
    async def messageFilter_get(self,ctx):
        """Sends the filter as a message or as a text file if it's over 2000 characters"""
        guildFilter = cursor.execute("SELECT * FROM message_filter WHERE guild = ?",(ctx.guild.id,)).fetchone()
        if len(str(guildFilter[2])) <= 1977:
            await ctx.send(f"Filter {'enabled' if guildFilter[1] == 1 else 'disabled'} ```{guildFilter[2] if guildFilter[2] else ' '}```")
        else:
            fp = io.StringIO(guildFilter[2])
            f = discord.File(fp,filename="filter.txt")
            await ctx.send(file=f)

    @messageFilter.command(name="toggle")
    async def messageFilter_toggle(self,ctx):
        """Toggles whether the filter is on or not."""
        enabled = cursor.execute("SELECT * FROM message_filter WHERE guild = ?",(ctx.guild.id,)).fetchone()[1]
        enabled = 1 if enabled == 0 else 0
        cursor.execute("UPDATE message_filter SET enabled=? WHERE guild=?",(enabled,ctx.guild.id))
        connection.commit()
        await ctx.send(f"Filter now {'enabled' if enabled == 1 else 'disabled'}.")

    async def check_message(self,message):
        if message.author == message.guild.me or message.author.bot:
            return
        if message.author.guild_permissions.manage_messages:
            return
        guildFilter = cursor.execute("SELECT * FROM message_filter WHERE guild = ?",(message.guild.id,)).fetchone()
        if guildFilter[1] == 1:
            bannedWords = guildFilter[2].split(";")
            if "" in bannedWords:
                bannedWords.remove("")
            if any(bannedWord in message.content.lower() for bannedWord in bannedWords):
                await message.delete()
                if message.channel.id not in self.bot.wordWarnCooldown:
                    self.bot.wordWarnCooldown[message.channel.id] = 0
                if self.bot.wordWarnCooldown[message.channel.id] < time.time():
                    await message.channel.send(f"Watch your language {message.author.mention}",delete_after=2)
                self.bot.wordWarnCooldown[message.channel.id] = time.time()+2

    @commands.Cog.listener()
    async def on_message(self,message):
        await self.check_message(message)

    @commands.Cog.listener()
    async def on_message_edit(self,before, after):
        await self.check_message(after)

def setup(bot):
    bot.add_cog(Moderation(bot))
 
class timeconverters:
    def secondsconverter(self, value, startType):
        if startType == "s":
            #time already in seconds
            pass
        elif startType == "m":
            value *= 60
        elif startType == "h":
            value *= 3600
        elif startType == "d":
            value *= 86400
        return value
    def fromseconds(self, seconds):
        if seconds >= 86400:
            days = seconds//86400
            return str(days) + " Days"
        elif seconds >= 3600:
            hours = seconds//3600
            return str(hours) + " Hours"
        elif seconds >= 60:
            minutes = seconds//60
            return str(minutes) + " Minutes"
        else:
            return str(seconds) + " Seconds"
class Sql:
    def newest_case(self):
        caseNumber = cursor.execute("SELECT id FROM caselog ORDER BY id DESC LIMIT 1").fetchone()
        if caseNumber == None:
            caseNumber = 0
        else:
            caseNumber = caseNumber[0]
        caseNumber += 1
        return(caseNumber)

    def new_case(self, user, guild, casetype, reason, started, expires, mod):
        caseID = self.newest_case()
        if expires != -1:
            cursor.execute("INSERT INTO active_cases(id, expiration) VALUES(?,?)", (caseID, expires))
        cursor.execute("INSERT INTO caselog(id, guild, user, type, reason, started, expires, moderator) VALUES(?,?,?,?,?,?,?,?)", (caseID, guild, user, casetype, reason, started, expires, mod))
        connection.commit()

    def get_role(self, guild, role):
        if role == "gravel":
            roleid = cursor.execute("SELECT gravel from role_ids WHERE guild = ?", (guild,)).fetchone()
        elif role == "muted":
            roleid = cursor.execute("SELECT muted from role_ids WHERE guild = ?", (guild,)).fetchone()
        return roleid[0]

SqlCommands = Sql()
TimeConversions = timeconverters()