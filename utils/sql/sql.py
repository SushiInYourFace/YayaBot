import time

import aiosqlite
from discord.ext import commands

class sql:
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