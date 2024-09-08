import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio

class Roll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="roll", description="Roll some dice!")
    @app_commands.describe(sides="Number of sides on each die", number_of_dice="Number of dice to roll")
    async def roll(self, ctx: discord.Interaction, sides: int = 6, number_of_dice: int = 1):
        # Check for max values
        if sides > 120 or number_of_dice > 8:
            return await ctx.response.send_message("The number of sides on the dice cannot be higher than 120, and the number of dice cannot exceed 8.", ephemeral=True)

        rolls = [random.randint(1, sides) for _ in range(number_of_dice)]
        total = sum(rolls)

        # Show typing indicator (loading animation)
        async with ctx.typing():
            await asyncio.sleep(2)  # Simulate rolling animation for 2 seconds

        embed = discord.Embed(
            title = "🎲 Roll",
            description = f"Rolling {number_of_dice}x{sides}",
            color = discord.Color.green()
        )
        embed.add_field(
            name = "Rolls",
            value = ' + '.join([str(roll) for roll in rolls]),
            inline = False
        )
        if number_of_dice > 1:
            embed.add_field(
                name = "Total",
                value = f"**{str(total)}**",
                inline = False
            )

        # Send the result message
        await ctx.response.send_message(embed=embed)
    
async def setup(bot):
    await bot.add_cog(Roll(bot))
