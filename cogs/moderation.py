import discord
from discord import errors
from discord.ext import commands

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

    #unban
    @commands.command(help="unbans a user")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user : discord.User):
        guild = ctx.guild
        try:
            await guild.fetch_ban(user)
        except discord.NotFound:
            notBannedEmbed = discord.Embed(title = "This user is not banned", color = 0xFF0000)
            await ctx.send(embed = notBannedEmbed)
            return
        await guild.unban(user)
        successEmbed = discord.Embed(title = "Unbanned " + user.name, color = 0x00FF00)
        await ctx.send(embed=successEmbed)




def setup(bot):
    bot.add_cog(Moderation(bot))