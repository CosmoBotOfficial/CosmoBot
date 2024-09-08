import discord

from datetime import datetime

from discord.ext import commands
from discord import app_commands

from config import Config as cfg
from globals import mod_perms

db = cfg.DB.main_database

modlog_collection = db.modlog_collection

class Logs(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def mod_log(self, title, description, footer, color: discord.Color, ctx, author: discord.Member = None, attachment = None):
        modlog_channel = await modlog_collection.find_one({"guild_id": ctx.guild_id})
        if modlog_channel:
            embed = discord.Embed(
                title=f"{title}",
                description=f"{description}",
                color=color,
                timestamp=datetime.now()
            )

            embed.set_footer(text=footer)

            if author:

                embed.set_author(name=author.name, icon_url=author.avatar.url)

            if attachment != "NA":

                embed.set_image(url=attachment)

            await self.bot.get_channel(modlog_channel["channel_id"]).send(embed=embed)
    
    modlogs_group = app_commands.Group(name="modlogs", description="Moderation logs")
    
    @modlogs_group.command(name="set", description="Set the server's modlog")
    @app_commands.check(mod_perms)
    async def set_modlog(self, ctx: discord.Interaction, channel: discord.TextChannel):
        current_channel = await modlog_collection.find_one({"guild_id": ctx.guild_id})
        if current_channel is None:
            document = {"channel_id": channel.id, "guild_id": ctx.guild_id}
            await modlog_collection.insert_one(document)
        else:
            await modlog_collection.update_one({"guild_id": ctx.guild_id}, {"$set": {"channel_id": channel.id}})
        
        embed = discord.Embed(
            title="Success",
            description=f"Set mod log channel to {channel.mention}.",
            color=discord.Color.green()
        )
        await ctx.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Logs(bot))