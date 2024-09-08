import discord

import json
import time as tm

from discord.ext import commands
from discord import app_commands

from config import Config as cfg
from src.cosmobot.cogs.dev.embeds import AfkEmbedSetup
from globals import timestamp
from globals import mod_perms

from math import ceil
from datetime import datetime, timedelta
from humanfriendly import parse_timespan


db = cfg.DB.main_database

afk_collection = db.afk_collection
afk_embed_collection = db.afk_embed_collection

class AfkCommandView(discord.ui.View): 
    current_page = 1
    sep = 5
    
    async def send(self, ctx):
        await ctx.response.send_message(embed=self.create_embed(self.get_current_page_data()), view=self)
        self.message = await ctx.original_response()

    def create_embed(self, data):
        embed = discord.Embed(title=f"Active AFKs (Page {self.current_page} / {ceil(len(self.data) / self.sep)})", description=f'Below are all the active AFKs in this server, showing 5 per page.')
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

class Afk(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    afk_group = app_commands.Group(name="afk", description="Set your AFK status.")

    @afk_group.command(name="response", description="Set your custom AFK response embed")
    @app_commands.describe(action = "Wheter you want to set or view your afk response embed")
    @app_commands.choices(action = [app_commands.Choice(name="Set", value='Set'), app_commands.Choice(name="View", value='View')])
    async def afkembed(self, ctx: discord.Interaction, action: str):

        if action == "Set":

            messa = await afk_embed_collection.find_one({"member_id": str(ctx.user.id)})

            embed = discord.Embed(
                title="AFK Response Embed Setup Menu",
                description="Placeholders:\n{reason}\n{duration}\n{went_afk}",
                color=discord.Colour.dark_orange()
            )

            if messa:

                await ctx.response.send_message(embed=embed, view=AfkEmbedSetup(timeout=600, target=ctx, type="Afk"))

                return

            
            else:

                document = {"member_id": str(ctx.user.id), "message": "placeholder"}

                afk_embed_collection.insert_one(document)

                await ctx.response.send_message(embed=embed, view=AfkEmbedSetup(timeout=600, target=ctx, type="Afk"))
        
        elif action == "View":
            messa = await afk_embed_collection.find_one({"member_id": str(ctx.user.id)})

            if messa:

                raw = messa["message"]

                to_dict = json.loads(
                    raw,
                    parse_int=lambda x: int(x),
                    parse_float=lambda x: float(x),
                )
                embed = discord.Embed.from_dict(to_dict)

                await ctx.response.send_message(embed=embed)

            else:

                await ctx.response.send_message("You dont have your afk response embed set use the /afk embed command to set your custom afk response message")
        
    
    @afk_group.command(name="add", description="Set your AFK status")
    @app_commands.describe(reason="The reason to why you are going afk")
    @app_commands.describe(duration="The duration of your AFK session, makes you immune from automatic AFK status removal for the time being")
    async def afk_add(self, ctx: discord.Interaction, reason: str = "No reason specified", duration: str = None):

        await ctx.response.defer(thinking=True)

        time: int = 0
        infinite = False
        
        already_afk = await afk_collection.find_one({"member_id": ctx.user.id, "guild_id": ctx.guild_id})
        
        if already_afk:
            embed = discord.Embed(
                title="Error",
                description="You are already AFK. If you wish to remove your afk status, use the `afk remove` command.",
                color=discord.Color.red()
            )
            await ctx.followup.send(embed=embed)
            return
        
        if duration is None or duration == "":
            infinite = True
        else:
            try:
                time = parse_timespan(duration)
            except:
                embed = discord.Embed(
                    title="Error",
                    description=f"`{duration}` is not a valid time. An example of a valid time is `43m`.",
                    color=discord.Color.red()
                )
                await ctx.followup.send(embed=embed)
                return
                
        document = {}
        
        if infinite:
            document = {"start": int(tm.time()), "ends": "infinite", "reason": reason, "member_id": ctx.user.id, "guild_id": ctx.guild_id}
        else:
            delta = timedelta(seconds=time)
            utc_now = datetime.now()
            end_time = utc_now + delta
            document = {"start": int(tm.time()), "ends": end_time, "reason": reason, "member_id": ctx.user.id, "guild_id": ctx.guild_id}
        
        afk_collection.insert_one(document)
        desc = f"You have set yourself as AFK for the reason of `{reason}` and for `{duration}`"
        
        if duration is None or duration == "":
            desc = f"You have set yourself as AFK"
        embed = discord.Embed(
            title="AFK Set",
            description=desc,
            color=discord.Color.green()
        )
        try:
            await ctx.user.edit(nick=f"[AFK] {ctx.user.nick if ctx.user.nick is not None else ctx.user.display_name}")
        except Exception as e:
            print(e)
        await ctx.followup.send(embed=embed)
    
    @afk_group.command(name="remove", description="Remove your AFK status")
    async def afk_remove(self, ctx: discord.Interaction):
        already_afk = await afk_collection.find_one({"member_id": ctx.user.id, "guild_id": ctx.guild_id})
        
        if not already_afk:
            embed = discord.Embed(
                title="Error",
                description="You are not AFK. You may set your AFK status using the `afk add` command.",
                color=discord.Color.red()
            )
            await ctx.response.send_message(embed=embed)
            return
        else:
            embed = discord.Embed(
                title="Removed your AFK status",
                description="Your AFK status has been removed. Welcome back!",
                color=discord.Color.green()
            )
            await afk_collection.find_one_and_delete({"member_id": ctx.user.id, "guild_id": ctx.guild_id})
            if ctx.user.nick.startswith("[AFK] "):
                await ctx.user.edit(nick=ctx.user.nick[6:])
            await ctx.response.send_message(embed=embed)
            return
    
    @afk_group.command(name="view", description="View all active AFks in the server (moderator only)")
    @app_commands.check(mod_perms)
    async def view_afks(self, ctx: discord.Interaction):
        afk_list = []
        async for i in afk_collection.find({"guild_id": ctx.guild.id}):
            afk_list.append(i)
        if len(afk_list) == 0:
            embed = discord.Embed(
                title="Active AFKs",
                description="There are no active AFKs in this server."
            )
            await ctx.response.send_message(embed=embed)
        else:
            fields = []
            now = datetime.now()
            for i in afk_list:
                member = await ctx.guild.fetch_member(i["member_id"])
                if i["ends"] > now:
                    fields.append({"name": member.name, "value": f'**Reason:** {i["reason"]}\n**Ends At (UTC):** {timestamp(i["ends"])}', "inline": False})
            pagination_view = AfkCommandView(timeout=None)
            pagination_view.data = fields
            pagination_view.update_buttons()
            await pagination_view.send(ctx)
            
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if message.author == self.bot.user:
            return
        
        afk = await afk_collection.find_one({"member_id": message.author.id, "guild_id": message.guild.id})

        if afk:
            if afk["ends"] != "infinite":
                now = datetime.now()
                if now > afk["ends"]:
                    await afk_collection.find_one_and_delete({"member_id": message.author.id, "guild_id": message.guild.id})
                    if message.author.nick.startswith("[AFK] "):
                        await message.author.edit(nick=message.author.nick[6:])
                    await message.reply("Welcome back!")

            elif afk["ends"] == "infinite":
                await afk_collection.find_one_and_delete({"member_id": message.author.id, "guild_id": message.guild.id})
                if message.author.nick.startswith("[AFK] "):
                    await message.author.edit(nick=message.author.nick[6:])
                await message.reply("Welcome back!")

        else:
            mentions = message.mentions
            afk = None
            for i in mentions:
                afk = await afk_collection.find_one({"member_id": i.id, "guild_id": message.guild.id})
                messa = await afk_embed_collection.find_one({"member_id": str(i.id)})

            if afk:

                if afk["ends"] != "infinite":
                    now = datetime.now()
                    if afk["ends"] > now:
                        
                        if messa:

                            reason = afk['reason']
                            duration = afk['ends']
                            started = afk['start']

                            raw = messa["message"]
                            
                            raw = raw.replace("{reason}", reason)
                            raw = raw.replace("{duration}", duration)
                            raw = raw.replace("{went_afk}", f"<t:{int(started)}:R>")

                            to_dict = json.loads(
                                raw,
                                parse_int=lambda x: int(x),
                                parse_float=lambda x: float(x),
                            )
                            embed = discord.Embed.from_dict(to_dict)

                            await message.reply(embed=embed)
                        
                        else:

                            await message.reply("They are currently AFK! Tip: Try `/afk embed` to set your own unique custom response messages!")

                elif afk["ends"] == "infinite":
                    if messa:
                            
                        reason = afk['reason']
                        duration = afk['ends']
                        started = afk['start']

                        raw = messa["message"]
                        
                        raw = raw.replace("{reason}", reason)
                        raw = raw.replace("{duration}", duration)
                        raw = raw.replace("{went_afk}", f"<t:{started}:R>")

                        to_dict = json.loads(
                            raw,
                            parse_int=lambda x: int(x),
                            parse_float=lambda x: float(x),
                        )
                        embed = discord.Embed.from_dict(to_dict)

                        await message.reply("**User Message:**", embed=embed)
                        
                    else:

                        await message.reply("They are currently AFK! Tip: Try /afk embed to set your own unique custom response messages!")
        await self.bot.process_commands(message)

async def setup(bot: commands.Bot):
    await bot.add_cog(Afk(bot))