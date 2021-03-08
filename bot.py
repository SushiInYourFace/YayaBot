import discord
from discord.ext import commands
import sqlite3
import logging

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
    return prefix

#intents, initializing bot
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix=get_pre, intents=intents, help_command=None)

#SQLite
con = sqlite3.connect("database.db")
cursor = con.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS guild_prefixes (guild INTEGER PRIMARY KEY, prefix TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS role_ids (guild INTEGER PRIMARY KEY, gravel INTEGER, muted INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS active_cases (id INTEGER PRIMARY KEY, expiration FLOAT)")
cursor.execute("CREATE TABLE IF NOT EXISTS caselog (id INTEGER PRIMARY KEY, guild INTEGER, user INTEGER, type TEXT, reason TEXT, started FLOAT, expires FLOAT, moderator TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS extensions (extension TEXT PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS message_filter (guild INTEGER PRIMARY KEY, enabled INTEGER NOT NULL, filter TEXT NOT NULL)")
cursor.execute("CREATE TABLE IF NOT EXISTS tags (guild INTEGER PRIMARY KEY, role INTEGER, tags TEXT NOT NULL)")
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
    ('cogs.cmty',),
    ('cogs.moderation',),
    ('cogs.utilities',),
    ('cogs.owner',)
]

extensions = cursor.execute("SELECT * FROM extensions").fetchall()

if not extensions:
    cursor.executemany("INSERT INTO extensions(extension) VALUES (?)", default_extensions)
    con.commit()
    extensions = default_extensions

print("")
logging.info("Loading Cogs.")
for extension in extensions:
    bot.load_extension(extension[0])
    logging.info(f"Loaded {extension[0]}")
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
        await ctx.send('Sorry, that is not a valid number of arguments for this command. If you need help understanding how this command works, please use the command help (your command)')
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

bot.run(Token)