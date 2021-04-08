import asyncio
import logging
import os
import random
import sqlite3
import subprocess
import sys
import typing

import discord
from discord.ext import commands

# Logging config
logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', level=logging.INFO)

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

    @commands.command()
    @commands.is_owner()
    async def restart(self,ctx):
        """Restarts the bot!"""
        await ctx.send("🏃‍♂️ Be right back!")
        self.bot.restart = True
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
                    logging.info(f"{cog} loaded.")
                except commands.ExtensionNotFound:
                    await ctx.send(f"Cog `{cog}` could not be found.")
                    continue
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
                    logging.info(f"{cog} unloaded")
                except:
                    await ctx.send(f"Unloading cog `{cog}` failed")
                    raise
            if inDb:
                cursor.execute("DELETE FROM extensions WHERE extension=?", (cog,))
                connection.commit()
            await ctx.send(f"Cog {cog} {'unloaded' if unloadCog else ''}{' and ' if (unloadCog and inDb) else ''}{'removed from database' if inDb else ''}.")

    @cog.command(aliases = ['r'])
    async def reload(self,ctx,*cogs:typing.Optional[str]):
        """Reloads cogs."""
        allReloaded = False
        if not cogs:
            if self.bot.previousReload == None:
                await ctx.send("Please specify a cog!")
                return
            else:
                cogs = self.bot.previousReload
        if cogs[0] in ["*","all"]:
            cogs = [cog.split(".")[1] for cog in self.bot.extensions.keys()]
            allReloaded = True
        notLoaded = []
        loaded = []
        for cog in cogs:
            try:
                self.bot.reload_extension(f"cogs.{cog}")
                logging.info(f"{cog} reloaded.")
                loaded.append(cog)
            except commands.ExtensionNotLoaded:
                notLoaded.append(cog)
                continue
            except:
                await ctx.send(f"Error while reloading {cog}.")
                raise
        await ctx.send(f"{'Cog '+', '.join(loaded)+' reloaded.' if loaded else ''}{(' Cog '+', '.join(notLoaded)+' was not found so not reloaded.') if notLoaded else ''}")
        if allReloaded:
            self.bot.previousReload = ["*"]
        else:
            self.bot.previousReload = loaded

    @cog.command(name="list",aliases=["ls"])
    async def cogs_list(self,ctx):
        """Lists loaded and unloaded cogs."""
        loaded_cogs = [cog.split(".")[1] for cog in self.bot.extensions.keys()]
        unloaded_cogs = [cog[:-3] for cog in os.listdir("cogs") if (cog[:-3] not in loaded_cogs and cog.endswith(".py"))]
        embed = discord.Embed(colour=discord.Colour.random(),title="Cogs.")
        embed.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)
        embed.add_field(name="Loaded Cogs:", value=", ".join(loaded_cogs)+".", inline=False)
        embed.add_field(name="Unloaded Cogs:", value=", ".join(unloaded_cogs)+".", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="reload")
    @commands.is_owner()
    async def reload_alias(self,ctx,*cogs:typing.Optional[str]):
        """Reloads specified cog or previously reloaded cog."""
        command = self.bot.get_command("cog reload")
        await ctx.invoke(command,*cogs)

    @commands.command()
    @commands.is_owner()
    async def update(self, ctx):
        """Pulls the latest commit from Github"""
        local = await asyncio.create_subprocess_shell("git fetch origin;git log --name-only FETCH_HEAD..HEAD", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await local.communicate()
        if out:
            await ctx.send("You have committed changes that you have not pushed, please push them before updating")
            return
        incoming = await asyncio.create_subprocess_shell("git fetch origin;git diff --name-only HEAD FETCH_HEAD", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await incoming.communicate()
        if not out:
            await ctx.send("No new changes!")
            return
        out = out.decode().split('\n')
        out.remove("")
        await asyncio.create_subprocess_shell("git pull", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await ctx.send(f"Update completed!\nThe following files have been changed\n```{', '.join(out)}```\nYou may have to restart the bot, or reload some cogs for it to take effect.")

    @commands.Cog.listener()
    async def on_message(self,message):
        if message.author.bot:
            return
        if isinstance(message.channel,discord.DMChannel):
            mention = self.bot.user.mention
        else:
            mention = message.guild.me.mention
        if message.content == mention:
            prefix = "!"
            try:
                guildcommand = cursor.execute("SELECT prefix FROM guild_prefixes WHERE guild = ?", (message.guild.id,)).fetchone()
                prefix = (str(guildcommand[0]))
            except TypeError:
                pass
            await message.channel.send(f"My prefix here is `{prefix}`",delete_after=6)
