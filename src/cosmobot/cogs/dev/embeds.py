import aiohttp
import re
import json
import copy
import discord

from io import BytesIO

from discord.ext import commands
from discord.ui import TextInput
from discord import app_commands, ChannelType
from discord.utils import MISSING
from discord import Color

from config import Config
from typing import Optional, Union, TypeVar

db = Config.DB.main_database

afk_embed_collection = db.afk_embed_collection

MYSTBIN_API_KEY = Config.MYSTBIN_API_KEY

CONTRAST_COLOR = Color.from_str("#F5837C")

HTTP_URL_REGEX = r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"

CosmoT = TypeVar("CosmoT", bound="commands.Bot")

class EmptyRoleClass:
    def __init__(self):
        self.id = None
        self.mention = "No role requirement"
    
def re_url_match(url: str):
    return re.fullmatch(HTTP_URL_REGEX, url)

def message_jump_button(url: str, to_where: str = "to Message"):
    if not re_url_match(url):
        raise ValueError("Invalid URL. Check `is_http` param.")

    return discord.ui.Button(
        label=f"Jump {to_where}", style=discord.ButtonStyle.link, url=url
    )

def truncate(string: str, width: int = 50) -> str:

    if len(string) > width:
        string = string[: width - 3] + "..."
    return string


class BaseView(discord.ui.View):

    def __init__(
        self,
        *,
        timeout=180,
        target: Optional[CosmoT] = None,
    ):
        self.target = target

        self.author: Optional[Union[discord.User, discord.Member]] = target and (
            target.user if isinstance(target, discord.Interaction) else target.author
        )

        self.ctx_msg = None

        super().__init__(timeout=timeout)

    async def stop(self, interaction: discord.Interaction):
        for child in self.children:
            child.disabled = True

        await interaction.edit_original_response(view=self)

        super().stop()

    async def interaction_check(
        self, interaction: discord.Interaction[discord.Client]
    ) -> bool:
        if self.target is None:
            return True

        assert self.author

        if self.author.id != interaction.user.id:
            return await interaction.response.send_message(
                f"Only the author can respond to this",
                ephemeral=True,
            )

        # chnl
        if (
            self.target.channel
            and interaction.channel
            and self.target.channel.id != interaction.channel.id
        ):
            return await interaction.response.send_message(
                f"This isn't in the right channel",
                ephemeral=True,
            )

        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True

        if not self.target:
            return

        if isinstance(self.target, discord.Interaction):
            await self.target.edit_original_response(view=self)
        else:
            await self.ctx_msg.edit(view=self)


class EmbedModal(discord.ui.Modal):
    def __init__(self, *, _embed: discord.Embed, parent_view: discord.ui.View) -> None:
        self.embed = _embed

        self.parent_view = parent_view

        self.em_title.default = _embed.title
        self.description.default = _embed.description

        _image = _embed.image
        if _image is not None:
            self.image.default = _image.url

        _thumbnail = _embed.thumbnail
        if _thumbnail is not None:
            self.thumbnail.default = _thumbnail.url

        check_color = _embed.color
        if check_color is not None:
            clr = _embed.color.to_rgb()

            self.color.default = f"rgb({clr[0]}, {clr[1]}, {clr[2]})"

        super().__init__(title="Edit Embed Components", timeout=None)

    em_title = TextInput(
        label="Title",
        placeholder="The title of the embed",
        style=discord.TextStyle.short,
        required=False,
        max_length=256,
    )
    description = TextInput(
        label="Description",
        placeholder="Upto 4000 characters. Out of shared max characters (6000)\nLorem ipsum dolor sit amet.\n",
        style=discord.TextStyle.long,
        required=False,
        max_length=4000,
    )
    image = TextInput(
        label="Image URL",
        placeholder="http://example.com/space.png",
        required=False,
        style=discord.TextStyle.short,
    )
    thumbnail = TextInput(
        label="Thumbnail URL",
        placeholder="http://example.com/stars.png",
        required=False,
        style=discord.TextStyle.short,
    )
    color = TextInput(
        label="Color",
        placeholder="Hex #FFFFFF | rgb(r, g, b)",
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        embed_copy = copy.deepcopy(self.embed)

        self.embed.title = self.em_title.value  
        self.embed.description = self.description.value  

        self.embed.set_image(url=self.image.value)
        self.embed.set_thumbnail(url=self.thumbnail.value)

        if self.color.value:
            self.embed.color = discord.Color.from_str(self.color.value)

        if len(self.embed) > 6000:
            self.parent_view.embed = embed_copy
            await interaction.response.send_message(
                f"Embed too long; Exceeded 6000 characters.",
                ephemeral=True,
            )
            return

        self.parent_view.update_counters()
        await interaction.response.edit_message(embed=self.embed, view=self.parent_view)

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        if isinstance(error, ValueError) or isinstance(
            error, discord.errors.HTTPException
        ):
            await interaction.response.send_message(
                f"Value Error. Please check for the following:\nEmpty Embed / Invalid Color / Invalid URL(s)",
                ephemeral=True,
            )
        else:
            raise error


class AuthorModal(discord.ui.Modal):
    def __init__(self, *, _embed: discord.Embed, parent_view: discord.ui.View) -> None:
        self.embed = _embed
        self.parent_view = parent_view

        self.author_name.default = _embed.author.name
        self.url.default = _embed.author.url
        self.icon_url.default = _embed.author.icon_url

        super().__init__(title="Edit Author Component", timeout=None)

    author_name = TextInput(
        label="Author Name",
        placeholder="The name of the author",
        style=discord.TextStyle.short,
        max_length=256,
        required=False,
    )
    url = TextInput(
        label="Author URL",
        placeholder="http://example.com",
        required=False,
        style=discord.TextStyle.short,
    )
    icon_url = TextInput(
        label="Author Icon URL",
        placeholder="http://example.com/astronaut.png",
        required=False,
        style=discord.TextStyle.short,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        embed_copy = copy.deepcopy(self.embed)

        self.embed.set_author(
            name=self.author_name.value,
            url=self.url.value,
            icon_url=self.icon_url.value,
        )
        if len(self.embed) > 6000:
            self.parent_view.embed = embed_copy
            await interaction.response.send_message(
                f"Embed too long; Exceeded 6000 characters.",
                ephemeral=True,
            )
            return

        self.parent_view.update_counters()
        await interaction.response.edit_message(embed=self.embed, view=self.parent_view)

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        if isinstance(error, ValueError) or isinstance(
            error, discord.errors.HTTPException
        ):
            await interaction.response.send_message(
                f"Value Error. Please check your input: Invalid URL(s)",
                ephemeral=True,
            )
        else:
            raise error


class FooterModal(discord.ui.Modal):
    def __init__(self, *, _embed: discord.Embed, parent_view: discord.ui.View) -> None:
        self.embed = _embed
        self.parent_view = parent_view

        self.text.default = _embed.footer.text
        self.icon_url.default = _embed.footer.icon_url

        super().__init__(title="Edit Footer Component", timeout=None)

    text = TextInput(
        label="Footer Text",
        placeholder="The text of the footer",
        style=discord.TextStyle.short,
        max_length=2048,
        required=False,
    )
    icon_url = TextInput(
        label="Footer Icon URL",
        placeholder="http://example.com/astronaut.png",
        required=False,
        style=discord.TextStyle.short,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        embed_copy = copy.deepcopy(self.embed)

        self.embed.set_footer(
            text=self.text.value,
            icon_url=self.icon_url.value,
        )
        if len(self.embed) > 6000:
            self.parent_view.embed = embed_copy
            await interaction.response.send_message(
                f"Embed too long; Exceeded 6000 characters.",
                ephemeral=True,
            )
            return
        self.parent_view.update_counters()
        await interaction.response.edit_message(embed=self.embed, view=self.parent_view)

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        if isinstance(error, ValueError) or isinstance(
            error, discord.errors.HTTPException
        ):
            await interaction.response.send_message(
                f"Value Error. Please check your input: Invalid URL(s)",
                ephemeral=True,
            )
        else:
            raise error


class URLModal(discord.ui.Modal):
    def __init__(self, *, _embed: discord.Embed, parent_view: discord.ui.View) -> None:
        self.embed = _embed

        self.parent_view = parent_view

        self.url.default = _embed.url

        super().__init__(title="Edit URL Component", timeout=None)

    url = TextInput(
        label="Title URL",
        placeholder="http://example.com",
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        embed_copy = copy.deepcopy(self.embed)

        if not self.embed.title:
            await interaction.response.send_message(
                f"Embed must have a title.", ephemeral=True
            )
            return

        self.embed.url = self.url.value

        if len(self.embed) > 6000:
            self.parent_view.embed = embed_copy
            await interaction.response.send_message(
                f"Embed too long; Exceeded 6000 characters.",
                ephemeral=True,
            )
            return

        self.parent_view.update_counters()
        await interaction.response.edit_message(embed=self.embed, view=self.parent_view)

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        if isinstance(error, ValueError) or isinstance(
            error, discord.errors.HTTPException
        ):
            await interaction.response.send_message(
                f"Value Error. Invalid URL",
                ephemeral=True,
            )
        else:
            raise error


class AddFieldModal(discord.ui.Modal):
    def __init__(self, *, _embed: discord.Embed, parent_view: discord.ui.View) -> None:
        self.embed = _embed
        self.parent_view = parent_view

        super().__init__(title="Add Field", timeout=None)

    fl_name = TextInput(
        label="Field Name",
        placeholder="The name of the field",
        style=discord.TextStyle.short,
        max_length=256,
        required=True,
    )
    value = TextInput(
        label="Field Value",
        placeholder="The value of the field",
        style=discord.TextStyle.long,
        max_length=1024,
        required=True,
    )
    inline = TextInput(
        label="Inline?",
        placeholder="True/False | T/F || Yes/No | Y/N (default: True)",
        style=discord.TextStyle.short,
        max_length=5,
        required=False,
    )
    index = TextInput(
        label="Index (Where to add the field)",
        placeholder="1 - 25 (default: 25)",
        style=discord.TextStyle.short,
        max_length=2,
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        embed_copy = copy.deepcopy(self.embed)

        inline_set = {
            "true": True,
            "t": True,
            "yes": True,
            "y": True,
            "false": False,
            "f": False,
            "no": False,
            "n": False,
        }
        if self.inline.value:
            inline = inline_set.get(self.inline.value.lower())
        else:
            inline = True

        index = (
            int(self.index.value) - 1 if self.index.value else len(self.embed.fields)
        )

        self.embed.insert_field_at(
            index,
            name=self.fl_name.value,
            value=self.value.value,
            inline=inline,
        )

        if len(self.embed) > 6000:
            self.parent_view.embed = embed_copy

            await interaction.response.send_message(
                f"Embed too long; Exceeded 6000 characters.",
                ephemeral=True,
            )
            return

        self.parent_view.update_counters()
        await interaction.response.edit_message(embed=self.embed, view=self.parent_view)

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        if isinstance(error, ValueError) or isinstance(
            error, discord.errors.HTTPException
        ):
            await interaction.response.send_message(
                f"Value Error. {str(error)}",
                ephemeral=True,
            )
        else:
            print(
                f"{error} {type(error)} {isinstance(error, discord.HTTPException)}",
                "red",
            )
            raise error


class DeleteFieldDropdown(discord.ui.Select):
    def __init__(
        self,
        *,
        _embed: discord.Embed,
        parent_view: discord.ui.View,
        original_msg: discord.Message,
    ):
        self.embed = _embed

        self.parent_view = parent_view

        self.original_msg = original_msg

        options = [
            discord.SelectOption(
                label=truncate(f"{i+1}. {field.name}"),
                value=str(i),
            )
            for i, field in enumerate(self.embed.fields)
        ]

        super().__init__(
            placeholder="Select a field", min_values=1, max_values=1, options=options
        )

    async def callback(self, interaction: discord.Interaction):
        self.embed.remove_field(int(self.values[0]))
        if len(self.embed) == 0:
            self.embed.description = "Lorem ipsum dolor sit amet."

        self.parent_view.update_counters()
        await self.original_msg.edit(embed=self.embed, view=self.parent_view)
        await interaction.response.edit_message(
            content=f"Field deleted.", view=None
        )


class EditFieldModal(discord.ui.Modal):
    fl_name = TextInput(
        label="Field Name",
        placeholder="The name of the field",
        style=discord.TextStyle.short,
        max_length=256,
        required=False,
    )
    value = TextInput(
        label="Field Value",
        placeholder="The value of the field",
        style=discord.TextStyle.long,
        max_length=1024,
        required=False,
    )
    inline = TextInput(
        label="Inline?",
        placeholder="True/False | T/F || Yes/No | Y/N",
        style=discord.TextStyle.short,
        max_length=5,
        required=False,
    )
    index = TextInput(
        label="Index (Where to add the field)",
        placeholder="1 - 25 (default: 25)",
        style=discord.TextStyle.short,
        max_length=2,
        required=False,
    )

    def __init__(
        self,
        *,
        _embed: discord.Embed,
        parent_view: discord.ui.View,
        field_index: int,
        original_msg: discord.Message,
    ) -> None:
        self.embed = _embed

        self.parent_view = parent_view
        self._old_index = int(field_index)

        self.original_msg = original_msg

        field = self.embed.fields[field_index]

        self.fl_name.default = field.name
        self.value.default = field.value
        self.inline.default = str(field.inline)
        self.index.default = str(field_index + 1)

        super().__init__(title=f"Editing Field {field_index+1}", timeout=None)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        embed_copy = copy.deepcopy(self.embed)

        inline_set = {
            "true": True,
            "t": True,
            "yes": True,
            "y": True,
            "false": False,
            "f": False,
            "no": False,
            "n": False,
        }
        inline = inline_set.get(self.inline.value.lower())

        if self.index.value:
            index = int(self.index.value) - 1
        else:
            index = len(self.embed.fields) - 1

        if index < 0 or index > len(self.embed.fields):
            raise IndexError("Index out of range.")

        if inline is None:
            raise ValueError("Inline value must be Boolean!")

        self.embed.remove_field(self._old_index)
        self.embed.insert_field_at(
            index, name=self.fl_name.value, value=self.value.value, inline=inline
        )

        if len(self.embed) > 6000:
            self.parent_view.embed = embed_copy

            await interaction.response.send_message(
                f"Embed too long; Exceeded 6000 characters.",
                ephemeral=True,
            )
            return

        self.parent_view.update_counters()
        await self.original_msg.edit(embed=self.embed, view=self.parent_view)

        await interaction.response.edit_message(
            content=f"Field edited.", view=None
        )

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        if isinstance(error, ValueError) or isinstance(
            error, discord.errors.HTTPException
        ):
            await interaction.response.edit_message(
                content=f" - Invalid Input: {str(error)}",
                view=None,
            )
        elif isinstance(error, IndexError):
            await interaction.response.edit_message(
                content=f" - Invalid Index: {str(error)}",
                view=None,
            )
        else:
            raise error


class EditFieldDropdown(discord.ui.Select):
    def __init__(
        self,
        *,
        _embed: discord.Embed,
        parent_view: discord.ui.View,
        original_msg: discord.Message,
    ):
        self.embed = _embed
        self.parent_view = parent_view
        self.original_msg = original_msg

        options = [
            discord.SelectOption(
                label=truncate(f"{i+1}. {field.name}", 100),
                value=str(i),
            )
            for i, field in enumerate(_embed.fields)
        ]

        super().__init__(
            placeholder="Select a field", min_values=1, max_values=1, options=options
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            EditFieldModal(
                _embed=self.embed,
                field_index=int(self.values[0]),
                original_msg=self.original_msg,
                parent_view=self.parent_view,
            )
        )
        await interaction.edit_original_response(view=None, content="Editing Field...")


class SendToChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, *, _embed: discord.Embed, bot):
        self.embed = _embed
        self.bot = bot

        super().__init__(
            placeholder="Select a channel.",
            channel_types=[
                ChannelType.text,
                ChannelType.news,
                ChannelType.private_thread,
                ChannelType.public_thread,
                ChannelType.voice,
            ],
        )

    async def callback(self, interaction: discord.Interaction):
        
        channel_id = self.values[0].id

        channel = self.bot.get_channel(channel_id)

        user_perms = channel.permissions_for(interaction.user)

        try:
            if user_perms.send_messages and user_perms.embed_links:
                msg = await channel.send(embed=self.embed)

                confirmed_view = BaseView(timeout=180, target=interaction).add_item(
                    message_jump_button(msg.jump_url)
                )
                await interaction.response.edit_message(
                    content=f" - Embed sent to {channel.mention}.",
                    view=confirmed_view,
                )
            else:
                await interaction.response.edit_message(
                    content=f" - You have permission to send embeds in {channel.mention}.",
                    view=None,
                )
        except discord.HTTPException:
            await interaction.response.edit_message(
                f" - Couldn't send the embed in {channel.mention}.",
                view=None,
            )


class SendViaWebhookModal(discord.ui.Modal):
    def __init__(self, *, _embed: discord.Embed):
        self.embed = _embed

        super().__init__(
            title="Send Embed via Webhook",
        )

    wh_url = discord.ui.TextInput(
        label="Webhook URL",
        required=True,
        placeholder="Webhook URL",
    )
    wh_name = discord.ui.TextInput(
        label="Webhook Name",
        placeholder="Name to send message under (optional)",
        required=False,
        max_length=80,
    )
    wh_avatar = discord.ui.TextInput(
        label="Webhook Avatar URL",
        placeholder="Avatar of the Webhook (optional)",
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        mtch = re.fullmatch(
            r"https?:\/\/discord\.com\/api\/webhooks\/\d+\/.+",
            self.wh_url.value,
        )

        if not mtch:
            await interaction.response.send_message(
                f" - Invalid URL",
                ephemeral=True,
            )
            return

        try:
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(self.wh_url.value, session=session)

                msg = await webhook.send(
                    username=self.wh_name.value or MISSING,
                    avatar_url=self.wh_avatar.value or MISSING,
                    embed=self.embed,
                    wait=True,
                )

            await interaction.response.send_message(
                f" - Embed sent [via webhook]({self.wh_url.value}).",
                ephemeral=True,
                view=BaseView().add_item(message_jump_button(msg.jump_url)),
            )
        except discord.HTTPException:
            await interaction.response.send_message(
                f" - Couldn't send the embed.",
                ephemeral=True,
            )


class ImportJSONModal(discord.ui.Modal):
    def __init__(self, *, _embed: discord.Embed, parent_view: discord.ui.View):
        self.embed = _embed
        self.parent_view = parent_view

        super().__init__(
            title="Import JSON",
        )

    json_or_mystbin = discord.ui.TextInput(
        label="JSON or Mystbin URL",
        placeholder="Paste JSON or mystb.in link here.\n"
        "If your JSON is too long, use https://mystb.in/ to upload it.\n",
        required=True,
        style=discord.TextStyle.paragraph,
    )

    async def get_mystb_file(self, paste_id: str) -> str:
        headers = {
            "Authorization": "Bearer " + MYSTBIN_API_KEY,
        }
        async with aiohttp.ClientSession() as session:
            sesh = await session.get(
                f"https://api.mystb.in/paste/{paste_id}", headers=headers
            )
            status_table = {
                401: "Unauthorised",
                404: "Not Found",
                422: "Unprocessable Entity",
            }
            if sesh.status != 200:
                raise ValueError(
                    f"Unable to fetch from mystb.in, API Returned {sesh.status}: {status_table[sesh.status]}"
                )

        json_str = json.loads(await sesh.content.read())["files"][0]["content"]
        return json_str

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if not re.fullmatch(HTTP_URL_REGEX, self.json_or_mystbin.value):
            json_value = self.json_or_mystbin.value

        else:
            if not self.json_or_mystbin.value.startswith("https://mystb.in/"):
                return await interaction.followup.send(
                    content=f" - Not a mystb.in URL",
                    ephemeral=True,
                )

            json_value = await self.get_mystb_file(
                self.json_or_mystbin.value.lstrip("https://mystb.in/")
            )

        to_dict = json.loads(
            json_value,
            parse_int=lambda x: int(x),
            parse_float=lambda x: float(x),
        )
        embed = discord.Embed.from_dict(to_dict)

        if len(embed) <= 0 or len(embed) > 6000:
            raise ValueError("Embed length is not 0-6000 characters long.")

        self.parent_view.embed = embed
        self.parent_view.update_counters()

        await interaction.edit_original_response(embed=embed, view=self.parent_view)
        await interaction.followup.send(
            content=f" - Embed imported from JSON",
            ephemeral=True,
        )

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        if isinstance(error, ValueError) or isinstance(
            error, discord.errors.HTTPException
        ):
            await interaction.followup.send(
                content=f" - Error: {str(error)}", ephemeral=True
            )
        elif isinstance(error, json.JSONDecodeError):
            await interaction.followup.send(
                f" - Invalid JSON.",
                ephemeral=True,
            )
        else:
            raise error


class AfkEmbedSetup(BaseView):
    def __init__(self, *, timeout: int, target: discord.Interaction, type: str):
        self.bot = target.client
        self.type = type
        super().__init__(timeout=timeout, target=target)

        self.embed = discord.Embed()

    def update_counters(self):
        self.character_counter.label = f"{len(self.embed)}/6000 Characters"
        self.field_counter.label = f"{len(self.embed.fields)}/25 Fields"

    @discord.ui.button(
        label="Edit:", style=discord.ButtonStyle.gray, disabled=True, row=0
    )
    async def _basic_tag(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()

    @discord.ui.button(label="Embed", style=discord.ButtonStyle.primary, row=0)
    async def edit_embed(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            EmbedModal(_embed=self.embed, parent_view=self)
        )

    @discord.ui.button(label="Author", style=discord.ButtonStyle.primary, row=0)
    async def edit_author(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            AuthorModal(_embed=self.embed, parent_view=self)
        )

    @discord.ui.button(label="Footer", style=discord.ButtonStyle.primary, row=0)
    async def edit_footer(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            FooterModal(_embed=self.embed, parent_view=self)
        )

    @discord.ui.button(label="URL", style=discord.ButtonStyle.primary, row=0)
    async def edit_url(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            URLModal(_embed=self.embed, parent_view=self)
        )

    @discord.ui.button(
        label="Fields:", style=discord.ButtonStyle.gray, disabled=True, row=1
    )
    async def _fields_tag(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()

    @discord.ui.button(
        emoji="➕", style=discord.ButtonStyle.green, row=1
    )
    async def add_field(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if len(self.embed.fields) == 25:
            await interaction.response.send_message(
                f" - Embed reached maximum of 25 fields.",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(
            AddFieldModal(_embed=self.embed, parent_view=self)
        )

    @discord.ui.button(
        emoji="➖", style=discord.ButtonStyle.red, row=1
    )
    async def delete_field(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if len(self.embed.fields) == 0:
            return await interaction.response.send_message(
                f" - There are no fields to delete.", ephemeral=True
            )
        view = BaseView(timeout=180, target=interaction)
        view.add_item(
            DeleteFieldDropdown(
                _embed=self.embed, original_msg=interaction.message, parent_view=self
            ),
        )
        await interaction.response.send_message(
            f"➖ - Choose a field to delete:",
            view=view,
            ephemeral=True,
        )

    @discord.ui.button(
        emoji="✏️", style=discord.ButtonStyle.primary, row=1
    )
    async def edit_field(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if len(self.embed.fields) == 0:
            return await interaction.response.send_message(
                f" - There are no fields to edit.", ephemeral=True
            )

        view = BaseView(timeout=180, target=interaction)
        view.add_item(
            EditFieldDropdown(
                _embed=self.embed,
                parent_view=self,
                original_msg=interaction.message,
            ),
        )
        await interaction.response.send_message(
            f"✏️ - Choose a field to edit:",
            view=view,
            ephemeral=True,
        )


    @discord.ui.button(label="Help", style=discord.ButtonStyle.gray, row=3)
    async def help_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        em1 = Embed.generate_help_embed()
        em2 = discord.Embed(
            color=CONTRAST_COLOR,
        )
        em2.add_field(
            name="Fields",
            inline=False,
            value=f"➕ Add a Field\n"
            f"➖ Delete a Field\n"
            f"✏️ Edit a field (or reorder)",
        )
        em2.add_field(
            name="JSON",
            inline=False,
            value=f"**Export JSON**: Export the embed to discord-valid JSON format.\n"
            f"**Import JSON**: Import the embed from discord-valid JSON format.",
        )
        em2.add_field(
            name="Done",
            inline=False,
            value="Finalize the embed and continue with the welcome/goodbye message setup process."
        )
        await interaction.response.send_message(embeds=[em1, em2], ephemeral=True)


    @discord.ui.button(label="Import JSON", style=discord.ButtonStyle.gray, row=3)
    async def import_json(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            ImportJSONModal(_embed=self.embed, parent_view=self)
        )

    @discord.ui.button(emoji="❌", style=discord.ButtonStyle.red, row=3)
    async def cancel_btn(
        self, interaction: discord.Interaction, button: discord.Button
    ):
        await interaction.response.defer()
        await self.stop(interaction)

    @discord.ui.button(
        label="0/6000 Characters",
        disabled=True,
        style=discord.ButtonStyle.gray,
        row=4,
    )
    async def character_counter(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()

    @discord.ui.button(
        label="0/25 Fields",
        disabled=True,
        style=discord.ButtonStyle.gray,
        row=4,
    )
    async def field_counter(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()
        
    @discord.ui.button(label="Done", style=discord.ButtonStyle.primary, row=4)
    async def done_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if len(self.embed) == 0:
            return await interaction.response.send_message(
                f" - Embed is empty!", ephemeral=True
            )
        else:
        
            json_cont = json.dumps(self.embed.to_dict(), indent=4)
            
            document = await afk_embed_collection.find_one({"member_id": str(interaction.user.id)})

            new_value = {"$set": {"message": json_cont}}
            
            
            await afk_embed_collection.update_one(document, new_value)
            
            embed = discord.Embed(description=f"Afk response embed has been set!",
                                    color=discord.Color.green())
            
            await interaction.message.reply(embed=embed)
    
        embed = discord.Embed(title=f" message setup menu", description="chan messo.")       
        
    
class EmbedBuilderView(BaseView):
    def __init__(self, *, timeout: int, target: discord.Interaction):
        self.bot = target.client
        super().__init__(timeout=timeout, target=target)

        self.embed = discord.Embed()

    def update_counters(self):
        self.character_counter.label = f"{len(self.embed)}/6000 Characters"
        self.field_counter.label = f"{len(self.embed.fields)}/25 Fields"

    @discord.ui.button(
        label="Edit:", style=discord.ButtonStyle.gray, disabled=True, row=0
    )
    async def _basic_tag(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()

    @discord.ui.button(label="Embed", style=discord.ButtonStyle.primary, row=0)
    async def edit_embed(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            EmbedModal(_embed=self.embed, parent_view=self)
        )

    @discord.ui.button(label="Author", style=discord.ButtonStyle.primary, row=0)
    async def edit_author(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            AuthorModal(_embed=self.embed, parent_view=self)
        )

    @discord.ui.button(label="Footer", style=discord.ButtonStyle.primary, row=0)
    async def edit_footer(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            FooterModal(_embed=self.embed, parent_view=self)
        )

    @discord.ui.button(label="URL", style=discord.ButtonStyle.primary, row=0)
    async def edit_url(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            URLModal(_embed=self.embed, parent_view=self)
        )

    @discord.ui.button(
        label="Fields:", style=discord.ButtonStyle.gray, disabled=True, row=1
    )
    async def _fields_tag(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()

    @discord.ui.button(
        emoji="➕", style=discord.ButtonStyle.green, row=1
    )
    async def add_field(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if len(self.embed.fields) == 25:
            await interaction.response.send_message(
                f" - Embed reached maximum of 25 fields.",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(
            AddFieldModal(_embed=self.embed, parent_view=self)
        )

    @discord.ui.button(
        emoji="➖", style=discord.ButtonStyle.red, row=1
    )
    async def delete_field(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if len(self.embed.fields) == 0:
            return await interaction.response.send_message(
                f" - There are no fields to delete.", ephemeral=True
            )
        view = BaseView(timeout=180, target=interaction)
        view.add_item(
            DeleteFieldDropdown(
                _embed=self.embed, original_msg=interaction.message, parent_view=self
            ),
        )
        await interaction.response.send_message(
            f"➖ - Choose a field to delete:",
            view=view,
            ephemeral=True,
        )

    @discord.ui.button(
        emoji="✏️", style=discord.ButtonStyle.primary, row=1
    )
    async def edit_field(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if len(self.embed.fields) == 0:
            return await interaction.response.send_message(
                f" - There are no fields to edit.", ephemeral=True
            )

        view = BaseView(timeout=180, target=interaction)
        view.add_item(
            EditFieldDropdown(
                _embed=self.embed,
                parent_view=self,
                original_msg=interaction.message,
            ),
        )
        await interaction.response.send_message(
            f"✏️ - Choose a field to edit:",
            view=view,
            ephemeral=True,
        )

    @discord.ui.button(
        label="Send:", style=discord.ButtonStyle.gray, disabled=True, row=2
    )
    async def send_tag(self, interaction: discord.Interaction, button: discord.Button):
        await interaction.response.defer()

    @discord.ui.button(label="To Channel", style=discord.ButtonStyle.green, row=2)
    async def send_to_channel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if len(self.embed) == 0:
            return await interaction.response.send_message(
                f" - Embed is empty!", ephemeral=True
            )

        view = BaseView(timeout=180, target=interaction)
        view.add_item(SendToChannelSelect(_embed=self.embed, bot=self.bot))
        await interaction.response.send_message(
            f"📝 - Choose a channel to send the embed to:",
            view=view,
            ephemeral=True,
        )

    @discord.ui.button(label="Via Webhook", style=discord.ButtonStyle.green, row=2)
    async def send_via_webhook(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if len(self.embed) == 0:
            return await interaction.response.send_message(
                f" - Embed is empty!", ephemeral=True
            )

        await interaction.response.send_modal(SendViaWebhookModal(_embed=self.embed))

    @discord.ui.button(label="To DM", style=discord.ButtonStyle.green, row=2)
    async def send_to_dm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if len(self.embed) == 0:
            return await interaction.response.send_message(
                f" - Embed is empty!", ephemeral=True
            )
        try:
            msg = await interaction.user.send(embed=self.embed)
            jump_view = discord.ui.View().add_item(message_jump_button(msg.jump_url))
            await interaction.response.send_message(
                f" - Embed sent to DM.",
                ephemeral=True,
                view=jump_view,
            )
        except discord.HTTPException:
            await interaction.response.send_message(
                f" - Couldn't send the embed to you via DM.",
                ephemeral=True,
            )

    @discord.ui.button(label="Help", style=discord.ButtonStyle.gray, row=3)
    async def help_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        em1 = Embed.generate_help_embed()
        em2 = discord.Embed(
            color=CONTRAST_COLOR,
        )
        em2.add_field(
            name="Fields",
            inline=False,
            value=f"➕ Add a Field\n"
            f"➖ Delete a Field\n"
            f"✏️ Edit a field (or reorder)",
        )
        em2.add_field(
            name="JSON",
            inline=False,
            value=f"**Export JSON**: Export the embed to discord-valid JSON format.\n"
            f"**Import JSON**: Import the embed from discord-valid JSON format.",
        )
        await interaction.response.send_message(embeds=[em1, em2], ephemeral=True)

    @discord.ui.button(label="Export JSON", style=discord.ButtonStyle.gray, row=3)
    async def export_json(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if len(self.embed) == 0:
            return await interaction.response.send_message(
                f" - Embed is empty!", ephemeral=True
            )
        json_cont = json.dumps(self.embed.to_dict(), indent=4)
        stream = BytesIO(json_cont.encode())

        file = discord.File(fp=stream, filename="embed.json")
        await interaction.response.send_message(
            content="Here's your Embed as a JSON file:", file=file, ephemeral=True
        )

    @discord.ui.button(label="Import JSON", style=discord.ButtonStyle.gray, row=3)
    async def import_json(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            ImportJSONModal(_embed=self.embed, parent_view=self)
        )

    @discord.ui.button(emoji="❌", style=discord.ButtonStyle.red, row=3)
    async def cancel_btn(
        self, interaction: discord.Interaction, button: discord.Button
    ):
        await interaction.response.defer()
        await self.stop(interaction)

    @discord.ui.button(
        label="0/6000 Characters",
        disabled=True,
        style=discord.ButtonStyle.gray,
        row=4,
    )
    async def character_counter(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()

    @discord.ui.button(
        label="0/25 Fields",
        disabled=True,
        style=discord.ButtonStyle.gray,
        row=4,
    )
    async def field_counter(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()


class Embed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def generate_help_embed() -> discord.Embed:
        emb = discord.Embed(
            title="Title",
            url="http://cosmo-bot.com",
            description="This is the _description_ of the embed.\n"
            "Descriptions can be upto **4000** characters long.\n"
            "There is a shared limit of **6000** characters (including fields) for the embed.\n"
            "Note that the description can be __split into multiple lines.__\n",
            color=CONTRAST_COLOR,
        )
        emb.set_author(
            name="<< Author Icon | Author Name",
            url="http://cosmo-bot.com",
            icon_url="https://i.imgur.com/pDzKwWY.png",
        )
        emb.set_footer(
            text="<< Footer Icon | This is the footer",
            icon_url="https://i.imgur.com/Ee7JnsT.png",
        )
        for i in range(1, 3):
            emb.add_field(
                name=f"Field {i}", value=f"Field {i} Value\nIt's Inline", inline=True
            )
        emb.add_field(
            name=f"Field 3", value=f"Field 3 Value\nIt's NOT Inline", inline=False
        )
        emb.set_image(url="https://i.imgur.com/yUDkRSQ.png")
        emb.set_thumbnail(url="https://i.imgur.com/piQAdNP.png")

        return emb
    
    group = app_commands.Group(name="embed", description="Embed builder")

    @group.command(name="create", description="Create an embed, using the embed builder.")
    async def embed_builder(
        self,
        interaction: discord.Interaction,
    ):
        
        await interaction.response.send_message(
            embed=self.generate_help_embed(),
            view=EmbedBuilderView(timeout=600, target=interaction),
        )


async def setup(bot: discord.Client):
    await bot.add_cog(Embed(bot))