import discord

from discord.ext import commands
from discord.ui import TextInput
from discord import app_commands

from src.cosmobot.cogs.moderation.userinfo import UserInfo
from src.cosmobot.cogs.moderation.mod_logs import Logs
from config import Config as cfg
from globals import mod_perms

from typing import Optional
from datetime import datetime
from random import randint
from datetime import datetime, timedelta
from humanfriendly import parse_timespan


db = cfg.DB.main_database

timeout_collection = db.timeout_collection
modlog_collection = db.modlog_collection
warn_collection = db.warn_collection

class UserInfoLookupModal(discord.ui.Modal):

    def __init__(self, bot: discord.Client):
        self.bot = bot
        super().__init__(title="User Info Lookup", timeout=None)

    user = TextInput(
        label="User's username / id",
        style=discord.TextStyle.short,
        placeholder="@rabbit29 / 349005764247158785",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        r_user = None

        if self.user.value.startswith("@"):
            
            r_user = interaction.guild.get_member_named(self.user.value[1:])

        elif self.user.value.isdigit():

            r_user = await self.bot.fetch_user(int(self.user.value))
            
        else:

            await interaction.response.send_message("Invalid user - it has to either be a user's ID or a user's mention")
            return
            
        await UserInfo.user_info(self, interaction, r_user)
        
class WarnModal(discord.ui.Modal):

    def __init__(self, bot: discord.Client):
        self.bot = bot
        super().__init__(title="Warn Member", timeout=None)

    async def mod_log(self, title, description, footer, color: discord.Color, ctx, author: discord.Member = None, attachment = None):
        modlog_channel = await modlog_collection.find_one({"guild_id": ctx.guild_id})
        if modlog_channel:
            embed = discord.Embed(
                title=f"{title}",
                description=f"{description}",
                color=color,
                timestamp=datetime.utcnow()
            )

            embed.set_footer(text=footer)

            if author:

                embed.set_author(name=author.name, icon_url=author.avatar.url)

            if attachment != "NA":

                embed.set_image(url=attachment)

            await self.bot.get_channel(modlog_channel["channel_id"]).send(embed=embed)

    user = TextInput(
        label="User's username / id",
        style=discord.TextStyle.short,
        placeholder="@rabbit29 / 349005764247158785",
        required=True
    )
    
    reason = TextInput(
        label="Reason for warning",
        style=discord.TextStyle.short,
        placeholder="Harrasment (If you want to upload proof, use the /warn add command)",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):

        r_user = None

        if self.user.value.startswith("@"):
            
            r_user = interaction.guild.get_member_named(self.user.value[1:])

        elif self.user.value.isdigit():

            r_user = await self.bot.fetch_user(int(self.user.value))
            
        else:

            await interaction.response.send_message("Invalid user - it has to either be a user's ID or a user's mention")
            return

        document = {"reason": self.reason.value, "member_id": r_user.id, "guild_id": interaction.guild_id, "at": datetime.utcnow(), "id": str(randint(10001, 99999)), "attachment": "N/A"}

        await warn_collection.insert_one(document)

        existing_warns = []

        async for i in warn_collection.find({"member_id": r_user.id, "guild_id": interaction.guild_id}):
            existing_warns.append(i)

        embed = discord.Embed(
            title="Warned",
            description=f"{r_user.mention} has been warned for `{self.reason.value}`. They now have `{len(existing_warns) + 1}` warn(s).",
            color=discord.Color.green()
        )

        await self.mod_log(
            title=f"Warned",
            description=f"{r_user.mention} has been warned by {interaction.user.mention}, for the reason: `{self.reason.value}`",
            footer=f"User ID: {r_user.id} | Moderator ID: {interaction.user.id}",
            color=discord.Color.green(),
            ctx=interaction,
            author=r_user
        )

        await interaction.response.send_message(embed=embed)

class KickModal(discord.ui.Modal):

    def __init__(self, bot: discord.Client):
        self.bot = bot
        super().__init__(title="Kick Member", timeout=None)

    user = TextInput(
        label="User's username / id",
        style=discord.TextStyle.short,
        placeholder="@rabbit29 / 349005764247158785",
        required=True
    )
    
    reason = TextInput(
        label="Reason for kick",
        style=discord.TextStyle.short,
        placeholder="Spam",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):

        if self.user.value.startswith("@"):
            
            r_user = interaction.guild.get_member_named(self.user.value[1:])
            
        await interaction.response.send_message(f"User: {r_user}\nReason: {self.reason.value}")

class BanModal(discord.ui.Modal):

    def __init__(self, bot: discord.Client):
        self.bot = bot
        super().__init__(title="Ban Member", timeout=None)

    user = TextInput(
        label="User's username / id",
        style=discord.TextStyle.short,
        placeholder="@rabbit29 / 349005764247158785",
        required=True
    )

    reason = TextInput(
        label="Reason for ban",
        style=discord.TextStyle.short,
        placeholder="Spam",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):

        r_user = None

        if self.user.value.startswith("@"):
            
            r_user = interaction.guild.get_member_named(self.user.value[1:])

        elif self.user.value.isdigit():

            r_user = await self.bot.fetch_user(int(self.user.value))
            
        else:

            await interaction.response.send_message("Invalid user - it has to either be a user's ID or a user's mention")
            return

        if self.reason.value == None:
            
            self.reason.value = "No reason specifined"

        await r_user.ban(reason=self.reason.value) 

        await interaction.response.send_message(f"Banned!\nUser: {r_user.mention}\nReason: {self.reason.value}")


class TimeoutModal(discord.ui.Modal):

    def __init__(self, bot: discord.Client):
        self.bot = bot
        super().__init__(title="Time member out", timeout=None)

    user = TextInput(
        label="User's username / id",
        style=discord.TextStyle.short,
        placeholder="@rabbit29 / 349005764247158785",
        required=True
    )
    
    duration = TextInput(
        label="Duration",
        style=discord.TextStyle.short,
        placeholder="10m, 1d",
        required=True
    )

    reason = TextInput(
        label="Reason",
        style=discord.TextStyle.short,
        placeholder="Spam",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):

        duration = self.duration.value

        r_user = None

        if self.user.value.startswith("@"):
            
            r_user = interaction.guild.get_member_named(self.user.value[1:])

        elif self.user.value.isdigit():

            r_user = await self.bot.fetch_user(int(self.user.value))
            
        else:

            await interaction.response.send_message("Invalid user - it has to either be a user's ID or a user's mention")
            return

        if self.reason.value == None:
            
            self.reason.value = "No reason specifined"

        time = 0

        try:

            time = timedelta(seconds=parse_timespan(duration))

        except:

            embed = discord.Embed(
                title="Error",
                description=f"`{duration}` is not a valid time. An example of a valid time is `43m`.",
                color=discord.Color.red()
            )

            await interaction.response.send_message(embed=embed)
            return
    

        await r_user.timeout(time, reason=self.reason.value)
        
        embed = discord.Embed(
            title="Timed Out",
            description=f"{r_user.mention} has been timed out for `{time}`.",
            color=discord.Color.green()
        )
        embed.set_footer(
            text=f"Reason: {self.reason.value}"
        )

        reason = self.reason.value
        
        document = {"duration": duration, "reason": reason, "member_id": r_user.id, "at": datetime.utcnow(), "guild_id": interaction.guild_id}
        
        await interaction.response.send_message(embed=embed)

        await timeout_collection.insert_one(document)

class PanelEmbed(discord.ui.View):

    def __init__(self, bot=discord.Client, timeout: float | None = 180):
        self.bot = bot
        super().__init__(timeout=timeout)

    @discord.ui.button(label="Ban", custom_id="Ban", style=discord.ButtonStyle.danger)
    async def ban_btn(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_modal(BanModal(self.bot))
    
    @discord.ui.button(label="Kick", custom_id="Kick", style=discord.ButtonStyle.danger)
    async def kick_btn(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_modal(KickModal(self.bot))

    @discord.ui.button(label="Timeout", custom_id="Timeout", style=discord.ButtonStyle.primary)
    async def timeout_btn(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_modal(TimeoutModal(self.bot))

    @discord.ui.button(label="Warn", custom_id="Warn", style=discord.ButtonStyle.primary)
    async def warn_btn(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_modal(WarnModal(self.bot))
    
    @discord.ui.button(label="User Info", custom_id="user_info_lookup", style=discord.ButtonStyle.secondary, row=2)
    async def warn_btn(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_modal(UserInfoLookupModal(self.bot))

    @discord.ui.button(label="Audit Logs", custom_id="audit_logs_lookup", style=discord.ButtonStyle.secondary, row=2)
    async def audit_logs_btn(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not interaction.user.guild_permissions.view_audit_log:

            return await interaction.response.send_message("You must have the permissions to view audit logs inorder to use this command!", ephemeral=True)

        entries = [entry async for entry in interaction.guild.audit_logs(limit=5)]

        embed = discord.Embed(title="Past 5 entries from the audit logs", color=discord.Color.orange())
        
        for i, ere in enumerate(entries):
            
            er: discord.AuditLogEntry = ere

            embed.add_field(name=f"{i+1} | User: {er.user}", value=f"Action: {er.action.name}\nReason: {er.reason}\nCreated At: <t:{int(er.created_at.timestamp())}:f>", inline=False)

        await interaction.response.send_message(embed=embed)
        

class ModPanel(commands.Cog):

    def __init__(self, bot: discord.Client):
        self.bot = bot

    mod_group = app_commands.Group(name="moderation", description="moderation commands")

    @mod_group.command(name="panel", description="Opens the moderation panel")
    @app_commands.check(mod_perms)
    async def mod_panel(self, ctx):

        await ctx.response.defer(thinking=True)

        emb = discord.Embed(title="Moderation Panel", description="Use the buttons below for actions.", color=discord.Color.red())

        await ctx.followup.send(embed=emb, view=PanelEmbed(self.bot))

async def setup(bot):
    await bot.add_cog(ModPanel(bot))