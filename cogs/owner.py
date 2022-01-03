import asyncio
import configparser
import gzip
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import typing
from datetime import datetime
from pathlib import Path

import discord
from utils import utils
from utils.checks import checks
from utils.sql.db import backups
from discord.ext import commands, tasks

import cogs.fancyEmbeds as fEmbeds

# Logging config
logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', level=logging.INFO)

#configparser
config = configparser.ConfigParser()

def setup(bot):
    bot.add_cog(Owner(bot))

class Owner(commands.Cog):
    """Cog for owners to do stuff!"""

    def __init__(self, bot):
        self.bot = bot
        self.bot.previousReload = None
        self.connection = bot.connection
        self.auto_backup.start()

    @commands.command(brief=":sleeping: ")
    @commands.is_owner()
    async def shutdown(self,ctx):
        """Shuts the bot down!"""
        await ctx.send("👋 Goodbye")
        await utils.close_bot(self.bot)

    @commands.command(brief=":arrows_counterclockwise: ")
    @commands.is_owner()
    async def restart(self,ctx):
        """Restarts the bot!"""
        await ctx.send("🏃‍♂️ Be right back!")
        self.bot.restart = True
        await utils.close_bot(self.bot)

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
            if self.bot.previousReload is None:
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
        loaded_cogs = ['.'.join(cog.split(".")[1:]) for cog in self.bot.extensions.keys()]
        unloaded_cogs = []
        visited = []
        for d, _, files in os.walk("cogs",followlinks=True):
            if os.path.realpath(d) in visited:
                logging.warning("There is infinite recursion in your cogs folder, there is a link to the cog folder or a parent folder of it, this limits the amount of folders we can search for cogs. To fix this remove the links.")
                break
            visited.append(os.path.realpath(d))
            for f in files:
                if d != "cogs":
                    f = d.replace("/",".")[5:] + "." + f
                if f[:-3] not in loaded_cogs and f.endswith(".py"):
                    unloaded_cogs.append("`"+f[:-3]+"`")

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        if emoji is False:
            emojia = ""
            emojib = ""
            emojic = ""
        else:
            emojia = ":gear: "
            emojib = ":wrench: "
            emojic = ":tools: "

        embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Cogs.", desc=None, useColor=2)
        embed.add_field(name=f"{emojib}Loaded Cogs:", value=", ".join(["`"+c+"`" for c in loaded_cogs])+".", inline=False)
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
        out, _ = await local.communicate()
        if out:
            await ctx.send("You have committed changes that you have not pushed, please push them before updating")
            return
        incoming = await asyncio.create_subprocess_shell(f"git diff --name-only HEAD origin/{branch}", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, _ = await incoming.communicate()
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
        await backups.make_backup(self.connection, self.bot.kept_backups)
        root_directory = Path('resources/backups')
        #functions in f-string gets size, count of everything in "backups" folder, 1 is subtracted from count because of gitkeep
        await ctx.send(f"Sounds good! I made a backup of your database. Currently, your {(len(os.listdir('resources/backups')))-1} backup(s) take up {round((sum(f.stat().st_size for f in root_directory.glob('**/*') if f.is_file())/1000),2)} kilobytes of space")

    @backup.command(name="list", brief=":card_box: ")
    async def list_backups(self, ctx):
        """Lists all your current backups"""
        files = [f[:-6] for f in os.listdir('resources/backups') if os.path.isfile(os.path.join('resources/backups',f)) and f != ".gitkeep"]
        message = f"```\n{os.linesep.join(sorted(files))}```\n**{(len(os.listdir('resources/backups')))-1} total backup(s)**" if len(os.listdir('resources/backups')) != 1 else "You currently have no backups"
        await ctx.send(message)

    @backup.command(brief=":wastebasket: ")
    async def delete(self, ctx, amount:int):
        """Deletes a specified number of backups"""
        files = [f for f in os.listdir('resources/backups') if os.path.isfile(os.path.join('resources/backups',f)) and f != ".gitkeep"]
        print(files)
        if len(files) < amount:
            await ctx.send("You don't have that many backups to delete!")
            return
        to_delete = sorted(files)[:amount]
        print(to_delete)
        for f in to_delete:
            os.remove(f"resources/backups/{f}")
        await ctx.send(f"Deleted {amount} backup(s), you now have {len(os.listdir('resources/backups'))}")

    @backup.command(brief=":pencil: ")
    async def setup(self, ctx):
        """Sets up the automatic backup schedule"""
        def check(response):
            return response.channel == ctx.channel and response.author == ctx.author
        async def get_message(allow_all=False, allow_off=False):
            while 1:
                try:
                    message = await self.bot.wait_for('message', timeout=60.0, check=check)
                except asyncio.TimeoutError:
                    await ctx.send("No response received. Cancelling, no changes have been made")
                    return False
                content = message.content
                try:
                    await message.delete()
                except commands.MissingPermissions:
                    pass
                if content.lower() == "cancel":
                    await ctx.send("Cancelling, no changes were made")
                    return False
                if allow_all and content.lower() == "all":
                    return "all"
                if allow_off and content.lower() == "off":
                    return "off"
                try:
                    int(content)
                except ValueError:
                    await ctx.send("Oops! Please make sure your response is an integer! Try again")
                    continue
                if int(content) < 1:
                    await ctx.send("Please make sure your response is 1 or larger! Try again")
                    continue
                return int(content)
        await ctx.send("Please specify the frequency, in hours, you would like backups to be made. For example, responding \"24\" would create a backup every day. If you want to turn automatic backups off completely, respond \"off\"")
        backup_frequency = await get_message(allow_off=True)
        if backup_frequency == False:
            return
        if backup_frequency == "off":
            config.read('resources/config.ini')
            config["BACKUPS"]["BackupInterval"] = "0"
            with open("resources/config.ini", "w") as config_file:
                config.write(config_file)
            self.bot.backup_interval = 0
            self.auto_backup.cancel()
            await ctx.send("Sounds good! Automatic backups have been turned off.")
            return

        await ctx.send("Please specify the number of backups you would like to keep. When this number of backups is reached, the oldest backup will be deleted. Alternatively, respond with \"all\" to never auto delete backups. Please note that you will have to manage storage yourself if you do this, though")
        kept_backups = await get_message(allow_all=True)
        if kept_backups == False:
            return
        if kept_backups == "all":
            kept_backups = 0
        config.read("resources/config.ini")
        config["BACKUPS"]["BackupInterval"] = str(backup_frequency)
        config["BACKUPS"]["KeptBackups"] = str(kept_backups)
        with open("resources/config.ini", "w") as config_file:
            config.write(config_file)
        self.bot.backup_interval = backup_frequency
        self.bot.kept_backups = kept_backups

        self.auto_backup.restart()

        await ctx.send(f"Sounds good! I'll make a backup every {backup_frequency} hours, and keep all of your backups" if kept_backups == 0 else f"Sounds good! I'll make a backup every {backup_frequency} hours, and keep your {kept_backups} most recent backups")

    @tasks.loop(hours=24) 
    #24 hours is a stand-in value, this should always be overwritten by the pre invoke if everything works correctly
    async def auto_backup(self):
        if os.path.isfile("resources/backups/tempbackupfile.db"):
            logging.warning("Unable to automatically create backup, database backup is already in process. If this problem persists, please contact SushiInYourFace")
            return() #should probably log this occurance, as it may signal something going wrong
        await backups.make_backup(self.connection, self.bot.kept_backups)
        logging.info("Database backup created.")

    @auto_backup.before_loop
    #waits for ready, sets correct interval
    async def before_auto_backup(self):
        await self.bot.wait_until_ready()
        if self.bot.backup_interval == 0:
            self.auto_backup.cancel()
            return
        self.auto_backup.change_interval(hours=self.bot.backup_interval)
        

    @commands.Cog.listener()
    async def on_message(self,message):
        if message.author.bot:
            return
        cursor = await self.connection.execute("SELECT command_usage FROM role_ids WHERE guild = ?", (message.guild.id,))
        commandRole = await cursor.fetchone()
        member_roles = [role.id for role in message.author.roles]
        if (not commandRole or commandRole[0] in member_roles) or (checks.has_adminrole(message,self.bot) or checks.has_modrole(message,self.bot)): # Only people with commands role/mod should be able to do this
            if re.match(r"^<@."+str(self.bot.user.id)+r">$",message.content): # making sure the mention is the only content (^ means start of str, $ end)
                prefix = self.bot.guild_prefixes.get(message.guild.id,"!")
                await message.channel.send(f"My prefix here is `{prefix}`",delete_after=8)

    @commands.command(aliases=["guilds"], brief=":desktop: ")
    @commands.is_owner()
    async def servers(self,ctx):
        guilds = self.bot.guilds
        guildDict = {}
        out = "Guilds I'm in:\n"
        number = 1
        for number,guild in enumerate(guilds):
            out += f"{number} - {guild.name}\n"
        out += "Type the number to make me leave the server, or say 'stop' to cancel (expires after 30 seconds with 🥛 reaction)."
        message = await ctx.send(out)
        def check(m):
            return m.channel == ctx.channel and m.author == ctx.author
        while 1:
            try:
                msg = await self.bot.wait_for('message',check=check,timeout=30)
            except asyncio.TimeoutError:
                await message.add_reaction("🥛")
                return
            try:
                if int(msg.content) < len(guilds) and int(msg.content) >= 0:
                    break
            except:
                pass
            if msg.content == "stop":
                return
            await ctx.send("That is not a server in the list, try again.",delete_after=3)
        guild = guilds[int(msg.content)]
        await ctx.send(f"Are you sure you want me to leave {guild.name}? Say `yes` to continue or 'no' to cancel.")
        def check(m):
            return m.content in ['yes','no'] and m.channel == ctx.channel and m.author == ctx.author
        try:
            msg = await self.bot.wait_for('message',check=check,timeout=15)
        except asyncio.TimeoutError:
            await ctx.send("Timed Out. Not leaving.")
            return
        else:
            if msg.content == "yes":
                await guild.leave()
                await ctx.send(f"Left {guild.name}.")
            else:
                await ctx.send("Ok, not leaving.")
