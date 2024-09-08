import discord
from discord import app_commands
from discord.ext import commands


class Ping(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        

    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping(self, ctx: discord.Interaction):
        ping = round(self.bot.latency * 1000)
        embed = discord.Embed(title="<:CosmoBot:1185861660251000842> Ping", description="The bot's latency", color=discord.Color.blurple())
        embed.add_field(name="Latency", value=f"{ping}ms", inline=True)
        await ctx.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Ping(bot))