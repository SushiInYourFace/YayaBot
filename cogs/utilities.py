import discord
from discord.ext import commands
import sqlite3
import asyncio
import json
import random

#sets up SQLite
connection = sqlite3.connect("database.db")
cursor = connection.cursor()

async def tag_check(ctx):
    tags = cursor.execute("SELECT * FROM tags WHERE guild = ?", (ctx.guild.id,)).fetchone()
    if (tags is None and ctx.author.guild_permissions.manage_messages):
        cursor.execute("INSERT INTO tags(guild,role,tags) VALUES(?,?,?)",(ctx.guild.id,ctx.author.top_role.id,"{}"))
        connection.commit()
        await ctx.send(f"Tags created and role set to {ctx.author.top_role.name}.")
        tags = cursor.execute("SELECT * FROM tags WHERE guild = ?", (ctx.guild.id,)).fetchone()
    elif tags is None:
        return False
    if ctx.guild.get_role(int(tags[1])) <= ctx.author.top_role:
        return True
    return False


class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
    
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
        await ctx.send("Last, please tell me what prefix you would like to use for commands")
        try:
            prefix = await self.bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("No response recieved. Cancelling")
            return
        cursor.execute("INSERT INTO guild_prefixes(guild,prefix) VALUES(?, ?) ON CONFLICT(guild) DO UPDATE SET prefix=excluded.prefix", (guild.id, prefix.content))
        cursor.execute("INSERT INTO role_ids(guild,gravel,muted) VALUES(?, ?, ?) ON CONFLICT(guild) DO UPDATE SET gravel=excluded.gravel, muted=excluded.muted", (guild.id, gravel, muted))
        connection.commit()
        response = discord.Embed(title="Server set up successfully!", color=0x00FF00)
        response.add_field(name="Gravel role", value=gravelRole.mention) 
        response.add_field(name="Muted role", value=mutedRole.mention)
        await ctx.send(embed=response)

    @commands.group(aliases=["t"])
    @commands.check(tag_check)
    async def tag(self,ctx):
        """Predefined messages which can be triggered by commands."""
        if ctx.invoked_subcommand is not None:
            return
        tag = ctx.message.content
        tag = tag[tag.find(' ')+1:]
        guildTags = cursor.execute("SELECT * FROM tags WHERE guild = ?",(ctx.guild.id,)).fetchone()
        if ctx.guild.get_role(int(guildTags[1])) <= ctx.author.top_role:
            tags = json.loads(guildTags[2])
            try:
                await ctx.send(tags[tag])
            except KeyError:
                pass

    @tag.command(name="(your tag here)")
    async def tag_yourtaghere(self,ctx):
        return

    @tag.command(name="set",aliases=["new","add"])
    async def tag_set(self,ctx,tag,*,text):
        if tag in ['(your tag here)','new','add','remove','delete','del','list','get','role']:
            await ctx.send("Tag cannot be named that.")
            return
        guildTags = cursor.execute("SELECT * FROM tags WHERE guild = ?",(ctx.guild.id,)).fetchone()
        tags = json.loads(guildTags[2])
        tags[tag] = text
        cursor.execute("UPDATE tags SET tags=? WHERE guild=?",(json.dumps(tags),ctx.guild.id))
        connection.commit()
        await ctx.send("Tag updated.")


    @tag.command(name="remove",aliases=["delete","del"])
    async def tag_remove(self,ctx,tag):
        guildTags = cursor.execute("SELECT * FROM tags WHERE guild = ?",(ctx.guild.id,)).fetchone()
        tags = json.loads(guildTags[2])
        tags.pop(tag)
        cursor.execute("UPDATE tags SET tags=? WHERE guild=?",(json.dumps(tags),ctx.guild.id))
        connection.commit()
        await ctx.send("Tag updated.")

    @tag.command(name="list",aliases=["get"])
    async def tag_list(self,ctx):
        guildTags = cursor.execute("SELECT * FROM tags WHERE guild = ?",(ctx.guild.id,)).fetchone()
        tags = json.loads(guildTags[2])
        colour = discord.Colour.from_rgb(random.randint(1,255),random.randint(1,255),random.randint(1,255))
        embed = discord.Embed(colour=colour,title=f"Tags.",description=", ".join(tags.keys())+f"\n\nUsable by {ctx.guild.get_role(int(guildTags[1])).mention} and above.")
        embed.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @tag.command(name="role")
    @commands.has_permissions(manage_messages=True)
    async def tag_role(self,ctx,*,role:discord.Role=None):
        if not role:
            role = ctx.author.top_role
        cursor.execute("UPDATE tags SET role=? WHERE guild=?",(role.id,ctx.guild.id))
        connection.commit()
        await ctx.send(f"Tag role set to {role.name}.")

def setup(bot):
    bot.add_cog(Utilities(bot))