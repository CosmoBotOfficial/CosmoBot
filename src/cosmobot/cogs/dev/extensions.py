import discord

from discord.ext import commands
from discord.ui import Button, View

from math import ceil

class ButtonView(discord.ui.View):

    """
    A View that creates a single button with a specified label, style, and callback.

    Parameters:
    label (str): The text to display on the button. Defaults to "Text".
    style (discord.ButtonStyle): The style of the button (e.g., ButtonStyle.blurple, ButtonStyle.green, etc.). Defaults to ButtonStyle.green.
    reply (str or None): The default reply message when the button is clicked. Defaults to None.
    callback (coroutine function or None): The coroutine function to call when the button is clicked. Defaults to None.

    Example:
        # Define a custom callback function
        async def custom_callback(interaction: discord.Interaction):
            await interaction.response.send_message("Custom callback executed!")

        # Create a ButtonView instance
        view = ButtonView(label="Click me!", style=discord.ButtonStyle.blurple, reply="Button clicked!", callback=custom_callback)

        # Send a message with the view
        await ctx.send("Here is a button", view=view)
    """

    def __init__(self, label="Button", style=discord.ButtonStyle.green, reply=None, callback=None):

        super().__init__()

        self._label = label
        self._style = style
        self._reply = reply
        self._callback = callback


        button = discord.ui.Button(label=self._label, style=self._style)

        if self._callback:

            button.callback = self._callback

        else:

            button.callback = self.default_callback

        self.add_item(button)

    def wrap_callback(self, callback):

        async def wrapped(interaction: discord.Interaction):

            await callback(interaction)

        return wrapped

    async def default_callback(self, interaction: discord.Interaction):

        await interaction.response.send_message(self._reply if self._reply else self._label)

class MultiButtonView(discord.ui.View):

    """
    A View that dynamically creates buttons with specified labels, styles, and callbacks.

    Parameters:
    buttons (list of tuples): A list of tuples where each tuple contains:
        - label (str): The text to display on the button.
        - style (discord.ButtonStyle): The style of the button (e.g., ButtonStyle.blurple, ButtonStyle.green, etc.).
        - callback (coroutine function or None): The coroutine function to call when the button is clicked.
    
    Example:
        # Define callback functions
        async def custom_callback1(interaction: discord.Interaction):
            await interaction.response.send_message("Custom callback 1 executed!")

        async def custom_callback2(interaction: discord.Interaction):
            await interaction.response.send_message("Custom callback 2 executed!")

        # Create button configurations
        buttons = [
            ("Button 1", discord.ButtonStyle.blurple, custom_callback1),
            ("Button 2", discord.ButtonStyle.green, custom_callback2),
            ("Default Button", discord.ButtonStyle.red, None)
        ]

        # Create a ButtonView instance
        view = ButtonView(buttons)

        # Send a message with the view
        await ctx.send("Here are some buttons", view=view)
    """

    def __init__(self, buttons):

        super().__init__()

        self.buttons = buttons

        for i, button_config in enumerate(self.buttons):

            label, style, callback = button_config

            button = Button(label=label, style=style, custom_id=f"button_{i}")
            button.callback = self.create_callback(callback, label)

            self.add_item(button)

    def create_callback(self, callback, label):

        async def wrapper(interaction: discord.Interaction):

            if callback:

                await callback(interaction)

            else:

                await interaction.response.send_message(label)
                
        return wrapper
    
class PaginationEmbed(discord.ui.View):

    """
    Initialize a PaginationEmbed view.

    Parameters:
    - current_page (int): The initial page number to display.
    - separtion (int): The number of items to display per page.
    - timeout (float or None, optional): The time (in seconds) after which the view will timeout. 
        If set to None, the view will not timeout. Defaults to 180 seconds.

    Attributes:
    - current_page (int): Stores the current page number.
    - sep (int): Stores the number of items per page.
    - timeout (float or None): The timeout duration for the view.

    Calls the parent class's (discord.ui.View) initializer with the specified timeout.
    """

    def __init__(self, current_page, separtion, timeout: float | None = 180):

        self.current_page = current_page
        self.sep = separtion

        super().__init__(timeout=timeout)

    async def send(self, ctx):
        await ctx.followup.send(embed=self.create_embed(self.get_current_page_data()), view=self)
        self.message = await ctx.original_response()

    def create_embed(self, data):
        embed = discord.Embed(title=f"{self.current_page} / {ceil(len(self.data) / self.sep)}")
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
