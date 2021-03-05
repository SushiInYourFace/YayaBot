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
    prefixes = ["!"]
    try:
         guildcommand = cursor.execute("SELECT prefix FROM guild_prefixes WHERE guild = ?", (message.guild.name,)).fetchone()
         prefixes.append(str(guildcommand[0]))
    except TypeError:
        pass
    return prefixes

#intents, initializing bot
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix=get_pre, intents=intents)

#SQLite
con = sqlite3.connect("database.db")
cursor = con.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS guild_prefixes (guild TEXT PRIMARY KEY, prefix TEXT)")

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
    else:
        await ctx.send("error")

bot.run(Token)

