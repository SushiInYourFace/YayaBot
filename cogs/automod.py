import datetime
import difflib
import io
import re
import sqlite3
import time

import aiohttp
import discord
from discord.ext import commands, tasks

import functions

#sets up SQLite
connection = sqlite3.connect("database.db")
cursor = connection.cursor()

async def filter_check(ctx):
    inDb = cursor.execute("SELECT * FROM message_filter WHERE guild = ?", (ctx.guild.id,)).fetchone()
    if (inDb is None): # Guild filter doesn't exist
        cursor.execute("INSERT INTO message_filter(guild,enabled,filterWildCard,filterExact) VALUES(?,?,?,?)",(ctx.guild.id,1,"",""))
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
            await ctx.send_help(ctx.command)

    @messageFilter.group(name="set")
    async def messageFilter_set(self,ctx):
        """Sets the server message filter to the specified string or contents of a supplied text file if the desired filter is longer than 2000 characters.
        Each word/phrase to be filtered should be separated by ;
        For exmaple to filter both mark and john you'd put `mark;john`
        Put nothing for filter to be reset to nothing."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    async def new_filter_format(self,ctx,new_filter):
        if (new_filter is None and ctx.message.attachments):
            async with aiohttp.ClientSession() as session:
                async with session.get(ctx.message.attachments[0].url) as r:
                    if r.status == 200:
                        new_filter = await r.text()
        elif (not ctx.message.attachments and new_filter is None):
            new_filter = ""
        if new_filter.endswith(";"):
            new_filter = new_filter[:-1]
        if new_filter.startswith(";"):
            new_filter = new_filter[1:]
        return new_filter

    @messageFilter_set.command(name="wild",aliases=["wildcard"])
    async def messageFilter_set_wild(self,ctx,*,new_filter=None):
        new_filter = await self.new_filter_format(ctx,new_filter)
        cursor.execute("UPDATE message_filter SET filterWildCard=? WHERE guild=?",(new_filter,ctx.guild.id))
        connection.commit()
        await ctx.send("Filter set.")

    @messageFilter_set.command(name="exact")
    async def messageFilter_set_exact(self,ctx,*,new_filter=None):
        new_filter = await self.new_filter_format(ctx,new_filter)
        cursor.execute("UPDATE message_filter SET filterExact=? WHERE guild=?",(new_filter,ctx.guild.id))
        connection.commit()
        await ctx.send("Filter set.")

    @messageFilter.command(name="add")
    async def messageFilter_add(self,ctx,*words):
        """Adds specified words/phrases to filter.
        You can specify multiple words with spaces, to add something that includes a space you must encase it in ".
        For example `[p]filter add "mario and luigi"` would filter `mario and luigi` only and not `mario`, `and` or `luigi` separately"""
        guildFilter = cursor.execute("SELECT * FROM message_filter WHERE guild = ?",(ctx.guild.id,)).fetchone()
        wildFilter = guildFilter[2].split(";")
        exactFilter = guildFilter[3].split(";")
        if not exactFilter:
            exactFilter = []
        if not wildFilter:
            wildFilter = []
        if "" in exactFilter:
            exactFilter.remove("")
        if "" in wildFilter:
            wildFilter.remove("")
        for word in words:
            if len(word) == 1:
                continue
            if word.startswith("*"):
                wildFilter.append(word[1:])
            else:
                guildFilter.append(word)
        wildFilter = ";".join(wildFilter)
        exactFilter = ";".join(exactFilter)
        cursor.execute("UPDATE message_filter SET filterWildCard=?, filterExact=? WHERE guild=?",(wildFilter,exactFilter,ctx.guild.id))
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
        """Sends the filter.
        Usually sent as a message but is sent as a text file if it's over 2000 characters"""
        guildFilter = cursor.execute("SELECT * FROM message_filter WHERE guild = ?",(ctx.guild.id,)).fetchone()
        text = f'Wildcard:\n{str(guildFilter[2])}\n\nExact:\n{str(guildFilter[3])}'
        if len(text) <= 1977:
            await ctx.send(f"Filter {'enabled' if guildFilter[1] == 1 else 'disabled'} ```{text}```")
        else:
            fp = io.StringIO(text)
            f = discord.File(fp,filename="filter.txt")
            await ctx.send("Filter is too large so is sent as a file:",file=f)    

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
        if message.author.discriminator == "0000":
            return
        if isinstance(message.channel, discord.channel.DMChannel):
            return
        if message.author.guild_permissions.manage_messages:
            return
        guildFilter = cursor.execute("SELECT * FROM message_filter WHERE guild = ?",(message.guild.id,)).fetchone() # Bad words.
        if not guildFilter:
            return
        if guildFilter[1] == 1:
            bannedWilds = guildFilter[2].split(";")
            bannedExacts = guildFilter[3].split(";")
            if "" in bannedWilds:
                bannedWilds.remove("")
            if "" in bannedExacts:
                bannedExacts.remove("")
            if " " in message.content.lower():
                words = message.content.split(" ")
            else:
                words = [message.content]
            if (any(bannedWord in message.content.lower() for bannedWord in bannedWilds) or any(bannedWord in words for bannedWord in bannedExacts)):
                await message.delete()
                if message.channel.id not in self.bot.wordWarnCooldown:
                    self.bot.wordWarnCooldown[message.channel.id] = 0
                if self.bot.wordWarnCooldown[message.channel.id] < time.time():
                    await message.channel.send(f"Watch your language {message.author.mention}",delete_after=2)
                self.bot.wordWarnCooldown[message.channel.id] = time.time()+2
        if False: # this should be a check for enabled emoji shit
            unicodeCheck = r"[^\w\s,.]"
            customCheck = r'<:\w*:\d*>'
            emojis = len(re.findall(unicodeCheck,message.content))
            emojis += len(re.findall(customCheck,message.content))
            if emojis > 5: # the number of emojis the guild allows
                await message.delete()
                if message.channel.id not in self.bot.wordWarnCooldown:
                    self.bot.wordWarnCooldown[message.channel.id] = 0
                if self.bot.wordWarnCooldown[message.channel.id] < time.time():
                    await message.channel.send(f"Too many emojis! {message.author.mention}",delete_after=2)
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
            beforecontent = discord.utils.escape_markdown(before.content)
            aftercontent = discord.utils.escape_markdown(after.content)
            result = list(d.compare(beforecontent.split(), aftercontent.split()))
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
            content = message.content
            if len(content) > 1024:
                content = content[:1020] + "..."
            deleteEmbed.add_field(name=f"Message deleted from **{message.channel.name}**", value=content)
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
                role = functions.Sql.get_role(member.guild.id, casetype)
                try:
                    role = member.guild.get_role(role)
                    await member.add_roles(role)
                except:
                    pass
                
def setup(bot):
    bot.add_cog(AutoMod(bot))
