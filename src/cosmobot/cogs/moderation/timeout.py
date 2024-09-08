import discord
import typing

from discord import app_commands
from discord.ext import commands

from config import Config as cfg
from globals import incomplete_message, timestamp, mod_perms
from src.cosmobot.cogs.moderation.mod_logs import Logs
from src.cosmobot.cogs.dev.extensions import PaginationEmbed

from datetime import datetime, timedelta
from humanfriendly import parse_timespan
from math import ceil
from random import randint

db = cfg.DB.main_database

timeout_collection = db.timeout_collection


class Timeout(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    timeout_group = app_commands.Group(name="timeout", description="Timeout a member")
    
    @timeout_group.command(name="add", description="Timeout a member")
    @app_commands.check(mod_perms)
    async def timeout(self, ctx: discord.Interaction, member: discord.Member, reason: str, duration: str):
        time = 0
        try:
            time = timedelta(seconds=parse_timespan(duration))
        except:
            embed = discord.Embed(
                title="Error",
                description=f"`{duration}` is not a valid time. An example of a valid time is `43m`.",
                color=discord.Color.red()
            )
            await ctx.response.send_message(embed=embed)
            return
        
        await member.timeout(time, reason=reason)

        await Logs.mod_log(
            self=self,
            title="Timeout | Add",
            description=f"**{member.mention}** was timed out by {ctx.user.mention}.\nReason: `{reason}`",
            footer=f"User ID: {member.id}",
            color=discord.Color.green(),
            ctx=ctx,
            author=member
        )
        
        embed = discord.Embed(
            title="Timeout | Add",
            description=f"**{member.name}** has been timed out for `{time}`.\nReason: `{reason}`",
            color=discord.Color.green()
        )

        member_embed = discord.Embed(
            title="Timeout | Add",
            description=f"You were timed out in **{ctx.guild}** for `{time}`\nReason: `{reason}",
            color=discord.Colour.orange()
        )
        
        await member.send(embed=member_embed)

        document = {"duration": duration, "reason": reason, "member_id": member.id, "at": datetime.now(), "guild_id": ctx.guild_id, "ended_at": None}
        
        await ctx.response.send_message(embed=embed)

        await timeout_collection.insert_one(document)


    @timeout_group.command(name="remove", description="Remove a member's timeout")
    @app_commands.check(mod_perms)
    async def timeout_remove(self, ctx: discord.Interaction, member: discord.Member):
        if member.timed_out_until is None:
            embed = discord.Embed(
                title="Error",
                description=f"**{member.name}** is not timed out.",
                color=discord.Color.red()
            )
            
            await ctx.response.send_message(embed=embed)
        else:
            await member.timeout(None)
            
            embed = discord.Embed(
                title="Timeout | Remove",
                description=f"**{member.name}**'s timeout has been removed.",
                color=discord.Color.green()
            )
            
            await ctx.response.send_message(embed=embed)

            await Logs.mod_log(
                self=self,
                title="Timeout | Remove",
                description=f"**{member.name}**'s timeout has been removed.",
                footer=f"User ID: {member.id}",
                color=discord.Color.green(),
                ctx=ctx,
                author=member
            )
             
            cursor = timeout_collection.find({"member_id": member.id, "guild_id": ctx.guild_id}).sort("at", -1)
            timeout_ends_data = await cursor.to_list(length=None)
            timeout_ends_data = timeout_ends_data[0]
            await timeout_collection.find_one_and_update({"member_id": member.id, "guild_id": ctx.guild_id, "_id": timeout_ends_data["_id"]}, {"$set":{"ended_at": datetime.now()}})

    @timeout_group.command(name="list", description="View the server's past timeouts")
    @app_commands.check(mod_perms)
    async def view_timeouts(self, ctx: discord.Interaction):
        await ctx.response.defer(thinking=True)
        
        cursor = timeout_collection.find({"guild_id": ctx.guild_id}).sort("at", -1)
        past_timeouts = await cursor.to_list(length=None)
        
        if len(past_timeouts) == 0:
            embed = discord.Embed(
                title=f"Past Timeouts",
                description=f"This server has no past timeouts."
            )
            await ctx.followup.send(embed=embed)
        else:
            fields = []
            now = datetime.now()
            for i in past_timeouts:
                member = await ctx.guild.fetch_member(i["member_id"])
                fields.append({"name": member.name, "value": f'**Reason:** {i["reason"]}\n**At:** {timestamp(i["at"])} \n**Duration:** {i["duration"]}\n**Ends/Ended At (UTC):** {(timestamp(i["at"] + timedelta(seconds=parse_timespan(i["duration"])) if i["ended_at"] is None else i["ended_at"]))}\n**Active**: {(i["at"] + timedelta(seconds=parse_timespan(i["duration"]))) > now if i["ended_at"] is None else "False"}', "inline": False})
            pagination_view = PaginationEmbed(current_page=1, separtion=5)
            pagination_view.data = fields
            pagination_view.update_buttons()
            await pagination_view.send(ctx)
            
    @timeout_group.command(name="view", description="View a member's timeouts")
    @app_commands.check(mod_perms)
    async def member_timeouts(self, ctx: discord.Interaction, member: discord.Member):
        
        await ctx.response.defer(thinking=True)

        cursor = timeout_collection.find({"member_id": member.id, "guild_id": ctx.guild_id}).sort("at", -1)
        past_timeouts = await cursor.to_list(length=None)
        
        if len(past_timeouts) == 0:
            embed = discord.Embed(
                title=f"{member.name}'s Past Timeouts",
                description=f"{member.name} has no past timeouts."
            )
            await ctx.followup.send(embed=embed)
        else:
            fields = []
            now = datetime.now()
            
            for i in past_timeouts:
                fields.append({"name": member.name, "value": f'**Reason:** {i["reason"]}\n**At:** {timestamp(i["at"])} \n**Duration:** {i["duration"]}\n**Ends/Ended At (UTC):** {(timestamp(i["at"] + timedelta(seconds=parse_timespan(i["duration"])) if i["ended_at"] is None else i["ended_at"]))}\n**Active**: {(i["at"] + timedelta(seconds=parse_timespan(i["duration"]))) > now if i["ended_at"] is None else "False"}', "inline": False})
                
            pagination_view = PaginationEmbed(current_page=1, separtion=5)
            pagination_view.data = fields
            pagination_view.update_buttons()
            await pagination_view.send(ctx)
        
async def setup(bot):
    await bot.add_cog(Timeout(bot))