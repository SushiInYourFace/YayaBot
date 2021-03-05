import discord
from discord.ext import commands
import sqlite3
import asyncio

#sets up SQLite
connection = sqlite3.connect("database.db")
cursor = connection.cursor()

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
        
        




def setup(bot):
    bot.add_cog(Utilities(bot))