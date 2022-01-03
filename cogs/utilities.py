import asyncio
import io
import json
import random
import typing

import aiohttp
import discord
from discord.ext import commands

import cogs.fancyEmbeds as fEmbeds
from utils import checks

class Utilities(commands.Cog):
    """Adds utilities for users!"""

    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.connection = bot.connection
        self.setup_running = []

    @commands.group(name="setup", help="setup some (or all) features of the bot", aliases=["su",], brief=":wrench: ")
    @commands.check_any(commands.has_permissions(administrator=True),commands.check(checks.has_adminrole))
    async def setup(self,ctx):
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self.bot.get_command('setup all'))

    @setup.command(help="Sets a server-specific bot prefix", name="prefix", aliases=["set_prefix",], brief=":pencil2: ")
    async def setup_prefix(self, ctx, prefix):
        cursor = await self.connection.cursor()
        await cursor.execute("INSERT INTO guild_prefixes(guild,prefix) VALUES(?, ?) ON CONFLICT(guild) DO UPDATE SET prefix=excluded.prefix", (ctx.guild.id, prefix))
        await self.connection.commit()
        await cursor.close()
        self.bot.guild_prefixes[ctx.guild.id] = prefix
        await ctx.send("Your new server-specific prefix is " + prefix)

    #all, chonky function
    @setup.command(help="Sets up all the bot's features", name="all", brief=":wrench: ")
    async def setup_all(self, ctx):
        guild = ctx.guild
        if guild.id in self.setup_running:
            await ctx.send("Someone is already setting up this server.")
            return
        self.setup_running.append(guild.id)
        setup_message = await ctx.send("Beginning server set-up")
        def check(response):
            return response.channel == ctx.channel and response.author == ctx.author
        async def get_message(convertTo=None,allowNone=False):
            while 1:
                try:
                    message = await self.bot.wait_for('message', timeout=60.0, check=check)
                except asyncio.TimeoutError:
                    await ctx.send("No response received. Cancelling")
                    return False
                content = message.content
                try:
                    await message.delete()
                except commands.MissingPermissions:
                    pass
                if content.lower() == "cancel":
                    await ctx.send("Cancelling..")
                    return False
                if (content.lower() == "none" and allowNone):
                    return None
                try:
                    if convertTo == "role":
                        content = await commands.RoleConverter().convert(ctx,content)
                    elif convertTo == "channel":
                        content = await commands.TextChannelConverter().convert(ctx,content)
                except (commands.RoleNotFound, commands.ChannelNotFound) as e:
                    await ctx.send(f"That {convertTo} could not be found. Try again and make sure the capitalisation and spelling is correct.",delete_after=3)
                    continue
                if convertTo == "int":
                    try:
                        content = int(content)
                    except:
                        await ctx.send("That doesn't seem to be a valid number. Try again.",delete_after=3)
                        continue
                return content

        await setup_message.edit(content="First, please say the name of your gravel role. (case sensitive)")
        gravelRole = await get_message("role")
        if gravelRole is False:
            return
        await setup_message.edit(content="Next, please give the name of your muted role.")
        mutedRole = await get_message("role")
        if mutedRole is False:
            return
        await setup_message.edit(content="Ok, now please tell me what the name is for your moderator role (people with this role will be able to use mod-only commands).")
        modRole = await get_message("role")
        if modRole is False:
            return
        await setup_message.edit(content="Now for the name of your admin role (people with this role will be able to use admin-only commands).")
        adminRole = await get_message("role")
        if adminRole is False:
            return
        await setup_message.edit(content="Please say the name of your trial moderator role (or 'none' for no role)")
        trialRole = await get_message("role",True)
        if trialRole is False:
            return
        await setup_message.edit(content="Enter the name of your commands role or 'none' for no role (if supplied, this role will be required to use any commands).")
        commandRole = await get_message("role",True)
        if commandRole is False:
            return
        await setup_message.edit(content="Enter the cooldown for your commands (in milliseconds) or type 'none' for no cooldown (cooldown does not apply to mods and admins).")
        commandCooldown = await get_message("int",True)
        if commandCooldown is False:
            return
        elif commandCooldown is None:
            commandCooldown = 0
        await setup_message.edit(content="Almost there! Please send me your modlog channel, or type \"None\" if you do not want a modlog channel.")
        logChannel = await get_message("channel",True)
        if logChannel is False:
            return
        await setup_message.edit(content="Last, please tell me what prefix you would like to use for commands")
        prefix = await get_message()
        if prefix is False:
            return
        await setup_message.delete()

        self.bot.guild_prefixes[ctx.guild.id] = prefix
        self.bot.modrole[ctx.guild.id] = modRole.id
        self.bot.adminrole[ctx.guild.id] = adminRole.id
        if trialRole is not None:
            self.bot.trialrole[ctx.guild.id] = trialRole.id

        cursor = await self.connection.cursor()
        await cursor.execute("INSERT INTO guild_prefixes(guild,prefix) VALUES(?, ?) ON CONFLICT(guild) DO UPDATE SET prefix=excluded.prefix", (guild.id, prefix))
        await cursor.execute("INSERT INTO role_ids(guild,gravel,muted,moderator,admin,trialmod,modlogs,command_usage,command_cooldown) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(guild) DO UPDATE SET gravel=excluded.gravel, muted=excluded.muted, moderator=excluded.moderator, admin=excluded.admin, trialmod=excluded.trialmod, modlogs=excluded.modlogs, command_usage=excluded.command_usage, command_cooldown=excluded.command_cooldown", (guild.id, gravelRole.id, mutedRole.id, modRole.id, adminRole.id, getattr(trialRole,"id",0),getattr(logChannel,"id",0), getattr(commandRole,"id",0),commandCooldown))
        await self.connection.commit()
        await cursor.close()


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
            emojij = ""
        else:
            emojia = ":wrench: "
            emojib = ":mute: "
            emojic = ":mute: "
            emojid = ":hammer_pick: "
            emojie = ":tools: "
            emojif = ":hammer: "
            emojig = ":file_folder: "
            emojih = ":page_facing_up: "
            emojii = ":stopwatch: "
            emojij = ":pencil2: "
            

        response = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Server set up successfully!", useColor=0)
        response.add_field(name=f"{emojib}Gravel role", value=gravelRole.mention)
        response.add_field(name=f"{emojic}Muted role", value=mutedRole.mention)
        response.add_field(name=f"{emojid}Moderator role", value=modRole.mention)
        response.add_field(name=f"{emojie}Admin role", value=adminRole.mention)
        response.add_field(name=f"{emojif}Trial Mod role", value=getattr(trialRole,"mention","None"))
        response.add_field(name=f"{emojig}Modlog channel", value=getattr(logChannel,"mention","None"))
        response.add_field(name=f"{emojih}Command role", value=getattr(commandRole,"mention","None"))
        response.add_field(name=f"{emojii}Command cooldown", value=f"{commandCooldown / 1000} Seconds")
        response.add_field(name=f"{emojij}Command Prefix", value=f"`{prefix}`")

        await ctx.send(embed=response)

    @setup.after_invoke
    async def setup_all_after_invoke(self,ctx):
        if ctx.message.content.endswith("all") or ctx.message.content.endswith("setup"):
            if ctx.guild.id in self.setup_running:
                self.setup_running.remove(ctx.guild.id)

    @setup.command(name="modlogs", help="Specifies the channel to be used for modlogs, do not specify a channel to remove logs.", aliases=["logchannel", "modlog", "logs",], brief=":file_folder: ")
    async def setup_modlogs(self, ctx, *, channel:discord.TextChannel=None):
        cursor = await self.connection.cursor()
        if channel:
            try:
                await channel.send("Set up modlogs in this channel!")
                await ctx.send(f"Set up modlogs in {channel.mention}!")
                await cursor.execute("INSERT INTO role_ids(guild, modlogs) VALUES(?,?) ON CONFLICT(guild) DO UPDATE SET modlogs=excluded.modlogs", (ctx.guild.id, channel.id))
            except:
                await ctx.send("Something went wrong. Please make sure you specify a valid channel, and that I have permissions to send messages to it")
                return
        else:
            await cursor.execute("INSERT INTO role_ids(guild,modlogs) VALUES(?,?) ON CONFLICT(guild) DO UPDATE SET modlogs=excluded.modlogs", (ctx.guild.id, 0))
            await ctx.send("Turned off modlogs")
        await self.connection.commit()
        await cursor.close()

    @setup.command(name="gravel", help="Specifies the role given to someone who is graveled", aliases=["gravelrole",], brief=":mute: ")
    async def setup_gravel(self, ctx, role:discord.Role):
        cursor = await self.connection.cursor()
        await cursor.execute("INSERT INTO role_ids(guild, gravel) VALUES(?,?) ON CONFLICT(guild) DO UPDATE SET gravel=excluded.gravel", (ctx.guild.id, role.id))
        await self.connection.commit()
        await cursor.close()

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
        cursor = await self.connection.cursor()
        await cursor.execute("INSERT INTO role_ids(guild, muted) VALUES(?,?) ON CONFLICT(guild) DO UPDATE SET muted=excluded.muted", (ctx.guild.id, role.id))
        await self.connection.commit()
        await cursor.close()

        e = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self , ctx.guild.id, e, "emoji")

        if emoji is False:
            emojia = ""
        else:
            emojia = ":mute: "

        embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Changed Muted Role:", desc=role.mention, useColor=1)
        await ctx.send(embed=embed)

    @setup.command(name="moderator", help="Sets the role used to determine whether a user can use moderation commands", aliases=["mod", "modrole"], brief=":hammer_pick: ")
    async def setup_moderator(self, ctx, *, role:discord.Role):
        cursor = await self.connection.cursor()
        await cursor.execute("INSERT INTO role_ids(guild, moderator) VALUES(?,?) ON CONFLICT(guild) DO UPDATE SET moderator=excluded.moderator", (ctx.guild.id, role.id))
        await self.connection.commit()
        await cursor.close()

        self.bot.modrole[ctx.guild.id] = role.id
        e = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self , ctx.guild.id, e, "emoji")

        if emoji is False:
            emojia = ""
        else:
            emojia = ":hammer_pick: "

        embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Changed Moderator Role:", desc=role.mention, useColor=1)
        await ctx.send(embed=embed)

    @setup.command(name="admin", help="Sets the role used to determine whether a user can use admin commands", aliases=["adminrole"], brief=":tools:")
    async def setup_admin(self, ctx, *, role:discord.Role):
        cursor = await self.connection.cursor()
        await cursor.execute("INSERT INTO role_ids(guild, admin) VALUES(?,?) ON CONFLICT(guild) DO UPDATE SET admin=excluded.admin", (ctx.guild.id, role.id))
        await self.connection.commit()
        await cursor.close()

        self.bot.modrole[ctx.guild.id] = role.id
        e = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self , ctx.guild.id, e, "emoji")

        if emoji is False:
            emojia = ""
        else:
            emojia = ":tools: "

        embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Admin role set", desc=role.mention, useColor=3)

        await ctx.send(embed=embed)

    @setup.command(name="trial", help="Sets the role used to determine whether a user is a trial mod.", aliases=["trialrole"], brief=":hammer:")
    async def setup_trial(self, ctx, *, role:discord.Role):
        cursor = await self.connection.cursor()
        await cursor.execute("INSERT INTO role_ids(guild, trialmod) VALUES(?,?) ON CONFLICT(guild) DO UPDATE SET trialmod=excluded.trialmod", (ctx.guild.id, role.id))
        await self.connection.commit()
        await cursor.close()

        self.bot.trialrole[ctx.guild.id] = role.id
        e = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self , ctx.guild.id, e, "emoji")

        if emoji is False:
            emojia = ""
        else:
            emojia = ":hammer: "

        embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Trial Mod role set", desc=role.mention, useColor=3)

        await ctx.send(embed=embed)

    @setup.command(name="command", help="Sets the role used to determine whether a user can use commands", aliases=["commandrole"], brief=":page_facing_up: ")
    async def setup_command(self, ctx, *, role:discord.Role=None):
        cursor = await self.connection.cursor()
        await cursor.execute("INSERT INTO role_ids(guild, command_usage) VALUES(?,?) ON CONFLICT(guild) DO UPDATE SET command_usage=excluded.command_usage", (ctx.guild.id, getattr(role,"id",0)))
        await self.connection.commit()
        await cursor.close()

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
        cursor = await self.connection.cursor()
        await cursor.execute("INSERT INTO role_ids(guild, command_cooldown) VALUES(?,?) ON CONFLICT(guild) DO UPDATE SET command_cooldown=excluded.command_cooldown", (ctx.guild.id, cooldown))
        await self.connection.commit()
        await cursor.close()

        e = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self , ctx.guild.id, e, "emoji")

        if emoji is False:
            emojia = ""
        else:
            emojia = ":stopwatch: "

        embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Cooldown set", desc=str(cooldown)+"ms", useColor=3)

        await ctx.send(embed=embed)

    @commands.group(aliases=["t"], brief=":label: ")
    async def tag(self,ctx):
        """Predefined messages which can be triggered by commands."""
        if ctx.invoked_subcommand is not None:
            return
        tag = ctx.message.content
        if tag.find(' ') == -1:
            await ctx.send_help(ctx.command)
        tag = tag[tag.find(' ')+1:]
        cursor = await self.connection.execute("SELECT tags FROM tags WHERE guild = ?",(ctx.guild.id,))
        guildTags = await cursor.fetchone()
        await cursor.close()
        tags = json.loads(guildTags[0])
        try:
            if (texttag := tags[tag]["text"]) and (embedtag := tags[tag]["embed"]):
                await ctx.send(texttag,embed=discord.Embed.from_dict(embedtag))
            elif (texttag := tags[tag]["text"]):
                await ctx.send(texttag)
            elif (embedtag := tags[tag]["embed"]):
                await ctx.send(embed=discord.Embed.from_dict(embedtag))
        except KeyError:
            pass

    @tag.before_invoke
    async def tag_before_invoke(self,ctx):
        if not (ctx.command.root_parent == "tag" or ctx.command.name == "tag"): # Check is not coming from a tag command so return True
            return
        cursor = await ctx.bot.connection.execute("SELECT tags FROM tags WHERE guild = ?", (ctx.guild.id,))
        tags = await cursor.fetchone()
        if (tags is None): # No guild tags and the user can manage messages
            await cursor.execute("INSERT INTO tags(guild,tags) VALUES(?,?)",(ctx.guild.id,"{}"))
            await ctx.bot.connection.commit()
            await ctx.send(f"Tags created.")

    @tag.command(name="(tag name)", brief=":placard: ")
    async def tag_tagname(self,ctx):
        """Sends the text assosiated to your tag."""
        return

    @tag.group(name="add",aliases=["new","set"], brief=":memo: ")
    @commands.check(checks.has_modrole)
    async def tag_add(self,ctx):
        """Sets a tags text assosiation."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @tag_add.command(name="text",aliases=["t"], brief=":placard: ")
    async def tag_add_text(self,ctx,tag,*,text):
        """Sets a tags text assosiation."""
        cursor = await self.connection.execute("SELECT tags FROM tags WHERE guild = ?",(ctx.guild.id,))
        guildTags = await cursor.fetchone()
        tags = json.loads(guildTags[0])
        tags[tag] = {"text": text,"embed": None}
        await cursor.execute("UPDATE tags SET tags=? WHERE guild=?",(json.dumps(tags),ctx.guild.id))
        await self.connection.commit()
        await cursor.close()
        await ctx.send("Tag updated.")

    @tag_add.command(name="simpleEmbed",aliases=["se","simpleembed","simple_embed"], brief=":bookmark_tabs: ")
    async def tag_add_simpleEmbed(self,ctx,tag,title,*,description=None):
        """Creates a simple embed with only a title and description.
        Title must be in "s and has a character limit of 256.."""
        cursor = await self.connection.execute("SELECT tags FROM tags WHERE guild = ?",(ctx.guild.id,))
        guildTags = await cursor.fetchone()
        tags = json.loads(guildTags[0])
        tags[tag] = {"text": None,"embed": {"title":title,"description":description if description else ""}}
        await cursor.execute("UPDATE tags SET tags=? WHERE guild=?",(json.dumps(tags),ctx.guild.id))
        await self.connection.commit()
        await cursor.close()
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
        cursor = await self.connection.execute("SELECT tags FROM tags WHERE guild = ?",(ctx.guild.id,))
        guildTags = await cursor.fetchone()
        tags = json.loads(guildTags[0])
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
        await cursor.execute("UPDATE tags SET tags=? WHERE guild=?",(json.dumps(tags),ctx.guild.id))
        await self.connection.commit()
        await cursor.close()
        await ctx.send("Tag updated.")

    @tag.command(name="remove",aliases=["delete","del"], brief=":scissors: ")
    @commands.check(checks.has_modrole)
    async def tag_remove(self,ctx,tag):
        """Removes a tag text assosiation."""
        cursor = await self.connection.execute("SELECT tags FROM tags WHERE guild = ?",(ctx.guild.id,))
        guildTags = await cursor.fetchone()
        tags = json.loads(guildTags[0])
        tags.pop(tag)
        await cursor.execute("UPDATE tags SET tags=? WHERE guild=?",(json.dumps(tags),ctx.guild.id))
        await self.connection.commit()
        await cursor.close()
        await ctx.send("Tag updated.")

    @tag.command(name="list",aliases=["get"], brief=":file_cabinet: ")
    async def tag_list(self,ctx):
        """Lists tags and their text assosiation."""
        cursor = await self.connection.execute("SELECT tags FROM tags WHERE guild = ?",(ctx.guild.id,))
        guildTags = await cursor.fetchone()
        await cursor.close()
        if guildTags:
            tags = json.loads(guildTags[0])
        else:
            tags = {}

        e = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self , ctx.guild.id, e, "emoji")

        if emoji is False:
            emojia = ""
        else:
            emojia = ":bookmark_tabs: "

        embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Tags:", useColor=2)
        await ctx.send(embed=embed)

    @commands.command(name="tags", brief=":file_cabinet: ",hidden=True)
    async def tags(self,ctx):
        await ctx.invoke(self.bot.get_command("tag list"))

    @commands.command(brief=":ping_pong: ")
    @commands.check(checks.has_modrole)
    async def ping(self, ctx):
        """Pong!"""
        await ctx.send(f"Pong! {round((self.bot.latency*1000),4)} ms")

    @commands.command(brief=":speech_balloon: ")
    @commands.check(checks.has_modrole)
    async def embed_message(self, ctx, *, text):
        """Sends a message to the channel the command is used in, contained within an embed."""
        embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, desc=text, useColor=0)
        await ctx.send(embed=embed)
        await ctx.message.delete()

    @commands.command(brief=":speech_balloon: ")
    @commands.check(checks.has_modrole)
    async def message(self, ctx, *, text):
        """Sends a message to the channel the command is used in."""
        await ctx.send(text)
        await ctx.message.delete()

def setup(bot):
    bot.add_cog(Utilities(bot))
