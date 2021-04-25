import io
import random

import discord
from discord.ext import commands
from PIL import Image


class Community(commands.Cog):
    """Commands for the community!"""
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    #rats
    @commands.command(help="RATS RATS RATS RATS RATS RATS RATS RATS RATS RATS RATS RATS", aliases=["rats", "RATS", "RAT"], brief=":rat: ")
    async def rat(self, ctx):
        rat = random.choice(open("resources/rats.txt").readlines())
        await ctx.send(rat)

    @commands.command(help="Gives you the number of people in the server", brief=":slight_smile: ")
    async def membercount(self, ctx):
        await ctx.send(f"There are currently {ctx.guild.member_count} members in the server")

    @commands.command(help="No", brief=":rage: ")
    async def dyno(self, ctx):
        await ctx.send("No")

    @commands.Cog.listener()
    async def on_message(self,message):
        if message.type == discord.MessageType.new_member:
            await message.add_reaction("🎉")

    @commands.command(help="worm.",name="worm",aliases=["wormonastring","woas","string"],brief=":worm: ")
    async def worm(self,ctx,*,user:discord.Member=None):
        if not user:
            user = ctx.author
        image,wormColour = await self.get_worm(user.id)
        await ctx.send(f"{user.display_name} is a {discord.Colour.from_rgb(wormColour[0],wormColour[1],wormColour[2])} coloured worm!",file=image)

    async def get_worm(self,id,colour=False):
        if not colour:
            rand = random.Random(id)
            wormColour = (rand.randint(1,255),rand.randint(1,255),rand.randint(1,255),255)
        else:
            wormColour = id
        im = Image.open("resources/worm.png")
        im = im.convert("RGBA")
        pixels = im.load()
        for y in range(im.size[1]):
            for x in range(im.size[0]):
                if pixels[x,y] == (255,0,0,255):
                    pixels[x,y] = wormColour
        arr = io.BytesIO()
        im.save(arr, format='PNG')
        arr.seek(0)
        return discord.File(arr,filename="worm.png"),wormColour

def setup(bot):
    bot.add_cog(Community(bot))
