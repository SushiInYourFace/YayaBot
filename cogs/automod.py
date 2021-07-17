import asyncio
import datetime
import difflib
import io
import re
import time

import aiohttp
import discord
from discord.ext import commands

import cogs.fancyEmbeds as fEmbeds
import functions


async def word_filter_pre_invoke(self,ctx):
    async with ctx.bot.connection.execute("SELECT * FROM message_filter WHERE guild = ?", (ctx.guild.id,)) as cursor:
        inDb = await cursor.fetchone()
        if inDb is None: # Guild filter doesn't exist
            await cursor.execute("INSERT INTO message_filter(guild,enabled,filterWildCard,filterExact) VALUES(?,?,?,?)",(ctx.guild.id,1,"",""))
            await ctx.bot.connection.commit()
            await ctx.send("Word filter created and enabled.")
        return True

async def spam_filter_pre_invoke(self,ctx):
    async with ctx.bot.connection.execute("SELECT * FROM message_filter WHERE guild = ?", (ctx.guild.id,)) as cursor:
        inDb = await cursor.fetchone()
        if inDb is None: # Guild filter doesn't exist
            await cursor.execute("INSERT INTO spam_filters(guild,emoji_limit,invite_filter,message_spam_limit,character_repeat_limit) VALUES(?,?,?,?,?)",(ctx.guild.id,-1,0,-1,-1))
            await ctx.bot.connection.commit()
            await ctx.send("Filter created and enabled.")
        return True

class AutoMod(commands.Cog):
    """Moderates chat and users automatically!"""

    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.warnCooldown = {}
        self.connection = bot.connection

    @commands.group(aliases=["word_filter"], brief=":abcd: ")
    @commands.check(functions.has_modrole)
    @commands.before_invoke(word_filter_pre_invoke)
    async def wordFilter(self,ctx):
        """Modifies the server message word filter."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @wordFilter.group(name="set", brief=":pencil2: ")
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
        new_filter = re.sub(r"[^\w ]|_","",new_filter)
        if new_filter.endswith(";"):
            new_filter = new_filter[:-1]
        if new_filter.startswith(";"):
            new_filter = new_filter[1:]
        return new_filter

    @wordFilter_set.command(name="wild",aliases=["wildcard"], brief=":fountain_pen: ")
    async def wordFilter_set_wild(self,ctx,*,new_filter=None):
        """Sets the wildcard filter."""
        new_filter = await self.new_filter_format(ctx,new_filter)
        await self.connection.execute("UPDATE message_filter SET filterWildCard=? WHERE guild=?",(new_filter,ctx.guild.id))
        await self.connection.commit()
        await ctx.send("Filter set.")
        async with self.connection.execute("SELECT * from message_filter WHERE guild=?",(ctx.guild.id,)) as cursor:
            current_filter = await cursor.fetchone()
            functions.update_filter(self.bot, current_filter)

    @wordFilter_set.command(name="exact", brief=":ballpoint_pen: ")
    async def wordFilter_set_exact(self,ctx,*,new_filter=None):
        """Sets the exact filter."""
        new_filter = await self.new_filter_format(ctx,new_filter)
        await self.connection.execute("UPDATE message_filter SET filterExact=? WHERE guild=?",(new_filter.replace(" ",""),ctx.guild.id))
        await self.connection.commit()
        await ctx.send("Filter set.")
        cursor = await self.connection.execute("SELECT * from message_filter WHERE guild=?",(ctx.guild.id,)).fetchone()
        current_filter = await cursor.fetchone()
        await cursor.close()
        functions.update_filter(self.bot, current_filter)

    @wordFilter.command(name="add", brief=":pencil: ")
    async def wordFilter_add(self,ctx,*words):
        """Adds specified words/phrases to filter.
        You can specify multiple words with spaces, to add something that includes a space you must encase it in ".
        To add a wildcard, prefix the word with `*`, for example `[p]filter add *mario luigi` would add mario to the wildcard filter and luigi to the exact.
        For example `[p]filter add "mario and luigi"` would filter `mario and luigi` only and not `mario`, `and` or `luigi` separately.
        Filter words must not contain characters other than letters or spaces and exact words cannot contain spaces."""
        cursor = await self.connection.cursor()
        guildFilter = await cursor.execute("SELECT * FROM message_filter WHERE guild = ?",(ctx.guild.id,))
        guildFilter = await guildFilter.fetchone()
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
            word = re.sub(r"[^\w *]|_","",word)
            for w in word.split(";"):
                if len(word) == 1:
                    continue
                if w.startswith("*"):
                    wildFilter.append(w.replace("*",""))
                else:
                    exactFilter.append(w.replace(" ","").replace("*",""))
        wildFilter = ";".join(wildFilter)
        exactFilter = ";".join(exactFilter)
        await cursor.execute("UPDATE message_filter SET filterWildCard=?, filterExact=? WHERE guild=?",(wildFilter,exactFilter,ctx.guild.id))
        await self.connection.commit()
        current_filter = await cursor.execute("SELECT * from message_filter WHERE guild=?",(ctx.guild.id,))
        current_filter = await current_filter.fetchone()
        await cursor.close()
        functions.update_filter(self.bot, current_filter)
        await ctx.send("Added to filter.")

    @wordFilter.command(name="remove",aliases=["del","delete"], brief=":x: ")
    async def wordFilter_remove(self,ctx,*words):
        """Removes specified words/phrases from filter.
        You can specify multiple words with spaces, to remove something that includes a space you must encase it in ".
        To remove a wildcard, prefix the word with `*`, for example `[p]filter remove *mario luigi` would remove mario from the wildcard filter and luigi from the exact.
        For example `[p]filter add "mario and luigi"` would remove `mario and luigi`"""
        cursor = await self.connection.cursor()
        guildFilter = await cursor.execute("SELECT * FROM message_filter WHERE guild = ?",(ctx.guild.id,))
        guildFilter = await cursor.fetchone()
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
        await cursor.execute("UPDATE message_filter SET filterWildCard=?, filterExact=? WHERE guild=?",(wildFilter,exactFilter,ctx.guild.id))
        await self.connection.commit()
        current_filter = await cursor.execute("SELECT * from message_filter WHERE guild=?",(ctx.guild.id,))
        current_filter = await current_filter.fetchone()
        await cursor.close()
        functions.update_filter(self.bot, current_filter)
        await ctx.send(f"Removed from filter. {'The following words were not found so not removed: ' if notFoundWords else ''}{' '.join(notFoundWords) if notFoundWords else ''}")

    @wordFilter.command(name="get",aliases=["list"], brief=":notepad_spiral: ")
    async def wordFilter_get(self,ctx):
        """Sends the filter.
        Usually sent as a message but is sent as a text file if it's over 2000 characters"""
        cursor = await self.connection.execute("SELECT * FROM message_filter WHERE guild = ?",(ctx.guild.id,))
        guildFilter = await cursor.fetchone()
        await cursor.close()
        text = f'Wildcard:\n{str(guildFilter[2])}\n\nExact:\n{str(guildFilter[3])}'
        if len(text) <= 1977:
            await ctx.send(f"Filter {'enabled' if guildFilter[1] == 1 else 'disabled'} ```{text}```")
        else:
            fp = io.StringIO(text)
            f = discord.File(fp,filename="filter.txt")
            await ctx.send("Filter is too large so is sent as a file:",file=f)

    @wordFilter.command(name="toggle", brief=":wrench: ")
    async def wordFilter_toggle(self,ctx):
        """Toggles whether the filter is on or not."""
        cursor = self.connection.cursor()
        enabled = await cursor.execute("SELECT * FROM message_filter WHERE guild = ?",(ctx.guild.id,))
        enabled = await enabled.fetchone()
        enabled = enabled[1]
        enabled = 1 if enabled == 0 else 0
        await cursor.execute("UPDATE message_filter SET enabled=? WHERE guild=?",(enabled,ctx.guild.id))
        await self.connection.commit()
        current_filter = await cursor.execute("SELECT * from message_filter WHERE guild=?",(ctx.guild.id,))
        current_filter = await current_filter.fetchone()
        await cursor.close()
        functions.update_filter(self.bot, current_filter)
        await ctx.send(f"Filter now {'enabled' if enabled == 1 else 'disabled'}.")

    @commands.group(name="spamFilter",aliases=["spam_filter"], brief=":loudspeaker: ")
    @commands.check(functions.has_modrole)
    @commands.before_invoke(spam_filter_pre_invoke)
    async def spamFilter(self,ctx):
        """Set various filters to help reduce spam!"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @spamFilter.group(name="get",aliases=["list"], brief=":notepad_spiral: ")
    async def spamFilter_get(self,ctx):
        """Sends current values for the spam filters."""
        cursor = await self.connection.execute("SELECT * FROM spam_filters WHERE guild = ?",(ctx.guild.id,))
        values = await cursor.fetchone()
        await cursor.close()

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        if emoji is False:
            emojia = ""
            emojib = ""
            emojic = ""
            emojid = ""
            emojie = ""
        else:
            emojia = ":x: "
            emojib = ":joy: "
            emojic = ":envelope: "
            emojid = ":speech_balloon: "
            emojie = ":repeat: "

        if values:
            embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Spam Filters:", useColor=2)
            embed.add_field(name=f"{emojib}Emoji Limit:", value=(values[1] if values[1] > -1 else 'disabled'))
            embed.add_field(name=f"{emojic}Invite Filter:", value=('enabled' if values[2] == 1 else 'disabled'))
            embed.add_field(name=f"{emojid}Message Spam Limit:", value=(values[3] if values[3] > -1 else 'disabled'))
            embed.add_field(name=f"{emojie}Character Repeat Limit:", value=(values[4] if values[4] > -1 else 'disabled'))

            await ctx.send(embed=embed)

    @spamFilter.command(name="invites", brief=":envelope: ")
    async def spamFilter_invites(self,ctx):
        """Toggles if invites are filtered."""
        cursor = await self.connection.cursor()
        enabled = await cursor.execute("SELECT invite_filter FROM spam_filters WHERE guild = ?",(ctx.guild.id,))
        enabled = await cursor.fetchone()
        enabled = enabled[0]
        enabled = 1 if enabled == 0 else 0
        await cursor.execute("UPDATE spam_filters SET invite_filter=? WHERE guild=?",(enabled,ctx.guild.id))
        await self.connection.commit()
        await cursor.close()
        await ctx.send(f"Invite filter now {'enabled' if enabled == 1 else 'disabled'}.")

    @spamFilter.command(name="emoji", brief=":slight_smile: ")
    async def spamFilter_emoji(self,ctx,limit:int=None):
        """Sets emoji limit. To remove, don't specify a limit."""
        if not limit:
            limit = -1
        cursor = await self.connection.cursor()
        await cursor.execute("UPDATE spam_filters SET emoji_limit=? WHERE guild=?",(limit,ctx.guild.id))
        await self.connection.commit()
        await cursor.close()
        await ctx.send(f"Emoji limit now {limit if limit > -1 else 'disabled'}.")

    @spamFilter.command(name="messageLimit",aliases=["message_limit"], brief=":speech_balloon: ")
    async def spamFilter_messageLimit(self,ctx,limit:int=None):
        """Sets the limit for messages sent within 5 seconds. To remove, don't specify a limit."""
        if not limit:
            limit = -1
        cursor = await self.connection.cursor()
        await cursor.execute("UPDATE spam_filters SET message_spam_limit=? WHERE guild=?",(limit,ctx.guild.id))
        await self.connection.commit()
        await cursor.close()
        await ctx.send(f"Message limit now {limit if limit > -1 else 'disabled'}.")

    @spamFilter.command(name="repeatingLimit",aliases=["repeating_limit"], brief=":repeat: ")
    async def spamFilter_repeatingLimit(self,ctx,limit:int=None):
        """Sets the limit for repeating characters in a message. To remove don't specify a limit."""
        if not limit:
            limit = -1
        cursor = await self.connection.cursor()
        await cursor.execute("UPDATE spam_filters SET character_repeat_limit=? WHERE guild=?",(limit,ctx.guild.id))
        await self.connection.commit()
        await cursor.close()
        await ctx.send(f"Character repeat limit now {limit if limit > -1 else 'disabled'}.")

    @commands.group(aliases=["name_filter"], brief=":name_badge: ")
    @commands.check(functions.has_modrole)
    async def nameFilter(self,ctx):
        """Modifies the name filter."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @nameFilter.command(name="toggle", brief=":wrench: ")
    async def nameFilter_toggle(self, ctx):
        "Toggles whether the name filter is enabled"
        cursor = await self.connection.cursor()
        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")
        prev_state = await SqlCommands.namefilter_enabled(ctx.guild.id)
        if prev_state is False:
            await cursor.execute("UPDATE name_filtering SET enabled= ? WHERE guild= ?",(1, ctx.guild.id))
            emojiA = ":white_check_mark:" if emoji else ""
            embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojiA}Name filtering enabled")
        elif prev_state is True:
            await cursor.execute("UPDATE name_filtering SET enabled= ? WHERE guild= ?",(1, ctx.guild.id))
            emojiA = ":regional_indicator_x:" if emoji else ""
            embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojiA}Name filtering disabled")
        await ctx.send(embed=embed)
        await self.connection.commit()
        await cursor.close()

    @nameFilter.command(name="setnames", brief=":pencil: ")
    async def nameFilter_setnames(self, ctx):
        "Sets a custom nickname to be used when a name is filtered"
        #fancy embeds
        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")
        failEmoji = ":x:" if emoji else ""
        filter_fail_embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{failEmoji}Cancelling", desc="That name fails your own filter. Kinda defeats the whole purpose, doesn't it?")
        too_long_embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{failEmoji}Cancelling", desc="That name is too long! Discord only allows nicknames 32 charactes in length or shorter")

        #used to make sure custom nickname follows guild filter (preventing an infinite loop) and doesn't exceed character limit
        def valid_nick(nick):
            if functions.filter_check(self.bot, nick, ctx.guild.id):
                return "failed filter"
            elif len(nick) > 32:
                return "too long"
            else:
                return "valid"
        #used to get responses
        async def get_message():
            try:
                message = await self.bot.wait_for('message', timeout=60.0, check=check)
                return message
            except asyncio.TimeoutError:
                await ctx.send("No response received. Cancelling")
                return
        def check(response):
            return response.channel == ctx.channel and response.author == ctx.author
        #actually getting user input now
        await ctx.send("What would you like people with a filtered nickname to be renamed to?")
        custom_nick = await get_message()
        custom_nick = custom_nick.content
        is_valid = valid_nick(custom_nick)
        if is_valid != "valid":
            if is_valid == "failed filter":
                await ctx.send(embed=filter_fail_embed)
                return
            elif is_valid == "too long":
                await ctx.send(embed=too_long_embed)
                return
            else:
                await ctx.send("Error! Please contact sushiinyourface if this persists") #this should never happen
                return
        await ctx.send("Sounds good! Now, what do you want to have people with a filtered username renamed to?")
        custom_username = await get_message()
        custom_username = custom_username.content
        is_valid = valid_nick(custom_username)
        if is_valid != "valid":
            if is_valid == "failed filter":
                await ctx.send(embed=filter_fail_embed)
                return
            elif is_valid == "too long":
                await ctx.send(embed=too_long_embed)
                return
            else:
                await ctx.send("Error! Please contact sushiinyourface if this persists") #this should never happen
                return
        cursor = await self.connection.cursor()
        await cursor.execute("INSERT INTO custom_names(guild,nickname,username) VALUES(?,?,?) ON CONFLICT(guild) DO UPDATE SET nickname=excluded.nickname, username=excluded.username", (ctx.guild.id, custom_nick, custom_username))
        await self.connection.commit()
        await cursor.close()
        success_emoji = ":white_check_mark:" if emoji else ""
        success_embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{success_emoji}Done!", desc=f"Bad Nicknames = {custom_nick} \nBad Usernames = {custom_username}")
        await ctx.send(embed=success_embed)


    async def check_message(self,message):
        if message.author.bot:
            return
        if message.author.discriminator == "0000":
            return
        if isinstance(message.channel, discord.channel.DMChannel):
            return
        if functions.has_modrole(message, self.bot) or functions.has_adminrole(message, self.bot):
            return
        if message.guild.id not in self.bot.guild_filters:
            return
        if not self.bot.guild_filters[message.guild.id].enabled:
            return
        should_delete = False
        guild_filter = self.bot.guild_filters[message.guild.id]
        formatted_content = re.sub(r"[^\w ]|_", "", message.content).lower()
        spaceless_content = re.sub(r"[^\w]|_", "", message.content)
        if guild_filter.wildcard:
            if guild_filter.wildcard.search(spaceless_content):
                should_delete = True
        if guild_filter.exact:
            if guild_filter.exact.search(formatted_content):
                should_delete = True
        if should_delete:
            await message.delete()
            if message.channel.id not in self.warnCooldown:
                self.warnCooldown[message.channel.id] = 0
            if self.warnCooldown[message.channel.id] < time.time():
                await message.channel.send(f"Watch your language {message.author.mention}",delete_after=2)
            self.warnCooldown[message.channel.id] = time.time()+2
        cursor = await self.connection.cursor()
        spamFilters = await cursor.execute("SELECT * FROM spam_filters WHERE guild = ?",(message.guild.id,))
        spamFilters = await spamFilters.fetchone()
        await cursor.close()
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

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, after.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, after.guild.id, style, "emoji")

        if emoji is False:
            emojia = ""
        else:
            emojia = ":memo: "
        cursor = await self.connection.execute("SELECT modlogs from role_ids WHERE guild = ?",(after.guild.id,))
        logID = await cursor.fetchone()
        await cursor.close()

        if after.author.bot:
            return
        if not logID:
            return
        if not logID[0]:
            return
        channel = after.guild.get_channel(logID[0])

        editEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, after.guild.id, embTitle=f"{emojia}Message edited in {after.channel.name}", useColor=3)
        editEmbed.set_author(name=str(after.author), icon_url=after.author.avatar.url)

        #difference
        d = difflib.Differ()
        beforecontent = discord.utils.escape_markdown(before.content)
        aftercontent = discord.utils.escape_markdown(after.content)
        result = list(d.compare(beforecontent.split(), aftercontent.split()))

        start = []
        end = []

        for i in enumerate(result):
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
        for i in enumerate(start):
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

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, message.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, message.guild.id, style, "emoji")

        if emoji is False:
            emojia = ""
        else:
            emojia = ":wastebasket: "

        cursor = await self.connection.execute("SELECT modlogs from role_ids WHERE guild = ?",(message.guild.id,))
        logID = await cursor.fetchone()
        await cursor.close()
        if logID and logID != 0 and not message.author.bot:
            channel = message.guild.get_channel(logID[0])
            content = message.content
            if len(content) > 1024:
                content = content[:1020] + "..."

            deleteEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, message.guild.id, embTitle=f"{emojia}Message deleted from **{message.channel.name}**", desc=content, force=True, forceColor=0xff0000)
            deleteEmbed.set_author(name=str(message.author), icon_url=message.author.avatar.url)

            await channel.send(embed=deleteEmbed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        #checks if username is appropriate
        if not await SqlCommands.namefilter_enabled(member.guild.id):
            return
        if functions.filter_check(self.bot, member.display_name, member.guild.id):
            try:
                new_name = await SqlCommands.get_new_nick(member.guild.id, "username")
                await member.edit(nick=new_name)
            except discord.errors.Forbidden:
                pass

        #Role Persists
        cursor = await self.connection.cursor()
        cases = await cursor.execute("SELECT id, type FROM caselog WHERE guild = ? AND user = ? AND expires >= ?", (member.guild.id, member.id, time.time(),))
        cases = await cases.fetchall()
        await cursor.close()
        persists = ""
        if cases is not None:
            #iterate through cases in case the user is both muted and graveled
            for case in cases:
                if case[1] == "mute":
                    casetype = "muted"
                    persists = persists + "m"
                elif case[1] == "gravel":
                    casetype = "gravel"
                    persists = persists + "g"
                else:
                    #sanity check
                    continue
                role = await SqlCommands.get_role(self, member.guild.id, casetype)
                try:
                    role = member.guild.get_role(role)
                    await member.add_roles(role)
                except:
                    pass

        #Join Logging
        cursor = await self.connection.execute("SELECT modlogs from role_ids WHERE guild = ?",(member.guild.id,))
        logID = await cursor.fetchone()
        await cursor.close()

        if logID and logID != 0:

            channel = member.guild.get_channel(logID[0])
            created = member.created_at
            timestamp = created.strftime("%Y-%m-%d, %H:%M:%S")
            url = member.avatar.url

            title=f"User Joined: {member.name}"
            desc=f"Account created: {timestamp}"

            if len(persists) > 0:
                if len(persists) == 2:
                    desc=f"{desc}\nThis member was previously **muted** and **graveled**, so these roles have been reapplied."
                elif persists == "m":
                    desc=f"{desc}\nThis member was previously **muted**, so their mute has been reapplied."
                elif persists == "g":
                    desc=f"{desc}\nThis member was previously **graveled**, so their gravel has been reapplied."

            embed = fEmbeds.fancyEmbeds.makeEmbed(self, member.guild.id, embTitle=title, desc=desc, force=True, forceColor=0x00ff00)
            embed.set_thumbnail(url=url)

            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_leave(self, member):

        #Leave Logging
        cursor = await self.connection.execute("SELECT modlogs from role_ids WHERE guild = ?",(member.guild.id,))
        logID = await cursor.fetchone()
        await cursor.close()

        if logID and logID != 0:

            channel = member.guild.get_channel(logID[0])
            url = member.avatar.url

            embed = fEmbeds.fancyEmbeds.makeEmbed(self, member.guild.id, embTitle=f"User Left: {member.name}", force=True, forceColor=0xff0000)
            embed.set_thumbnail(url=url)

            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        #Checks if member has an appropriate nick when they update it
        if not await SqlCommands.namefilter_enabled(after.guild.id):
            return
        if functions.filter_check(self.bot, after.display_name, after.guild.id):
            try:
                new_name = await SqlCommands.get_new_nick(after.guild.id, "nickname")
                await after.edit(nick=new_name)

                member = after

                cursor = await self.connection.execute("SELECT modlogs from role_ids WHERE guild = ?",(after.guild.id,))
                logID = await cursor.fetchone()
                await cursor.close()

                if logID and logID != 0:

                    channel = member.guild.get_channel(logID[0])
                    title = f"Member Renamed: {member.name}"
                    desc = "Reason: Inappropriate nickname - Automod"
                    url = member.avatar.url

                    embed = fEmbeds.fancyEmbeds.makeEmbed(self, after.guild.id, embTitle=title, desc=desc, useColor=1)
                    embed.set_thumbnail(url=url)

                    await channel.send(embed=embed)

            except discord.errors.Forbidden:
                pass


    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        #fires when someone updates their username, and makes sure it's appropriate
        for guild in after.mutual_guilds:
            member = guild.get_member(after.id)
            if not await SqlCommands.namefilter_enabled(guild.id):
                continue
            if not member.nick and functions.filter_check(self.bot, member.display_name, member.guild.id):
                try:
                    new_name = await SqlCommands.get_new_nick(after.guild.id, "username")
                    await after.edit(nick=new_name)

                    cursor = await self.connection.execute("SELECT modlogs from role_ids WHERE guild = ?",(after.guild.id,))
                    logID = await cursor.fetchone()
                    await cursor.close()
                    if logID and logID != 0:

                        channel = member.guild.get_channel(logID[0])
                        title = f"Member Renamed: {member.name}"
                        desc = "Reason: Inappropriate username - Automod"
                        url = member.avatar.url

                        embed = fEmbeds.fancyEmbeds.makeEmbed(self, member.guild.id, embTitle=title, desc=desc, useColor=1)
                        embed.set_thumbnail(url=url)

                        await channel.send(embed=embed)

                except discord.errors.Forbidden:
                    pass

SqlCommands = None

def setup(bot):
    global SqlCommands
    bot.add_cog(AutoMod(bot))
    SqlCommands = functions.Sql(bot)
