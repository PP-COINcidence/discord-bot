import discord
import datetime
from discord.ext import commands
from enum import Enum
import json
import logging
import random
import requests


logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

config = {}
with open('config.json') as f:
    config = json.load(f)
description = '''A really ghetto Discord bot.'''
bot = commands.Bot(command_prefix='.', description=description)


class UptimeStatus(Enum):
    Online = 1
    Offline = 2


class UptimeMap(object):
    def __init__(self):
        self.internal_map = {}

    def reset_user(self, mid, time=None):
        self.internal_map[mid] = (UptimeStatus.Online, time)

    def logout_user(self, mid, time):
        self.internal_map[mid] = (UptimeStatus.Offline, time)

    def remove_user(self, mid):
        self.internal_map.pop(mid, None)

    def get_users_uptime(self, mid):
        return self.internal_map.get(mid, (None, None))


uptime_map = UptimeMap()

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')
    if not hasattr(bot, 'uptime'):
        bot.uptime = datetime.datetime.utcnow()
    for server in bot.servers:
        for member in server.members:
            if member.status != discord.Status.offline:
                uptime_map.reset_user(member.id, None)

@bot.event
async def on_member_update(before, after):
    if before.status == discord.Status.offline and after.status != discord.Status.offline:
        # "Log" user in
        uptime_map.reset_user(after.id, datetime.datetime.utcnow())
    elif before.status != discord.Status.offline and after.status == discord.Status.offline:
        # "Log out" the user
        uptime_map.logout_user(after.id, datetime.datetime.utcnow())

@bot.event
async def on_member_join(member):
    uptime_map.reset_user(member.id, None)

@bot.event
async def on_member_remove(member):
    uptime_map.remove_user(member.id)

def get_bot_uptime():
    return get_human_readable_uptime_diff(bot.uptime)

def get_human_readable_user_uptime(name, mid):
    status, time = uptime_map.get_users_uptime(mid)
    if not status:
        return "I haven't seen {0} since I've been brought online.".format(name)
    status_str = 'online' if status == UptimeStatus.Online else 'offline'
    if not time:
        return "{0} has been {1} for as long as I have -- I don't know the exact details.".format(name, status_str)
    return "{0} has been {1} for {2}.".format(name, status_str, get_human_readable_uptime_diff(time))

def get_human_readable_uptime_diff(start_time):
    now = datetime.datetime.utcnow()
    delta = now - start_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)
    if days:
        fmt = '{d} days, {h} hours, {m} minutes, and {s} seconds'
    else:
        fmt = '{h} hours, {m} minutes, and {s} seconds'
    return fmt.format(d=days, h=hours, m=minutes, s=seconds)

@bot.command()
async def uptime():
    await bot.say('Uptime: **{}**'.format(get_bot_uptime()))

@bot.command()
async def add(left : int, right : int):
    """Adds two numbers together."""
    await bot.say(left + right)

@bot.command()
async def roll(dice : str):
    """Rolls a dice in NdN format."""
    try:
        rolls, limit = map(int, dice.split('d'))
    except Exception:
        await bot.say('Format has to be in NdN!')
        return

    result = ', '.join(str(random.randint(1, limit)) for r in range(rolls))
    await bot.say(result)

@bot.command(pass_context=True)
async def disconnect(ctx):
    perms = ctx.message.author.permissions_in(ctx.message.channel)
    if perms.administrator:
        await bot.say(random.choice(config['disconnect_msgs']))
        await bot.logout()
    else:
        await bot.say("You can't tell me what to do! (Administrator access is required)")

@bot.command()
async def choose(*choices : str):
    """Chooses between multiple choices."""
    await bot.say(random.choice(choices))

@bot.command(pass_context=True, description='Looks up an image from Emil\'s gallery and posts it.')
async def img(ctx, name : str):
    payload = {'q': name}
    r = requests.get(config['gallery_url'], params=payload).json()
    results = r['results']
    if results:
        author = ctx.message.author
        author_avatar_url = author.avatar_url or author.default_avatar_url
        em = discord.Embed(title=name, color=0xFFFFFF)
        em.set_author(name=author.name, icon_url=author_avatar_url)
        em.set_image(url=results[0])
        await bot.say(embed=em)
        await bot.delete_message(ctx.message)
    else:
        await bot.say('No image could be matched.', delete_after=3)

@bot.command(pass_context=True, description='Creates a new voice or text channel.')
async def create(ctx, channel_type, name):
    msg = ctx.message
    server = msg.server
    channel_type_map = {
        'text': discord.ChannelType.text,
        'voice': discord.ChannelType.voice
    }
    if channel_type not in channel_type_map:
        await bot.say('The channel type must be \"text\" or \"voice\".', delete_after=3)
        return
    everyone = discord.PermissionOverwrite()
    mine = discord.PermissionOverwrite(manage_channels=True, manage_roles=True, move_members=True)
    try:
        await bot.create_channel(msg.server, name, (server.default_role, everyone), (msg.author, mine), type=channel_type_map[channel_type])
        await bot.say('Okay {0}, created the {1} channel named \"{2}\".'.format(msg.author, channel_type, name))
    except Exception as e:
        await bot.say('Couldn\'t create the channel: {0}'.format(e))

@bot.command(pass_context=True, description='Tells you long a user has been offline or online.')
async def user_uptime(ctx, name : str):
    # convert name to mid if possible
    if ctx.message.server:
        # Not a PM
        user = ctx.message.server.get_member_named(name)
    else:
        # person pm'd the bot, so search all our servers
        user = None
        for server in bot.servers:
            user = server.get_member_named(name)
            if user:
                break
    if not user:
        await bot.say('Sorry, I couldn\'t find a user named \'{0}\'.'.format(name))
    else:
        await bot.say(get_human_readable_user_uptime(name, user.id))

bot.run(config['token'])
