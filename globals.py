import discord
import random

from datetime import datetime, timedelta
from time import mktime

from config import Config as cfg

db = cfg.DB.main_database

unique_collection = db.unique_collection

async def incomplete_message(ctx: discord.Interaction):
    embed = discord.Embed(
        title="Incomplete Command",
        description="This command is undergoing development.",
        color=discord.Color.red()
    )
    embed.set_footer(text="Use /help to see a list of commands")
    await ctx.response.send_message(embed=embed)


async def developer_only(ctx: discord.Interaction, command: str):
    embed = discord.Embed(
        title="Developer Commmand",
        description="The "f"{command}"" command is reserved for usage by CosmoBot developers only.",
        color=discord.Color.red()
    )
    embed.set_footer(text="Use /help to see a list of commands")
    await ctx.message.reply(embed=embed)

async def mod_perms(ctx: discord.Interaction): 
    return ctx.user.guild_permissions.moderate_members


def timestamp(time: datetime):
    return f"<t:{int(mktime((time).timetuple()))}:F>"

async def no_permission(ctx: discord.Interaction, command: str):
    embed = discord.Embed(
        title="No Permissions",
        description="You do not have the required permissions to use the "f"{command}"" command.",
        color=discord.Color.red()
    )
    embed.set_footer(text="Use /help to see a list of commands")
    await ctx.response.send_message(embed=embed)

async def gen_unique(length: int):

    while True:
        random_number = ''.join(random.choices('0123456789abcdefghijklmnopqrstuv', k=length))

        search = await unique_collection.find_one({"friend_code": random_number})

        if not search:
            await unique_collection.insert_one({"unique_id": random_number})
            return random_number