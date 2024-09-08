import discord

from discord.ext import commands
from discord import app_commands

from config import Config as cfg
from src.cosmobot.cogs.moderation.mod_logs import Logs
from globals import timestamp, mod_perms, gen_unique
from src.cosmobot.cogs.dev.extensions import PaginationEmbed

from math import ceil
from datetime import datetime
from random import randint

db = cfg.DB.main_database

warn_collection = db.warn_collection


class Warn(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    warn_group = app_commands.Group(name="warn", description="Warn a member")
    
    @warn_group.command(name="add", description="Warn a member")
    @app_commands.check(mod_perms)
    async def add_warn(self, ctx: discord.Interaction, member: discord.Member, reason: str, attachment: discord.Attachment = None, private: bool = False, dm: bool = True):

        await ctx.response.defer(thinking=True)

        existing_warns = []

        async for i in warn_collection.find({"member_id": member.id, "guild_id": ctx.guild_id}):
            existing_warns.append(i)

        now = datetime.now()

        if attachment:
            attachment = attachment.url

        elif not attachment:
            attachment = "NA"

        case_id = await gen_unique(5)

        document = {"reason": reason, "member_id": member.id, "guild_id": ctx.guild_id, "at": now, "id": case_id, "attachment": attachment}

        await warn_collection.insert_one(document)

        embed = discord.Embed(
            description=f"**{member.name}** has been warned for `{reason}`. They now have `{len(existing_warns) + 1}` warn(s).",
            color=discord.Color.green()
        )

        if attachment != "NA":
            embed.set_image(url=attachment)
        
        await Logs.mod_log(
            self=self,
            title=f"ID: {case_id}",
            description=f"{member.mention} has been warned by {ctx.user.mention}, for the reason: `{reason}`",
            footer=f"User ID: {member.id} | Moderator ID: {ctx.user.id}",
            color=discord.Color.green(),
            ctx=ctx,
            author=member,
            attachment=attachment
        )
        if private:
            await ctx.followup.send(embed=embed, ephemeral=True)

            if dm:
                await member.send(embed=embed)

        else:
            await ctx.followup.send(embed=embed)

            if dm:
                await member.send(embed=embed)
    
    @warn_group.command(name="remove", description="Remove a member's warnings")
    @app_commands.check(mod_perms)
    async def remove_warn_number(self, ctx: discord.Interaction, member: discord.Member, id: str):

        existing_warns = []

        async for i in warn_collection.find({"member_id": member.id, "guild_id": ctx.guild_id}):
            existing_warns.append(i)

        if len(existing_warns) == 0:
            embed = discord.Embed(
                title="Error",
                description=f"{member.name} does not have any existing warnings.",
                color=discord.Color.red()
            )
            await ctx.response.send_message(embed=embed)

        async for i in warn_collection.find({"member_id": member.id, "guild_id": ctx.guild_id, "id": id}).sort("at", -1):
            await warn_collection.find_one_and_delete({"_id": i["_id"]})

        embed = discord.Embed(
            description=f"**{member.name}**'s warning with the id of `{id}` has been removed. They now have `{len(existing_warns) - 1}` warn(s).",
            color=discord.Color.green()
        )
        await Logs.mod_log(
            self=self,
            title=f"Remove | Warn",
            description=f"{member.mention}'s warning with the ID of `{id}` has been removed by {ctx.user.mention}.",
            footer=f"User ID: {member.id} | Moderator ID: {ctx.user.id}",
            color=discord.Color.red(),
            ctx=ctx,
            author=member
        )
        await ctx.response.send_message(embed=embed)
        
    @warn_group.command(name="wipe", description="Remove a certain amount of a member's warnings")
    @app_commands.check(mod_perms)
    async def remove_warn_number(self, ctx: discord.Interaction, member: discord.Member, amount: int):
        if amount > 25 or amount <= 0:
            embed = discord.Embed(
                title="Error",
                description="Invalid amount. Must be between `0` and `25`.",
                color=discord.Color.red()
            )
            await ctx.response.send_message(embed=embed)
        existing_warns = []
        async for i in warn_collection.find({"member_id": member.id, "guild_id": ctx.guild_id}):
            existing_warns.append(i)
        if len(existing_warns) == 0:
            embed = discord.Embed(
                title="Error",
                description=f"{member.name} does not have any existing warnings.",
                color=discord.Color.red()
            )
            await ctx.response.send_message(embed=embed)
        async for i in warn_collection.find({"member_id": member.id, "guild_id": ctx.guild_id}).sort("at", -1).limit(amount):
            await warn_collection.find_one_and_delete({"_id": i["_id"]})
        embed = discord.Embed(
            description=f"**{amount}** of **{member.name}**'s warnings has been removed. They now have `{len(existing_warns) - amount if len(existing_warns) - amount > 0 else 0}` warn(s).",
            color=discord.Color.green()
        )
        await Logs.mod_log(
            self=self,
            title=f"Wipe | Warns",
            description=f"**{amount}** warning(s) of {member.mention} were/was removed by {ctx.user.mention}.",
            footer=f"User ID: {member.id} | Moderator ID: {ctx.user.id}",
            color=discord.Color.red(),
            ctx=ctx,
            author=member
        )
        await ctx.response.send_message(embed=embed)
        
    @warn_group.command(name="view", description="View a member's past warnings")
    @app_commands.check(mod_perms)
    async def view_warns(self, ctx: discord.Interaction, member: discord.Member):
        await ctx.response.defer(thinking=True)
        cursor = warn_collection.find({"member_id": member.id, "guild_id": ctx.guild_id}).sort("at", -1)
        past_warns = await cursor.to_list(length=None)
            
        if len(past_warns) == 0:
            embed = discord.Embed(
                title=f"{member.name}'s Past Warnings",
                description=f"{member.name} has no past warnings."
            )
            await ctx.followup.send(embed=embed)
        else:
            fields = []
            member = ctx.user
            
            for i in past_warns:
                fields.append({"name": member.name, "value": f'**Reason:** {i["reason"]}\n**At:** {timestamp(i["at"])}\n**ID:** {i["id"]}\n**Attachment Url:** {i["attachment"]}', "inline": False})

            pagination_view = PaginationEmbed(current_page=1, separtion=5)
            pagination_view.data = fields
            pagination_view.update_buttons()

            await pagination_view.send(ctx)
    
    @warn_group.command(name="list", description="View the server's past warnings")
    @app_commands.check(mod_perms)
    async def warn_list(self, ctx: discord.Interaction):

        await ctx.response.defer(thinking=True)

        cursor = warn_collection.find({"guild_id": ctx.guild_id}).sort("at", -1)
        past_warns = await cursor.to_list(length=None)
        
        if len(past_warns) == 0:
            embed = discord.Embed(
                title=f"Past Warnings",
                description=f"This server has no past warnings."
            )
            await ctx.followup.send(embed=embed)
        else:
            fields = []
            for i in past_warns:
                member = await ctx.guild.fetch_member(i["member_id"])
                fields.append({"name": member.name, "value": f'**Reason:** {i["reason"]}\n**At:** {timestamp(i["at"])}\n**ID:** {i["id"]}', "inline": False})

            pagination_view = PaginationEmbed(current_page=1, separtion=5)
            pagination_view.data = fields
            pagination_view.update_buttons()
            await pagination_view.send(ctx)
        
async def setup(bot):
    await bot.add_cog(Warn(bot))