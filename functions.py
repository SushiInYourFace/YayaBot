import sqlite3

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