import discord

from discord.ext import commands
from discord import app_commands

from src.cosmobot.setup import globals as g
from src.cosmobot.cogs.moderation.mod_logs import Logs
from globals import mod_perms


class Kick(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.describe(member="The member to kick", reason="The reason for kicking this member")
    @app_commands.check(mod_perms)
    async def kick(self, ctx: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        embed = discord.Embed(
            description = f"{member.name} has been kicked.",
            color = discord.Color.green()
        )
        embed.add_field(
            name = "Reason",
            value = reason,
            inline = False
        )

        if ctx.user.guild_permissions.kick_members:
            await member.kick(reason=reason)
            await ctx.response.send_message(embed=embed)

            await Logs.mod_log(
                self=self,
                title = "Moderation | Kick",
                description = f"**{member.mention}** has been kicked.",
                footer=f"User ID: {member.id} | Moderator ID: {ctx.user.id}",
                color = discord.Color.green(),
                ctx=ctx,
                author=member
            )

        else:
            await g.no_permission(ctx, self, Ephemeral=True)

        
async def setup(bot):
    await bot.add_cog(Kick(bot))