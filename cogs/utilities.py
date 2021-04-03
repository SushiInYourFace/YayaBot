import discord
from discord.ext import commands
import sqlite3
import asyncio
import json
import random
import aiohttp

#sets up SQLite
connection = sqlite3.connect("database.db")
cursor = connection.cursor()

async def tag_check(ctx):
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

    @commands.group(name="setup", help="setup some (or all) features of the bot", aliases=["su",])
    @commands.has_permissions(administrator=True)
    async def setup(self,ctx):
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self.bot.get_command('setup all'),)
    
    @setup.command(help="Sets a server-specific bot prefix", name="prefix", aliases=["set_prefix",])
    async def setup_prefix(self, ctx, prefix):
        cursor.execute("INSERT INTO guild_prefixes(guild,prefix) VALUES(?, ?) ON CONFLICT(guild) DO UPDATE SET prefix=excluded.prefix", (ctx.guild.id, prefix))
        connection.commit()
        await ctx.send("Your new server-specific prefex is " + prefix)

    #all, chonky function
    @setup.command(help="Sets up all the bot's features", name="all")
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
        gravel = await get_message()
        try:
            gravelRole = await commands.RoleConverter().convert(ctx,gravel.content)
        except commands.RoleNotFound:
            await ctx.send("That does not appear to be a valid role. Cancelling")
            return
        await ctx.send("Next, please give the name of your muted role.")
        muted = await get_message()
        try:
            mutedRole = await commands.RoleConverter().convert(ctx,muted.content)
        except commands.RoleNotFound:
            await ctx.send("That does not appear to be a valid role. Cancelling")
            return
        await ctx.send("Ok, now please tell me what the name is for your moderator role (people with this role will be able to use mod-only commands).")
        moderator = await get_message()
        try:
            modRole = await commands.RoleConverter().convert(ctx,moderator.content)
        except commands.RoleNotFound:
            await ctx.send("That does not appear to be a valid role. Cancelling")
            return
        await ctx.send("Almost there! Please send me your modlog channel, or type \"None\" if you do not want a modlog channel.")
        modlogs = await get_message()
        if modlogs.content.lower() != "none":
            try:
                logChannel = await commands.TextChannelConverter().convert(ctx,muted.content)
                modlogs = logChannel.id
            except commands.ChannelNotFound:
                await ctx.send("That does not appear to be a valid channel. Cancelling")
                return
        else:
            modlogs = 0
            logChannel = None
        await ctx.send("Last, please tell me what prefix you would like to use for commands")
        prefix = await get_message()

        cursor.execute("INSERT INTO guild_prefixes(guild,prefix) VALUES(?, ?) ON CONFLICT(guild) DO UPDATE SET prefix=excluded.prefix", (guild.id, prefix.content))
        cursor.execute("INSERT INTO role_ids(guild,gravel,muted,moderator, modlogs) VALUES(?, ?, ?, ?, ?) ON CONFLICT(guild) DO UPDATE SET gravel=excluded.gravel, muted=excluded.muted, moderator=excluded.moderator, modlogs=excluded.modlogs", (guild.id, gravelRole.id, mutedRole.id, modRole.id, modlogs))
        connection.commit()

        response = discord.Embed(title="Server set up successfully!", color=0x00FF00)
        response.add_field(name="Gravel role", value=gravelRole.mention) 
        response.add_field(name="Muted role", value=mutedRole.mention)
        response.add_field(name="Moderator role", value=modRole.mention)
        response.add_field(name="Modlog channel", value=getattr(logChannel,"mention","None"))
        await ctx.send(embed=response)

    @setup.command(name="modlogs", help="Specifies the channel to be used for modlogs, do not specify a channel to remove logs.", aliases=["logchannel", "modlog", "logs",])
    async def setup_modlogs(self, ctx, channel:discord.TextChannel=None):
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

    @setup.command(name="gravel", help="Specifies the role given to someone who is graveled", aliases=["gravelrole",])
    async def setup_gravel(self, ctx, role:discord.Role):
        cursor.execute("INSERT INTO role_ids(guild, gravel) VALUES(?,?) ON CONFLICT(guild) DO UPDATE SET gravel=excluded.gravel", (ctx.guild.id, role.id))
        connection.commit()
        embed = discord.Embed(title="Gravel role set",description=role.mention)
        await ctx.send(embed=embed)
        
    @setup.command(name="mute", help="Specifies the role given to someone who is muted", aliases=["muterole", "muted", "mutedrole"])
    async def setup_mute(self, ctx, role:discord.Role):
        cursor.execute("INSERT INTO role_ids(guild, muted) VALUES(?,?) ON CONFLICT(guild) DO UPDATE SET muted=excluded.muted", (ctx.guild.id, role.id))
        connection.commit()
        embed = discord.Embed(title="Muted role set",description=role.mention)
        await ctx.send(embed=embed)

    @setup.command(name="moderator", help="Sets the role used to determine whether a user can use moderation commands", aliases=["mod", "modrole"])
    async def setup_moderator(self, ctx, role:discord.Role=None):
        cursor.execute("INSERT INTO role_ids(guild, moderator) VALUES(?,?) ON CONFLICT(guild) DO UPDATE SET moderator=excluded.moderator", (ctx.guild.id, role.id))
        connection.commit()
        embed = discord.Embed(title="Moderator role set",description=role.mention)
        await ctx.send(embed=embed)

    @commands.group(aliases=["t"])
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

    @tag.command(name="(tag name)")
    async def tag_tagname(self,ctx):
        """Sends the text assosiated to your tag."""
        return

    @tag.group(name="set",aliases=["new","add"])
    @commands.has_permissions(manage_messages=True)
    async def tag_set(self,ctx):
        """Sets a tags text assosiation."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @tag_set.command(name="text",aliases=["t"])
    @commands.has_permissions(manage_messages=True)
    async def tag_set_text(self,ctx,tag,*,text):
        """Sets a tags text assosiation."""
        guildTags = cursor.execute("SELECT * FROM tags WHERE guild = ?",(ctx.guild.id,)).fetchone()
        tags = json.loads(guildTags[2])
        tags[tag] = {"text": text,"embed": None}
        cursor.execute("UPDATE tags SET tags=? WHERE guild=?",(json.dumps(tags),ctx.guild.id))
        connection.commit()
        await ctx.send("Tag updated.")

    @tag_set.command(name="simpleEmbed",aliases=["se","simpleembed","simple_embed"])
    async def tag_set_simpleEmbed(self,ctx,tag,title,*,description=None):
        """Creates a simple embed with only a title and description.
        Title must be in "s and has a character limit of 256.."""
        guildTags = cursor.execute("SELECT * FROM tags WHERE guild = ?",(ctx.guild.id,)).fetchone()
        tags = json.loads(guildTags[2])
        tags[tag] = {"text": None,"embed": {"title":title,"description":description if description else ""}}
        cursor.execute("UPDATE tags SET tags=? WHERE guild=?",(json.dumps(tags),ctx.guild.id))
        connection.commit()
        await ctx.send("Tag updated.")

    @tag_set.command(name="embed",aliases=["e"])
    async def tag_set_embed(self,ctx,tag,*,embed=None):
        """Creates an embed tag from the dictionary given,
        create an embed at https://leovoel.github.io/embed-visualizer/ and copy the JSON over.
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

    @tag.command(name="remove",aliases=["delete","del"])
    @commands.has_permissions(manage_messages=True)
    async def tag_remove(self,ctx,tag):
        """Removes a tag text assosiation."""
        guildTags = cursor.execute("SELECT * FROM tags WHERE guild = ?",(ctx.guild.id,)).fetchone()
        tags = json.loads(guildTags[2])
        tags.pop(tag)
        cursor.execute("UPDATE tags SET tags=? WHERE guild=?",(json.dumps(tags),ctx.guild.id))
        connection.commit()
        await ctx.send("Tag updated.")

    @tag.command(name="list",aliases=["get"])
    async def tag_list(self,ctx):
        """Lists tags and their text assosiation."""
        guildTags = cursor.execute("SELECT * FROM tags WHERE guild = ?",(ctx.guild.id,)).fetchone()
        tags = json.loads(guildTags[2])
        embed = discord.Embed(colour=discord.Colour.random(),title="Tags.",description=", ".join(tags.keys())+f"\n\nUsable by {ctx.guild.get_role(int(guildTags[1])).mention} and above.")
        embed.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @tag.command(name="role")
    @commands.has_permissions(manage_messages=True)
    async def tag_role(self,ctx,*,role:discord.Role=None):
        """Sets the lowest role to be able to use tags."""
        if not role:
            role = ctx.author.top_role
        cursor.execute("UPDATE tags SET role=? WHERE guild=?",(role.id,ctx.guild.id))
        connection.commit()
        await ctx.send(f"Tag role set to {role.name}.")

def setup(bot):
    bot.add_cog(Utilities(bot))