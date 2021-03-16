import discord
from discord import errors
from discord.ext import commands, tasks
import cogs.moderation as modcog
import sqlite3
import time
import difflib
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

class AutoMod(commands.Cog):
    """Moderates chat and users automatically!"""
    
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.bot.wordWarnCooldown = {}

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
        if message.author == message.author.bot:
            return
        if isinstance(message.channel, discord.channel.DMChannel):
            return
        if message.author.guild_permissions.manage_messages:
            return
        guildFilter = cursor.execute("SELECT * FROM message_filter WHERE guild = ?",(message.guild.id,)).fetchone()
        if not guildFilter:
            return
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
        if isinstance(after.channel, discord.channel.DMChannel):
            return
        logID = cursor.execute("SELECT modlogs from role_ids WHERE guild = ?",(after.guild.id,)).fetchone()
        if logID and logID !=0 and not after.author.bot:
            channel = after.guild.get_channel(logID[0])
            editEmbed = discord.Embed(title=f"Message edited in {after.channel.name}", color=0xFFFF00)
            editEmbed.set_author(name=str(after.author), icon_url=after.author.avatar_url)
            now = datetime.datetime.now()
            #difference
            d = difflib.Differ()
            result = list(d.compare(before.content.split(), after.content.split()))
            start = []
            end = []
            for i in range(len(result)):
                if result[i].startswith("- "):
                    start.append("~~" + result[i].strip("- ")+ "~~")
                elif result[i].startswith("+ "):
                    end.append("*" + result[i].strip("+ ") + "*")
                elif result[i].startswith("? "):
                    pass
                else:
                    start.append(result[i].strip(" "))
                    end.append(result[i].strip(" "))
            #formats strikethroughs pretty
            for i in range(len(start)):
                try:
                    if start[i].endswith("~~") and start[i+1].startswith("~~"):
                        start[i] = start[i][:-2]
                        start[i+1] = start[i+1][2:]
                except IndexError:
                    pass
            editEmbed.add_field(name="Before", value=" ".join(start))
            editEmbed.add_field(name="After", value=" ".join(end))
            date = now.strftime("%Y-%m-%d, %H:%M:%S")
            editEmbed.set_footer(text=f"edited at {date}")
            await channel.send(embed=editEmbed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        logID = cursor.execute("SELECT modlogs from role_ids WHERE guild = ?",(message.guild.id,)).fetchone()
        if logID and logID !=0 and not message.author.bot:
            channel = message.guild.get_channel(logID[0])
            deleteEmbed = discord.Embed(color=0xFF0000)
            deleteEmbed.set_author(name=str(message.author), icon_url=message.author.avatar_url)
            now = datetime.datetime.now()
            deleteEmbed.add_field(name=f"Message deleted from **{message.channel.name}**", value=message.content)
            date = now.strftime("%Y-%m-%d, %H:%M:%S")
            deleteEmbed.set_footer(text=f"deleted at {date}")
            await channel.send(embed=deleteEmbed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        cases = cursor.execute("SELECT id, type FROM caselog WHERE guild = ? AND user = ? AND expires >= ?", (member.guild.id, member.id, time.time(),)).fetchall()
        if cases is not None:
            #iterate through cases in case the user is both muted and graveled
            for case in cases:
                if case[1] == "mute":
                    casetype = "muted"
                elif case[1] == "gravel":
                    casetype = "gravel"
                else:
                    #sanity check
                    return
                role = modcog.SqlCommands.get_role(member.guild.id, casetype)
                try:
                    role = member.guild.get_role(role)
                    await member.add_roles(role)
                except:
                    pass

def setup(bot):
    bot.add_cog(AutoMod(bot))