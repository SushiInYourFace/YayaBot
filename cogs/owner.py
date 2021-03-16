import discord
from discord.ext import commands
import random
import os
import sqlite3

connection = sqlite3.connect("database.db")
cursor = connection.cursor()

def setup(bot):
    bot.add_cog(Owner(bot))

class Owner(commands.Cog):
    """Cog for owners to do stuff!"""

    def __init__(self, bot):
        self.bot = bot
        self.bot.previousReload = None

    @commands.command()
    @commands.is_owner()
    async def shutdown(self,ctx):
        """Shuts the bot down!"""
        await ctx.send("👋 Goodbye")
        await self.bot.close()

    @commands.group(aliases = ['c'])
    @commands.is_owner()
    async def cog(self,ctx):
        """Commands to add, reload and remove cogs."""
        if ctx.invoked_subcommand is None:
            await self.bot.send_help(ctx)

    @cog.command(aliases = ['l'])
    async def load(self,ctx,*cogs):
        """Loads a cog."""
        for cog in cogs:
            cog = f"cogs.{cog}"
            inDb = cursor.execute("SELECT * FROM extensions WHERE extension = ?", (cog,)).fetchone()
            inDb = (inDb is not None)
            loadCog = (cog not in self.bot.extensions.keys())
            if ((not loadCog) and inDb):
                await ctx.send(f"Cog `{cog}` is already loaded.")
                return
            if loadCog:
                try:
                    self.bot.load_extension(cog)
                except commands.ExtensionNotFound:
                    await ctx.send(f"Cog `{cog}` could not be found.")
                    return
                except:
                    await ctx.send(f"Loading cog `{cog}` failed")
                    raise
            if not inDb:
                cursor.execute("INSERT INTO extensions(extension) VALUES(?)", (cog,))
                connection.commit()
            await ctx.send(f"Cog `{cog}` {'loaded' if loadCog else ''}{' and ' if (loadCog and not inDb) else ''}{'added to database' if not inDb else ''}.")

    @cog.command(aliases = ['u'])
    async def unload(self,ctx,*cogs):
        """Unloads a cog."""
        for cog in cogs:
            if cog == 'owner':
                await ctx.send("Cannot unload owner.")
                return
            cog = f"cogs.{cog}"
            inDb = cursor.execute("SELECT count(*) FROM extensions WHERE extension = ?", (cog,)).fetchone()
            inDb = (inDb is not None)
            unloadCog = (cog in self.bot.extensions.keys())
            if not (unloadCog and inDb):
                await ctx.send(f"Cog {cog} is not loaded.")
                return
            if unloadCog:
                try:
                    self.bot.unload_extension(cog)
                except:
                    await ctx.send(f"Unloading cog `{cog}` failed")
                    raise
            if inDb:
                cursor.execute("DELETE FROM extensions WHERE extension=?", (cog,))
                connection.commit()
            await ctx.send(f"Cog {cog} {'unloaded' if unloadCog else ''}{' and ' if (unloadCog and inDb) else ''}{'removed from database' if inDb else ''}.")

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
        """Reloads specified cog or previously reloaded cog."""
        command = self.bot.get_command("cog reload")
        await ctx.invoke(command,cog)