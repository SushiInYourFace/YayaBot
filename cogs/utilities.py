import discord
from discord.ext import commands
import sqlite3

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




def setup(bot):
    bot.add_cog(Utilities(bot))