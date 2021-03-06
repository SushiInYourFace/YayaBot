import discord
from discord.ext import commands
import random
import os

def setup(bot):
    bot.add_cog(Owner(bot))

class Owner(commands.Cog):
    """owner cog!"""

    def __init__(self, bot):
        self.bot = bot
        self.bot.previousReload = None

    @commands.command()
    @commands.is_owner()
    async def shutdown(self,ctx):
        await ctx.send("👋 Goodbye")
        await self.bot.close()

    @commands.group(aliases = ['c'])
    @commands.is_owner()
    async def cog(self,ctx):
        """Commands to add, reload and remove cogs."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @cog.command(aliases = ['l'])
    async def load(self,ctx,*cogs):
        """Loads a cog."""
        for cog in cogs:
            self.bot.load_extension(f"cogs.{cog}")
            await ctx.send(f"Cog {cog} loaded.")

    @cog.command(aliases = ['u'])
    async def unload(self,ctx,*cogs):
        """Unloads a cog."""
        for cog in cogs:
            if cog == 'owner':
                await ctx.send("Cannot unload owner.")
                return
            self.bot.unload_extension(f"cogs.{cog}")
            await ctx.send(f"Cog {cog} unloaded.")

    @cog.command(aliases = ['r'])
    async def reload(self,ctx,cog=None):
        """Reload cog."""
        if cog == None:
            if self.bot.previousReload == None:
                return
            else:
                cog = self.bot.previousReload
        self.bot.reload_extension(f"cogs.{cog}")
        await ctx.send(f"Cog {cog} reloaded.")
        self.bot.previousReload = cog

    @cog.command(name="list",aliases=["ls"])
    async def cogs_list(self,ctx):
        """Lists loaded and unloaded cogs."""
        colour = discord.Colour.from_rgb(random.randint(1,255),random.randint(1,255),random.randint(1,255))
        loaded_cogs = [cog.split(".")[1] for cog in self.bot.extensions.keys()]
        unloaded_cogs = [cog[:-3] for cog in os.listdir("cogs") if (cog[:-3] not in loaded_cogs and cog.endswith(".py"))]
        embed = discord.Embed(colour=colour,title="Cogs.")
        embed.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)
        embed.add_field(name="Loaded Cogs:", value=", ".join(loaded_cogs)+".", inline=False)
        embed.add_field(name="Unloaded Cogs:", value=", ".join(unloaded_cogs)+".", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="reload")
    @commands.is_owner()
    async def reload_alias(self,ctx,cog=None):
        command = self.bot.get_command("cog reload")
        await ctx.invoke(command,cog)
