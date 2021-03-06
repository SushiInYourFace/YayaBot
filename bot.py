import discord
from discord.ext import commands
import sqlite3
import logging

# Logging config
logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', level=logging.INFO)

#Open txt files
with open("Discord_Token.txt") as f:
    Token = f.read()

with open("Filtered.txt", "r") as f:
    bannedWords = [word.strip() for word in f.readlines()]

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
bot = commands.Bot(command_prefix=get_pre, intents=intents)

#SQLite
con = sqlite3.connect("database.db")
cursor = con.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS guild_prefixes (guild INTEGER PRIMARY KEY, prefix TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS role_ids (guild INTEGER PRIMARY KEY, gravel INTEGER, muted INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS extensions (extension TEXT PRIMARY KEY)")
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
initial_extensions = [
    'cogs.cmty',
    'cogs.moderation',
    'cogs.utilities',
    'cogs.owner'
]

for extension in initial_extensions:
    bot.load_extension(extension)

#on message
@bot.event
async def on_message(message):
    if message.author == bot.user or message.author.bot:
        return
    if any(bannedWord in message.content for bannedWord in bannedWords):
        await message.channel.send("Watch your goddamn mouth, libtard")
        await message.delete()
    await bot.process_commands(message)

#on edited message
@bot.event
async def on_message_edit(before, after):
    if any(bannedWord in after.content for bannedWord in bannedWords):
        await after.channel.send("Watch your goddamn mouth, libtard")
        try:
            await after.delete()
        except:
            pass
        
#error handling
@bot.event
async def on_command_error(ctx, error):
    if hasattr(ctx.command, 'on_error'):
            return
    ignored = (commands.CommandNotFound, )
    error = getattr(error, 'original', error)
    #ignores ignored errors
    if isinstance(error, ignored):
        return
    if isinstance(error, commands.MemberNotFound):
        await ctx.send("User not found")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Sorry, that is not a valid number of arguments for this command. If you need help understanding how this command works, please use the command %help (your command)')
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("Sorry, you don't have permission to use that command!")
    elif isinstance(error, discord.errors.Forbidden):
        await ctx.send("I don't have permission to do that.")
    else:
        await ctx.send("error")
        raise error

bot.run(Token)