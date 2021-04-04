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
import cogs.fancyEmbeds as fEmbeds

#sets up SQLite
connection = sqlite3.connect("database.db")
cursor = connection.cursor()

async def word_filter_pre_invoke(self,ctx):
    inDb = cursor.execute("SELECT * FROM message_filter WHERE guild = ?", (ctx.guild.id,)).fetchone()
    if (inDb is None): # Guild filter doesn't exist
        cursor.execute("INSERT INTO message_filter(guild,enabled,filterWildCard,filterExact) VALUES(?,?,?,?)",(ctx.guild.id,1,"",""))
        connection.commit()
        await ctx.send("Word filter created and enabled.")
    return True

async def spam_filter_pre_invoke(self,ctx):
    inDb = cursor.execute("SELECT * FROM spam_filters WHERE guild = ?", (ctx.guild.id,)).fetchone()
    if (inDb is None): # Guild filter doesn't exist
        cursor.execute("INSERT INTO spam_filters(guild,emoji_limit,invite_filter,message_spam_limit,character_repeat_limit) VALUES(?,?,?,?,?)",(ctx.guild.id,-1,0,-1,-1))
        connection.commit()
        await ctx.send("Filter created and enabled.")
    return True

class AutoMod(commands.Cog):
    """Moderates chat and users automatically!"""
    
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.warnCooldown = {}

    @commands.group(aliases=["word_filter"])
    @commands.check(functions.has_modrole)
    @commands.before_invoke(word_filter_pre_invoke)
    async def wordFilter(self,ctx):
        """Modifies the server message word filter."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @wordFilter.group(name="set")
    async def wordFilter_set(self,ctx):
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
        new_filter = re.sub("[^\w ]|_","",new_filter)
        if new_filter.endswith(";"):
            new_filter = new_filter[:-1]
        if new_filter.startswith(";"):
            new_filter = new_filter[1:]
        return new_filter

    @wordFilter_set.command(name="wild",aliases=["wildcard"])
    async def wordFilter_set_wild(self,ctx,*,new_filter=None):
        """Sets the wildcard filter."""
        new_filter = await self.new_filter_format(ctx,new_filter)
        cursor.execute("UPDATE message_filter SET filterWildCard=? WHERE guild=?",(new_filter,ctx.guild.id))
        connection.commit()
        await ctx.send("Filter set.")

    @wordFilter_set.command(name="exact")
    async def wordFilter_set_exact(self,ctx,*,new_filter=None):
        """Sets the exact filter."""
        new_filter = await self.new_filter_format(ctx,new_filter)
        cursor.execute("UPDATE message_filter SET filterExact=? WHERE guild=?",(new_filter.replace(" ",""),ctx.guild.id))
        connection.commit()
        await ctx.send("Filter set.")

    @wordFilter.command(name="add")
    async def wordFilter_add(self,ctx,*words):
        """Adds specified words/phrases to filter.
        You can specify multiple words with spaces, to add something that includes a space you must encase it in ".
        To add a wildcard, prefix the word with `*`, for example `[p]filter add *mario luigi` would add mario to the wildcard filter and luigi to the exact.
        For example `[p]filter add "mario and luigi"` would filter `mario and luigi` only and not `mario`, `and` or `luigi` separately.
        Filter words must not contain characters other than letters or spaces and exact words cannot contain spaces."""
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
            word = re.sub("[^\w *]|_","",word)
            for w in word.split(";"):
                if len(word) == 1:
                    continue
                if word.startswith("*"):
                    wildFilter.append(word.replace("*",""))
                else:
                    exactFilter.append(word.replace(" ","").replace("*",""))
        wildFilter = ";".join(wildFilter)
        exactFilter = ";".join(exactFilter)
        cursor.execute("UPDATE message_filter SET filterWildCard=?, filterExact=? WHERE guild=?",(wildFilter,exactFilter,ctx.guild.id))
        connection.commit()
        await ctx.send("Added to filter.")

    @wordFilter.command(name="remove",aliases=["del","delete"])
    async def wordFilter_remove(self,ctx,*words):
        """Removes specified words/phrases from filter.
        You can specify multiple words with spaces, to remove something that includes a space you must encase it in ".
        To remove a wildcard, prefix the word with `*`, for example `[p]filter remove *mario luigi` would remove mario from the wildcard filter and luigi from the exact.
        For example `[p]filter add "mario and luigi"` would remove `mario and luigi`"""
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
        notFoundWords = []
        for word in words:
            if word.startswith("*"):
                try:
                    wildFilter.remove(word[1:])
                except:
                    notFoundWords.append(word)
            else:
                try:
                    exactFilter.remove(word)
                except:
                    notFoundWords.append(word)
        wildFilter = ";".join(wildFilter)
        exactFilter = ";".join(exactFilter)
        cursor.execute("UPDATE message_filter SET filterWildCard=?, filterExact=? WHERE guild=?",(wildFilter,exactFilter,ctx.guild.id))
        connection.commit()
        await ctx.send(f"Removed from filter. {'The following words were not found so not removed: ' if notFoundWords else ''}{' '.join(notFoundWords) if notFoundWords else ''}")
        
    @wordFilter.command(name="get",aliases=["list"])
    async def wordFilter_get(self,ctx):
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

    @wordFilter.command(name="toggle")
    async def wordFilter_toggle(self,ctx):
        """Toggles whether the filter is on or not."""
        enabled = cursor.execute("SELECT * FROM message_filter WHERE guild = ?",(ctx.guild.id,)).fetchone()[1]
        enabled = 1 if enabled == 0 else 0
        cursor.execute("UPDATE message_filter SET enabled=? WHERE guild=?",(enabled,ctx.guild.id))
        connection.commit()
        await ctx.send(f"Filter now {'enabled' if enabled == 1 else 'disabled'}.")

    @commands.group(name="spamFilter",aliases=["spam_filter"])
    @commands.check(functions.has_modrole)
    @commands.before_invoke(spam_filter_pre_invoke)
    async def spamFilter(self,ctx):
        """Set various filters to help reduce spam!"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @spamFilter.group(name="get",aliases=["list"])
    async def spamFilter_get(self,ctx):
        """Sends current values for the spam filters."""
        values = cursor.execute("SELECT * FROM spam_filters WHERE guild = ?",(ctx.guild.id,)).fetchone()
        if values:
            embed = discord.Embed(colour=discord.Colour.random(),title="Spam Filters:")
            embed.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)
            embed.add_field(name="Emoji Limit:", value=(values[1] if values[1] > -1 else 'disabled'))
            embed.add_field(name="Invite Filter:", value=('enabled' if values[2] == 1 else 'disabled'))
            embed.add_field(name="Message Spam Limit:", value=(values[3] if values[3] > -1 else 'disabled'))
            embed.add_field(name="Character Repeat Limit:", value=(values[4] if values[4] > -1 else 'disabled'))
            await ctx.send(embed=embed)

    @spamFilter.command(name="invites")
    async def spamFilter_invites(self,ctx):
        """Toggles if invites are filtered."""
        enabled = cursor.execute("SELECT invite_filter FROM spam_filters WHERE guild = ?",(ctx.guild.id,)).fetchone()[0]
        enabled = 1 if enabled == 0 else 0
        cursor.execute("UPDATE spam_filters SET invite_filter=? WHERE guild=?",(enabled,ctx.guild.id))
        connection.commit()
        await ctx.send(f"Invite filter now {'enabled' if enabled == 1 else 'disabled'}.")

    @spamFilter.command(name="emoji")
    async def spamFilter_emoji(self,ctx,limit:int=None):
        """Sets emoji limit. To remove, don't specify a limit."""
        if not limit:
            limit = -1
        cursor.execute("UPDATE spam_filters SET emoji_limit=? WHERE guild=?",(limit,ctx.guild.id))
        connection.commit()
        await ctx.send(f"Emoji limit now {limit if limit > -1 else 'disabled'}.")

    @spamFilter.command(name="messageLimit",aliases=["message_limit"])
    async def spamFilter_messageLimit(self,ctx,limit:int=None):
        """Sets the limit for messages sent within 5 seconds. To remove, don't specify a limit."""
        if not limit:
            limit = -1
        cursor.execute("UPDATE spam_filters SET message_spam_limit=? WHERE guild=?",(limit,ctx.guild.id))
        connection.commit()
        await ctx.send(f"Message limit now {limit if limit > -1 else 'disabled'}.")

    @spamFilter.command(name="repeatingLimit",aliases=["repeating_limit"])
    async def spamFilter_repeatingLimit(self,ctx,limit:int=None):
        """Sets the limit for repeating characters in a message. To remove don't specify a limit."""
        if not limit:
            limit = -1
        cursor.execute("UPDATE spam_filters SET character_repeat_limit=? WHERE guild=?",(limit,ctx.guild.id))
        connection.commit()
        await ctx.send(f"Character repeat limit now {limit if limit > -1 else 'disabled'}.")

    async def check_message(self,message):
        if message.author.bot:
            return
        if message.author.discriminator == "0000":
            return
        if isinstance(message.channel, discord.channel.DMChannel):
            return
        if functions.has_modrole(message) or functions.has_adminrole(message):
            return
        guildFilter = cursor.execute("SELECT * FROM message_filter WHERE guild = ?",(message.guild.id,)).fetchone() # Bad words.
        if not guildFilter:
            return
        if guildFilter[1] == 1:
            bannedWilds = guildFilter[2].split(";")
            bannedExacts = guildFilter[3].split(";")
            formatted_content = re.sub("[^\w ]|_", "", message.content)
            spaceless_content = re.sub("[^\w]|_", "", message.content)
            if "" in bannedWilds:
                bannedWilds.remove("")
            if "" in bannedExacts:
                bannedExacts.remove("")
            if " " in formatted_content.lower():
                words = formatted_content.split(" ")
            else:
                words = [formatted_content]
            if (any(bannedWord in spaceless_content.lower() for bannedWord in bannedWilds) or any(bannedWord in words for bannedWord in bannedExacts)):
                await message.delete()
                if message.channel.id not in self.warnCooldown:
                    self.warnCooldown[message.channel.id] = 0
                if self.warnCooldown[message.channel.id] < time.time():
                    await message.channel.send(f"Watch your language {message.author.mention}",delete_after=2)
                self.warnCooldown[message.channel.id] = time.time()+2
        spamFilters = cursor.execute("SELECT * FROM spam_filters WHERE guild = ?",(message.guild.id,)).fetchone()
        if spamFilters:
            if spamFilters[1] > -1: # emoji limit enabled
                unicodeCheck = re.compile('[\U00010000-\U0010ffff]', flags=re.UNICODE)
                customCheck = r'<:\w*:\d*>'
                emojis = len(re.findall(unicodeCheck,message.content))
                emojis += len(re.findall(customCheck,message.content))
                if emojis > spamFilters[1]: # over the number of emojis the guild allows
                    await message.delete()
                    if message.channel.id not in self.warnCooldown:
                        self.warnCooldown[message.channel.id] = 0
                    if self.warnCooldown[message.channel.id] < time.time():
                        await message.channel.send(f"Too many emojis! {message.author.mention}",delete_after=2)
                    self.warnCooldown[message.channel.id] = time.time()+2
            if spamFilters[2] == 1: # invite censorship enabled:
                if re.search(r"discord.gg/\S|discord.com/invite/\S|discordapp.com/invite/\S",message.content):
                    await message.delete()
                    if message.channel.id not in self.warnCooldown:
                        self.warnCooldown[message.channel.id] = 0
                    if self.warnCooldown[message.channel.id] < time.time():
                        await message.channel.send(f"No invite links {message.author.mention}",delete_after=2)
                    self.warnCooldown[message.channel.id] = time.time()+2
            if spamFilters[3] > -1: # message spam limit
                fiveSecondsAgo = datetime.datetime.utcnow() - datetime.timedelta(seconds=5)
                userMessages = [msg for msg in self.bot.cached_messages if msg.author == message.author and msg.created_at >= fiveSecondsAgo]
                if len(userMessages) >= spamFilters[3]:
                    await message.channel.delete_messages(userMessages)
                    if message.channel.id not in self.warnCooldown:
                        self.warnCooldown[message.channel.id] = 0
                    if self.warnCooldown[message.channel.id] < time.time():
                        await message.channel.send(f"No spamming {message.author.mention}",delete_after=2)
                    self.warnCooldown[message.channel.id] = time.time()+2
            if spamFilters[4] > -1:
                if re.search(f"(.*.)(?=.*\\1{{{str(spamFilters[4]-1)},}})",message.content):
                    await message.delete()
                    if message.channel.id not in self.warnCooldown:
                        self.warnCooldown[message.channel.id] = 0
                    if self.warnCooldown[message.channel.id] < time.time():
                        await message.channel.send(f"No spamming {message.author.mention}",delete_after=2)
                    self.warnCooldown[message.channel.id] = time.time()+2

    @commands.Cog.listener()
    async def on_message(self,message):
        await self.check_message(message)

    @commands.Cog.listener()
    async def on_message_edit(self,before, after):
        await self.check_message(after)
        if isinstance(after.channel, discord.channel.DMChannel):
            return

        style = fEmbeds.fancyEmbeds.getActiveStyle(self)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, style, "emoji")

        if emoji == False:
            emojia = ""
        else:
            emojia = ":memo: "

        logID = cursor.execute("SELECT modlogs from role_ids WHERE guild = ?",(after.guild.id,)).fetchone()

        if after.author.bot:
            return
        if not logID[0]:
            return
        channel = after.guild.get_channel(logID[0])

        editEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, embTitle=f"{emojia}Message edited in {after.channel.name}", useColor=3)
        editEmbed.set_author(name=str(after.author), icon_url=after.author.avatar_url)

        #difference
        d = difflib.Differ()
        beforecontent = discord.utils.escape_markdown(before.content)
        aftercontent = discord.utils.escape_markdown(after.content)
        result = list(d.compare(beforecontent.split(), aftercontent.split()))

        start = []
        end = []

        for i in range(len(result)):
            if result[i].startswith("- "):
                start.append("~~" + result[i][2:] + "~~")
            elif result[i].startswith("+ "):
                end.append("*" + result[i][2:] + "*")
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
        
        await channel.send(embed=editEmbed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):

        style = fEmbeds.fancyEmbeds.getActiveStyle(self)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, style, "emoji")

        if emoji == False:
            emojia = ""
        else:
            emojia = ":wastebasket: "

        logID = cursor.execute("SELECT modlogs from role_ids WHERE guild = ?",(message.guild.id,)).fetchone()
        if logID and logID != 0 and not message.author.bot:
            channel = message.guild.get_channel(logID[0])
            content = message.content
            if len(content) > 1024:
                content = content[:1020] + "..."

            deleteEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, embTitle=f"{emojia}Message deleted from **{message.channel.name}**", desc=content, force=True, forceColor=0xff0000)
            deleteEmbed.set_author(name=str(message.author), icon_url=message.author.avatar_url)

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
