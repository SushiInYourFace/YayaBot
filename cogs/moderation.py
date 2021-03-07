import discord
from discord import errors
from discord.ext import commands
import sqlite3
import time
import requests
import io

#sets up SQLite
connection = sqlite3.connect("database.db")
cursor = connection.cursor()

async def filter_check(ctx):
    inDb = cursor.execute("SELECT * FROM message_filter WHERE guild = ?", (ctx.guild.id,)).fetchone()
    if (inDb is None):
        cursor.execute("INSERT INTO message_filter(guild,enabled,filter) VALUES(?,?,?)",(ctx.guild.id,1,""))
        connection.commit()
        await ctx.send("Filter created and enabled.")
    return True

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.group(help="Purge command.")
    async def purge(self,ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    #purge command
    @purge.command(help="Purges a specified amount of messages from the chat",name="number",aliases=["n"])
    @commands.has_permissions(manage_messages=True)
    async def purge_number(self, ctx, arg:int):
        arg += 1 # adding one to ignore the command invoking message
        await ctx.channel.purge(limit=arg)
    
    #purge match command, only purges messages that contain a certain string
    @purge.command(help="Purges messages containing a certain string", name="match", aliases=["m"])
    @commands.has_permissions(manage_messages=True)
    async def purge_match(self, ctx, limit:int, *, filtered):
        limit += 1
        def filter_check(message):
            return filtered in message.content
        await ctx.channel.purge(limit=limit, check=filter_check)

    #ban
    @commands.command(help="bans a user")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member : discord.Member, *, arg):
        guild = ctx.guild
        username = member.name
        userid = member.id
        bantime = time.time()
        banEmbed = discord.Embed(title="You have been banned from "+ ctx.guild.name, color=0xFF0000)
        banEmbed.add_field(name="Ban reason:", value=arg)
        try:
            await member.send(embed=banEmbed)
            unsent = False
        except errors.HTTPException:
            unsent = True
        await guild.ban(member, reason=arg)
        successEmbed = discord.Embed(title="Banned " + username, color=0xFF0000)
        if unsent:
            successEmbed.set_footer(text="Failed to send a message to this user")
        await ctx.send(embed=successEmbed)
        SqlCommands.new_case(userid, "ban", arg, bantime, -1)


    #unban
    @commands.command(help="unbans a user")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user : discord.User):
        guild = ctx.guild
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
        SqlCommands.new_case(userid, "unban", "N/A", unbanTime, -1)

    @commands.group(name="filter",aliases=["messageFilter","message_filter"])
    @commands.has_permissions(manage_guild=True)
    @commands.check(filter_check)
    async def messageFilter(self,ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

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
            if any(bannedWord in message.content for bannedWord in bannedWords):
                await message.delete()
                await message.channel.send(f"Watch your language {message.author.mention}",delete_after=2)

    @commands.Cog.listener()
    async def on_message(self,message):
        await self.check_message(message)

    @commands.Cog.listener()
    async def on_message_edit(self,before, after):
        await self.check_message(after)

def setup(bot):
    bot.add_cog(Moderation(bot))

class Sql:
    def newest_case(self):
        caseNumber = cursor.execute("SELECT id FROM caselog ORDER BY id DESC LIMIT 1").fetchone()
        if caseNumber == None:
            caseNumber = 0
        else:
            caseNumber = caseNumber[0]
        caseNumber += 1
        return(caseNumber)

    def new_case(self, user, casetype, reason, started, expires):
        caseID = self.newest_case()
        if expires != -1:
            cursor.execute("INSERT INTO active_cases(id, expiration) VALUES(?,?)", (caseID, expires))
        cursor.execute("INSERT INTO caselog(id, user, type, reason, started, expires) VALUES(?,?,?,?,?,?)", (caseID, user, casetype, reason, started, expires))
        connection.commit()

SqlCommands = Sql()