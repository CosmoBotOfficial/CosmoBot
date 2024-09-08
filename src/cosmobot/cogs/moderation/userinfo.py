import discord
import typing

from discord import app_commands
from discord.ext import commands

from config import Config as cfg
from src.cosmobot.cogs.moderation.warn import warn_collection
from src.cosmobot.cogs.moderation.mod_logs import Logs
from src.cosmobot.cogs.moderation.timeout import timeout_collection
from src.cosmobot.cogs.dev.extensions import PaginationEmbed

from globals import incomplete_message, timestamp, mod_perms
from humanfriendly import parse_timespan
from math import ceil

from datetime import datetime, timedelta


class MemberRoleViewCommand(discord.ui.View): 
    current_page = 1
    sep = 5
    
    def __init__(self, user: str):
        self.username = user
        super().__init__(timeout=600)
    
    async def send(self, ctx):
        await ctx.followup.send(embed=self.create_embed(self.get_current_page_data()), view=self)
        self.message = await ctx.original_response()

    def create_embed(self, data):
        embed = discord.Embed(title=f"{self.username}'s Roles (Page {self.current_page} / {ceil(len(self.data) / self.sep)})", description=f"Below are {self.username}'s roles, showing 5 per page and sorting by hierarchy.")
        for item in data:
            embed.add_field(name=item['name'], value=item['value'], inline=item['inline'])
        return embed

    async def update_message(self, data):
        self.update_buttons()
        await self.message.edit(embed=self.create_embed(data), view=self)

    def update_buttons(self):
        if self.current_page == 1:
            self.first_page_button.disabled = True
            self.prev_button.disabled = True
            self.first_page_button.style = discord.ButtonStyle.gray
            self.prev_button.style = discord.ButtonStyle.gray
        else:
            self.first_page_button.disabled = False
            self.prev_button.disabled = False
            self.first_page_button.style = discord.ButtonStyle.green
            self.prev_button.style = discord.ButtonStyle.primary

        if self.current_page == ceil(len(self.data) / self.sep):
            self.next_button.disabled = True
            self.last_page_button.disabled = True
            self.last_page_button.style = discord.ButtonStyle.gray
            self.next_button.style = discord.ButtonStyle.gray
        else:
            self.next_button.disabled = False
            self.last_page_button.disabled = False
            self.last_page_button.style = discord.ButtonStyle.green
            self.next_button.style = discord.ButtonStyle.primary

    def get_current_page_data(self):
        until_item = self.current_page * self.sep
        from_item = until_item - self.sep
        if self.current_page == 1:
            from_item = 0
            until_item = self.sep
        if self.current_page == ceil(len(self.data) / self.sep) + 1:
            from_item = self.current_page * self.sep - self.sep
            until_item = len(self.data)
        return self.data[from_item:until_item]

class UserInfoView(discord.ui.View):

    def __init__(self, user: discord.Member):
        self.user = user
        
        super().__init__(timeout=600)
        
        url_button = discord.ui.Button(label="View User Avatar", style=discord.ButtonStyle.link, url=user.avatar.url)
        self.add_item(url_button)
    
    @discord.ui.button(label="View Past Warns", style=discord.ButtonStyle.primary)
    async def past_warns(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.defer(thinking=True)

        cursor = warn_collection.find({"member_id": self.user.id, "guild_id": interaction.guild_id}).sort("at", -1)
        past_warns = await cursor.to_list(length=None)
        
        if len(past_warns) == 0:
            embed = discord.Embed(
                title=f"Past Warnings",
                description=f"{self.user.name} has no past warnings."
            )
            await interaction.followup.send(embed=embed)
            return
            
        fields = []
        member = self.user
        
        for i in past_warns:
            fields.append({"name": member.name, "value": f'**Reason:** {i["reason"]}\n**At:** {timestamp(i["at"])}\n**ID:** {i["id"]}\n**Attachment Url:** {i["attachment"]}', "inline": False})

        pagination_view = PaginationEmbed(current_page=1, separtion=5)
        pagination_view.data = fields
        pagination_view.update_buttons()
        await pagination_view.send(interaction)

    @discord.ui.button(label="View Past Timeouts", style=discord.ButtonStyle.primary)
    async def past_timeouts(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.defer(thinking=True)

        cursor = timeout_collection.find({"member_id": self.user.id, "guild_id": interaction.guild_id}).sort("at", -1)
        past_timeouts = await cursor.to_list(length=None)
        
        if len(past_timeouts) == 0:
            embed = discord.Embed(
                title=f"Past Timeouts",
                description=f"{self.user.name} has no past timeouts."
            )
            await interaction.followup.send(embed=embed)
            return
            
        fields = []
        
        now = datetime.utcnow()
        member = self.user
        
        for i in past_timeouts:
            fields.append({"name": member.name, "value": f'**Reason:** {i["reason"]}\n**Duration:** {i["duration"]}\n**End/Ended At (UTC):** {timestamp(i["at"] + timedelta(seconds=parse_timespan(i["duration"])))}\n**Active**: {(i["at"] + timedelta(seconds=parse_timespan(i["duration"]))) > now}', "inline": False})
            
        pagination_view = PaginationEmbed(current_page=1, separtion=5)
        pagination_view.data = fields
        pagination_view.update_buttons()
        await pagination_view.send(interaction)

    @discord.ui.button(label="View Roles", style=discord.ButtonStyle.primary)
    async def view_roles(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.defer(thinking=True)

        roles = self.user.roles
        
        if len(roles) == 0:
            embed = discord.Embed(
                title=f"User Roles",
                description=f"{self.user.name} has no roles."
            )
            await interaction.followup.send(embed=embed)
            return
        
        fields = []
        
        roles = list(reversed(roles))
        
        for i in roles:
            fields.append({"name": i.name, "value": i.mention, "inline": False})
            
        pagination_view = PaginationEmbed(current_page=1, separtion=5)
        pagination_view.data = fields
        pagination_view.update_buttons()
        await pagination_view.send(interaction)


class UserInfo(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def user_info(self, interaction: discord.Interaction, member: discord.Member):

        await interaction.response.defer(thinking=True)

        cursor = warn_collection.find({"member_id": member.id, "guild_id": interaction.guild_id}).sort("at", -1)
        past_warns = await cursor.to_list(length=None)
        
        cursor = timeout_collection.find({"member_id": member.id, "guild_id": interaction.guild_id}).sort("at", -1)
        past_timeouts = await cursor.to_list(length=None)
        
        embed = discord.Embed(title=f"{member.name}'s User Info")
        
        embed.set_thumbnail(url=member.avatar.url)
        embed.add_field(name="Username", value=member.name)
        embed.add_field(name="Nickname", value="No nickname" if member.nick is None else member.nick)
        embed.add_field(name="User ID", value=str(member.id))
        
        embed.add_field(name="Joined Guild", value=timestamp(member.joined_at))
        embed.add_field(name="Joined Discord", value=timestamp(member._user.created_at))
        embed.add_field(name="User's Highest Role", value=member.top_role.mention)
        
        embed.add_field(name="Past Warns", value=str(len(past_warns)))
        embed.add_field(name="Past Timeouts", value=str(len(past_timeouts)))
        
        await interaction.followup.send(embed=embed, view=UserInfoView(user=member))

    userinfo_group = app_commands.Group(name="user", description="User's information lookup")

    @userinfo_group.command(name="info", description="Get the user's information")
    @app_commands.check(mod_perms)
    async def user_info_cmd(self, interaction: discord.Interaction, member: discord.Member=None):

        if member is None:
            member = interaction.user
            
        await self.user_info(interaction, member)
        
async def setup(bot):
    await bot.add_cog(UserInfo(bot))