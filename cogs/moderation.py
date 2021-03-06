import discord
from discord import errors
from discord.ext import commands
import sqlite3
import time

#sets up SQLite
connection = sqlite3.connect("database.db")
cursor = connection.cursor()

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    #purge command
    @commands.command(help="Purges a specified amount of messages from the chat")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, arg):
        try:
            arg = int(arg)
        except ValueError:
            await ctx.send("That's not a valid number. To use this command, please use the number of messages to purge as your argument")
        await ctx.channel.purge(limit=arg)
    
    #purge match command, only purges messages that contain a certain string
    @commands.command(help="Purges messages containing a certain string", aliases=["purge-match",])
    @commands.has_permissions(manage_messages=True)
    async def purgematch(self, ctx, limit, *, filtered):
        try:
            limit = int(limit)
        except ValueError:
            await ctx.send("That's not a valid number. To use this command, please use the number of messages to purge as yor first argument, and the filter to use as your second")
        def filter_check(message):
            return filtered in message.content
        await ctx.channel.purge(limit=limit, check=filter_check)

    #ban
    @commands.command(help="bans a user")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member : discord.Member, *, arg):
        guild = ctx.guild
        username = member.name
        userid = member.id
        bantime = time.time()
        banEmbed = discord.Embed(title="You have been banned from "+ ctx.guild.name, color=0xFF0000)
        banEmbed.add_field(name="Ban reason:", value=arg)
        try:
            await member.send(embed=banEmbed)
            unsent = False
        except errors.HTTPException:
            unsent = True
        await guild.ban(member, reason=arg)
        successEmbed = discord.Embed(title="Banned " + username, color=0xFF0000)
        if unsent:
            successEmbed.set_footer(text="Failed to send a message to this user")
        await ctx.send(embed=successEmbed)
        SqlCommands.new_case(userid, "ban", arg, bantime, -1)


    #unban
    @commands.command(help="unbans a user")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user : discord.User):
        guild = ctx.guild
        userid = user.id
        unbanTime = time.time()
        try:
            await guild.fetch_ban(user)
        except discord.NotFound:
            notBannedEmbed = discord.Embed(title = "This user is not banned", color = 0xFF0000)
            await ctx.send(embed = notBannedEmbed)
            return
        await guild.unban(user)
        successEmbed = discord.Embed(title = "Unbanned " + user.name, color = 0x00FF00)
        await ctx.send(embed=successEmbed)
        SqlCommands.new_case(userid, "unban", "N/A", unbanTime, -1)




def setup(bot):
    bot.add_cog(Moderation(bot))

class Sql:
    def newest_case(self):
        caseNumber = cursor.execute("SELECT id FROM caselog ORDER BY id DESC LIMIT 1").fetchone()
        if caseNumber == None:
            caseNumber = 0
        else:
            caseNumber = caseNumber[0]
        caseNumber += 1
        return(caseNumber)

    def new_case(self, user, casetype, reason, started, expires):
        caseID = self.newest_case()
        if expires != -1:
            cursor.execute("INSERT INTO active_cases(id, expiration) VALUES(?,?)", (caseID, expires))
        cursor.execute("INSERT INTO caselog(id, user, type, reason, started, expires) VALUES(?,?,?,?,?,?)", (caseID, user, casetype, reason, started, expires))
        connection.commit()

SqlCommands = Sql()