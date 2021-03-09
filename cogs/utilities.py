import discord
from discord.ext import commands
import sqlite3
import asyncio
import json
import random
import requests

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
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.bot.send_help = self.send_command_help
    
    @commands.command(help="Sets a server-specific bot prefix", aliases=["set_prefix",])
    @commands.has_permissions(administrator=True)
    async def change_prefix(self, ctx, arg):
        cursor.execute("INSERT INTO guild_prefixes(guild,prefix) VALUES(?, ?) ON CONFLICT(guild) DO UPDATE SET prefix=excluded.prefix", (ctx.guild.id, arg))
        connection.commit()
        await ctx.send("Your new server-specific prefex is " + arg)

    #setup, ideally will only be used the first time the bot joins
    @commands.command(help="Sets up all the bot's features")
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx):
        guild = ctx.guild
        await ctx.send("Beginning server set-up")
        await ctx.send("First, please give the ID (it will be a number) of your gravel role")
        def check(response):
            return response.channel == ctx.channel and response.author == ctx.author
        try:
            gravel = await self.bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("No response received. Cancelling")
            return
        gravel = gravel.content
        try:
            gravelRole = guild.get_role(int(gravel))
        except ValueError:
            gravelRole = False
        if not gravelRole:
            await ctx.send("That does not appear to be a valid role ID. Cancelling")
            return
        await ctx.send("Next, please give the ID of your muted role")
        try:
            muted = await self.bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("No response recieved. Cancelling")
            return
        muted = muted.content
        try:
            mutedRole = guild.get_role(int(muted))
        except ValueError:
            mutedRole = False
        if not mutedRole:
            await ctx.send("That does not appear to be a valid role ID. Cancelling")
            return
        await ctx.send("Now, please send the ID (not a mention) of your modlog channel")
        try:
            modlogs = await self.bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("No response recieved. Cancelling")
            return
        modlogs = modlogs.content
        try:
            logchannel = guild.get_channel(int(modlogs))
        except ValueError:
            logchannel = False
        if not logchannel:
            await ctx.send("That does not appear to be a valid channel ID. Cancelling")
            return
        await ctx.send("Last, please tell me what prefix you would like to use for commands")
        try:
            prefix = await self.bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("No response recieved. Cancelling")
            return
        cursor.execute("INSERT INTO guild_prefixes(guild,prefix) VALUES(?, ?) ON CONFLICT(guild) DO UPDATE SET prefix=excluded.prefix", (guild.id, prefix.content))
        cursor.execute("INSERT INTO role_ids(guild,gravel,muted) VALUES(?, ?, ?) ON CONFLICT(guild) DO UPDATE SET gravel=excluded.gravel, muted=excluded.muted", (guild.id, gravel, muted))
        cursor.execute("INSERT INTO modlog_channels(guild,channel) VALUES(?,?) ON CONFLICT(guild) DO UPDATE SET channel = excluded.channel", (guild.id, modlogs))
        connection.commit()
        response = discord.Embed(title="Server set up successfully!", color=0x00FF00)
        response.add_field(name="Gravel role", value=gravelRole.mention) 
        response.add_field(name="Muted role", value=mutedRole.mention)
        response.add_field(name="Modlog channel", value=logchannel.mention)
        await ctx.send(embed=response)

    @commands.group(aliases=["t"])
    @commands.check(tag_check)
    async def tag(self,ctx):
        """Predefined messages which can be triggered by commands."""
        if ctx.invoked_subcommand is not None:
            return
        tag = ctx.message.content
        if tag.find(' ') == -1:
            await self.bot.send_help(ctx)
        tag = tag[tag.find(' ')+1:]
        guildTags = cursor.execute("SELECT * FROM tags WHERE guild = ?",(ctx.guild.id,)).fetchone()
        if ctx.guild.get_role(int(guildTags[1])) <= ctx.author.top_role:
            tags = json.loads(guildTags[2])
            try:
                if tags[tag]["text"] and tags[tag]["embed"]:
                    await ctx.send(tags[tag]["text"],embed=discord.Embed.from_dict(tags[tag]["embed"]))
                elif tags[tag]["text"]:
                    await ctx.send(tags[tag]["text"])
                elif tags[tag]["embed"]:
                    await ctx.send(embed=discord.Embed.from_dict(tags[tag]["embed"]))
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
            await self.bot.send_help(ctx)

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
            response = requests.get(ctx.message.attachments[0].url)
            response.raise_for_status()
            embed = response.json()
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
        colour = discord.Colour.from_rgb(random.randint(1,255),random.randint(1,255),random.randint(1,255))
        embed = discord.Embed(colour=colour,title=f"Tags.",description=", ".join(tags.keys())+f"\n\nUsable by {ctx.guild.get_role(int(guildTags[1])).mention} and above.")
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

    async def send_all_help(self,ctx,pageOut):
        colour = discord.Colour.from_rgb(random.randint(1,255),random.randint(1,255),random.randint(1,255))
        titleDesc = ["YayaBot Help!",f"Say `{ctx.prefix}help <command>` for more info on a command!"] 
        page = [discord.Embed(colour=colour,title=titleDesc[0],description=titleDesc[1])]
        cogs = sorted(list(self.bot.cogs.keys()))
        fields = 0
        for cog in cogs:
            cog_command = False
            if fields == 25:
                page.append(discord.Embed(colour=colour,title=titleDesc[0],description=titleDesc[1]))
                fields = 0
            page[-1].add_field(name=f"—————————————————————————", value=f"**{cog}**", inline=False)
            fields += 1
            for command in self.bot.cogs[cog].get_commands():
                try:
                    can_run = await command.can_run(ctx)
                except:
                    can_run = False
                if can_run:
                    cog_command = True
                    if fields == 25:
                        page.append(discord.Embed(colour=colour,title=titleDesc[0],description=titleDesc[1]))
                        fields = 0
                        page[-1].add_field(name=f"—————————————————————————", value=f"**{cog}**", inline=False)
                    if command.help:
                        description = command.help.replace("\n"," ")
                        if len(description) > 200:
                            description = description[:197] + "..."
                    else:
                        description = "..."
                    page[-1].add_field(name=f"{command.name}", value=f"{description}", inline=True)
                    fields += 1
            if not cog_command:
                page[-1].remove_field(len(page[-1].fields)-1)
        if pageOut + 1 > len(page):
            pageOut = len(page) - 1
        page[pageOut].set_footer(text=f"{pageOut+1} of {len(page)}")
        msg = await ctx.send(embed=page[pageOut])
        if len(page) == 1:
            return
        for emoji in ["⏪","◀️","▶️","⏩"]:
            await msg.add_reaction(emoji)
        def check(react, user):
            return react.message == msg and (ctx.message.author == user and str(react.emoji) in ["⏪","◀️","▶️","⏩"])
        while True:
            try:
                reaction,user = await self.bot.wait_for("reaction_add",timeout=30,check=check)
            except asyncio.TimeoutError:
                await msg.clear_reactions()
                break
            pageOut = {"⏪":0,"◀️":(pageOut-1) if pageOut-1 >= 0 else pageOut,"▶️":(pageOut+1) if pageOut+1 < len(page) else pageOut,"⏩":len(page)-1}[str(reaction.emoji)]
            page[pageOut].set_footer(text=f"{pageOut+1} of {len(page)}")
            await msg.edit(embed=page[pageOut])
            await reaction.remove(user)

    async def send_command_help(self,ctx,command=None):
        command = self.bot.get_command(command) if command else ctx.command
        if not command:
            await ctx.send("Command could not be found.")
            return
        try:
            await command.can_run(ctx)
        except:
            return
        random.seed(command.qualified_name)
        colour = discord.Colour.from_rgb(random.randint(1,255),random.randint(1,255),random.randint(1,255))
        random.seed()
        embed = discord.Embed(colour=colour,title=f"Help for {command.qualified_name}",description=(f"Aliases: {', '.join(list(command.aliases))}" if command.aliases else ""))
        embed.add_field(name="Usage",value=f"`{ctx.prefix}{command.qualified_name}{(' ' + command.signature.replace('_',' ')    ) if command.signature else ' <subcommand>' if isinstance(command,commands.Group) else ''}`")
        embed.add_field(name="Description",value=(command.help.replace("[p]",ctx.prefix) if command.help else '...'),inline=False)
        if isinstance(command,commands.Group):
            embed.add_field(name="———————",value="**Subcommands**",inline=False)
            subFields = 0
            for subcommand in sorted(command.commands, key=lambda x: x.name):
                if subcommand.help:
                    description = subcommand.help.replace("\n"," ")
                    if len(description) > 100:
                        description = description[:97] + "..."
                else:
                    description = "..."
                embed.add_field(name=subcommand.name,value=description, inline=True)
                subFields += 1
            while not subFields % 3 == 0:
                embed.add_field(name=".",value=".", inline=True)
                subFields += 1
        await ctx.send(embed=embed)
        

    @commands.command()
    async def help(self,ctx,*,command=None):
        """Displays help, like what you're seeing now!"""
        if not command:
            command = 1
        try:
            pageOut = int(command)-1
        except:
            pageOut = None
        if pageOut is not None:
            await self.send_all_help(ctx,pageOut)
            return
        await self.send_command_help(ctx,command)
        
def setup(bot):
    bot.add_cog(Utilities(bot))