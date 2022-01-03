import re

class checks:
    """
    Includes different checks, for uses such as with the command decorator `@functions.check()`.
    """
    
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