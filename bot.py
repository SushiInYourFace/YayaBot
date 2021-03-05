import discord
from discord.ext import commands
import sqlite3

#Open txt files
Token = open("Discord_Token.txt").read()
filterFile = open("Filtered.txt", "r")
bannedWords = filterFile.readlines()
bannedWords = [word.strip() for word in bannedWords]
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
con.commit()

#startup
@bot.event
async def on_ready():
    print("Connected!")

#cogs to be loaded on startup
initial_extensions = [
    'cogs.cmty',
    'cogs.moderation',
    'cogs.utilities'
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
    await bot.process_commands(message)

#on edited message
@bot.event
async def on_message_edit(before, after):
    if any(bannedWord in after.content for bannedWord in bannedWords):
        await after.channel.send("Watch your goddamn mouth, libtard")
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
    else:
        await ctx.send("error")

bot.run(Token)

