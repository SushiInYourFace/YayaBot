import io
import asyncio
import random
import datetime
import time
import logging

import discord
from discord.ext import commands, tasks
from PIL import Image

import functions
import cogs.fancyEmbeds as fEmbeds
from utils.checks import checks


class Community(commands.Cog):
    """Commands for the community!"""
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.connection = bot.connection
        self.poll_check.start()

    def cog_unload(self):
        self.poll_check.cancel()

    #rats
    @commands.command(help="RATS RATS RATS RATS RATS RATS RATS RATS RATS RATS RATS RATS", aliases=["rats", "RATS", "RAT"], brief=":rat: ")
    async def rat(self, ctx):
        rat = random.choice(open("resources/rats.txt").readlines())
        await ctx.send(rat)

    @commands.command(help="Gives you the number of people in the server", brief=":slight_smile: ")
    async def membercount(self, ctx):
        await ctx.send(f"There are currently {ctx.guild.member_count} members in the server")

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

    @commands.group(brief=":ballot_box: ")
    @commands.check(checks.has_modrole)
    async def poll(self, ctx):
        """Create polls!"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
    
    @poll.command(brief=":pencil2: ", name="create")
    async def poll_create(self, ctx, description: str, channel: str, duration: str):
        """
        Creates a new poll in the current channel.
        Valid time duration formats: `s, m, h, d`
        """
        try:
            if duration[-1:] == "s":
                dur = int(duration[:-1])
                duration = duration.replace("s", " seconds")
            elif duration[-1:] == "m":
                dur = int(duration[:-1]) * 60
                duration = duration.replace("m", " minutes")
            elif duration[-1:] == "h":
                dur = int(duration[:-1]) * 3600
                duration = duration.replace("h", " hours")
            elif duration[-1:] == "d":
                dur = int(duration[:-1]) * 86400
                duration = duration.replace("d", " days")
            else:
                badtimemsg = await ctx.send("You did not specify a correct time format!")
                await badtimemsg.delete(delay=5.0)
                return
        except ValueError:
            badtimemsg = await ctx.send("You did not specify a valid amount of time!")
            await badtimemsg.delete(delay=5.0)
            return

        try:
            channel = await commands.TextChannelConverter().convert(ctx,channel)
        except discord.ext.commands.errors.ChannelNotFound:
            badchannelmsg = await ctx.send("That is not a valid channel!")
            await badchannelmsg.delete(delay=5.0)
            return

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        if emoji is False:
            emojis = ["", "", ""]
        else:
            emojis = [":ballot_box: ", ":alarm_clock: ", ":white_check_mark: "]

        options = []
        messages = []
        output = ""
        active = True
        cancelmsg = " Type \"stop\" to stop adding options."
        i = 0
        nums = [":one: ", ":two: ", ":three: ", ":four: ", ":five: ", ":six: ", ":seven: ", ":eight: ", ":nine: "]
        reacts = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]

        def check(reply):
            return reply.author == ctx.author

        async def clean(messages):
            for message in messages:
                try:
                    await message.delete()
                except discord.errors.NotFound:
                    pass
            messages = []

        while active:
            index = len(options)
            try:
                optionmsg = f"Please state option {index + 1} of this poll. Say \"cancel\" to abort creating this poll."
                message = await ctx.send(optionmsg + cancelmsg if index > 0 else optionmsg)
                messages.append(message)
                reply = await self.bot.wait_for("message", timeout=60.0, check=check)
                messages.append(reply)
            except asyncio.TimeoutError:
                timeoutmsg = await ctx.send("You didn't reply in time! Cancelling poll creation...")
                await clean(messages)
                await timeoutmsg.delete(delay=5.0)
                return
            if reply.content.lower() == "stop":
                if index > 0:
                    active = False
                    await clean(messages)
                    break
                else:
                    nooptionsmsg = await ctx.send("You can't make a poll with no options!")
                    await clean(messages)
                    await nooptionsmsg.delete(delay=3.0)
                    return
            else:
                options.append(reply.content)
                addmsg = await ctx.send(f"Added option {index + 1}:\n{reply.content}")
                messages.append(addmsg)
            if reply.content.lower() == "cancel":
                cancel = await ctx.send("Aborting poll creation...")
                await clean(messages)
                await cancel.delete(delay=3.0)
                return
            await message.delete()
            await reply.delete()
            if index == 8:
                maxopsmsg = await ctx.send("Reached the maximum number of poll options.")
                active = False
                await clean(messages)
                await maxopsmsg.delete(delay=3.0)

        for option in options:
            output = output + reacts[i] + " " + options[i] + "\n"
            i = i + 1

        expires = int(time.time()) + dur

        embed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, f"{emojis[0]}**Poll**", description + f"\n{emojis[1]}Poll duration: {duration} (ends <t:{expires}:R>)", useColor=1)
        embed.add_field(name="**Options**", value=output)

        poll = await channel.send(embed=embed)
        for n in range(0, i):
            await poll.add_reaction(emoji=reacts[n])

        if channel != ctx.channel:
            confirmembed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, f"{emojis[2]}**Poll Created**", f"[Jump to Message]({poll.to_reference().jump_url})", footer=f"Poll ID: {channel.id}/{poll.id}")
            await ctx.send(embed=confirmembed)

        cursor = await self.connection.cursor()
        await cursor.execute("INSERT INTO active_polls(id, guildid, channelid, expires, description) VALUES(?, ?, ?, ?, ?)", (poll.id, ctx.guild.id, channel.id, expires, description))
        await self.connection.commit()
        await cursor.close()

    @poll.command(brief=":fast_forward: ", name="end")
    async def poll_end(self, ctx, id):
        """
        End a poll before it was scheduled to end.
        Note that ids are given in the form `channelid/messageid` not JUST the message id. 
        """
        #basically just the poll task but copied and tweaked
        id = id.partition("/")
        if id[1] != "/":
            await ctx.send("That is not a valid poll id!")
        channel_id = id[0]
        id = id[2]
        
        for channel in ctx.guild.text_channels:
            if str(channel.id) == str(channel_id):
                msg = await channel.fetch_message(id)
                break
            
        try:
            test = msg.content
        except UnboundLocalError:
            await ctx.send("That is not a valid poll id!")
            return

        cursor = await self.connection.execute(f"SELECT id, description FROM active_polls WHERE id = ?", (id,))
        try:
            polls = await cursor.fetchall()
            await cursor.close()
        except AttributeError:
            await ctx.send("That is not an active poll!")
            await cursor.close()
            return
        try:
            test = polls[0]
        except IndexError:
            await ctx.send("That is not an active poll!")
            return

        for poll in polls:
            guild = ctx.guild
            outputs = []
            options = []
            fieldcont = ""
            output = ""
            votes = []
            most_votes = [0, 0]
            nums = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
            total = 0
            i = 0
            vi = 0
            reacts = msg.reactions
            embed = msg.embeds[0]
            field = embed.fields[0]
            value = field.value
            option_count = value.count("\n")
            for n in range(0, option_count + 1):
                tup = value.partition("\n")
                options.append((nums[n],tup[0]))
                value = tup[2]
            for react in reacts:
                for tup in options:
                    if react.emoji == tup[0]:
                        count = react.count - 1 #Take one to counter bot reaction
                        output = tup[1]
                        outputs.append([output, count])
            for output in outputs:
                votes.append(output[1])
                total = total + output[1]
            for vote in votes:
                if vote > most_votes[0]:
                    most_votes = [vote, vi]
                vi = vi + 1 
            for output in outputs:
                winner = False
                if i == most_votes[1]:
                    winner = True
                if votes[i] > 0:
                    if votes[i] > 1:
                        s = "s"
                    else: 
                        s = ""
                    votestr = f" - {votes[i]} Vote{s} ({(votes[i] / total) * 100}%)\n"
                else:
                    votestr = " - No Votes\n"
                output[0] = output[0] + votestr
                if winner:
                    output[0] = "**" + output[0] + "**"
                fieldcont = fieldcont + output[0]
                i = i + 1

            style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
            emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

            if emoji is False:
                emoji = ""
            else:
                emoji = ":white_check_mark: "

            embed = fEmbeds.fancyEmbeds.makeEmbed(self, guild.id, embed.title, poll[1] + f"\nPoll Over!", useColor=1)
            embed = embed.add_field(name=f"**Results (Total Votes - {total})**", value=fieldcont)
            await msg.edit(embed=embed)
            cursor = await self.connection.execute("DELETE FROM active_polls WHERE id = ?", (poll[0],))
            await self.connection.commit()
            await cursor.close()

            successembed = fEmbeds.fancyEmbeds.makeEmbed(self, guild.id, f"{emoji}Successfully ended poll.", useColor=3)
            await ctx.send(embed=successembed)

    @poll.command(brief=":wastebasket: ", name="delete")
    async def poll_delete(self, ctx, id):
        """
        Delete an active poll in its entirety with the given ID.
        This does NOT calculate the poll results.
        Note that ids are given in the form `channelid/messageid` not JUST the message id.
        """
        id = id.partition("/")
        if id[1] != "/":
            await ctx.send("That is not a valid poll id!")
        channel_id = id[0]
        id = id[2]
        
        for channel in ctx.guild.text_channels:
            if str(channel.id) == str(channel_id):
                msg = await channel.fetch_message(id)
                break
            
        try:
            test = msg.content
        except UnboundLocalError:
            await ctx.send("That is not a valid poll id!")
            return

        cursor = await self.connection.execute(f"SELECT id, description FROM active_polls WHERE id = ?", (id,))
        try:
            polls = await cursor.fetchall()
            await cursor.close()
        except AttributeError:
            await ctx.send("That is not an active poll!")
            await cursor.close()
            return
        try:
            test = polls[0]
        except IndexError:
            await ctx.send("That is not an active poll!") 
            return

        style = fEmbeds.fancyEmbeds.getActiveStyle(self, ctx.guild.id)
        emoji = fEmbeds.fancyEmbeds.getStyleValue(self, ctx.guild.id, style, "emoji")

        if emoji is False:
            emojis = ["", ""]
        else:
            emojis = [":white_check_mark: ", ":x: "]

        try:
            await msg.delete()
            confirmembed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, f"{emojis[0]}Successfully deleted poll.", useColor=2)
            await ctx.send(embed=confirmembed)
            cursor = await self.connection.execute("DELETE FROM active_polls WHERE id = ?", (id,))
            await self.connection.commit()
            await cursor.close()
        except discord.errors.Forbidden:
            failembed = fEmbeds.fancyEmbeds.makeEmbed(self, ctx.guild.id, f"{emojis[1]}Failed to delete poll.", force=True, forceColor=0xFF0000)
            await ctx.send(embed=failembed)

    @tasks.loop(seconds=10.0)
    async def poll_check(self):
        #Checks the list of active polls to see if any have ended.
        #what the actual fuck did i do here (seriously this seems too messy to work but it does??)
        cursor = await self.connection.execute(f"SELECT id, guildid, channelid, expires, description FROM active_polls WHERE expires < {int(time.time())}")
        try:
            polls = await cursor.fetchall()
            await cursor.close()
        except AttributeError:
            await cursor.close()
            return
        for poll in polls:
            guild = self.bot.get_guild(poll[1])
            outputs = []
            options = []
            fieldcont = ""
            output = ""
            votes = []
            most_votes = [0, 0]
            nums = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
            total = 0
            i = 0
            vi = 0
            for channel in guild.text_channels:
                if channel.id == poll[2]:
                    msg = await channel.fetch_message(poll[0])
                    reacts = msg.reactions
                    embed = msg.embeds[0]
                    field = embed.fields[0]
                    value = field.value
                    option_count = value.count("\n")
                    for n in range(0, option_count + 1):
                        tup = value.partition("\n")
                        options.append((nums[n],tup[0]))
                        value = tup[2]
                    for react in reacts:
                        for tup in options:
                            if react.emoji == tup[0]:
                                count = react.count - 1 #Take one to counter bot reaction
                                output = tup[1]
                                outputs.append([output, count])
                    for output in outputs:
                        votes.append(output[1])
                        total = total + output[1]
                    for vote in votes:
                        if vote > most_votes[0]:
                            most_votes = [vote, vi]
                        vi = vi + 1 
                    for output in outputs:
                        winner = False
                        if i == most_votes[1]:
                            winner = True
                        if votes[i] > 0:
                            if votes[i] > 1:
                                s = "s"
                            else: 
                                s = ""
                            votestr = f" - {votes[i]} Vote{s} ({(votes[i] / total) * 100}%)\n"
                        else:
                            votestr = " - No Votes\n"
                        output[0] = output[0] + votestr
                        if winner:
                            output[0] = "**" + output[0] + "**"
                        fieldcont = fieldcont + output[0]
                        i = i + 1
                    embed = fEmbeds.fancyEmbeds.makeEmbed(self, guild.id, embed.title, poll[4] + f"\nPoll Over!", useColor=1)
                    embed = embed.add_field(name=f"**Results (Total Votes - {total})**", value=fieldcont)
                    await msg.edit(embed=embed)
                    cursor = await self.connection.execute("DELETE FROM active_polls WHERE id = ?", (poll[0],))
                    await self.connection.commit()
                    await cursor.close()

    @poll_check.before_loop
    async def before_poll_check(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(Community(bot))
