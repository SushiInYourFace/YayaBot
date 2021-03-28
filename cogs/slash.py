import discord
from discord.ext import commands
from discord_slash import cog_ext, SlashContext

class Slash(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(name="test")
    async def _test(self, ctx: SlashContext):
        embed = discord.Embed(title="The Industrial Revolution and its consequences have been a disaster for the human race")
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Slash(bot))
