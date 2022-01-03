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


def has_modrole(ctx, bot=None):
    if not bot:
        modrole = ctx.bot.modrole.get(ctx.guild.id)
        trialrole = ctx.bot.modrole.get(ctx.guild.id)
    else:
        modrole = bot.modrole.get(ctx.guild.id)
        trialrole = bot.trialrole.get(ctx.guild.id)
    member_roles = [role.id for role in ctx.author.roles]
    if modrole is None and trialrole is None:
        return False
    elif modrole in member_roles or trialrole in member_roles:
        return True
    else:
        return False

#For when you can't use context
def has_modrole_no_ctx(member, bot):
    modrole = bot.modrole.get(member.guild.id)
    member_roles = [role.id for role in member.roles]
    if modrole is None:
        return False
    elif modrole in member_roles:
        return True
    else:
        return False

def has_adminrole(ctx, bot=None):
    if not bot:
        adminrole = ctx.bot.adminrole.get(ctx.guild.id)
    else:
        adminrole = bot.adminrole.get(ctx.guild.id)
    member_roles = [role.id for role in ctx.author.roles]
    if adminrole is None:
        return False
    elif adminrole in member_roles:
        return True
    else:
        return False

#For when you can't use context
def has_adminrole_no_ctx(member, bot):
    adminrole = bot.adminrole.get(member.guild.id)
    member_roles = [role.id for role in member.roles]
    if adminrole is None:
        return False
    elif adminrole in member_roles:
        return True
    else:
        return False

def filter_check(bot, message, guildID: int):
    #returns a boolean depending on whether a message should be filtered according to the rules of a guild
    should_filter = False
    try:
        guild_filter = bot.guild_filters[guildID]
    except KeyError:
        print("The bot tried to reference filters for a guild it does not have stored in memory. Please contact SushiInYourFace if this problem persists")
        return False
    formatted_content = re.sub(r"[^\w ]|_", "", message).lower()
    spaceless_content = re.sub(r"[^\w]|_", "", message)
    if guild_filter.wildcard:
        if guild_filter.wildcard.search(spaceless_content):
            should_filter = True
    if guild_filter.exact:
        if guild_filter.exact.search(formatted_content):
            should_filter = True
    return should_filter

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

async def make_backup(connection, kept_backups):
    """Creates a backup file of the current SQL database"""
    backup = sqlite3.connect("resources/backups/tempbackupfile.db")
    with backup:
        await connection.backup(backup, pages=1) #actual backup happens here
    backup.close()
    timestamp = datetime.datetime.now().strftime('%m_%d_%Y-%H_%M_%S')
    fname = f'resources/backups/{timestamp}.db.gz'
    with gzip.open(fname, 'wb') as f_out:
        with open("resources/backups/tempbackupfile.db", "rb") as f_in:
            shutil.copyfileobj(f_in, f_out)
    os.remove("resources/backups/tempbackupfile.db")
    if kept_backups != 0:
        #list of all files except gitkeep, sorted chronologically
        files = sorted([f for f in os.listdir('resources/backups') if os.path.isfile(os.path.join('resources/backups',f)) and f != ".gitkeep"])
        while len(files) > kept_backups:
            oldest_file = files[0]
            os.remove(f"resources/backups/{oldest_file}")
            files = sorted([f for f in os.listdir('resources/backups') if os.path.isfile(os.path.join('resources/backups',f)) and f != ".gitkeep"])


class Sql:
    def __init__(self, bot):
        self.bot = bot
        self.connection: aiosqlite.Connection = self.bot.connection
    async def newest_case(self):
        caseNumber = None
        async with self.connection.execute("SELECT id FROM caselog ORDER BY id DESC LIMIT 1") as cursor:
            caseNumber = await cursor.fetchone()
        if caseNumber is None:
            caseNumber = 0
        else:
            caseNumber = caseNumber[0]
        caseNumber += 1
        return caseNumber

    async def newest_guild_case(self, guild):
        async with self.connection.execute("SELECT id_in_guild FROM caselog WHERE guild = ? ORDER BY id DESC LIMIT 1", (guild,)) as cursor:
            guildCaseNumber = await cursor.fetchone()
            if guildCaseNumber is None:
                guildCaseNumber = 0
            else:
                guildCaseNumber = guildCaseNumber[0]
            guildCaseNumber += 1
            return guildCaseNumber


    async def new_case(self, user, guild, casetype, reason, started, expires, mod):
        caseID = await self.newest_case()
        id_in_guild = await self.newest_guild_case(guild)
        cursor = await self.connection.cursor()
        if expires != -1:
            #checks if user already has an active case of the same type, and removes it if it is less severe
            unexpired_cases = await cursor.execute("SELECT id FROM caselog WHERE guild=? AND user=? AND type=? AND expires >=? AND expires <=? ", (guild,user, casetype, time.time(), expires))
            #should only ever be <=1 case that meets these criteria, but better safe than sorry
            if unexpired_cases is not None:
                unexpired_cases = await unexpired_cases.fetchall()
                for case in unexpired_cases:
                    await cursor.execute("DELETE FROM active_cases WHERE id = ?", (case[0],))
            await cursor.execute("INSERT INTO active_cases(id, expiration) VALUES(?,?)", (caseID, expires))
        await cursor.execute("INSERT INTO caselog(id, id_in_guild, guild, user, type, reason, started, expires, moderator) VALUES(?,?,?,?,?,?,?,?,?)", (caseID, id_in_guild, guild, user, casetype, reason, started, expires, mod))
        await self.connection.commit()
        await cursor.close()

    async def get_role(self, guild, role):
        if role == "gravel":
            cursor = await self.connection.execute("SELECT gravel FROM role_ids WHERE guild = ?", (guild,))
        elif role == "muted":
            cursor = await self.connection.execute("SELECT muted FROM role_ids WHERE guild = ?", (guild,))
        roleid = await cursor.fetchone()
        await cursor.close()
        return roleid[0]

    async def namefilter_enabled(self, guild):
        #checks if filter is enabled
        cursor = await self.connection.cursor()
        filter_status = await cursor.execute("SELECT enabled FROM name_filtering WHERE guild = ?",(guild,))
        try:
            filter_status = await filter_status.fetchone()
        except AttributeError:
            return
        if filter_status is not None:
            await cursor.close()
            return bool(filter_status[0]) #casts the 0 or 1 stored to a boolean
        else:
            #guild hasn't set up name filtering, create a row in the table for them and disable the filter
            await cursor.execute("INSERT INTO name_filtering(guild, enabled) VALUES(?,?)",(guild, 0))
            await self.connection.commit()
            await cursor.close()
            return False

    async def get_new_nick(self, guild, flagged_nametype):
        #returns a replacement nickname when when the bot flags one as needing to be changed
        async with self.connection.execute("SELECT * FROM custom_names WHERE guild=?",(guild,)) as cursor:
            server_nicks = await cursor.fetchone()
            no_table = False
            if server_nicks is None:
                no_table = True
                #Server does not have a table for custom nicknames yet
                await cursor.execute("INSERT INTO custom_names(guild, nickname, username) VALUES(?,?,?)",(guild, "I had a bad nickname", "I had a bad username"))
                self.connection.commit()
            if flagged_nametype == "nickname":
                return server_nicks[1] if not no_table else "I had a bad nickname"
            elif flagged_nametype == "username":
                return server_nicks[2] if not no_table else "I had a bad username"
            else:
                return "I had a bad name"