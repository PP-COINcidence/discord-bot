import discord
from discord.ext import commands
import json
import random
import requests


config = {}
with open('config.json') as f:
    config = json.load(f)
description = '''A really ghetto Discord bot.'''
bot = commands.Bot(command_prefix='.', description=description)

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

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

@bot.command(description='Looks up an image from Emil\'s gallery and posts it.')
async def img(name : str):
    payload = {'q': name}
    r = requests.get(config['gallery_url'], params=payload).json()
    results = r['results']
    if results:
        await bot.say(results[0])
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
    mine = discord.PermissionOverwrite(manage_channels=True, manage_roles=True)
    try:
        await bot.create_channel(msg.server, name, (server.default_role, everyone), (msg.author, mine), type=channel_type_map[channel_type])
        await bot.say('Okay {0}, created the {1} channel named \"{2}\".'.format(msg.author, channel_type, name))
    except Exception as e:
        await bot.say('Couldn\'t create the channel: {0}'.format(e))


bot.run(config['token'])
