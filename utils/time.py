import datetime
from typing import Union

from discord.ext import commands

class timeconverters:
    def secondsconverter(self, value, startType):
        if startType == "s":
            return value
        elif startType == "m":
            return value * 60
        elif startType == "h":
            return value * 3600
        elif startType == "d":
            return value * 86400
        return None

    def fromseconds(self, seconds):
        if seconds >= 86400:
            days = seconds//86400
            return str(days) + (" Day" if days==1 else " Days")
        elif seconds >= 3600:
            hours = seconds//3600
            return str(hours) + (" Hour" if hours==1 else " Hours")
        elif seconds >= 60:
            minutes = seconds//60
            return str(minutes) + (" Minute" if minutes==1 else " Minutes")
        else:
            return str(seconds) + (" Second" if seconds==1 else " Seconds")

class InSeconds(commands.Converter):
    async def convert(self,ctx,argument):
        try:
            int(str(argument)[-1])
        except: # The last character cannot be an int so convert
            try:
                argument = timeconverters().secondsconverter(int(str(argument[:-1])),str(argument)[-1])
            except ValueError:
                raise commands.BadArgument("That isn't a timeframe!\nExamples of valid timeframes: `20s`, `1h`")
            if argument is None:
                raise commands.BadArgument(f"I couldn't understand the units.\nSupported units are: `s`, `m`, `h`, `d`\nExamples: `20s`, `1h`")
            return argument
        else: # The last character can be int so we assume it's in seconds
            try:
                return int(argument)
            except ValueError:
                raise commands.BadArgument("That isn't a timeframe!\nExamples of valid timeframes: `20s`, `1h`")

class DiscordTimestamp():
    """
    A class useful for creating timestamps for display in discord.
    Timestamp can be a UNIX timestamp, datetime or timedelta.
    Relative means time is added to current time.
    """
    def __init__(self,timestamp: Union[datetime.datetime,datetime.timedelta,int], relative: bool=False):
        if isinstance(timestamp,datetime.datetime):
            timestamp = timestamp.timestamp()
        elif isinstance(timestamp,datetime.timedelta) and not relative:
            timestamp = timestamp.total_seconds()
        if relative:
            if isinstance(timestamp,int):
                timestamp = (datetime.datetime.now() + datetime.timedelta(seconds=timestamp)).timestamp()
            else:
                timestamp = (datetime.datetime.now() + timestamp).timestamp()
        self.timestamp = int(timestamp)

    def _to_discord(self,t: str):
        return f"<t:{str(self.timestamp)}:{t}>"

    @property
    def date(self):
        """A date displayed in Discord, `10/07/2021` or `07/10/2021`."""
        return self._to_discord("d")

    @property
    def date_full(self):
        """A date displayed in readable format in Discord, `10 July 2021` or `July 10, 2021`."""
        return self._to_discord("D")

    @property
    def time(self):
        """A time displayed in Discord, `18:21` or `6:21 PM`."""
        return self._to_discord("t")

    @property
    def time_full(self):
        """A time displayed with seconds in Discord, `18:21:21` or `6:21:21 PM`."""
        return self._to_discord("T")

    @property
    def date_time(self):
        """A time displayed with date and time in Discord, `10 July 2021 18:21` or `July 10, 2021 6:21 PM`."""
        return self._to_discord("f")

    @property
    def date_time_full(self):
        """A time displayed with date, time and weekday in Discord, `Saturday, 10 July 2021 18:21` or `Saturday, July 10, 2021 6:21 PM`."""
        return self._to_discord("F")

    @property
    def relative(self):
        """A time displayed as relative in Discord, `10 minutes ago` if before current time or `in 10 minutes` if in the future."""
        return self._to_discord("R")