import asyncio
import json
import random
import sqlite3
import io
import aiohttp

import cogs.fancyEmbeds as fEmbeds
import functions

import discord
from discord.ext import commands

#sets up SQLite
connection = sqlite3.connect("database.db")
cursor = connection.cursor()

async def tag_check(ctx):
    if ctx.invoked_with == "help":
        return True
    tags = cursor.execute("SELECT * FROM tags WHERE guild = ?", (ctx.guild.id,)).fetchone()
    if (tags is None and ctx.author.guild_permissions.manage_messages): # No guild tags and the user can manage messages
        if not (ctx.command.root_parent == "tag" or ctx.command.name == "tag"): # Check is not coming from a tag command so return True
            return True
        cursor.execute("INSERT INTO tags(guild,role,tags) VALUES(?,?,?)",(ctx.guild.id,ctx.author.top_role.id,"{}"))
        connection.commit()
        await ctx.send(f"Tags created and role set to {ctx.author.top_role.name}.")
        tags = cursor.execute("SELECT * FROM tags WHERE guild = ?", (ctx.guild.id,)).fetchone()
    elif tags is None: # User cannot manage messages but there are no tags
        return False
    if ctx.guild.get_role(int(tags[1])) <= ctx.author.top_role: # Tags do exist and the user has the roles required
        return True
    return False


class Utilities(commands.Cog):
    """Adds utilities for users!"""

    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.group(name="setup", help="setup some (or all) features of the bot", aliases=["su",], brief=":wrench: ")
    @commands.check_any(commands.has_permissions(administrator=True),commands.check(functions.has_adminrole))
    async def setup(self,ctx):
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self.bot.get_command('setup all'))

    @setup.command(help="Sets a server-specific bot prefix", name="prefix", aliases=["set_prefix",], brief=":pencil2: ")
    async def setup_prefix(self, ctx, prefix):
        cursor.execute("INSERT INTO guild_prefixes(guild,prefix) VALUES(?, ?) ON CONFLICT(guild) DO UPDATE SET prefix=excluded.prefix", (ctx.guild.id, prefix))
        connection.commit()
        await ctx.send("Your new server-specific prefix is " + prefix)

    #all, chonky function
    @setup.command(help="Sets up all the bot's features", name="all", brief=":wrench: ")
    async def setup_all(self, ctx):
        guild = ctx.guild
        await ctx.send("Beginning server set-up")
        await ctx.send("First, please say the name of your gravel role. (case sensitive)")
        def check(response):
            return response.channel == ctx.channel and response.author == ctx.author
        async def get_message():
            try:
                message = await self.bot.wait_for('message', timeout=60.0, check=check)
                return message
            except asyncio.TimeoutError:
                await ctx.send("No response received. Cancelling")
                return
        message = await get_message()
        try:
            gravelRole = await commands.RoleConverter().convert(ctx,message.content)
        except commands.RoleNotFound:
            await ctx.send("That does not appear to be a valid role. Cancelling")
            return
        await ctx.send("Next, please give the name of your muted role.")
        message = await get_message()
        try:
            mutedRole = await commands.RoleConverter().convert(ctx,message.content)
        except commands.RoleNotFound:
            await ctx.send("That does not appear to be a valid role. Cancelling")
            return
        await ctx.send("Ok, now please tell me what the name is for your moderator role (people with this role will be able to use mod-only commands).")
        message = await get_message()
        try:
            modRole = await commands.RoleConverter().convert(ctx,message.content)
        except commands.RoleNotFound:
            await ctx.send("That does not appear to be a valid role. Cancelling")
            return
        await ctx.send("Now for the name of your admin role (people with this role will be able to use admin-only commands).")
        message = await get_message()
        try:
            adminRole = await commands.RoleConverter().convert(ctx,message.content)
        except commands.RoleNotFound:
            await ctx.send("That does not appear to be a valid role. Cancelling")
            return
        await ctx.send("Enter the name of your commands role or 'none' for no role (if supplied, this role will be required to use any commands).")
        message = await get_message()
        if message.content.lower() != "none":
            try:
                commandRole = await commands.RoleConverter().convert(ctx,message.content)
            except commands.RoleNotFound:
                await ctx.send("That does not appear to be a valid role. Cancelling")
                return
        else:
            commandRole = None
        await ctx.send("Enter the cooldown for your commands (in milliseconds) or type 'none' for no cooldown (cooldown does not apply to mods and admins).")
        message = await get_message()
        if message.content.lower() != "none":
            try:
                commandCooldown = int(message.content)
            except ValueError:
                await ctx.send("That does not appear to be a valid number. Cancelling")
                return
        else:
            commandCooldown = 0
        await ctx.send("Almost there! Please send me your modlog channel, or type \"None\" if you do not want a modlog channel.")
        message = await get_message()
        if message.content.lower() != "none":
            try:
                logChannel = await commands.TextChannelConverter().convert(ctx,message.content)
            except commands.ChannelNotFound:
                await ctx.send("That does not appear to be a valid channel. Cancelling")
                return
        else:
            logChannel = None
        await ctx.send("Last, please tell me what prefix you would like to use for commands")
        prefix = await get_message()

        cursor.execute("INSERT INTO guild_prefixes(guild,prefix) VALUES(?, ?) ON CONFLICT(guild) DO UPDATE SET prefix=excluded.prefix", (guild.id, prefix.content))
        cursor.execute("INSERT INTO role_ids(guild,gravel,muted,moderator,admin,modlogs,command_usage,command_cooldown) VALUES(?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(guild) DO UPDATE SET gravel=excluded.gravel, muted=excluded.muted, moderator=excluded.moderator, admin=excluded.admin, modlogs=excluded.modlogs, command_usage=excluded.command_usage, command_cooldown=excluded.command_cooldown", (guild.id, gravelRole.id, mutedRole.id, modRole.id, adminRole.id, getattr(logChannel,"id",0), getattr(commandRole,"id",0),commandCooldown))
        connection.commit()

        e = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self , ctx.guild.id, e, "emoji")
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
        else:
            emojia = ":wrench: "
            emojib = ":mute: "
            emojic = ":mute: "
            emojid = ":hammer: "
            emojie = ":tools: "
            emojif = ":file_folder: "
            emojig = ":page_facing_up: "
            emojih = ":stopwatch: "
            emojii = ":pencil2: "

        response = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Server set up successfully!", useColor=0)
        response.add_field(name=f"{emojib}Gravel role", value=gravelRole.mention) 
        response.add_field(name=f"{emojic}Muted role", value=mutedRole.mention)
        response.add_field(name=f"{emojid}Moderator role", value=modRole.mention)
        response.add_field(name=f"{emojie}Admin role", value=adminRole.mention)
        response.add_field(name=f"{emojif}Modlog channel", value=getattr(logChannel,"mention","None"))
        response.add_field(name=f"{emojig}Command role", value=getattr(commandRole,"mention","None"))
        response.add_field(name=f"{emojih}Command cooldown", value=f"{commandCooldown / 1000} Seconds")
        response.add_field(name=f"{emojii}Command Prefix", value=f"`{prefix.content}`")

        await ctx.send(embed=response)

    @setup.command(name="modlogs", help="Specifies the channel to be used for modlogs, do not specify a channel to remove logs.", aliases=["logchannel", "modlog", "logs",], brief=":file_folder: ")
    async def setup_modlogs(self, ctx, *, channel:discord.TextChannel=None):
        if channel:
            try:
                await channel.send("Set up modlogs in this channel!")
                await ctx.send(f"Set up modlogs in {channel.mention}!")
                cursor.execute("INSERT INTO role_ids(guild, modlogs) VALUES(?,?) ON CONFLICT(guild) DO UPDATE SET modlogs=excluded.modlogs", (ctx.guild.id, channel.id))
            except:
                await ctx.send("Something went wrong. Please make sure you specify a valid channel, and that I have permissions to send messages to it")
                return
        else:
            cursor.execute("INSERT INTO role_ids(guild,modlogs) VALUES(?,?) ON CONFLICT(guild) DO UPDATE SET modlogs=excluded.modlogs", (ctx.guild.id, 0))
            await ctx.send("Turned off modlogs")
        connection.commit()

    @setup.command(name="gravel", help="Specifies the role given to someone who is graveled", aliases=["gravelrole",], brief=":mute: ")
    async def setup_gravel(self, ctx, role:discord.Role):
        cursor.execute("INSERT INTO role_ids(guild, gravel) VALUES(?,?) ON CONFLICT(guild) DO UPDATE SET gravel=excluded.gravel", (ctx.guild.id, role.id))
        connection.commit()

        e = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self , ctx.guild.id, e, "emoji")

        if emoji is False:
            emojia = ""
        else:
            emojia = ":mute: "

        embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Changed Gravel Role:", desc=role.mention, useColor=1)
        await ctx.send(embed=embed)
        
    @setup.command(name="mute", help="Specifies the role given to someone who is muted", aliases=["muterole", "muted", "mutedrole"], brief=":mute: ")
    async def setup_mute(self, ctx, *, role:discord.Role):
        cursor.execute("INSERT INTO role_ids(guild, muted) VALUES(?,?) ON CONFLICT(guild) DO UPDATE SET muted=excluded.muted", (ctx.guild.id, role.id))
        connection.commit()

        e = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self , ctx.guild.id, e, "emoji")

        if emoji is False:
            emojia = ""
        else:
            emojia = ":mute: "

        embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Changed Muted Role:", desc=role.mention, useColor=1)
        await ctx.send(embed=embed)

    @setup.command(name="moderator", help="Sets the role used to determine whether a user can use moderation commands", aliases=["mod", "modrole"], brief=":hammer: ")
    async def setup_moderator(self, ctx, *, role:discord.Role):
        cursor.execute("INSERT INTO role_ids(guild, moderator) VALUES(?,?) ON CONFLICT(guild) DO UPDATE SET moderator=excluded.moderator", (ctx.guild.id, role.id))
        connection.commit()

        e = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self , ctx.guild.id, e, "emoji")

        if emoji is False:
            emojia = ""
        else:
            emojia = ":hammer: "

        embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Changed Moderator Role:", desc=role.mention, useColor=1)
        await ctx.send(embed=embed)

    @setup.command(name="admin", help="Sets the role used to determine whether a user can use admin commands", aliases=["adminrole"], brief=":tools:")
    async def setup_admin(self, ctx, *, role:discord.Role):
        cursor.execute("INSERT INTO role_ids(guild, admin) VALUES(?,?) ON CONFLICT(guild) DO UPDATE SET admin=excluded.admin", (ctx.guild.id, role.id))
        connection.commit()

        e = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self , ctx.guild.id, e, "emoji")

        if emoji is False:
            emojia = ""
        else:
            emojia = ":tools: "

        embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Admin role set", desc=role.mention, useColor=3)

        await ctx.send(embed=embed)

    @setup.command(name="command", help="Sets the role used to determine whether a user can use commands", aliases=["commandrole"], brief=":page_facing_up: ")
    async def setup_command(self, ctx, *, role:discord.Role=None):
        cursor.execute("INSERT INTO role_ids(guild, command_usage) VALUES(?,?) ON CONFLICT(guild) DO UPDATE SET command_usage=excluded.command_usage", (ctx.guild.id, getattr(role,"id",0)))
        connection.commit()

        e = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self , ctx.guild.id, e, "emoji")

        if emoji is False:
            emojia = ""
        else:
            emojia = ":page_facing_up: "

        embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Command role set", desc=role.mention, useColor=3)

        await ctx.send(embed=embed)

    @setup.command(name="cooldown", help="Sets the cooldown (in ms) between command uses", aliases=["commandCooldown","command_cooldown"], brief=":stopwatch: ")
    async def setup_cooldown(self, ctx, cooldown:int=0):
        cursor.execute("INSERT INTO role_ids(guild, command_cooldown) VALUES(?,?) ON CONFLICT(guild) DO UPDATE SET command_cooldown=excluded.command_cooldown", (ctx.guild.id, cooldown))
        connection.commit()

        e = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self , ctx.guild.id, e, "emoji")

        if emoji is False:
            emojia = ""
        else:
            emojia = ":stopwatch: "

        embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Cooldown set", desc=str(cooldown)+"ms", useColor=3)

        await ctx.send(embed=embed)

    @commands.group(aliases=["t"], brief=":label: ")
    @commands.check(tag_check)
    async def tag(self,ctx):
        """Predefined messages which can be triggered by commands."""
        if ctx.invoked_subcommand is not None:
            return
        tag = ctx.message.content
        if tag.find(' ') == -1:
            await ctx.send_help(ctx.command)
        tag = tag[tag.find(' ')+1:]
        guildTags = cursor.execute("SELECT * FROM tags WHERE guild = ?",(ctx.guild.id,)).fetchone()
        if ctx.guild.get_role(int(guildTags[1])) <= ctx.author.top_role:
            tags = json.loads(guildTags[2])
            try:
                if (texttag := tags[tag]["text"]) and (embedtag := tags[tag]["embed"]):
                    await ctx.send(texttag,embed=discord.Embed.from_dict(embedtag))
                elif (texttag := tags[tag]["text"]):
                    await ctx.send(texttag)
                elif (embedtag := tags[tag]["embed"]):
                    await ctx.send(embed=discord.Embed.from_dict(embedtag))
            except KeyError:
                pass

    @tag.command(name="(tag name)", brief=":placard: ")
    async def tag_tagname(self,ctx):
        """Sends the text assosiated to your tag."""
        return

    @tag.group(name="add",aliases=["new","set"], brief=":memo: ")
    @commands.check(functions.has_modrole)
    async def tag_add(self,ctx):
        """Sets a tags text assosiation."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @tag_add.command(name="text",aliases=["t"], brief=":placard: ")
    async def tag_add_text(self,ctx,tag,*,text):
        """Sets a tags text assosiation."""
        guildTags = cursor.execute("SELECT * FROM tags WHERE guild = ?",(ctx.guild.id,)).fetchone()
        tags = json.loads(guildTags[2])
        tags[tag] = {"text": text,"embed": None}
        cursor.execute("UPDATE tags SET tags=? WHERE guild=?",(json.dumps(tags),ctx.guild.id))
        connection.commit()
        await ctx.send("Tag updated.")

    @tag_add.command(name="simpleEmbed",aliases=["se","simpleembed","simple_embed"], brief=":bookmark_tabs: ")
    async def tag_add_simpleEmbed(self,ctx,tag,title,*,description=None):
        """Creates a simple embed with only a title and description.
        Title must be in "s and has a character limit of 256.."""
        guildTags = cursor.execute("SELECT * FROM tags WHERE guild = ?",(ctx.guild.id,)).fetchone()
        tags = json.loads(guildTags[2])
        tags[tag] = {"text": None,"embed": {"title":title,"description":description if description else ""}}
        cursor.execute("UPDATE tags SET tags=? WHERE guild=?",(json.dumps(tags),ctx.guild.id))
        connection.commit()
        await ctx.send("Tag updated.")

    @tag_add.command(name="embed",aliases=["e"], brief=":newspaper: ")
    async def tag_add_embed(self,ctx,tag,*,embed=None):
        """Creates an embed tag from the dictionary given,
        create an embed at [https://leovoel.github.io/embed-visualizer/](https://leovoel.github.io/embed-visualizer/) and copy the JSON over.
        It must a be a single line with no newlines, this can be done easily by pasting it into a browser address bar and copying it again.
        If it is larger than 2000 characters you may send it as a text file.
        Note: timestamp will be ignored."""
        if (embed is None and ctx.message.attachments):
            async with aiohttp.ClientSession() as session:
                async with session.get(ctx.message.attachments[0].url) as r:
                    if r.status == 200:
                        embed = json.loads(await r.text())
        elif (not ctx.message.attachments and embed is None):
            await ctx.send("You must send the embed JSON as text or attach a file containing the embed JSON if it is too large.")
        else:
            embed.replace("\n","")
            embed = json.loads(embed)
        guildTags = cursor.execute("SELECT * FROM tags WHERE guild = ?",(ctx.guild.id,)).fetchone()
        tags = json.loads(guildTags[2])
        if 'content' in embed.keys():
            text = embed["content"]
        else:
            text = None
        if 'embed' in embed.keys():
            if "timestamp" in embed["embed"].keys():
                embed["embed"].pop("timestamp")
            embed = embed["embed"]
        else:
            embed = None
        tags[tag] = {"text": text,"embed": embed}
        cursor.execute("UPDATE tags SET tags=? WHERE guild=?",(json.dumps(tags),ctx.guild.id))
        connection.commit()
        await ctx.send("Tag updated.")

    @tag.command(name="remove",aliases=["delete","del"], brief=":scissors: ")
    @commands.check(functions.has_modrole)
    async def tag_remove(self,ctx,tag):
        """Removes a tag text assosiation."""
        guildTags = cursor.execute("SELECT * FROM tags WHERE guild = ?",(ctx.guild.id,)).fetchone()
        tags = json.loads(guildTags[2])
        tags.pop(tag)
        cursor.execute("UPDATE tags SET tags=? WHERE guild=?",(json.dumps(tags),ctx.guild.id))
        connection.commit()
        await ctx.send("Tag updated.")

    @tag.command(name="list",aliases=["get"], brief=":file_cabinet: ")
    async def tag_list(self,ctx):
        """Lists tags and their text assosiation."""
        guildTags = cursor.execute("SELECT * FROM tags WHERE guild = ?",(ctx.guild.id,)).fetchone()
        tags = json.loads(guildTags[2])

        e = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self , ctx.guild.id, e, "emoji")

        if emoji is False:
            emojia = ""
        else:
            emojia = ":bookmark_tabs: "
        
        embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Tags:", desc=", ".join(tags.keys())+f"\n\nUsable by {ctx.guild.get_role(int(guildTags[1])).mention} and above.", useColor=2)
        await ctx.send(embed=embed)

    @tag.command(name="role", brief=":page_facing_up: ")
    @commands.check(functions.has_modrole)
    async def tag_role(self,ctx,*,role:discord.Role=None):
        """Sets the lowest role to be able to use tags."""
        if not role:
            role = ctx.author.top_role
        cursor.execute("UPDATE tags SET role=? WHERE guild=?",(role.id,ctx.guild.id))
        connection.commit()
        await ctx.send(f"Tag role set to {role.name}.")

    @commands.command()
    @commands.check(functions.has_modrole)
    async def ping(self, ctx):
        await ctx.send(f"Pong! {round((self.bot.latency*1000),4)} ms")



def setup(bot):
    bot.add_cog(Utilities(bot))
