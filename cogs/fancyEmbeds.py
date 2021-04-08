import discord
from discord.ext import commands
import sqlite3, json
import time, datetime
import functions

connection = sqlite3.connect("database.db")
c = connection.cursor()

def setup(bot):
    bot.add_cog(fancyEmbeds(bot))

def tryMakeStorage():
    try:
        with open("embeds.json", "x") as f:
            json.dump(
                {
                    "active": "default",
                    "styles": {
                        "default": {"colors": [0xef7d0d, 0xc51111, 0xb33e15, 0xc28722], "time": True, "emoji": True}
                    },
                }, 
                f, 
                indent=4
            )
    except:
        return

class fancyEmbeds(commands.Cog):
    """Makes embeds look cool and fancy!"""

    def __init__(self, bot):
        self.bot = bot
        tryMakeStorage()

    def getActiveStyle(self):
        """Returns the active embed style."""
        with open("embeds.json", "r+") as f:
            f_ = json.load(f)
            return f_["active"]

    def getStyleValue(self, style, data):
        """Returns a value from the specified style. To get the active style, use fancyEmbeds.getActiveStyle()."""
        with open("embeds.json", "r+") as f:
            f_ = json.load(f)
            return f_["styles"][style][data]

    def makeEmbed(self, embTitle="", desc=None, useColor=0, force=False, forceColor=None, footer=None, nofooter=False):
        """Build an embed based on the current embed Style.
        
        Returns a discord.Embed with a title, description (if specified), color and footer based on the active embed style values.\n
        You can set the keyword Force to True if you wish to force a specific color onto the embed, and specify that color as forceColor. 
        """
        with open("embeds.json", "r+") as f:
            f_ = json.load(f)
            style = f_["active"]
            colorType = f_["styles"][style]["colors"][int(useColor)]
            timestamps = f_["styles"][style]["time"]

        if force is True:
            if forceColor is None:
                raise TypeError
            colorType = int(forceColor)

        if desc == None and timestamps == False:
            emb = discord.Embed(title=embTitle, color=discord.Colour(int(colorType)))
        elif desc == None:
            emb = discord.Embed(title=embTitle, color=discord.Colour(colorType), timestamp=datetime.datetime.utcfromtimestamp(time.time()))
        elif timestamps == False:
            emb = discord.Embed(title=embTitle, color=discord.Colour(colorType), description=desc)
        else:
            emb = discord.Embed(title=embTitle, color=discord.Colour(colorType), description=desc, timestamp=datetime.datetime.utcfromtimestamp(time.time()))

        if nofooter == False:
            if footer == None:
                emb.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
            else:
                emb.set_footer(text=f"{self.bot.user.name} - {footer}", icon_url=self.bot.user.avatar_url)

        return emb

    def addFooter(self, embed, footer):
        embed.set_footer(text=f"{self.bot.user.name} - {footer}", icon_url=self.bot.user.avatar_url)
        
        return embed

    @commands.group(help="Manage how embeds are sent.")
    @commands.check(functions.has_modrole)
    async def embed(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @embed.group(help="Manage your embed styles.")
    async def style(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @style.command(help="List available embed styles.")
    async def list(self, ctx):
        s = fancyEmbeds.getActiveStyle(self)
        if fancyEmbeds.getStyleValue(self, s, "emoji") is False:
            emojia = ""
            emojib = ""
            emojic = ""
        else:
            emojia = ":ledger: "
            emojib = ":clock3: "
            emojic = ":slight_smile: "

        emb = fancyEmbeds.makeEmbed(self, embTitle=f"{emojia}Embed Styles", desc="Currently available embed styles:", useColor=0)

        with open("embeds.json", "r+") as f:
            f_ = json.load(f)
            for s in f_["styles"].keys():
                ts = fancyEmbeds.getStyleValue(self, s, "time")
                emoji = fancyEmbeds.getStyleValue(self, s, "emoji")
                emb.add_field(name=s, value=f"{emojib}Uses Timestamps: {ts}\n{emojic}Uses Emoji: {emoji}")

        await ctx.send(embed=emb)

    @style.command(help="Change the in-use embed style.")
    async def set(self, ctx, new: str):
        with open("embeds.json", "r+") as f:
            f_ = json.load(f)
            try:
                test = f_["styles"][new]
            except KeyError:
                await ctx.send("Sorry, that style does not exist!")
                return
            
            f_["active"] = new

            with open("embeds.json", "w") as f:
                json.dump(f_, f, indent=4)

            await ctx.send(f"Changed to embed style {new} successfully!")

    @style.command(help="Create a new embed style.")
    async def new(self, ctx, name: str):
        with open("embeds.json", "r+") as f:
            f_ = json.load(f)
            f_["styles"][name] = {}
            f_["styles"][name]["colors"] = [0x000000, 0x000000, 0x000000, 0x000000]
            f_["styles"][name]["time"] = True
            f_["styles"][name]["emoji"] = True

        with open("embeds.json", "w") as f:
            json.dump(f_, f, indent=4)

        await ctx.send(f"Created a new style with the name {name}.")

    @style.command(help="View the properties of an embed style.")
    async def preview(self, ctx, name:str):
        with open("embeds.json", "r+") as f:
            f_ = json.load(f)
            col = f_["styles"][name]["colors"]
            time = f_["styles"][name]["time"]
            emoji = f_["styles"][name]["emoji"]

        if emoji is False:
            emojia = ""
            emojib = ""
            emojic = ""
            emojid = ""
        else:
            emojia = ":ledger:"
            emojib = ":clock3:"
            emojic = ":slight_smile:"
            emojid = ":paintbrush:"

        embed = fancyEmbeds.makeEmbed(self, embTitle=f"{emojia}Embed style properties for {name}:", desc=None, useColor=1)
        embed.add_field(name=f"{emojid}Colors", value=f"This style uses the following color values:\n{col[0]}, {col[1]}, {col[2]}, and {col[3]}", inline=False)

        if time is True:
            embed.add_field(name=f"{emojib}Timestamp", value="This style will show timestamps.")
        else:
            embed.add_field(name=f"{emojib}Timestamp", value="This style will not show timestamps.")

        if emoji is True:
            embed.add_field(name=f"{emojic}Emoji", value="This style will use emoji.")
        else:
            embed.add_field(name=f"{emojic}Emoji", value="This style will not use emoji.")

        await ctx.send(embed=embed)

    @style.group(help="Customize the properties of an embed style.")
    async def customize(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @customize.command(help="Change the colors of an embed style. Colors should use base16/hexcolor values.")
    async def color(self, ctx, style: str, color1, color2, color3, color4):
        with open("embeds.json", "r+") as f:
            f_ = json.load(f)
            try:
                test = f_["styles"][style]
            except KeyError:
                await ctx.send(f"The style {style} does not exist!")
                return

            f__ = f_["styles"][style]["colors"]

        #this may be unoptimized, but it works for now!

        newCol = []

        if len(color1) > 6:
            await ctx.send("That is not a valid color!")
            return
        if len(color2) > 6:
            await ctx.send("That is not a valid color!")
            return
        if len(color3) > 6:
            await ctx.send("That is not a valid color!")
            return
        if len(color4) > 6:
            await ctx.send("That is not a valid color!")
            return

        color1 = int(color1, 16)
        color2 = int(color2, 16)
        color3 = int(color3, 16)
        color4 = int(color4, 16)

        if color1 == 0:
            newCol.append(f__[0])
        else:
            newCol.append(color1)

        if color2 == 0:
            newCol.append(f__[1])
        else:
            newCol.append(color2)

        if color3 == 0:
            newCol.append(f__[2])
        else:
            newCol.append(color3)

        if color4 == 0:
            newCol.append(f__[3])
        else:
            newCol.append(color4)
            
        f_["styles"][style]["colors"] = newCol

        with open("embeds.json", "w") as f:
            json.dump(f_, f, indent=4)

        await ctx.send(f"Updated colors for style {style}")

    @customize.command(help="Change whether a style shows timestamps.")
    async def toggletime(self, ctx, style):
        with open("embeds.json", "r+") as f:
            f_ = json.load(f)
            try:
                test = f_["styles"][style]
            except KeyError:
                await ctx.send(f"The style {style} does not exist!")
                return

            f__ = f_["styles"][style]["time"]

            if f__ is False:
                f_["styles"][style]["time"] = True
                new = True
            else:
                f_["styles"][style]["time"] = False
                new = False

        with open("embeds.json", "w") as f:
            json.dump(f_, f, indent=4)

        await ctx.send(f"Set showing timestamps to {new} for style {style}.")

    @customize.command(help="Change whether a style shows emoji.")
    async def toggleemoji(self, ctx, style):
        with open("embeds.json", "r+") as f:
            f_ = json.load(f)
            try:
                test = f_["styles"][style]
            except KeyError:
                await ctx.send(f"The style {style} does not exist!")
                return

            f__ = f_["styles"][style]["emoji"]

            if f__ is False:
                f_["styles"][style]["emoji"] = True
                new = True
            else:
                f_["styles"][style]["emoji"] = False
                new = False

        with open("embeds.json", "w") as f:
            json.dump(f_, f, indent=4)

        await ctx.send(f"Set showing emoji to {new} for style {style}.")