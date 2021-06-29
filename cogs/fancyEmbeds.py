import datetime
import json
import logging
import time
import typing

import discord
from discord.ext import commands

import functions

#Add cog to the bot
def setup(bot):
    bot.add_cog(fancyEmbeds(bot))

#Attempts to make a storage for the given guild id. Called by many of the embed commands andfunctions when they throw KeyErrors.
def tryMakeStorage(guildid):
    try:
        #Check to see if the storage exists, if not, create it and dump a json object for the guild id into it.
        with open("embeds.json", "x") as f:
            json.dump(
                {
                    guildid: {
                        "active": "shinyamber",
                        "styles": {
                            "shinyamber": {"colors": [0xFF8F00, 0xFFB300, 0xFFAB40, 0xFFE082], "time": True, "emoji": True},
                            "electricblue": {"colors":[0x03A9F4, 0x0288D1, 0x4FC3F7, 0x80D8FF], "time": True, "emoji": True},
                            "lushgreen": {"colors":[0x64DD17, 0x388E3C, 0x8BC34A, 0xA5D6A7], "time": True, "emoji": True},
                            "royalpurple": {"colors":[0xE040FB, 0xD500F9, 0xEA80FC, 0xB388FF], "time": True, "emoji": True},
                            "colorful": {"colors":[0x2196F3, 0xFFC107, 0xF44336, 0x76FF03], "time": True, "emoji": True}
                        },
                    }
                },
                f,
                indent=4
            )
        logging.info(f"Created new storage and added object for guild with id {guildid}")
    except:
        #If the storage exists, read and load the file to a variable to add to.
        with open("embeds.json", "r+") as f:
            f_ = json.load(f)
                #This should throw a KeyError
            if "active" in f_[guildid]:
                #This shouldn't happen, if it does, then i probably overlooked something somewhere. This only appears when tryMakeStorage() is called when the given guildid already has a storage.
                logging.error("If you see this, then you found something that shouldn't happen! If this problem persists, you should report it.")
            else:
                #Add the new object into the storage with the default data.
                f_[guildid] = {
                    "active": "shinyamber",
                    "styles": {
                        "shinyamber": {"colors": [0xFF8F00, 0xFFB300, 0xFFAB40, 0xFFE082], "time": True, "emoji": True},
                        "electricblue": {"colors":[0x03A9F4, 0x0288D1, 0x4FC3F7, 0x80D8FF], "time": True, "emoji": True},
                        "lushgreen": {"colors":[0x64DD17, 0x388E3C, 0x8BC34A, 0xA5D6A7], "time": True, "emoji": True},
                        "royalpurple": {"colors":[0xE040FB, 0xD500F9, 0xEA80FC, 0xB388FF], "time": True, "emoji": True},
                        "colorful": {"colors":[0x2196F3, 0xFFC107, 0xF44336, 0x76FF03], "time": True, "emoji": True}
                    },
                }
                logging.info(f"Created storage object for guild with id {guildid}")
        #Dump the new storage into embedss.json.
        with open("embeds.json", "w") as f:
            json.dump(f_, f, indent=4)

class fancyEmbeds(commands.Cog):
    """Makes embeds look cool and fancy!"""

    def __init__(self, bot):
        self.bot = bot

    def getActiveStyle(self, guildid):
        """Returns the active embed style."""
        guildid = str(guildid)
        try:
            with open("embeds.json", "r+") as f:
                f_ = json.load(f)
                return f_[guildid]["active"]
        except:
            tryMakeStorage(guildid)
            with open("embeds.json", "r+") as f:
                f_ = json.load(f)
                return f_[guildid]["active"]

    def getStyleValue(self, guildid, style, data):
        """Returns a value from the specified style. To get the active style, use fancyEmbeds.getActiveStyle()."""
        guildid = str(guildid)
        try:
            with open("embeds.json", "r+") as f:
                f_ = json.load(f)
                return f_[guildid]["styles"][style][data]
        except:
            tryMakeStorage(guildid)
            with open("embeds.json", "r+") as f:
                f_ = json.load(f)
                return f_[guildid]["styles"][style][data]

    #This should always be used instead of discord.Embed() when you want to make an embed in the bot. Hopefully this accounts for your embed needs.
    #Fields can still be created in the normal way.
    def makeEmbed(self, guildid, embTitle="", desc=None, useColor=0, force=False, forceColor=None, footer=None, nofooter=False, b=None):
        """Build an embed based on the current embed Style.

        Returns a discord.Embed with a title, description (if specified), color and footer based on the active embed style values.\n
        You can set the keyword Force to True if you wish to force a specific color onto the embed, and specify that color as forceColor.\n
        To add content to the footer here, set footer, or if you want to set a footer later, set nofooter to True here and add it later through addFooter()
        """
        #Get all the required embed style data from storage
        style = fancyEmbeds.getActiveStyle(self, guildid)
        col = fancyEmbeds.getStyleValue(self, guildid, style, "colors")
        colorType = discord.Colour(col[int(useColor)])
        timestamps = fancyEmbeds.getStyleValue(self, guildid, style, "time")

        #Color override
        if force is True:
            if forceColor is None:
                raise TypeError
            if isinstance(forceColor,tuple):
                red = int(forceColor[0])
                green = int(forceColor[1])
                blue = int(forceColor[2])

                colorType = discord.Colour.from_rgb(red, green, blue)
            else:
                colorType = discord.Colour(int(forceColor))

        #Create the embed, this little block handles the four scenarios which change the values which should be passed.
        if desc is None and timestamps is False:
            emb = discord.Embed(title=embTitle, color=colorType)
        elif desc is None:
            emb = discord.Embed(title=embTitle, color=colorType, timestamp=datetime.datetime.utcfromtimestamp(time.time()))
        elif timestamps is False:
            emb = discord.Embed(title=embTitle, color=colorType, description=desc)
        else:
            emb = discord.Embed(title=embTitle, color=colorType, description=desc, timestamp=datetime.datetime.utcfromtimestamp(time.time()))

        #Check to see whether the footer should be added and if so, add it.
        if nofooter is False:
            #This might not be necessary, could be removed soon.
            if b is not None:
                self.bot = b

            #Create footer with bot icon, name, and, if specified, extra footer content.
            if footer is None:
                emb.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
            else:
                emb.set_footer(text=f"{self.bot.user.name} - {footer}", icon_url=self.bot.user.avatar_url)

        #finally, return the embed.
        return emb

    #For adding footers at a later point, in scenarios where you can't know what you'll need as extra content until after the intial embed creation.
    def addFooter(self, embed, footer, bot):
        """"Add a footer to an embed with fancy embeds formatting. Only necessary when you make an embed with nofooter set to True, otherwise makeEmbed() will create this for you."""
        embed.set_footer(text=f"{bot.user.name} - {footer}", icon_url=bot.user.avatar_url)

        return embed

    #Embed command group
    @commands.group(help="Manage how embeds are sent.", brief=":page_facing_up: ")
    @commands.check(functions.has_modrole)
    async def embed(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    #Style Listing
    @embed.command(help="List available embed styles.", aliases=["styles", "l"], brief=":ledger: ")
    async def list(self, ctx):
        guildid = str(ctx.guild.id)

        s = fancyEmbeds.getActiveStyle(self, guildid)

        if fancyEmbeds.getStyleValue(self, guildid, s, "emoji") is False:
            emojia = ""
            emojib = ""
            emojic = ""
        else:
            emojia = ":ledger: "
            emojib = ":clock3: "
            emojic = ":slight_smile: "

        emb = fancyEmbeds.makeEmbed(self, guildid, embTitle=f"{emojia}Embed Styles", desc="Currently available embed styles:", useColor=0)

        with open("embeds.json", "r+") as f:
            f_ = json.load(f)
            for s in f_[guildid]["styles"].keys():
                ts = fancyEmbeds.getStyleValue(self, guildid, s, "time")
                emoji = fancyEmbeds.getStyleValue(self, guildid, s, "emoji")
                emb.add_field(name=s, value=f"{emojib}Timestamps: {ts}\n{emojic}Emoji: {emoji}")

        await ctx.send(embed=emb)

    #Change the active embed style
    @embed.command(help="Change the in-use embed style.", aliases=["setactive", "a"], brief=":bookmark_tabs: ")
    async def active(self, ctx, new: str):
        try:
            with open("embeds.json", "r+") as f:
                f_ = json.load(f)
                if not new in f_[str(ctx.guild.id)]["styles"]:
                    await ctx.send("Sorry, that style does not exist!")
                    return
        except:
            tryMakeStorage(ctx.guild.id)
            with open("embeds.json", "r+") as f:
                f_ = json.load(f)
                if not new in f_[str(ctx.guild.id)]["styles"]:
                    await ctx.send("Sorry, that style does not exist!")
                    return

        f_[str(ctx.guild.id)]["active"] = new

        with open("embeds.json", "w") as f:
            json.dump(f_, f, indent=4)

        await ctx.send(f"Changed to embed style {new} successfully!")

    #Create a new embed style. Could add optional ability to add colours and set time/emoji here too.
    @embed.command(help="Create a new embed style.", aliases=["create", "add", "n"], brief=":pencil2: ")
    async def new(self, ctx, name: str):
        try:
            with open("embeds.json", "r+") as f:
                f_ = json.load(f)
                f_[str(ctx.guild.id)]["styles"][name] = {}
                f_[str(ctx.guild.id)]["styles"][name]["colors"] = [0x000000, 0x000000, 0x000000, 0x000000]
                f_[str(ctx.guild.id)]["styles"][name]["time"] = True
                f_[str(ctx.guild.id)]["styles"][name]["emoji"] = True

            with open("embeds.json", "w") as f:
                json.dump(f_, f, indent=4)
        except:
            tryMakeStorage(ctx.guild.id)
            with open("embeds.json", "r+") as f:
                f_ = json.load(f)
                f_[str(ctx.guild.id)]["styles"][name] = {}
                f_[str(ctx.guild.id)]["styles"][name]["colors"] = [0x000000, 0x000000, 0x000000, 0x000000]
                f_[str(ctx.guild.id)]["styles"][name]["time"] = True
                f_[str(ctx.guild.id)]["styles"][name]["emoji"] = True

            with open("embeds.json", "w") as f:
                json.dump(f_, f, indent=4)

        await ctx.send(f"Created a new style with the name {name}.")

    #Preview the values of a given embed style. Currently this is honestly useless, i'll need to add colour previews before this stops sucking and has any real value aside from testing.
    @embed.command(help="View the properties of an embed style.", aliases=["view", "p"], brief=":newspaper: ")
    async def preview(self, ctx, name):
        guildid = ctx.guild.id

        #Check that the style exists first. Throws a false error later if the style doesn't exist.
        with open("embeds.json", "r+") as f:
            f_ = json.load(f)
            if not name in f_[str(guildid)]["styles"]:
                await ctx.send("That style does not exist!")
                return

        col = fancyEmbeds.getStyleValue(self, guildid, name, "colors")
        time = fancyEmbeds.getStyleValue(self, guildid, name, "time")
        emoji = fancyEmbeds.getStyleValue(self, guildid, name, "emoji")

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

        embed = fancyEmbeds.makeEmbed(self, ctx.guild.id, embTitle=f"{emojia}Embed style properties for {name}:", desc=None, useColor=1)
        embed.add_field(name=f"{emojid}Colors", value=f"This style uses the following color values:\n{hex(col[0])}, {hex(col[1])}, {hex(col[2])}, and {hex(col[3])}", inline=False)

        if time is True:
            embed.add_field(name=f"{emojib}Timestamp", value="This style shows timestamps.")
        else:
            embed.add_field(name=f"{emojib}Timestamp", value="This style does not show timestamps.")

        if emoji is True:
            embed.add_field(name=f"{emojic}Emoji", value="This style uses emoji.")
        else:
            embed.add_field(name=f"{emojic}Emoji", value="This style does not use emoji.")

        await ctx.send(embed=embed)

    #Change the colour values in an embed.
    @embed.command(help="Change the colors of an embed style, using hexcolor values.", aliases=["c", "setcolor", "colour", "setcolour"], brief=":yellow_square: ")
    async def color(self, ctx, style: str, color1: typing.Optional[str] = "-1", color2: typing.Optional[str] = "-1", color3: typing.Optional[str] = "-1", color4: typing.Optional[str] = "-1"):
        try:
            with open("embeds.json", "r+") as f:
                f_ = json.load(f)
                if not style in f_[str(ctx.guild.id)]["styles"]:
                    await ctx.send(f"The style {style} does not exist!")
                    return
            f__ = f_[str(ctx.guild.id)]["styles"][style]["colors"]
        except:
            tryMakeStorage(ctx.guild.id)
            with open("embeds.json", "r+") as f:
                f_ = json.load(f)
                if not style in f_[str(ctx.guild.id)]["styles"][style]:
                    await ctx.send(f"The style {style} does not exist!")
                    return
            f__ = f_[str(ctx.guild.id)]["styles"][style]["colors"]

        oldCol = [color1, color2, color3, color4]
        newCol = []
        i = 0

        for color in oldCol:
            if len(color) > 6:
                await ctx.send("That is not a valid color!")
                return
            try:
                color = int(color, 16)
            except:
                await ctx.send("That is not a valid color!")
                return
            if color == -1:
                newCol.append(f__[i])
            else:
                newCol.append(color)
            i = i + 1

        f_[str(ctx.guild.id)]["styles"][style]["colors"] = newCol

        with open("embeds.json", "w") as f:
            json.dump(f_, f, indent=4)

        await ctx.send(f"Updated colors for style {style}.")

    #Toggle timestamps on/off
    @embed.command(help="Change whether a style shows timestamps.", aliases=["time", "t", "tt"], brief=":clock3: ")
    async def toggletime(self, ctx, style):
        try:
            with open("embeds.json", "r+") as f:
                f_ = json.load(f)
                if not style in f_[str(ctx.guild.id)]["styles"]:
                    await ctx.send(f"The style {style} does not exist!")
                    return
        except:
            tryMakeStorage(ctx.guild.id)
            with open("embeds.json", "r+") as f:
                f_ = json.load(f)
                if not style in f_[str(ctx.guild.id)]["styles"]:
                    await ctx.send(f"The style {style} does not exist!")
                    return

        f__ = f_[str(ctx.guild.id)]["styles"][style]["time"]

        if f__ is False:
            f_[str(ctx.guild.id)]["styles"][style]["time"] = True
        else:
            f_[str(ctx.guild.id)]["styles"][style]["time"] = False

        with open("embeds.json", "w") as f:
            json.dump(f_, f, indent=4)

        if f__ is False:
            await ctx.send(f"Timestamps now show for the style {style}.")
        else:
            await ctx.send(f"Timestamps no longer show for the style {style}")

    #Toggle emojis on/off
    @embed.command(help="Change whether a style shows emoji.", aliases=["emoji", "e", "te"], brief=":slight_smile: ")
    async def toggleemoji(self, ctx, style):
        try:
            with open("embeds.json", "r+") as f:
                f_ = json.load(f)
                if not style in f_[str(ctx.guild.id)]["styles"]:
                    await ctx.send(f"The style {style} does not exist!")
                    return
        except:
            tryMakeStorage(ctx.guild.id)
            with open("embeds.json", "r+") as f:
                f_ = json.load(f)
                if not style in f_[str(ctx.guild.id)]["styles"]:
                    await ctx.send(f"The style {style} does not exist!")
                    return

        f__ = f_[str(ctx.guild.id)]["styles"][style]["emoji"]

        if f__ is False:
            f_[str(ctx.guild.id)]["styles"][style]["emoji"] = True
        else:
            f_[str(ctx.guild.id)]["styles"][style]["emoji"] = False

        with open("embeds.json", "w") as f:
            json.dump(f_, f, indent=4)

        if f__ is False:
            await ctx.send(f"Emoji now show for the style {style}.")
        else:
            await ctx.send(f"Emoji no longer show for the style {style}")
