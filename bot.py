import asyncio
import datetime
import logging
import platform
import sqlite3
import sys
import time
from collections import namedtuple

import aiosqlite
import discord
from discord.ext import commands

import cogs.fancyEmbeds as fEmbeds
import functions

# Logging config
logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', level=logging.INFO)

Token = None
#Open txt files
try:
    with open("token.txt") as f:
        Token = f.read()
except FileNotFoundError:
    #user has not created token.txt
    print("You don't seem to have created token.txt yet. Not a problem! Please send your bot token, and it will be made for you")
    print("If you don't want to do this, you can just quit the program with ctrl+c, or type \"exit\" now")
    Token = input()
    if Token.lower() == "exit":
        sys.exit(0)
    with open("token.txt", "w") as f:
        f.write(Token)

#Guild-Specific prefixes
async def get_pre(bot, message):
    return bot.guild_prefixes.get(message.guild.id,"!")

#Help command
class NewHelp(commands.HelpCommand):
    async def create_help_field(self,ctx,embed,command,emoji):
        if command.help:
            description = (command.help[:command.help.find("\n")+1] if '\n' in command.help else command.help)
            if len(description) > 200:
                description = description[:197] + "..."
        else:
            description = "..."
        if command.brief:
            emote = command.brief
        elif command.name == "help":
            emote = ":question: "
        else:
            emote = ""
        embed.add_field(name=f"{emote}{command.name}", value=f"{description}", inline=True)
        return embed

    async def send_bot_help(self,mapping):
        style = fEmbeds.fancyEmbeds.getActiveStyle(self, self.context.guild.id)
        useEmoji = fEmbeds.fancyEmbeds.getStyleValue(self, self.context.guild.id, style, "emoji")
        pageOut = 0
        titleDesc = ["YayaBot Help!",f"Say `{self.context.clean_prefix}help <command>` for more info on a command!"]
        page = [fEmbeds.fancyEmbeds.makeEmbed(self, self.context.guild.id, embTitle=titleDesc[0], desc=titleDesc[1], useColor=0, nofooter=True)]
        for cog,commands in mapping.items():
            commands = await self.filter_commands(commands)
            if not commands:
                continue
            if len(page[-1].fields) >= 24: # If no space for commands or no space at all
                page.append(fEmbeds.fancyEmbeds.makeEmbed(self, self.context.guild.id, embTitle=titleDesc[0], desc=titleDesc[1], useColor=0, nofooter=True)) # New page
            cogName = getattr(cog,'qualified_name','Other')
            cogDesc = '\n> '+ getattr(cog,"description",'...') if not cogName == "Other" else "> Other commands that don't fit into a category."
            page[-1].add_field(name=f"> **{cogName}**", value=cogDesc, inline=False) # Add cog field
            for command in commands:
                page[-1] = await self.create_help_field(self.context,page[-1],command,useEmoji)
                if command != commands[-1] and len(page[-1].fields) == 25: # If not the last command and new page is required
                    page.append(fEmbeds.fancyEmbeds.makeEmbed(self, self.context.guild.id, embTitle=titleDesc[0], desc=titleDesc[1], useColor=0, nofooter=True)) # New page
                    page[-1].add_field(name=f"> **{cogName}**", value=cogDesc, inline=False) # Add cog field
        if pageOut + 1 > len(page):
            pageOut = len(page) - 1
        page[pageOut] = fEmbeds.fancyEmbeds.addFooter(self, page[pageOut], f"Page {pageOut+1} of {len(page)}", bot) # Add footer now (didn't know how many pages previously)
        msg = await self.get_destination().send(embed=page[pageOut])
        if len(page) == 1: # If only one page no turning is required
            return
        for emoji in ["⏪","◀️","▶️","⏩","🇽"]: # Page turning
            await msg.add_reaction(emoji)
        def check(react, user):
            return react.message == msg and (self.context.message.author == user and str(react.emoji) in ["⏪","◀️","▶️","⏩","🇽"])
        while True:
            try:
                reaction,user = await bot.wait_for("reaction_add",timeout=30,check=check)
            except asyncio.TimeoutError:
                await msg.clear_reactions()
                break
            if str(reaction.emoji) == "🇽":
                await self.context.channel.delete_messages([self.context.message,msg])
                return
            pageOut = {"⏪":0,"◀️":(pageOut-1) if pageOut-1 >= 0 else pageOut,"▶️":(pageOut+1) if pageOut+1 < len(page) else pageOut,"⏩":len(page)-1}[str(reaction.emoji)]
            page[pageOut] = fEmbeds.fancyEmbeds.addFooter(self, page[pageOut], f"Page {pageOut+1} of {len(page)}", bot)
            await msg.edit(embed=page[pageOut])
            await reaction.remove(user)

    async def send_command_help(self,command):
        style = fEmbeds.fancyEmbeds.getActiveStyle(self, self.context.guild.id)
        useEmoji = fEmbeds.fancyEmbeds.getStyleValue(self, self.context.guild.id, style, "emoji")

        if not useEmoji:
            emojia = ""
            emojib = ""
        else:
            emojia = ":screwdriver: "
            emojib = ":scroll: "

        if not isinstance(command,commands.Cog):
            try:
                await command.can_run(self.context)
            except:
                return
        embed = fEmbeds.fancyEmbeds.makeEmbed(self, self.context.guild.id, embTitle=f"Help for {command.qualified_name}" + (" cog" if isinstance(command,commands.Cog) else ' command'), desc=(f"Aliases: {', '.join(list(command.aliases))}" if command.aliases else ""), useColor=1, b=bot)
        if not isinstance(command,commands.Cog):
            embed.add_field(name=f"{emojia}Usage",value=f"`{self.context.clean_prefix}{command.qualified_name}{(' ' + command.signature.replace('_',' ')    ) if command.signature else ' <subcommand>' if isinstance(command,commands.Group) else ''}`")
        embed.add_field(name=f"{emojib}Description",value=(command.help.replace("[p]",self.context.clean_prefix) if command.help else '...'),inline=False)
        if isinstance(command,commands.Group) or isinstance(command,commands.Cog):
            embed.add_field(name="———————",value="**Subcommands**" if isinstance(command,commands.Group) else "**Commands**",inline=False)
            for subcommand in await self.filter_commands(command.commands, sort=True):
                embed = await self.create_help_field(self.context,embed,subcommand,useEmoji)
        await self.get_destination().send(embed=embed)

    async def send_group_help(self,group):
        await self.send_command_help(group)

    async def send_cog_help(self,cog):
        cog.aliases = None
        cog.help = cog.description
        cog.commands = cog.get_commands()
        await self.send_command_help(cog)

#intents, initializing bot
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix=get_pre, intents=intents, help_command=NewHelp())

#SQLite
con = sqlite3.connect("database.db")
cursor = con.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS guild_prefixes (guild INTEGER PRIMARY KEY, prefix TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS role_ids (guild INTEGER PRIMARY KEY, gravel INTEGER, muted INTEGER, moderator INTEGER, admin INTEGER, trialmod INTEGER, modlogs INTEGER, command_usage INTEGER, command_cooldown INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS active_cases (id INTEGER PRIMARY KEY, expiration FLOAT)")
cursor.execute("CREATE TABLE IF NOT EXISTS caselog (id INTEGER PRIMARY KEY, id_in_guild INTEGER, guild INTEGER, user INTEGER, type TEXT, reason TEXT, started FLOAT, expires FLOAT, moderator TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS extensions (extension TEXT PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS message_filter (guild INTEGER PRIMARY KEY, enabled INTEGER NOT NULL, filterWildCard TEXT NOT NULL, filterExact TEXT NOT NULL)")
cursor.execute("CREATE TABLE IF NOT EXISTS spam_filters (guild INTEGER PRIMARY KEY, emoji_limit INTEGER, invite_filter INTEGER, message_spam_limit INTEGER, character_repeat_limit INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS tags (guild INTEGER PRIMARY KEY, tags TEXT NOT NULL)")
cursor.execute("CREATE TABLE IF NOT EXISTS name_filtering (guild INTEGER PRIMARY KEY, enabled INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS custom_names (guild INTEGER PRIMARY KEY, nickname TEXT, username TEXT)")
con.commit()

#load filters into bot variable
bot.guild_filters = {}
filters = cursor.execute("SELECT * FROM message_filter").fetchall()
filter_tuple = namedtuple("filter_tuple", ["enabled", "wildcard", "exact"])
for guild_filter in filters:
    functions.update_filter(bot, guild_filter)

#load prefixes into bot var
bot.guild_prefixes = {}
prefixes = cursor.execute("SELECT * FROM guild_prefixes").fetchall()
if prefixes is not None:
    for prefix in prefixes:
        bot.guild_prefixes[prefix[0]] = prefix[1]

#fuck it, load mod and admin roles into bot var. (Not sure if this is how this should be done permanently, but it will work for now)
bot.modrole = {}
bot.adminrole = {}
bot.trialrole = {}
modroles = cursor.execute("SELECT guild, moderator, admin, trialmod FROM role_ids").fetchall()
if modroles is not None:
    for server_roles in modroles:
        bot.modrole[server_roles[0]] = server_roles[1]
        bot.adminrole[server_roles[0]] = server_roles[2]
        bot.trialrole[server_roles[0]] = server_roles[3]

#cogs to be loaded on startup
default_extensions = [
    ('cogs.community',),
    ('cogs.moderation',),
    ('cogs.utilities',),
    ('cogs.owner',),
    ('cogs.automod',),
    ('cogs.fancyEmbeds',),
]

extensions = cursor.execute("SELECT * FROM extensions").fetchall()

if not extensions:
    cursor.executemany("INSERT INTO extensions(extension) VALUES (?)", default_extensions)
    con.commit()
    extensions = default_extensions
cursor.close()
con.close()

#initialize aiosql connection
async def async_connect(bot):
    bot.connection = await aiosqlite.connect("database.db")

asyncio.get_event_loop().run_until_complete(async_connect(bot))

logging.info("Loading Cogs.")
for extension in extensions:
    try:
        bot.load_extension(extension[0])
        logging.info(f"Loaded {extension[0]}")
    except commands.ExtensionNotFound:
        logging.info(f"Could not find {extension[0]}")
logging.info("Done.")


#startup
@bot.event
async def on_ready():
    bot.startTime = time.time()
    bot.restart = False
    bot.args = sys.argv
    appinfo = await bot.application_info()
    logging.info(f"Bot started! Hello {str(appinfo.owner)}")
    logging.info(f"I'm connected as {str(bot.user)} - {bot.user.id}!")
    logging.info(f"In {len(bot.guilds)} guilds overlooking {len(list(bot.get_all_channels()))} channels and {len(list(bot.get_all_members()))} users.")

@bot.command(aliases=["info","bot"], brief=":green_book: " )
async def about(ctx):
    """Sends some information about the bot!"""
    currentTime = time.time()
    uptime = int(round(currentTime - bot.startTime))
    uptime = str(datetime.timedelta(seconds=uptime))
    appinfo = await bot.application_info()

    b = bot.get_cog("fancyEmbeds")

    e = fEmbeds.fancyEmbeds.getActiveStyle(b, ctx.guild.id)
    emoji = fEmbeds.fancyEmbeds.getStyleValue(b, ctx.guild.id, e, "emoji")

    if emoji is False:
        emojia = ""
        emojib = ""
        emojic = ""
        emojid = ""
    else:
        emojia = ":slight_smile: "
        emojib = ":snake: "
        emojic = ":stopwatch: "
        emojid = ":desktop: "

    embed = fEmbeds.fancyEmbeds.makeEmbed(b, ctx.guild.id, desc="Yayabot!", useColor=0)
    embed.set_author(name="YayaBot", url="https://wwww.github.com/SushiInYourFace/YayaBot", icon_url=bot.user.avatar.url)
    embed.add_field(name=f"{emojia}Instance Owner:", value=appinfo.owner, inline=True)
    embed.add_field(name="_ _", value="_ _", inline=True)
    embed.add_field(name=f"{emojib}Python Version:", value=f"[{platform.python_version()}](https://www.python.org)", inline=True)
    embed.add_field(name=f"{emojic}Bot Uptime:", value=f"{uptime}", inline=True)
    embed.add_field(name="_ _", value="_ _", inline=True)
    embed.add_field(name=f"{emojid}Discord.py Version:", value=f"[{discord.__version__}](https://github.com/Rapptz/discord.py)", inline=True)
    await ctx.send(embed=embed)

#error handling
@bot.event
async def on_command_error(ctx, error):
    if hasattr(ctx.command, 'on_error'):
        return
    ignored = (commands.CommandNotFound, commands.CheckFailure)
    error = getattr(error, 'original', error)
    #ignores ignored errors
    if isinstance(error, ignored):
        return
    if isinstance(error, commands.MemberNotFound):
        await ctx.send("Sorry, I couldn't find that user")
    elif isinstance(error, commands.MissingRequiredArgument):
        commandUsageLine = f"{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}"
        paramLocation = commandUsageLine.index("<" + error.param.name + ">")
        paramLength = len("<" + error.param.name + ">")
        await ctx.send(f"```{commandUsageLine}\n{' '*paramLocation}{'^'*paramLength}\n{str(error)}```")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("Sorry, you don't have permission to use that command!")
    elif isinstance(error, discord.errors.Forbidden):
        await ctx.send("I don't have permission to do that.")
    elif isinstance(error, commands.NotOwner):
        await ctx.send("You need to be owner to do that.")
    elif isinstance(error,commands.ExpectedClosingQuoteError):
        await ctx.send("You have inputted arguments incorrectly, you may have forgotten a closing \" or put one in by accident.")
    elif isinstance(error, commands.RoleNotFound):
        await ctx.send("That role could not be found.")
    elif isinstance(error, sqlite3.OperationalError):
        await ctx.send("Something went wrong while trying to access the SQL database. You may need to restore to a backup")
        raise error
    else:
        await ctx.send("Something has gone wrong somewhere, and most likely needs to be fixed")
        raise error

bot.run(Token)


if bot.restart:
    sys.exit(1)
else:
    sys.exit(0)
