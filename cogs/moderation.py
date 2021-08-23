import datetime
import logging
import time

import discord
from discord.ext import commands, tasks

import cogs.fancyEmbeds as fEmbeds
import functions


class Moderation(commands.Cog):
    """Cog for moderators to help them moderate!"""

    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.timedRoleCheck.start()
        self.bot.cooldowns = {}
        self.bot.pending_cooldowns = {}
        self.bot.before_invoke(self.before_invoke)
        self.connection = bot.connection

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

        emojis = (":no_entry_sign: ", ":hammer: ", ":cop: ", ":scroll: ") if emoji else ("","","","")

        bantime = time.time()

        banEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojis[0]}You have been banned from {ctx.guild.name}", force=True, forceColor=0xff0000)
        banEmbed.add_field(name="Ban reason: ", value=reason)
        try:
            await member.send(embed=banEmbed)
            unsent = False
        except discord.errors.HTTPException:
            unsent = True

        if unsent:
            successEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojis[1]}Banned {str(member)}", force=True, forceColor=0x00ff00, desc="Failed to send a message to the user.")
        else:
            successEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojis[1]}Banned {str(member)}", force=True, forceColor=0x00ff00)

        await ctx.send(embed=successEmbed)

        await SqlCommands.new_case(member.id, ctx.guild.id, "ban", reason, bantime, -1, str(ctx.author))

        cursor = await self.connection.execute("SELECT modlogs from role_ids WHERE guild = ?",(member.guild.id,))
        logID = await cursor.fetchone()
        await cursor.close()

        if logID and logID != 0:

            channel = member.guild.get_channel(logID[0])

            title = f"{emojis[1]}User Banned: {member.name}"
            desc = f"{emojis[2]}Responsible Moderator: {ctx.author.name}\n{emojis[3]}Reason: {reason}"
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
        if reason is None:
            reason = "No reason specified"

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        emojis = (":boot: ",":cop: ",":scroll: ") if emoji else ("","","")

        kicktime = time.time()

        kickEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojis[0]}You have been kicked from {ctx.guild.name}", force=True, forceColor=0xff0000)
        kickEmbed.add_field(name="Kick reason:", value=reason)

        await ctx.guild.kick(member, reason=reason)
        try:
            await member.send(embed=kickEmbed)
            unsent = False
        except discord.errors.HTTPException:
            unsent = True

        if unsent:
            successEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojis[0]}Kicked {str(member)}", force=True, forceColor=0x00ff00, desc="Failed to send a message to the user.")
        else:
            successEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojis[0]}Kicked {str(member)}", force=True, forceColor=0x00ff00)

        await ctx.send(embed=successEmbed)

        await SqlCommands.new_case(member.id, ctx.guild.id, "kick", reason, kicktime, -1, str(ctx.author))

        cursor = await self.connection.execute("SELECT modlogs from role_ids WHERE guild = ?",(ctx.guild.id,))
        logID = await cursor.fetchone()
        await cursor.close()

        if logID and logID != 0:

            channel = member.guild.get_channel(logID[0])

            title = f"{emojis[0]}User Kicked: {member.name}"
            desc = f"{emojis[1]}Responsible Moderator: {ctx.author.name}\n{emojis[2]}Reason: {reason}"
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

        emojis = (":x: ",":white_check_mark: ",":cop: ") if emoji else ("","","")

        try:
            await ctx.guild.fetch_ban(user)
        except discord.NotFound:
            notBannedEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojis[0]}This user is not banned.", useColor=2)
            await ctx.send(embed = notBannedEmbed)
            return

        await ctx.guild.unban(user)

        successEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojis[1]}Unbanned {str(user)}", useColor=3, force=True, forceColor=0x00ff00)

        await ctx.send(embed=successEmbed)

        await SqlCommands.new_case(user.id, ctx.guild.id, "unban", "N/A", unbanTime, -1, str(ctx.author))

        cursor = await self.connection.execute("SELECT modlogs from role_ids WHERE guild = ?",(ctx.guild.id,))
        logID = await cursor.fetchone()
        await cursor.close()

        if logID and logID != 0:

            channel = ctx.guild.get_channel(logID[0])

            title = f"{emojis[0]}User Unbanned: {user.name}"
            desc = f"{emojis[2]}Responsible Moderator: {ctx.author.name}"
            url = user.avatar_url

            embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=title, desc=desc, useColor=1)
            embed.set_thumbnail(url=url)

            await channel.send(embed=embed)

    #gravel
    @commands.command(help="Gravels a user", brief=":mute: ")
    @commands.check(functions.has_modrole)
    async def gravel(self, ctx, member : discord.Member, graveltime: functions.InSeconds, *, reason=None):
        if reason is None:
            reason = "No reason specified"
        roleid = await SqlCommands.get_role(ctx.guild.id, "gravel")
        converter = commands.RoleConverter()
        role = await converter.convert(ctx,str(roleid))
        await member.add_roles(role)
        now = time.time()
        end = now + graveltime

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        emojis = (":mute: ",":white_check_mark: ",":cop: ",":scroll: ") if emoji else ("","","","")

        gravelEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojis[0]}You have been graveled in {ctx.guild.name} for {TimeConversions.fromseconds(graveltime)}", force=True, forceColor=0xff0000)
        gravelEmbed.add_field(name="Reason:", value=reason)

        try:
            await member.send(embed=gravelEmbed)
            unsent = False
        except discord.errors.HTTPException:
            unsent = True

        await SqlCommands.new_case(member.id, ctx.guild.id, "gravel", reason, now, end, str(ctx.author))

        if unsent:
            successEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojis[1]}Gravelled " + str(member), desc="Failed to send a message to the user.",  useColor=1)
        else:
            successEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojis[1]}Gravelled " + str(member), useColor=1)

        await ctx.send(embed=successEmbed)

        cursor = await self.connection.execute("SELECT modlogs from role_ids WHERE guild = ?",(ctx.guild.id,))
        logID = await cursor.fetchone()
        await cursor.close()

        if logID and logID != 0:

            channel = member.guild.get_channel(logID[0])

            title = f"{emojis[0]}User Gravelled: {member.name}"
            desc = f"{emojis[2]}Responsible Moderator: {ctx.author.name}\n{emojis[3]}Reason: {reason}"
            url = member.avatar_url

            embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=title, desc=desc, useColor=2)
            embed.set_thumbnail(url=url)

            await channel.send(embed=embed)

    @commands.command(help="Mutes a user", brief=":mute: ")
    @commands.check(functions.has_modrole)
    async def mute(self, ctx, member : discord.Member, mutetime: functions.InSeconds, *, reason=None):
        now = time.time()
        if reason is None:
            reason = "No reason specified"
        totalsecs = TimeConversions.secondsconverter(timevalue, timeformat)
        roleid = await SqlCommands.get_role(ctx.guild.id, "muted")
        roleid = str(roleid)
        converter = commands.RoleConverter()
        role = await converter.convert(ctx,roleid)
        await member.add_roles(role)
        end = now + mutetime

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        emojis = (":mute: ",":white_check_mark: ",":cop: ") if emoji else ("","","")

        muteEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojis[0]}You have been muted in {ctx.guild.name} for {TimeConversions.fromseconds(mutetime)}.", force=True, forceColor=0xFF0000)

        muteEmbed.add_field(name="Reason:", value=reason)

        try:
            await member.send(embed=muteEmbed)
            unsent = False
        except discord.errors.HTTPException:
            unsent = True

        await SqlCommands.new_case(member.id, ctx.guild.id, "mute", reason, now, end, str(ctx.author))

        if unsent:
            successEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojis[1]}Muted " + str(member), desc="Failed to send a message to the user.", useColor=1)
        else:
            successEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojis[1]}Muted " + str(member), useColor=1)

        await ctx.send(embed=successEmbed)

        cursor = await self.connection.execute("SELECT modlogs from role_ids WHERE guild = ?",(ctx.guild.id,))
        logID = await cursor.fetchone()
        await cursor.close()

        if logID and logID != 0:

            channel = member.guild.get_channel(logID[0])

            title = f"{emojis[0]}User Muted: {member.name}"
            desc = f"{emojis[2]}Responsible Moderator: {ctx.author.name}\nReason: {reason}"
            url = member.avatar_url

            embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=title, desc=desc, useColor=2)
            embed.set_thumbnail(url=url)

            await channel.send(embed=embed)

    @commands.command(help="warns a user", brief=":warning: ")
    @commands.check(functions.has_modrole)
    async def warn(self, ctx, member : discord.Member, *, reason):

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        emojis = (":exclamation: ",":white_check_mark: ",":notepad_spiral: ",":cop: ",":scroll: ") if emoji else ("","","","","")

        warnEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojis[0]}You have been warned in {ctx.guild.name}", force=True, forceColor=0xff0000)
        warnEmbed.add_field(name="Reason:", value=reason)

        await SqlCommands.new_case(member.id, ctx.guild.id, "warn", reason, time.time(), -1, str(ctx.author))

        try:
            await member.send(embed=warnEmbed)
            successEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojis[1]}Successfully warned {str(member)}", force=True, forceColor=0x00ff00)
            await ctx.send(embed=successEmbed)
        except discord.errors.HTTPException:
            failEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojis[2]}Logged a warning for user {str(member)}", desc="Failed to send a message to the user.", force=True, forceColor=0x00ff00)
            await ctx.send(embed=failEmbed)

        cursor = await self.connection.execute("SELECT modlogs from role_ids WHERE guild = ?",(ctx.guild.id,))
        logID = await cursor.fetchone()
        await cursor.close()

        if logID and logID != 0:

            channel = member.guild.get_channel(logID[0])

            title = f"{emojis[0]}User Warned: {member.name}"
            desc = f"{emojis[3]}Responsible Moderator: {ctx.author.name}\n{emojis[4]}Reason: {reason}"
            url = member.avatar_url

            embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=title, desc=desc, useColor=2)
            embed.set_thumbnail(url=url)

            await channel.send(embed=embed)

    @commands.command(help="Shows a user's modlogs", brief=":file_folder: ")
    @commands.check(functions.has_modrole)
    async def modlogs(self, ctx, member : discord.User):

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        emojis = (":open_file_folder: ",":notepad_spiral: ",":page_facing_up: ",":pencil2: ",":clock3: ",":stopwatch: ",":cop: ") if emoji else ("","","","","","")

        logEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojis[0]}{str(member)}'s Modlogs", useColor=1)

        cursor = await self.connection.execute("SELECT id_in_guild, guild, user, type, reason, started, expires, moderator FROM caselog WHERE user = ? AND guild = ?", (member.id, ctx.guild.id))
        logs = await cursor.fetchall()
        await cursor.close()

        for log in logs:
            if time.time() - int(log[5]) < (60*60*24):
                form = "R"
            else:
                form = "F"
            start = f"<t:{int(log[5])}:{form}>"
            if int(log[6]) != -1:
                totaltime = TimeConversions.fromseconds(int(int(log[6])) - int(log[5]))
            else:
                totaltime = "N/A"

            logEmbed.add_field(name=f"{emojis[1]}__**Case {str(log[0])}**__", value=f"{emojis[2]}**Type- **{log[3]}\n{emojis[3]}**Reason- **{log[4]}\n{emojis[4]}**Time- **{start}\n{emojis[5]}**Length- **{totaltime}\n{emojis[6]}**Moderator- **{log[7]}", inline=True)

        logEmbed.set_thumbnail(url=member.avatar_url)

        await ctx.send(embed = logEmbed)

    @commands.command(help="Shows information on a case", brief=":notepad_spiral: ")
    @commands.check(functions.has_modrole)
    async def case(self, ctx, case:int):
        cursor = await self.connection.execute("SELECT id_in_guild, guild, user, type, reason, started, expires, moderator FROM caselog WHERE id = ?", (case,))
        caseinfo = await cursor.fetchone()
        await cursor.close()
        try:
            if time.time() - int(caseinfo[5]) < (60*60*24):
                form = "R"
            else:
                form = "F"
            start = f"<t:{int(caseinfo[5])}:{form}>"
        except TypeError:
            await ctx.send("Could not find that case number")
            return
        if int(caseinfo[6]) != -1:
            totaltime = TimeConversions.fromseconds(int(int(caseinfo[6])) - int(caseinfo[5]))
        else:
            totaltime = "N/A"

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        emojis = (":notepad_spiral: ",":page_facing_up: ",":pencil2: ",":clock3: ",":stopwatch: ",":cop: ") if emoji else ("","","","","","")

        logEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojis[0]}Case {str(case)}", useColor=3)

        user = await self.bot.fetch_user(caseinfo[2])

        logEmbed.add_field(name=user, value=f"{emojis[1]}**Type- **" + caseinfo[3] + f"\n{emojis[2]}**Reason- **" + caseinfo[4] + f"\n{emojis[3]}**Time- **" + start + f"\n{emojis[4]}**Length- **" + totaltime + f"\n{emojis[5]}**Moderator- **" + caseinfo[7], inline=True)
        logEmbed.set_thumbnail(url=user.avatar_url)

        await ctx.send(embed = logEmbed)

    @commands.command(help="Unmutes a User", brief=":sound: ")
    @commands.check(functions.has_modrole)
    async def unmute(self, ctx, member : discord.Member):
        mod = str(ctx.author)
        unmutetime = time.time()
        muted = await SqlCommands.get_role(ctx.guild.id, "muted")
        mutedRole = ctx.guild.get_role(muted)
        await member.remove_roles(mutedRole,)

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        emojis = (":sound: ",":cop: ") if emoji else ("","")

        successEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojis[0]}Unmuted {str(member)}", force=True, forceColor=0x00ff00)

        await ctx.send(embed=successEmbed)

        await SqlCommands.new_case(member.id, ctx.guild.id, "unmute", "N/A", unmutetime, -1, mod)

        cursor = await self.connection.execute("SELECT modlogs from role_ids WHERE guild = ?",(ctx.guild.id,))
        logID = await cursor.fetchone()
        await cursor.close()

        if logID and logID != 0:

            channel = member.guild.get_channel(logID[0])

            title = f"{emojis[0]}User Unmuted: {member.name}"
            desc = f"{emojis[1]}Responsible Moderator: {ctx.author.name}"
            url = member.avatar_url

            embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=title, desc=desc, useColor=1)
            embed.set_thumbnail(url=url)

            await channel.send(embed=embed)

    @commands.command(help="Ungravels a User", brief=":sound: ")
    @commands.check(functions.has_modrole)
    async def ungravel(self, ctx, member : discord.Member):
        mod = str(ctx.author)
        ungraveltime = time.time()
        gravel = await SqlCommands.get_role(ctx.guild.id, "gravel")
        mutedRole = ctx.guild.get_role(gravel)
        await member.remove_roles(mutedRole,)

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        emojis = (":sound: ",":cop: ") if emoji else ("","")

        successEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojis[0]}Removed gravel from {str(member)}", force=True, forceColor=0x00ff00)

        await ctx.send(embed=successEmbed)

        await SqlCommands.new_case(member.id, ctx.guild.id, "ungravel", "N/A", ungraveltime, -1, mod)

        cursor = await self.connection.execute("SELECT modlogs from role_ids WHERE guild = ?",(ctx.guild.id,))
        logID = await cursor.fetchone()
        await cursor.close()

        if logID and logID != 0:

            channel = member.guild.get_channel(logID[0])

            title = f"{emojis[0]}User Ungraveled: {member.name}"
            desc = f"{emojis[1]}Responsible Moderator: {ctx.author.name}"
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

        emojis = (":scroll: ",":tools: ",":inbox_tray: ",":dividers: ",":ledger: ",":green_book: ") if emoji else ("","","","","","")

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
        rolefieldname = ""
        rolefieldvalue = ""

        for role in roles:
            if not role.is_default():
                mentionedroles.append(role.mention)
                if role.is_premium_subscriber():
                    ack = ack + "Server Booster, "

        for role in reversed(mentionedroles):
            rolefieldvalue = rolefieldvalue + role

        if len(mentionedroles) == 0:
            rolefieldname = "Roles"
            rolefieldvalue = "This member has no roles."
        else:
            rolefieldname = f"Roles - {len(mentionedroles)}"

        if functions.has_modrole_no_ctx(member, self.bot):
            ack = ack + "Server Moderator, "
        if functions.has_adminrole_no_ctx(member, self.bot):
            ack = ack + "Server Administrator, "
        if member == member.guild.owner:
            ack = ack + "Server Owner, "

        if perms.administrator:
            permlist = "Administrator, "
        else:
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

        embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojis[0]} {name}#{discrim}", desc=desc, useColor=1, force=force, forceColor=color, footer=f"Member ID: {memberid}")

        if isbot:
            embed.add_field(name="Bot", value="This user is a bot, beep boop!", inline=False)

        embed.add_field(name=f"{emojis[1]} Creation Date", value=f"<t:{int(created.timestamp() + 0.5)}:f>")
        embed.add_field(name=f"{emojis[2]} Join Date", value=f"<t:{int(joined.timestamp() + 0.5)}:f>")
        embed.add_field(name="_ _", value="_ _")
        embed.add_field(name=f"{emojis[3]} {rolefieldname}", value=f"{rolefieldvalue}", inline=False)
        embed.add_field(name=f"{emojis[4]} Acknowledgements", value=ack)
        embed.add_field(name=f"{emojis[5]} Key Permissions", value=permlist, inline=False)

        embed.set_thumbnail(url=avatar)

        await ctx.send(embed=embed)

    @commands.command(aliases=["serverstats"], brief=":books: ")
    async def serverinfo(self, ctx):
        """Show an overview of this server's information."""

        #Initial Embed Setup

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        emojis = (
            ":books: ",":crown: ",":keyboard: ",":sound: ",":card_box: ",":slight_smile: ",
            ":earth_africa: ",":dollar: ",":page_facing_up: ",":innocent: ",":magic_wand: ",
            ":frame_photo: ",":triangular_flag_on_post: ",":pencil2: ",":dividers: ",":books: "
        ) if emoji else ("","","","","","","","","","","","","","","","")

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
                invite = invite[0].url
        else:
            invites = await guild.invites()
            invite = invites[0].url

        title = f"{emojis[0]}Server Statistics"
        if desc is not None:
            description = f"Server Invite: {invite}\nID: {guildid}\nServer Description: {desc}"
        else:
            description = f"Server Invite: {invite}\nID: {guildid}"

        description = description + f"\nServer Created on <t:{int(created_at.timestamp())}:F>"

        embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=title, desc=description, force=True, forceColor=boostcol)
        embed.add_field(name=f"{emojis[1]}Owner", value=owner)
        embed.add_field(name=f"{emojis[2]}Text Channels", value=channels)
        embed.add_field(name=f"{emojis[3]}Voice Channels", value=voice)
        embed.add_field(name=f"{emojis[4]}Channel Categories", value=categories)
        embed.add_field(name=f"{emojis[5]}Members", value=members)
        embed.add_field(name=f"{emojis[6]}Region", value=region)
        embed.add_field(name=f"{emojis[7]}Boost Status - Tier: {boost} ({boosters} boosters)", value="_ _", inline=False)
        embed.add_field(name=f"{emojis[8]}Filesize Limit", value=f"{maxfilesize / 1024 ** 2}MB")
        embed.add_field(name=f"{emojis[9]}Emojis", value=f"{emoji}/{maxemoji} slots used.")
        embed.add_field(name=f"{emojis[10]}Animated Icon", value=animicon)
        embed.add_field(name=f"{emojis[11]}Invite Splash", value=invsplash)
        embed.add_field(name=f"{emojis[12]}Banner", value=canbanner)
        embed.add_field(name=f"{emojis[13]}Vanity Url", value=customurl)
        embed.add_field(name=f"{emojis[14]}Roles - {n}", value=rolelist, inline=False)
        if community:
            embed.add_field(name=f"{emojis[15]}Other Statistics", value=f"Verified: {verified}\nDiscord Partner: {partner}\nCommunity Server: Yes\nServer Discovery: {discoverable}\nServer Featuring: {featurable}\nWelcome Screen: {welcomescr}\nVerification Gate: {vergate}")
        else:
            embed.add_field(name=f"{emojis[15]}Other Statistics", value=f"Verified: {verified}\nDiscord Partner: {partner}\nCommunity Server: No")
        embed.set_author(name=name, icon_url=icon)
        embed.set_thumbnail(url=icon)

        await ctx.send(embed=embed)

    @commands.command(brief=":card_box: ")
    @commands.check(functions.has_modrole)
    async def moderations(self, ctx):
        """Shows all active moderations in the current guild."""

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        emojis = (":card_box: ",":notepad_spiral: ",":slight_smile: ",":page_facing_up: ",":stopwatch: ") if emoji else ("","","","","")

        cursor = await self.connection.execute("SELECT id_in_guild, guild, user, type, expires FROM caselog WHERE id > ? AND guild = ?", (0, ctx.guild.id))
        logs = await cursor.fetchall()
        await cursor.close()

        #cursor = await self.connection.execute("SELECT id_in_guild, guild, user, type, expires FROM caselog WHERE guild = ?", (ctx.guild.id))
        #logs = await cursor.fetchall()

        timestamp = f"<t:{int(time.time())}:F>"

        modEmbed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojis[0]}Active Moderations", desc=f"as of {timestamp}", useColor=1)

        for log in logs:
            if int(time.time()) - int(log[4]) < 0:
                if int(time.time()) - int(log[4]) < (60*60*24):
                    form = "R"
                else:
                    form = "F"

                user = self.bot.get_user(log[2])

                modEmbed.add_field(name=f"{emojis[1]}__**Case {str(log[0])}**__", value=f"{emojis[2]}**User:** {user.name}#{user.discriminator}\n{emojis[3]}**Type:** {log[3]}\n{emojis[4]}**Expires** <t:{int(log[4])}:{form}>")

        await ctx.send(embed=modEmbed)

    @commands.command(brief=":mute: ", help="Server mutes a user, preventing them from talking in VC", aliases=["servermute", "voicemute"])
    @commands.check(functions.has_modrole)
    async def server_mute(self, ctx, member: discord.Member):
        if member.voice == None:
            await ctx.send("This user isn't currently in a voice channel!")
            return
        elif member.voice.mute == True:
            await ctx.send("This user is already server muted!")
        else:
            await member.edit(mute=True)
            await ctx.send(f"Sounds good! I server muted {member.name}")

    @commands.command(brief=":speaker: ", help="Unmutes a user that is server muted", aliases=["serverunmute", "voiceunmute", "unmutevoice"])
    @commands.check(functions.has_modrole)
    async def server_unmute(self, ctx, member: discord.Member):
        if member.voice == None:
            await ctx.send("This user isn't currently in a voice channel!")
            return
        elif member.voice.mute == False:
            await ctx.send("This user isn't server muted!")
            return
        else:
            await member.edit(mute=False)
            await ctx.send(f"Sounds good! I unmuted {member.name}")

    #End of Commands

    #checks if a role needs to be removed
    @tasks.loop(seconds=5.0)
    async def timedRoleCheck(self):
        now = time.time()
        cursor = await self.connection.cursor()
        expired = await cursor.execute(f"SELECT active_cases.id AS case_id, guild, user, type FROM active_cases INNER JOIN caselog ON active_cases.id == caselog.id WHERE expiration <= {str(now)} ")
        try:
            expired = await expired.fetchall()
        except AttributeError:
            return
        for case in expired:
            guild = self.bot.get_guild(int(case[1]))
            if case[3] == "gravel":
                roleid = await SqlCommands.get_role(case[1], "gravel")
                role = guild.get_role(roleid)
                member = guild.get_member(case[2])
                try:
                    await member.remove_roles(role)
                except:
                    pass
            elif case[3] == "mute":
                roleid = await SqlCommands.get_role(case[1], "muted")
                role = guild.get_role(roleid)
                member = guild.get_member(case[2])
                try:
                    await member.remove_roles(role)
                except:
                    pass
            await cursor.execute("DELETE FROM active_cases WHERE id = ?", (case[0],))
        await self.connection.commit()
        await cursor.close()

    @timedRoleCheck.before_loop
    async def before_TimedRoleCheck(self):
        await self.bot.wait_until_ready()

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
        cursor = await self.connection.execute("SELECT command_usage, command_cooldown FROM role_ids WHERE guild = ?", (ctx.guild.id,))
        cmd = await cursor.fetchone()
        if cmd:
            commandRole, commandCooldown = cmd
        else:
            return True
        member_roles = [role.id for role in ctx.author.roles]
        if not commandRole:
            if commandCooldown and not (ctx.invoked_with == "help" and ctx.command.name != "help"):
                self.bot.pending_cooldowns[ctx.guild.id][ctx.author.id] = (ctx.command,datetime.datetime.now() + datetime.timedelta(milliseconds=commandCooldown))
            return True
        elif commandRole in member_roles:
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

SqlCommands = None
TimeConversions = functions.timeconverters()

def setup(bot):
    global SqlCommands
    SqlCommands = functions.Sql(bot)
    bot.add_cog(Moderation(bot))
