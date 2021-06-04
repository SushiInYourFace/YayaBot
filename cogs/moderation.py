import datetime
import io
import json
import sqlite3
import time
import logging

import discord
from discord import errors
from discord.ext import commands, tasks

import functions
import cogs.fancyEmbeds as fEmbeds

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

    @commands.group(help="Purge command.", brief=":x: ")
    @commands.check(functions.has_modrole)
    async def purge(self,ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    #purge command
    @purge.command(help="Purges a specified amount of messages from the chat",name="number",aliases=["n"], brief=":1234: ")
    async def purge_number(self, ctx, arg:int):
        arg += 1 # adding one to ignore the command invoking message
        await ctx.channel.purge(limit=arg)
    
    #purge match command, only purges messages that contain a certain string
    @purge.command(help="Purges messages containing a certain string", name="match", aliases=["m"], brief=":abcd: ")
    async def purge_match(self, ctx, limit:int, *, filtered):
        limit += 1
        def filter_check(message):
            return filtered in message.content
        await ctx.channel.purge(limit=limit, check=filter_check)

    #ban
    @commands.command(help="bans a user", brief=":hammer: ")
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

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        if emoji == False:
            emojia = ""
            emojib = ""
            emojic = ""
            emojid = ""
        else:
            emojia = ":no_entry_sign: "
            emojib = ":hammer: "
            emojic = ":cop: "
            emojid = ":scroll: "

        bantime = time.time()
        
        banEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}You have been banned from "+ ctx.guild.name, force=True, forceColor=0xff0000)
        banEmbed.add_field(name="Ban reason: ", value=reason)
        try:
            await member.send(embed=banEmbed)
            unsent = False
        except errors.HTTPException:
            unsent = True
        
        if unsent:
            successEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojib}Banned " + str(member), force=True, forceColor=0x00ff00, desc="Failed to send a message to the user.")
        else:
            successEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojib}Banned " + str(member), force=True, forceColor=0x00ff00)
            
        await ctx.send(embed=successEmbed)

        SqlCommands.new_case(member.id, ctx.guild.id, "ban", reason, bantime, -1, str(ctx.author))

        logID = cursor.execute("SELECT modlogs from role_ids WHERE guild = ?",(member.guild.id,)).fetchone()
        
        if logID and logID != 0:

            channel = member.guild.get_channel(logID[0])

            title = f"{emojib}User Banned: {member.name}"
            desc = f"{emojic}Responsible Moderator: {ctx.author.name}\n{emojid}Reason: {reason}"
            url = member.avatar_url

            embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=title, desc=desc, useColor=2)
            embed.set_thumbnail(url=url)

            await channel.send(embed=embed)

    @commands.command(help="kicks a user", brief=":boot: ")
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

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        if emoji == False:
            emojia = ""
            emojib = ""
            emojic = ""
        else:
            emojia = ":boot: "
            emojib = ":cop: "
            emojic = ":scroll: "
            
        kicktime = time.time()

        kickEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}You have been kicked from "+ ctx.guild.name, force=True, forceColor=0xff0000)
        kickEmbed.add_field(name="Kick reason:", value=reason)

        await ctx.guild.kick(member, reason=reason)
        try:
            await member.send(embed=kickEmbed)
            unsent = False
        except errors.HTTPException:
            unsent = True
        
        if unsent:
            successEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Kicked " + str(member), force=True, forceColor=0x00ff00, desc="Failed to send a message to the user.")
        else:
            successEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Kicked " + str(member), force=True, forceColor=0x00ff00)

        await ctx.send(embed=successEmbed)

        SqlCommands.new_case(member.id, ctx.guild.id, "kick", reason, kicktime, -1, str(ctx.author))

        logID = cursor.execute("SELECT modlogs from role_ids WHERE guild = ?",(member.guild.id,)).fetchone()
        
        if logID and logID != 0:

            channel = member.guild.get_channel(logID[0])

            title = f"{emojia}User Kicked: {member.name}"
            desc = f"{emojib}Responsible Moderator: {ctx.author.name}\n{emojic}Reason: {reason}"
            url = member.avatar_url

            embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=title, desc=desc, useColor=2)
            embed.set_thumbnail(url=url)

            await channel.send(embed=embed)

    #unban
    @commands.command(help="unbans a user", brief=":key: ")
    @commands.check(functions.has_modrole)
    async def unban(self, ctx, user : discord.User):
        unbanTime = time.time()

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        if emoji == False:
            emojia = ""
            emojib = ""
            emojic = ""
        else:
            emojia = ":x: "
            emojib = ":white_check_mark: "
            emojic = ":cop: "

        try:
            await ctx.guild.fetch_ban(user)
        except discord.NotFound:
            notBannedEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}This user is not banned.", useColor=2)
            await ctx.send(embed = notBannedEmbed)
            return

        await ctx.guild.unban(user)

        successEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojib}Unbanned " + str(user), useColor=3, force=True, forceColor=0x00ff00)

        await ctx.send(embed=successEmbed)

        SqlCommands.new_case(user.id, ctx.guild.id, "unban", "N/A", unbanTime, -1, str(ctx.author))

        logID = cursor.execute("SELECT modlogs from role_ids WHERE guild = ?",(member.guild.id,)).fetchone()

        if logID and logID != 0:

            channel = member.guild.get_channel(logID[0])

            title = f"{emojia}User Unbanned: {member.name}"
            desc = f"{emojic}Responsible Moderator: {ctx.author.name}"
            url = member.avatar_url

            embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=title, desc=desc, useColor=1)
            embed.set_thumbnail(url=url)

            await channel.send(embed=embed)

    #gravel
    @commands.command(help="Gravels a user", brief=":mute: ")
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

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        if emoji == False:
            emojia = ""
            emojib = ""
            emojic = ""
            emojid = ""
        else:
            emojia = ":mute: "
            emojib = ":white_check_mark: "
            emojic = ":cop: "
            emojid = ":scroll: "

        gravelEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}You have been graveled in {ctx.guild.name} for {TimeConversions.fromseconds(totalsecs)}", force=True, forceColor=0xff0000)
        gravelEmbed.add_field(name="Reason:", value=reason)

        try:
            await member.send(embed=gravelEmbed)
            unsent = False
        except errors.HTTPException:
            unsent = True

        SqlCommands.new_case(member.id, ctx.guild.id, "gravel", reason, now, end, str(ctx.author))

        if unsent:
            successEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle="Gravelled " + str(member), desc="Failed to send a message to the user.",  useColor=1)
        else:
            successEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle="Gravelled " + str(member), useColor=1)

        await ctx.send(embed=successEmbed)

        logID = cursor.execute("SELECT modlogs from role_ids WHERE guild = ?",(member.guild.id,)).fetchone()

        if logID and logID != 0:

            channel = member.guild.get_channel(logID[0])

            title = f"{emojia}User Gravelled: {member.name}"
            desc = f"{emojic}Responsible Moderator: {ctx.author.name}\n{emojid}Reason: {reason}"
            url = member.avatar_url

            embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=title, desc=desc, useColor=2)
            embed.set_thumbnail(url=url)

            await channel.send(embed=embed)

    @commands.command(help="Mutes a user", brief=":mute: ")
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

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        if emoji == False:
            emojia = ""
            emojib = ""
            emojic = ""
        else:
            emojia = ":mute: "
            emojib = ":white_check_mark: "
            emojic = ":cop: "

        muteEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}You have been muted in {ctx.guild.name} for {TimeConversions.fromseconds(totalsecs)}.", force=True, forceColor=0xFF0000)

        muteEmbed.add_field(name="Reason:", value=reason)
        
        try:
            await member.send(embed=muteEmbed)
            unsent = False
        except errors.HTTPException:
            unsent = True

        SqlCommands.new_case(member.id, ctx.guild.id, "mute", reason, now, end, str(ctx.author))

        if unsent:
            successEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojib}Muted " + str(member), desc="Failed to send a message to the user.", useColor=1)
        else:
            successEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojib}Muted " + str(member), useColor=1)

        await ctx.send(embed=successEmbed)

        logID = cursor.execute("SELECT modlogs from role_ids WHERE guild = ?",(member.guild.id,)).fetchone()

        if logID and logID != 0:

            channel = member.guild.get_channel(logID[0])

            title = f"{emojia}User Muted: {member.name}"
            desc = f"{emojic}Responsible Moderator: {ctx.author.name}\nReason: {reason}"
            url = member.avatar_url

            embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=title, desc=desc, useColor=2)
            embed.set_thumbnail(url=url)

            await channel.send(embed=embed)

    @commands.command(help="warns a user", brief=":warning: ")
    @commands.check(functions.has_modrole)
    async def warn(self, ctx, member : discord.Member, *, reason):

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        if emoji == False:
            emojia = ""
            emojib = ""
            emojic = ""
            emojid = ""
            emojie = ""
        else:
            emojia = ":exclamation: "
            emojib = ":white_check_mark: "
            emojic = ":notepad_spiral: "
            emojid = ":cop: "
            emojie = ":scroll: "

        warnEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}You have been warned in {ctx.guild.name}", force=True, forceColor=0xff0000)
        warnEmbed.add_field(name="Reason:", value=reason)

        SqlCommands.new_case(member.id, ctx.guild.id, "warn", reason, time.time(), -1, str(ctx.author))

        try:
            await member.send(embed=warnEmbed)
            successEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojib}Successfully warned {str(member)}", force=True, forceColor=0x00ff00)
            await ctx.send(embed=successEmbed)
        except errors.HTTPException:
            failEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojic}Logged a warning for user {str(member)}", desc="Failed to send a message to the user.", force=True, forceColor=0x00ff00)
            await ctx.send(embed=failEmbed)

        logID = cursor.execute("SELECT modlogs from role_ids WHERE guild = ?",(member.guild.id,)).fetchone()
        
        if logID and logID != 0:

            channel = member.guild.get_channel(logID[0])

            title = f"{emojia}User Warned: {member.name}"
            desc = f"{emojid}Responsible Moderator: {ctx.author.name}\n{emojie}Reason: {reason}"
            url = member.avatar_url

            embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=title, desc=desc, useColor=2)
            embed.set_thumbnail(url=url)

            await channel.send(embed=embed)

    @commands.command(help="Shows a user's modlogs", brief=":file_folder: ")
    @commands.check(functions.has_modrole)
    async def modlogs(self, ctx, member : discord.User):

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        if emoji == False:
            emojia = ""
            emojib = ""
            emojic = ""
            emojid = ""
            emojie = ""
            emojif = ""
            emojig = ""
        else:
            emojia = ":open_file_folder: "
            emojib = ":notepad_spiral: "
            emojic = ":page_facing_up: "
            emojid = ":pencil2: "
            emojie = ":clock3: "
            emojif = ":stopwatch: "
            emojig = ":cop: "

        logEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}{str(member)}'s Modlogs", useColor=1)

        logs = cursor.execute("SELECT id_in_guild, guild, user, type, reason, started, expires, moderator FROM caselog WHERE user = ? AND guild = ?", (member.id, ctx.guild.id)).fetchall()

        for log in logs:
            start = datetime.datetime.fromtimestamp(int(log[5])).strftime('%Y-%m-%d %H:%M:%S')
            if int(log[6]) != -1:
                totaltime = TimeConversions.fromseconds(int(int(log[6])) - int(log[5]))
            else:
                totaltime = "N/A"

            logEmbed.add_field(name=f"{emojib}__**Case " + str(log[0]) + "**__", value=f"{emojic}**Type- **" + log[3] + f"\n{emojid}**Reason- **" + log[4] + f"\n{emojie}**Time- **" + start + f"\n{emojif}**Length- **" + totaltime + f"\n{emojig}**Moderator- **" + log[7], inline=True)
        
        logEmbed.set_thumbnail(url=member.avatar_url)

        await ctx.send(embed = logEmbed)

    @commands.command(help="Shows information on a case", brief=":notepad_spiral: ")
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

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        if emoji == False:
            emojia = ""
            emojib = ""
            emojic = ""
            emojid = ""
            emojie = ""
            emojif = ""
        else:
            emojia = ":notepad_spiral: "
            emojib = ":page_facing_up: "
            emojic = ":pencil2: "
            emojid = ":clock3: "
            emojie = ":stopwatch: "
            emojif = ":cop: "

        logEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Case {str(case)}", useColor=3)

        user = await self.bot.fetch_user(caseinfo[2])

        logEmbed.add_field(name=user, value=f"{emojib}**Type- **" + caseinfo[3] + f"\n{emojic}**Reason- **" + caseinfo[4] + f"\n{emojid}**Time- **" + start + f"\n{emojie}**Length- **" + totaltime + f"\n{emojif}**Moderator- **" + caseinfo[7], inline=True)
        logEmbed.set_thumbnail(url=user.avatar_url)

        await ctx.send(embed = logEmbed)

    @commands.command(help="Unmutes a User", brief=":sound: ")
    @commands.check(functions.has_modrole)
    async def unmute(self, ctx, member : discord.Member):
        mod = str(ctx.author)
        unmutetime = time.time()
        muted = SqlCommands.get_role(ctx.guild.id, "muted")
        mutedRole = ctx.guild.get_role(muted)
        await member.remove_roles(mutedRole,)

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        if emoji == False:
            emojia = ""
            emojib = ""
        else:
            emojia = ":sound: "
            emojib = ":cop: "

        successEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Unmuted {str(member)}", force=True, forceColor=0x00ff00)

        await ctx.send(embed=successEmbed)

        SqlCommands.new_case(member.id, ctx.guild.id, "unmute", "N/A", unmutetime, -1, mod)

        logID = cursor.execute("SELECT modlogs from role_ids WHERE guild = ?",(member.guild.id,)).fetchone()
        
        if logID and logID != 0:

            channel = member.guild.get_channel(logID[0])

            title = f"{emojia}User Unmuted: {member.name}"
            desc = f"{emojib}Responsible Moderator: {ctx.author.name}"
            url = member.avatar_url

            embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=title, desc=desc, useColor=1)
            embed.set_thumbnail(url=url)

            await channel.send(embed=embed)

    @commands.command(help="Ungravels a User", brief=":sound: ")
    @commands.check(functions.has_modrole)
    async def ungravel(self, ctx, member : discord.Member):
        mod = str(ctx.author)
        ungraveltime = time.time()
        gravel = SqlCommands.get_role(ctx.guild.id, "gravel")
        mutedRole = ctx.guild.get_role(gravel)
        await member.remove_roles(mutedRole,)

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        if emoji == False:
            emojia = ""
            emojib = ""
        else:
            emojia = ":sound: "
            emojib = ":cop: "

        successEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Removed gravel from {str(member)}", force=True, forceColor=0x00ff00)

        await ctx.send(embed=successEmbed)

        SqlCommands.new_case(member.id, ctx.guild.id, "ungravel", "N/A", ungraveltime, -1, mod)

        logID = cursor.execute("SELECT modlogs from role_ids WHERE guild = ?",(member.guild.id,)).fetchone()
        
        if logID and logID != 0:

            channel = member.guild.get_channel(logID[0])

            title = f"{emojia}User Ungraveled: {member.name}"
            desc = f"{emojib}Responsible Moderator: {ctx.author.name}"
            url = member.avatar_url

            embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=title, desc=desc, useColor=1)
            embed.set_thumbnail(url=url)

            await channel.send(embed=embed)

    @commands.command(aliases=["whois"], brief=":mag: ")
    async def memberinfo(self, ctx, member: discord.Member):
        """Shows information about a given user."""

        #Initial embed setup

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        if emoji == False:
            emojia = ""
            emojib = ""
            emojic = ""
            emojid = ""
            emojie = ""
            emojif = ""
        else:
            emojia = ":scroll: "
            emojib = ":tools: "
            emojic = ":inbox_tray: "
            emojid = ":card_box: "
            emojie = ":ledger: "
            emojif = ":green_book: "

        #Assigning Variables relating to the member

        isbot = member.bot
        created = member.created_at
        joined = member.joined_at
        roles = member.roles
        avatar = member.avatar_url
        nickname = member.display_name
        memberid = member.id
        perms = member.guild_permissions
        discrim = member.discriminator
        color = member.color.to_rgb()
        name = member.name

        #Creating and sending the embed

        if nickname != name: 
            desc = f"This member has a nickname of: {nickname}" 
        else:
            desc = ""

        ack = ""

        permlist = ""

        mentionedroles = []
        out = f""
        n = 0
        x = 0

        for role in roles:
            if not role.is_default():
                mentionedroles.append(role.mention)
                n = n + 1
                if role.is_premium_subscriber():
                    ack = ack + "Server Booster, "

        while x < n:
            out = out + f"{mentionedroles[x]} "
            x = x + 1

        x = f" - {x}"

        if out == f"":
            out = "This member has no roles."
            x = ""

        if functions.has_modrole_no_ctx(member):
            ack = ack + "Server Moderator, "
        if functions.has_adminrole_no_ctx(member):
            ack = ack + "Server Administrator, "
        if member == member.guild.owner:
            ack = ack + "Server Owner, "

        if perms.administrator:
            permlist = permlist + "Administrator, "
        if perms.ban_members:
            permlist = permlist + "Ban Members, "
        if perms.deafen_members:
            permlist = permlist + "Deafen Members, "
        if perms.kick_members:
            permlist = permlist + "Kick Members, "
        if perms.manage_channels:
            permlist = permlist + "Manage Channels, "
        if perms.manage_emojis:
            permlist = permlist + "Manage Emojis, "
        if perms.manage_guild:
            permlist = permlist + "Manage Guild, "
        if perms.manage_messages:
            permlist = permlist + "Manage Messages, "
        if perms.manage_nicknames:
            permlist = permlist + "Manage Nicknames, "
        if perms.manage_permissions:
            permlist = permlist + "Manage Permissions, "
        if perms.manage_roles:
            permlist = permlist + "Manage Roles, "
        if perms.mention_everyone:
            permlist = permlist + "Mention Everyone, "
        if perms.mute_members:
            permlist = permlist + "Mute Members, "
        if perms.priority_speaker:
            permlist = permlist + "Priority Speaker, "
        if perms.send_tts_messages:
            permlist = permlist + "Send TTS Messages, "
        if perms.use_slash_commands:
            permlist = permlist + "Use Slash Commands, "
        if perms.view_audit_log:
            permlist = permlist + "View Audit Log, "
        if perms.view_guild_insights:
            permlist = permlist + "View Guild Insights, "

        if ack == "":
            ack = "This member has no acknowledgements."
        else:
            ack = ack[0:len(ack) - 2]

        if permlist == "":
            permlist = "This user has no Key Permissions."
        else:
            permlist = permlist[0:len(permlist) - 2]

        force = True

        if color == discord.Colour.default().to_rgb():
            force = False

        embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Member information for {name}#{discrim}:", desc=desc, useColor=1, force=force, forceColor=color, footer=f"Member ID: {memberid}")

        if isbot:
            embed.add_field(name="Bot", value="This user is a bot, beep boop!", inline=False)

        embed.add_field(name=f"{emojib}Creation Date", value=f"{created.strftime('%Y-%m-%d %H:%M:%S')}")
        embed.add_field(name=f"{emojic}Join Date", value=f"{joined.strftime('%Y-%m-%d %H:%M:%S')}")
        embed.add_field(name="_ _", value="_ _")
        embed.add_field(name=f"{emojid}Roles{x}", value=f"{out}")
        embed.add_field(name=f"{emojie}Acknowledgements", value=ack)
        embed.add_field(name=f"{emojif}Key Permissions", value=permlist, inline=False)

        embed.set_thumbnail(url=avatar)

        await ctx.send(embed=embed)

    @commands.command(aliases=["serverstats"], brief=":books: ")
    async def serverinfo(self, ctx):
        """Show an overview of this server's information."""

        #Initial Embed Setup

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        if emoji is False:
            emojia = ""
            emojib = ""
            emojic = ""
            emojid = ""
            emojie = ""
            emojif = ""
            emojig = ""
            emojih = ""
            emojii = ""
            emojij = ""
            emojik = ""
            emojil = ""
            emojim = ""
            emojin = ""
            emojio = ""
            emojip = ""
        else:
            emojia = ":books: "
            emojib = ":crown: "
            emojic = ":keyboard: "
            emojid = ":sound: "
            emojie = ":card_box: "
            emojif = ":slight_smile: "
            emojig = ":earth_africa: "
            emojih = ":dollar: "
            emojii = ":page_facing_up: "
            emojij = ":innocent: "
            emojik = ":magic_wand: "
            emojil = ":frame_photo: "
            emojim = ":triangular_flag_on_post: "
            emojin = ":pencil2: "
            emojio = ":dividers: "
            emojip = ":books: "

        #Setting Variables

        guild = ctx.guild

        owner = guild.owner.name + "#" + guild.owner.discriminator
        created_at = guild.created_at
        region = guild.region
        roles = guild.roles
        channels = len(guild.text_channels)
        voice = len(guild.voice_channels)
        boost = guild.premium_tier
        boosters = guild.premium_subscription_count
        name = guild.name
        guildid = guild.id
        members = guild.member_count
        categories = len(guild.categories)
        allchannels = guild.channels
        icon = guild.icon_url
        desc = guild.description
        banner = guild.banner_url
        maxemoji = guild.emoji_limit
        emoji = len(guild.emojis)
        maxfilesize = guild.filesize_limit
        features = guild.features

        #Creating and sending an embed

        boostcolors = [0x2c2f33, 0x7289DA, 0xcc76fc, 0xfd73fa]
        boostcol = boostcolors[boost]

        n = 0
        rolelist = ""
        for role in roles:
            if not role.is_default():
                rolelist = rolelist + f"{role.mention}, "
                n = n + 1

        rolelist = rolelist[0:len(rolelist) - 2]

        customurl = "Locked"
        invsplash = "Locked"
        verified = "No"
        partner = "No"
        discoverable = "Off"
        featurable = "Off"
        community = False
        canbanner = "Locked"
        animicon = "Locked"
        welcomescr = "Off"
        vergate = "Off"
        for feature in features:
            if feature == "VANITY_URL":
                customurl = "Unlocked"
            if feature == "INVITE_SPLASH":
                invsplash = "Unlocked"
            if feature == "VERIFIED":
                verified = "Yes"
            if feature == "PARTNERED":
                partner = "Yes"
            if feature == "DISCOVERABLE":
                discoverable = "On"
            if feature == "FEATURABLE":
                featurable = "On"
            if feature == "COMMUNITY":
                community = True
            if feature == "BANNER":
                canbanner = "Unlocked"
            if feature == "ANIMATED_ICON":
                animicon = "Unlocked"
            if feature == "WELCOME_SCREEN_ENABLED":
                welcomescr = "On"
            if feature == "MEMBER_VERIFICATION_GATE_ENABLED":
                vergate = "On"

        if customurl == "Unlocked":
            try:
                invite = await guild.vanity_invite().url
            except:
                invite = await guild.invites()
                invite = invites[0].url
        else:
            invites = await guild.invites()
            invite = invites[0].url

        title = f"{emojia}Server Statistics"
        if desc is not None:
            description = f"Server Invite: {invite}\nID: {guildid}\nServer Description: {desc}"
        else:
            description = f"Server Invite: {invite}\nID: {guildid}"

        embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=title, desc=description, force=True, forceColor=boostcol, footer=f"Server Created At {created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        embed.add_field(name=f"{emojib}Owner", value=owner)
        embed.add_field(name=f"{emojic}Text Channels", value=channels)
        embed.add_field(name=f"{emojid}Voice Channels", value=voice)
        embed.add_field(name=f"{emojie}Channel Categories", value=categories)
        embed.add_field(name=f"{emojif}Members", value=members)
        embed.add_field(name=f"{emojig}Region", value=region)
        embed.add_field(name=f"{emojih}Boost Status - Tier: {boost} ({boosters} boosters)", value="_ _", inline=False)
        embed.add_field(name=f"{emojii}Filesize Limit", value=f"{maxfilesize / 1024 ** 2}MB")
        embed.add_field(name=f"{emojij}Emojis", value=f"{emoji}/{maxemoji} slots used.")
        embed.add_field(name=f"{emojik}Animated Icon", value=animicon)
        embed.add_field(name=f"{emojil}Invite Splash", value=invsplash)
        embed.add_field(name=f"{emojim}Banner", value=canbanner)
        embed.add_field(name=f"{emojin}Vanity Url", value=customurl)
        embed.add_field(name=f"{emojio}Roles - {n}", value=rolelist, inline=False)
        if community:
            embed.add_field(name=f"{emojip}Other Statistics", value=f"Verified: {verified}\nDiscord Partner: {partner}\nCommunity Server: Yes\nServer Discovery: {discoverable}\nServer Featuring: {featurable}\nWelcome Screen: {welcomescr}\nVerification Gate: {vergate}")
        else:
            embed.add_field(name=f"{emojip}Other Statistics", value=f"Verified: {verified}\nDiscord Partner: {partner}\nCommunity Server: No")
        embed.set_author(name=name, icon_url=icon)
        embed.set_thumbnail(url=icon)

        await ctx.send(embed=embed)
        

    #End of Commands


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
