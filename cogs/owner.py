import asyncio
import logging
import os
import random
import sqlite3
import subprocess
import sys
import typing
import io
import gzip
import shutil
from pathlib import Path
from datetime import datetime

import cogs.fancyEmbeds as fEmbeds
import functions

import discord
from discord.ext import commands

# Logging config
logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', level=logging.INFO)

def setup(bot):
    bot.add_cog(Owner(bot))

class Owner(commands.Cog):
    """Cog for owners to do stuff!"""

    def __init__(self, bot):
        self.bot = bot
        self.bot.previousReload = None
        self.connection = bot.connection

    @commands.command(brief=":sleeping: ")
    @commands.is_owner()
    async def shutdown(self,ctx):
        """Shuts the bot down!"""
        await ctx.send("👋 Goodbye")
        await self.bot.close()

    @commands.command(brief=":arrows_counterclockwise: ")
    @commands.is_owner()
    async def restart(self,ctx):
        """Restarts the bot!"""
        await ctx.send("🏃‍♂️ Be right back!")
        self.bot.restart = True
        await self.bot.close()

    @commands.group(aliases = ['c'], brief=":gear: ")
    @commands.is_owner()
    async def cog(self,ctx):
        """Commands to add, reload and remove cogs."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @cog.command(aliases = ['l'], brief=":inbox_tray: ")
    async def load(self,ctx,*cogs):
        """Loads a cog."""
        for cog in cogs:
            cog = f"cogs.{cog}"
            cursor = await self.connection.execute("SELECT * FROM extensions WHERE extension = ?", (cog,))
            inDb = await cursor.fetchone()
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
                await cursor.execute("INSERT INTO extensions(extension) VALUES(?)", (cog,))
                await self.connection.commit()
            await ctx.send(f"Cog `{cog}` {'loaded' if loadCog else ''}{' and ' if (loadCog and not inDb) else ''}{'added to database' if not inDb else ''}.")
            await cursor.close()

    @cog.command(aliases = ['u'], brief=":outbox_tray: ")
    async def unload(self,ctx,*cogs):
        """Unloads a cog."""
        for cog in cogs:
            if cog == 'owner':
                await ctx.send("Cannot unload owner.")
                return
            cog = f"cogs.{cog}"
            cursor = await self.connection.execute("SELECT count(*) FROM extensions WHERE extension = ?", (cog,))
            inDb = await cursor.fetchone()
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
                await cursor.execute("DELETE FROM extensions WHERE extension=?", (cog,))
                await self.connection.commit()
            await cursor.close()
            await ctx.send(f"Cog {cog} {'unloaded' if unloadCog else ''}{' and ' if (unloadCog and inDb) else ''}{'removed from database' if inDb else ''}.")

    @cog.command(aliases = ['r'], brief=":arrows_counterclockwise: ")
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

    @cog.command(name="list",aliases=["ls"], brief=":gear: ")
    async def cogs_list(self,ctx):
        """Lists loaded and unloaded cogs."""
        loaded_cogs = [cog.split(".")[1] for cog in self.bot.extensions.keys()]
        unloaded_cogs = [cog[:-3] for cog in os.listdir("cogs") if (cog[:-3] not in loaded_cogs and cog.endswith(".py"))]
        
        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        if emoji == False:
            emojia = ""
            emojib = ""
            emojic = ""
        else:
            emojia = ":gear: "
            emojib = ":wrench: "
            emojic = ":tools: "

        embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Cogs.", desc=None, useColor=2)
        embed.add_field(name=f"{emojib}Loaded Cogs:", value=", ".join(loaded_cogs)+".", inline=False)
        embed.add_field(name=f"{emojic}Unloaded Cogs:", value=", ".join(unloaded_cogs)+".", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="reload", brief=":arrows_counterclockwise: ")
    @commands.is_owner()
    async def reload_alias(self,ctx,*cogs:typing.Optional[str]):
        """Reloads specified cog or previously reloaded cog."""
        command = self.bot.get_command("cog reload")
        await ctx.invoke(command,*cogs)

    @commands.command(brief=":wrench: ")
    @commands.is_owner()
    async def update(self, ctx):
        """Pulls the latest commit from Github"""
        b = await asyncio.create_subprocess_shell("git fetch origin")
        await b.communicate()
        b = await asyncio.create_subprocess_shell("git rev-parse --abbrev-ref HEAD",stdout=subprocess.PIPE)
        branch = await b.communicate()
        branch = branch[0].decode().replace("\n","")
        local = await asyncio.create_subprocess_shell(f"git log --name-only origin/{branch}..HEAD", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await local.communicate()
        if out:
            await ctx.send("You have committed changes that you have not pushed, please push them before updating")
            return
        incoming = await asyncio.create_subprocess_shell(f"git diff --name-only HEAD origin/{branch}", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await incoming.communicate()
        if not out:
            await ctx.send("No new changes!")
            return
        out = out.decode().split('\n')
        out.remove("")
        await asyncio.create_subprocess_shell("git pull", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await ctx.send(f"Update completed!\nThe following files have been changed\n```{', '.join(out)}```\nYou may have to restart the bot, or reload some cogs for it to take effect.")


    @commands.group(aliases = ['bu'], brief=":recycle: ")
    @commands.is_owner()
    async def backup(self,ctx):
        """Create and manage backups of the bot database."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @backup.command(aliases=["make",], brief=":pencil2: ")
    async def create(self, ctx):
        """Creates a backup of the current database"""
        if os.path.isfile("resources/backups/tempbackupfile.db"):
            await ctx.send("A backup is already in the process of being made! Please wait a moment before trying this again")
            return()
        backup = sqlite3.connect("resources/backups/tempbackupfile.db")
        with backup:
            await self.connection.backup(backup, pages=1) #actual backup happens here
        backup.close()
        timestamp = datetime.now().strftime('%m_%d_%Y-%H_%M_%S')
        fname = f'resources/backups/{timestamp}.db.gz'
        with gzip.open(fname, 'wb') as f_out:
            with open("resources/backups/tempbackupfile.db", "rb") as f_in:
                shutil.copyfileobj(f_in, f_out)
        os.remove("resources/backups/tempbackupfile.db")
        root_directory = Path('resources/backups')
        #functions in f-string gets size, count of everything in "backups" folder, 1 is subtracted from count because of gitkeep
        await ctx.send(f"Sounds good! I made a backup of your database. Currently, your {(len(os.listdir('resources/backups')))-1} backup(s) take up {round((sum(f.stat().st_size for f in root_directory.glob('**/*') if f.is_file())/1000),2)} kilobytes of space")

    @backup.command(name="list", brief=":card_box: ")
    async def list_backups(self, ctx):
        """Lists all your current backups"""
        files = [f[:-6] for f in os.listdir('resources/backups') if os.path.isfile(os.path.join('resources/backups',f)) and f != ".gitkeep"]
        #functions in fstring go brrrr
        message = f"```{os.linesep.join(sorted(files))}```\n**{(len(os.listdir('resources/backups')))-1} total backup(s)**" if len(os.listdir('resources/backups')) != 1 else "You currently have no backups"
        await ctx.send(message)

    @backup.command(brief=":wastebasket: ")
    async def delete(self, ctx, amount:int):
        """Deletes a specified number of backups"""
        files = [f for f in os.listdir('resources/backups') if os.path.isfile(os.path.join('resources/backups',f))]
        if len(files) < amount:
            await ctx.send("You don't have that many backups to delete!")
            return
        to_delete = sorted(files)[:amount]
        for f in to_delete:
            os.remove(f"resources/backups/{f}")
        await ctx.send(f"Deleted {amount} backup(s), you now have {len(os.listdir('resources/backups'))}")

    @commands.Cog.listener()
    async def on_message(self,message):
        if message.author.bot:
            return
        if self.bot.user.mentioned_in(message):
            prefix = "!"
            try:
                cursor = await self.connection.execute("SELECT prefix FROM guild_prefixes WHERE guild = ?", (message.guild.id,))
                guildcommand = await cursor.fetchone()
                await cursor.close()
                prefix = (str(guildcommand[0]))
            except TypeError:
                pass
            await message.channel.send(f"My prefix here is `{prefix}`",delete_after=8)
