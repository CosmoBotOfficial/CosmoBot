import os
import sys
import asyncio
import discord
from discord.ext import commands
from config import Config as cfg
from dotenv import load_dotenv
from src.cosmobot.setup.output import Styles as style
from src.cosmobot.setup.output import StandardColors as color

c = color
s = style

load_dotenv()

bot = commands.Bot(command_prefix=".", intents=discord.Intents.all())

status_dict = {
    1: discord.Status.online,
    2: discord.Status.idle,
    3: discord.Status.dnd
}
status = status_dict.get(1, discord.Status.online)

cog_list = {
    "dev": ["development", "logging", "remote", "embeds"],
    "moderation": ["kick", "ai", "mod_logs", "warn", "ban", "timeout", "userinfo", "modpanel"],
    "utility": ["ping", "vote", "afk", "levelling", "execute"],
    "games": ["roll"]
}

@bot.event
async def on_ready():
    text = f"""
    {bot.user} is ready! 
    CosmoBot v{cfg.VERSION} 
    Using Discord.py {discord.__version__} on Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}
    Running on {sys.platform.title()}, {sys.path[0]}
    Ping: {round(bot.latency * 1000)}ms
    Copyright © CosmoBot 2024. All rights reserved.
    """

    print(f'{text}')

    print(f"{c.FG_MAGENTA}Attending {str(len(bot.guilds))} Guilds:\n")
    for g in bot.guilds:
        print(f"{c.FG_BLUE}{g.id} = {g.name}")
    print(f"\n\n{c.FG_MAGENTA}Cogs:")

    developer_mode = os.getenv('DEVELOPER_MODE', 'false').lower() == 'true'

    await load_cog_list(cog_list)

    print(f'\n\n{c.FG_YELLOW}{"":_^80}\n\n\n{c.RESET}')

    activity = os.getenv('ACTIVITY')
    await bot.change_presence(status=status, activity=discord.Activity(type=discord.ActivityType.watching, name=activity))

async def load_cog_list(cog_list):
    for category, cog_names in cog_list.items():
        print(f"\n{c.FG_MAGENTA}Loading cogs in category '{category}'...{c.RESET}")
        for cog_name in cog_names:
            try:
                await bot.load_extension(f"src.cosmobot.cogs.{category}.{cog_name}")
                print(f"{c.FG_GREEN}+ Loaded {cog_name}{c.RESET}")
            except Exception as e:
                print(f"{c.FG_RED}- Failed to load {cog_name}: {e}{c.RESET}")

token = os.getenv("DISCORD_BOT_TOKEN")

if token is None:
    print(f"{color.FG_RED}ERROR: The TOKEN environment variable is not set! Exiting...{color.RESET}")
else:
    bot.run(token)
