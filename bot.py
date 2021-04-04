import discord
from discord.ext import commands
import sqlite3
import logging
import asyncio

# Logging config
logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', level=logging.INFO)

#Open txt files
with open("token.txt") as f:
    Token = f.read()

#Guild-Specific prefixes
async def get_pre(bot, message):
    prefix = "!"
    try:
        guildcommand = cursor.execute("SELECT prefix FROM guild_prefixes WHERE guild = ?", (message.guild.id,)).fetchone()
        prefix = (str(guildcommand[0]))
    except TypeError:
        pass
    except AttributeError:
        pass
    return prefix

#Help command
class NewHelp(commands.HelpCommand):
    async def create_help_field(self,ctx,embed,command):
        if command.help:
            description = (command.help[:command.help.find("\n")+1] if '\n' in command.help else command.help)
            if len(description) > 200:
                description = description[:197] + "..."
        else:
            description = "..."
        embed.add_field(name=f"{command.name}", value=f"{description}", inline=True)
        return embed

    async def send_bot_help(self,mapping):
        pageOut = 0
        colour = discord.Colour.random()
        titleDesc = ["YayaBot Help!",f"Say `{self.clean_prefix}help <command>` for more info on a command!"] 
        page = [discord.Embed(colour=colour,title=titleDesc[0],description=titleDesc[1])]
        for cog,commands in mapping.items():
            commands = await self.filter_commands(commands)
            if not commands:
                continue
            if len(page[-1].fields) >= 24: # If no space for commands or no space at all
                page.append(discord.Embed(colour=colour,title=titleDesc[0],description=titleDesc[1])) # New page
            cogName = getattr(cog,'qualified_name','No Category')
            cogDesc = '\n> '+ getattr(cog,"description",'...')
            page[-1].add_field(name=f"> **{cogName}**", value=cogDesc, inline=False) # Add cog field
            for command in commands:
                page[-1] = await self.create_help_field(self.context,page[-1],command)
                if command != commands[-1] and len(page[-1].fields) == 25: # If not the last command and new page is required
                    page.append(discord.Embed(colour=colour,title=titleDesc[0],description=titleDesc[1])) # New page
                    page[-1].add_field(name=f"> **{cogName}**", value=cogDesc, inline=False) # Add cog field
        if pageOut + 1 > len(page):
            pageOut = len(page) - 1
        page[pageOut].set_footer(text=f"Page {pageOut+1} of {len(page)}") # Add footer now (didn't know how many pages previously)
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
            page[pageOut].set_footer(text=f"{pageOut+1} of {len(page)}")
            await msg.edit(embed=page[pageOut])
            await reaction.remove(user)

    async def send_command_help(self,command):
        if not isinstance(command,commands.Cog):
            try:
                await command.can_run(self.context)
            except:
                return
        embed = discord.Embed(colour=discord.Colour.random(seed=command.qualified_name),title=f"Help for {command.qualified_name}" + (" cog" if isinstance(command,commands.Cog) else ' command'),description=(f"Aliases: {', '.join(list(command.aliases))}" if command.aliases else ""))
        if not isinstance(command,commands.Cog):
            embed.add_field(name="Usage",value=f"`{self.clean_prefix}{command.qualified_name}{(' ' + command.signature.replace('_',' ')    ) if command.signature else ' <subcommand>' if isinstance(command,commands.Group) else ''}`")
        embed.add_field(name="Description",value=(command.help.replace("[p]",self.clean_prefix) if command.help else '...'),inline=False)
        if isinstance(command,commands.Group) or isinstance(command,commands.Cog):
            embed.add_field(name="———————",value="**Subcommands**" if isinstance(command,commands.Group) else "**Commands**",inline=False)
            for subcommand in await self.filter_commands(command.commands, sort=True):
                embed = await self.create_help_field(self.context,embed,subcommand)
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
cursor.execute("CREATE TABLE IF NOT EXISTS role_ids (guild INTEGER PRIMARY KEY, gravel INTEGER, muted INTEGER, moderator INTEGER, admin INTEGER, modlogs INTEGER, command_usage INTEGER, command_cooldown INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS active_cases (id INTEGER PRIMARY KEY, expiration FLOAT)")
cursor.execute("CREATE TABLE IF NOT EXISTS caselog (id INTEGER PRIMARY KEY, id_in_guild INTEGER, guild INTEGER, user INTEGER, type TEXT, reason TEXT, started FLOAT, expires FLOAT, moderator TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS extensions (extension TEXT PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS message_filter (guild INTEGER PRIMARY KEY, enabled INTEGER NOT NULL, filterWildCard TEXT NOT NULL, filterExact TEXT NOT NULL)")
cursor.execute("CREATE TABLE IF NOT EXISTS spam_filters (guild INTEGER PRIMARY KEY, emoji_limit INTEGER, invite_filter INTEGER, message_spam_limit INTEGER, character_repeat_limit INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS tags (guild INTEGER PRIMARY KEY, role INTEGER, tags TEXT NOT NULL)")
cursor.execute("CREATE TABLE IF NOT EXISTS modlog_channels (guild INTEGER PRIMARY KEY, channel INTEGER)")
con.commit()

#startup
@bot.event
async def on_ready():
    appinfo = await bot.application_info()
    print("")
    logging.info(f"Bot started! Hello {str(appinfo.owner)}")
    logging.info(f"I'm connected as {str(bot.user)} - {bot.user.id}!")
    logging.info(f"In {len(bot.guilds)} guilds overlooking {len(list(bot.get_all_channels()))} channels and {len(list(bot.get_all_members()))} users.")
    print("")

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

print("")
logging.info("Loading Cogs.")
for extension in extensions:
    try:
        bot.load_extension(extension[0])
        logging.info(f"Loaded {extension[0]}")
    except commands.ExtensionNotFound:
        logging.info(f"Could not find {extension[0]}")
logging.info("Done.")
print("")
        
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
    elif isinstance(error, commands.RoleNotFound):
        await ctx.send("That role could not be found.")
    else:
        await ctx.send("Something has gone wrong somewhere, and most likely needs to be fixed")
        raise error

#check for mod-only commands
def has_modrole(ctx):
    modrole = cursor.execute("SELECT moderator FROM role_ids WHERE guild = ?", (ctx.guild.id,)).fetchone()
    member_roles = []
    for role in ctx.member.roles:
        member_roles.append(role.id)
    if modrole is None:
        return False
    elif (modrole in member_roles):
        return True
    else:
        return False

bot.run(Token)
print("Bot Session Ended")