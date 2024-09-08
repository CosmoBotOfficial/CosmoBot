import discord

from discord.ext import commands
from discord import app_commands

from src.cosmobot.cogs.moderation.mod_logs import Logs
from src.cosmobot.cogs.dev.extensions import PaginationEmbed
from globals import mod_perms

from math import ceil


class BanListView(discord.ui.View): 
    current_page = 1
    sep = 5

    async def send(self, ctx):
        await ctx.response.send_message(embed=self.create_embed(self.get_current_page_data()), view=self)
        self.message = await ctx.original_response()

    def create_embed(self, data):
        embed = discord.Embed(title=f"Ban list Page")
        if data != []:
            for item in data:
                embed.add_field(name=f'i{item[0]}', value=f'{item[1]}', inline=False)
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

    @discord.ui.button(label="|<", style=discord.ButtonStyle.gray, disabled=True)
    async def first_page_button(self, ctx: discord.Interaction, button: discord.ui.Button):
        await ctx.response.defer()
        self.current_page = 1
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="<", style=discord.ButtonStyle.gray, disabled=True)
    async def prev_button(self, ctx: discord.Interaction, button: discord.ui.Button):
        await ctx.response.defer()
        self.current_page -= 1
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_button(self, ctx: discord.Interaction, button: discord.ui.Button):
        await ctx.response.defer()
        self.current_page += 1
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label=">|", style=discord.ButtonStyle.green)
    async def last_page_button(self, ctx: discord.Interaction, button: discord.ui.Button):
        await ctx.response.defer()
        self.current_page = ceil(len(self.data) / self.sep)
        await self.update_message(self.get_current_page_data())

class Ban(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.check(mod_perms)
    async def ban(self, ctx: discord.Interaction, member: discord.Member, reason: str):
        try:
            await member.ban(reason=reason)

            embed = discord.Embed(
                title="Banned",
                description=f"Banned {member.name} from the server",
                color=discord.Color.green()
            )

            embed.set_footer(
                text=f"reason: {reason}"
            )
            await ctx.response.send_message(embed=embed)

            await Logs.mod_log(
                    title=f"Moderation | Ban",
                    description=f"**{member.mention}** was banned by **{ctx.user}** for **{reason}**",
                    footer=f"User ID: {member.id} | Moderator ID: {ctx.user.id}",
                    color=discord.Color.green(),
                    ctx=ctx,
                    author=member
                )

        except:
            embed = discord.Embed(
                title="Error",
                description=f"Couldn't ban {member.name}",
                color=discord.Color.red()
            )

            await ctx.response.send_message(embed=embed)


    @app_commands.command(name="unban", description="Unban a member")
    @app_commands.check(mod_perms)
    async def unban(self, ctx: discord.Interaction, user: discord.User, reason: str):
        assert ctx.guild is not None
        try:
            await ctx.guild.fetch_ban(user)

            try: 
                await ctx.guild.unban(user, reason=reason)

                embed = discord.Embed(
                    description=f"Unbanned **{user}** from this server",
                    color=discord.Color.green()
                )

                embed.set_footer(
                    text=f"Reason: {reason}"
                )

                await ctx.response.send_message(embed=embed)

                await Logs.mod_log(
                    title=f"Moderation | Unban",
                    description=f"**{user}** was unbanned by **{ctx.user}**",
                    footer=f"User ID: {user.id} | Moderator ID: {ctx.user.id}",
                    color=discord.Color.green(),
                    ctx=ctx,
                    author=user
                )
            except:
                embed = discord.Embed(
                    title=f"Error",
                    description=f"Couldn't unban **{user}** from this server",
                    color=discord.Color.red()
                )
        except:
            embed = discord.Embed(
                title=f"Error",
                description=f"Couldn't unban **{user}** from this server",
                color=discord.Color.red()
            )

            await ctx.response.send_message(embed=embed)

    
    ban_group = app_commands.Group(name="bans", description="view bans")

    @ban_group.command(name="view", description="View the server's past bans")
    @app_commands.check(mod_perms)
    async def view_bans(self, ctx: discord.Interaction):
        assert ctx.guild is not None
        bans = [entry async for entry in ctx.guild.bans(limit=2000)]
        formatedBans = []
        if bans:
            for ban in bans:
                user = ban.user
                reason = ban.reason if ban.reason else "No reason provided"
                formatedBans.append([user.name, reason])

        if formatedBans != []:
            pagview = PaginationEmbed(current_page=1, separtion=5)
            pagview.data = formatedBans
            await pagview.send(ctx)
        else:
            embed = discord.Embed(
                title="Ban List",
                description="There are no bans in this server"
            )

            await ctx.response.send_message(embed=embed)
        
async def setup(bot):
    await bot.add_cog(Ban(bot))