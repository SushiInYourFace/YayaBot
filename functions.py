import sqlite3
import time

con = sqlite3.connect("database.db")
cursor = con.cursor()

def has_modrole(ctx):
    modrole = cursor.execute("SELECT moderator FROM role_ids WHERE guild = ?", (ctx.guild.id,)).fetchone()
    member_roles = []
    for role in ctx.author.roles:
        member_roles.append(role.id)
    if modrole is None:
        return False
    elif (modrole[0] in member_roles):
        return True
    else:
        return False


class Sql:
    def newest_case(self):
        caseNumber = cursor.execute("SELECT id FROM caselog ORDER BY id DESC LIMIT 1").fetchone()
        if caseNumber == None:
            caseNumber = 0
        else:
            caseNumber = caseNumber[0]
        caseNumber += 1
        return(caseNumber)

    def new_case(self, user, guild, casetype, reason, started, expires, mod):
        caseID = self.newest_case()
        if expires != -1:
            #checks if user already has an active case of the same type, and removes it if it is less severe
            unexpired_cases = cursor.execute("SELECT id FROM caselog WHERE guild=? AND user=? AND type=? AND expires >=? AND expires <=? ", (guild,user, casetype, time.time(), expires)).fetchall()
            #should only ever be <=1 case that meets these criteria, but better safe than sorry
            if unexpired_cases is not None:    
                for case in unexpired_cases:
                    cursor.execute("DELETE FROM active_cases WHERE id = ?", (case[0],))
            cursor.execute("INSERT INTO active_cases(id, expiration) VALUES(?,?)", (caseID, expires))
        cursor.execute("INSERT INTO caselog(id, guild, user, type, reason, started, expires, moderator) VALUES(?,?,?,?,?,?,?,?)", (caseID, guild, user, casetype, reason, started, expires, mod))
        con.commit()

    def get_role(self, guild, role):
        if role == "gravel":
            roleid = cursor.execute("SELECT gravel FROM role_ids WHERE guild = ?", (guild,)).fetchone()
        elif role == "muted":
            roleid = cursor.execute("SELECT muted FROM role_ids WHERE guild = ?", (guild,)).fetchone()
        return roleid[0]

class timeconverters:
    def secondsconverter(self, value, startType):
        if startType == "s":
            #time already in seconds
            pass
        elif startType == "m":
            value *= 60
        elif startType == "h":
            value *= 3600
        elif startType == "d":
            value *= 86400
        return value
    def fromseconds(self, seconds):
        if seconds >= 86400:
            days = seconds//86400
            return str(days) + " Days"
        elif seconds >= 3600:
            hours = seconds//3600
            return str(hours) + " Hours"
        elif seconds >= 60:
            minutes = seconds//60
            return str(minutes) + " Minutes"
        else:
            return str(seconds) + " Seconds"