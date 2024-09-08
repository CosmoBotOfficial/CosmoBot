import discord

from discord.ext import commands
from discord import app_commands, ChannelType

from config import Config
from src.cosmobot.cogs.dev.extensions import PaginationEmbed

from random import randint
from DiscordLevelingCard import RankCard, Settings

from datetime import datetime

from math import ceil

db = Config.DB.main_database

levelling_collection = db.levelling_collection
levelling_up_message = db.levelling_up_message

class LevellingLeaderboardViewCommand(discord.ui.View): 
    current_page = 1
    sep = 10
    
    async def send(self, ctx):
        await ctx.followup.send(embed=self.create_embed(self.get_current_page_data()), view=self)
        self.message = await ctx.original_response()

    def create_embed(self, data):
        embed = discord.Embed(title=f"Levelling Leaderboard (Page {self.current_page} / {ceil(len(self.data) / self.sep)})", description=f"Below are the top 100 members in this server with the highest level and EXP, showing 10 per page.")
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
        
class Levelling(commands.Cog):
    
    def __init__(self, bot: commands.Bot):

        self.bot = bot

        self.antispam = commands.CooldownMapping.from_cooldown(1, 2, commands.BucketType.member)

        self.multiplier = 1.2
        self.base_exp = 100

    def calculate_max_exp(self, level):
        return int(self.base_exp * (self.multiplier ** level))
    
    def next_level_exp(self, current_exp, current_level):
        max_exp_current_level = self.calculate_max_exp(current_level)
        if current_exp >= max_exp_current_level:
            return True
        else:
            return False

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if type(message.channel) is not discord.TextChannel or message.author.bot: return

        bucket = self.antispam.get_bucket(message)
        retry_after = bucket.update_rate_limit()

        if retry_after:

            return

        else:

            level = await levelling_collection.find_one({"member_id": message.author.id, "guild_id": message.guild.id})

            experience = randint(1,2)

            if level:
                
                new_experience = level['experience'] + experience

                if self.next_level_exp(level['experience'], level['level']):
                    search = await levelling_up_message.find_one({"guild_id": message.guild.id})
                    
                    if search and search["enabled"]:
                        if search["channel"] == "DEF":
                            channel_id = message.channel.id
                        else:
                            channel_id = search["channel"]
                            
                        channel = self.bot.get_channel(channel_id)
                        await channel.send(f"Congratulations {message.author.mention}! You just levelled up to {level['level'] + 1}!")
                    elif search["enabled"]:
                        await message.channel.send(f"Congratulations! You just levelled up to {level['level'] + 1}!")
                    
                    new_value = {"$set": {"experience": 0, "level": level['level'] + 1}}
                else:
                    new_value = {"$set": {"experience": new_experience}}

                await levelling_collection.update_one(level, new_value)

            else:

                document = {"member_id": message.author.id, "guild_id": message.guild.id, "level": 0, "experience": experience}

                await levelling_collection.insert_one(document)

    levelling_group = app_commands.Group(name="levelling", description="levelling system")

    @levelling_group.command(name="leaderboard", description="View the top 100 members with the highest level and EXP")
    async def lb(self, interaction: discord.Interaction):

        await interaction.response.defer(thinking=True)

        cursor = levelling_collection.find({"guild_id": interaction.guild_id}).sort({"level": -1, "experience": -1}).limit(100)
        members_raw = await cursor.to_list(length=None)

        leaderboard_data = []  # List to hold tuples of (member_id, level, experience)

        for member in members_raw:
            leaderboard_data.append((member['member_id'], member['level'], member['experience']))

        embed = discord.Embed(
            title="Leaderboard",
            description="Below is the leaderboard for the top 100 members of the server with the highest level and EXP."
        )

        fields = []
        
        for data in leaderboard_data:
            member_id, level, experience = data
            user = await self.bot.fetch_user(int(member_id))
            fields.append({"name": user.name, "value": f"Level: {level}, Experience: {experience}", "inline": False})

        pagination_view = PaginationEmbed(current_page=1, separtion=10)
        pagination_view.data = fields
        pagination_view.update_buttons()
        await pagination_view.send(interaction)
    


    @levelling_group.command(name="level", description="View your or other's level")
    async def lvl(self, ctx: discord.Interaction, user: discord.Member = None):

        await ctx.response.defer()
        
        if not user:

            user = ctx.user

        level = await levelling_collection.find_one({"member_id": user.id, "guild_id": user.guild.id})

        lvl = level['level']
        exp = level['experience']
        max_exp = self.calculate_max_exp(level['level'] + 1)


        card_settings = Settings(
            background="https://cdn.discordapp.com/attachments/1249459349407924254/1279489267885670501/Screenshot_2024-06-20_at_6.png?ex=66d4a0bd&is=66d34f3d&hm=d509073fa87440cecbb036cde7a12751f58a5d1db76cf3550fbdd1ab0f8031bb&",
            text_color="white",
            bar_color="#F09C7A"
        )

        card = RankCard(
            settings=card_settings,
            avatar=user.display_avatar.url,
            level=lvl,
            current_exp=exp,
            max_exp=max_exp,
            username=user.display_name
        )

        image = await card.card3()
    
        await ctx.followup.send(file=discord.File(image, 'rank.png'))

    @levelling_group.command(name="message", description="Configure level up messages; leave the options blank for default configuration")
    @app_commands.choices(action = [app_commands.Choice(name="View", value='View')])
    async def lvlup(self, ctx: discord.Interaction, channel: discord.TextChannel = None, enabled: bool = True, action: str = None):

        if channel == None:

            channel = "DEF"

        else:

            channel = channel.id

        search = await levelling_up_message.find_one({"guild_id": ctx.guild_id})

        if action == "View":

            if search["channel"] == "DEF":

                embed = discord.Embed(
                    title="Level up messages configuration",
                    description=f"The message will be sent to the channel in which the user levelled up in.\nCurrent status: {search['enabled']}"
                )


            else:

                raw = self.bot.get_channel(search["channel"])

                embed = discord.Embed(
                    title="Level up messages configuration",
                    description=f"Level up messages are sent on: {raw.mention}\nCurrent status: {search['enabled']}"
                )

            await ctx.response.send_message(embed=embed)

            return

        document = {"guild_id": ctx.guild_id, "channel": channel, "enabled": enabled}

        if not search:

            await levelling_up_message.insert_one(document)
            await ctx.response.send_message("Data has been set successfully, use `/levelling message action: View` to see the current configuration")

        else:

            new_value = {"$set": {"channel": channel, "enabled": enabled}}

            await levelling_up_message.update_one(search, new_value)

            await ctx.response.send_message("Data has been set successfully, use `/levelling message action: View` to see the current configuration")


async def setup(bot):
    await bot.add_cog(Levelling(bot))