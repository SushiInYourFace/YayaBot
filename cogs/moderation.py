import discord
from discord.ext import commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(help="Purges a specified amount of messages from the chat")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, arg):
        try:
            arg = int(arg)
        except ValueError:
            await ctx.send("That's not a valid number. To use this command, please use the number of messages to purge as your argument")
        await ctx.channel.purge(limit=arg)

def setup(bot):
    bot.add_cog(Moderation(bot))