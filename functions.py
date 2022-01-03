import datetime
import gzip
import os
import re
import shutil
import time
from collections import namedtuple
from typing import Union
import sqlite3

import aiosqlite
from discord.ext import commands


async def close_bot(bot):
    #Shuts down the bot completely, closing the database connection in the process
    await bot.connection.close()
    await bot.close()

#adds a guild's up-to-date regexes to the bot
def update_filter(bot, guild_filter):
    filter_tuple = namedtuple("filter_tuple", ["enabled", "wildcard", "exact"])
    enabled = True if guild_filter[1] == 1 else False
    #getting lists
    bannedWilds = guild_filter[2].split(";")
    bannedExacts = guild_filter[3].split(";")
    if "" in bannedWilds:
        bannedWilds.remove("")
    if "" in bannedExacts:
        bannedExacts.remove("")
    #creating regexes
    if bannedWilds:
        wilds_pattern = "|".join(bannedWilds)
        wilds_re = re.compile(wilds_pattern)
    else:
        wilds_re = None
    if bannedExacts:
        exacts_pattern = "|".join(bannedExacts)
        exacts_re = re.compile(r"\b(?:%s)\b" % exacts_pattern)
    else:
        exacts_re = None
    guild_tuple = filter_tuple(enabled=enabled, wildcard=wilds_re, exact=exacts_re)
    bot.guild_filters[guild_filter[0]] = guild_tuple