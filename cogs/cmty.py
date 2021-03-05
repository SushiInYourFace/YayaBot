import discord
from discord.ext import commands
import random

class Community(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    #rats
    @commands.command(help="RATS RATS RATS RATS RATS RATS RATS RATS RATS RATS RATS RATS", aliases=["rat", "RATS", "RAT"])
    async def rats(self, ctx):
        rat = random.choice(open("RATSRATSRATS.txt").readlines())
        await ctx.send(rat)

    #hello
    @commands.command(help="Says hello")
    async def hello(self, ctx):
        await ctx.send("Hello there")

def setup(bot):
    bot.add_cog(Community(bot))