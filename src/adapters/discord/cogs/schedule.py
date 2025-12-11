from __future__ import annotations

import os
import logging
import datetime
import discord
from discord.ext import commands

from src.core.url_store import set_user_url, load_urls
from src.core.storage import get_user_schedule_file
from src.core.parser import download_schedule
from src.core.services.schedule_service import get_schedule_data_for_day  # переместил под src/core/services

log = logging.getLogger("discord.schedule")


class ScheduleButtons(discord.ui.View):
    def __init__(self, user_id: int, current_date: datetime.date):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.current_date = current_date

    @discord.ui.button(label="← Wczoraj", style=discord.ButtonStyle.secondary)
    async def prev_day(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Ta panel nie jest dla ciebie.", ephemeral=True)
            return

        new_date = self.current_date - datetime.timedelta(days=1)
        schedule = await get_schedule_data_for_day(new_date, self.user_id)

        await interaction.response.edit_message(
            content=f"**{new_date.isoformat()}**\n\n{schedule}",
            view=ScheduleButtons(self.user_id, new_date),
        )

    @discord.ui.button(label="Dzisiaj", style=discord.ButtonStyle.primary)
    async def today(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Ta panel nie jest dla ciebie.", ephemeral=True)
            return

        new_date = datetime.date.today()
        schedule = await get_schedule_data_for_day(new_date, self.user_id)

        await interaction.response.edit_message(
            content=f"**{new_date.isoformat()}**\n\n{schedule}",
            view=ScheduleButtons(self.user_id, new_date),
        )

    @discord.ui.button(label="Jutro →", style=discord.ButtonStyle.secondary)
    async def next_day(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Ta panel nie jest dla ciebie.", ephemeral=True)
            return

        new_date = self.current_date + datetime.timedelta(days=1)
        schedule = await get_schedule_data_for_day(new_date, self.user_id)

        await interaction.response.edit_message(
            content=f"**{new_date.isoformat()}**\n\n{schedule}",
            view=ScheduleButtons(self.user_id, new_date),
        )


class ScheduleCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.waiting_for_file: dict[int, bool] = {}
        self.waiting_for_url: dict[int, bool] = {}

    @commands.command()
    async def start(self, ctx: commands.Context):
        await ctx.send(
            "Cześć! Jestem botem z planem zajęć.\n"
            "Polecenia:\n"
            "`!today` — plan na dziś\n"
            "`!tomorrow` — plan na jutro\n"
            "`!seturl <url>` — zapisz link\n"
            "`!update` — pobierz plan z zapisanego linku\n"
            "`!upload` — prześlij ręcznie plik .csv\n"
        )

    @commands.command()
    async def seturl(self, ctx: commands.Context, url: str):
        if not url.startswith(("http://", "https://")):
            await ctx.send("❗ Podaj poprawny adres URL, np. https://example.com/schedule.csv")
            return

        set_user_url(ctx.author.id, url)
        await ctx.send("Link zapisany. Użyj `!update` aby pobrać plan.")

    @commands.command()
    async def update(self, ctx: commands.Context):
        user_id = ctx.author.id
        links = load_urls()

        if str(user_id) in links:
            url = links[str(user_id)]
            file_path = get_user_schedule_file(user_id)

            msg = await ctx.send("⏳ Aktualizuję plan zajęć...")

            try:
                if os.path.exists(file_path):
                    os.remove(file_path)

                await download_schedule(url, file_path)

                await msg.edit(content="✅ Plan zaktualizowany.")
            except Exception as e:
                await msg.edit(content=f"❌ Błąd:\n{e}")
            return

        self.waiting_for_url[user_id] = True
        await ctx.send("Wklej link do planu zajęć w następnym wiadomości.")

    @commands.command()
    async def upload(self, ctx: commands.Context):
        self.waiting_for_file[ctx.author.id] = True
        await ctx.send("Prześlij plik CSV w jednej wiadomości.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        user_id = message.author.id
        content = (message.content or "").strip()

        if self.waiting_for_url.get(user_id):
            file_path = get_user_schedule_file(user_id)
            url = content

            msg = await message.channel.send("⏳ Pobieram plan zajęć...")

            try:
                set_user_url(user_id, url)

                if os.path.exists(file_path):
                    os.remove(file_path)

                await download_schedule(url, file_path)

                await msg.edit(content="✅ Plan zaktualizowany.")
            except Exception as e:
                await msg.edit(content=f"❌ Błąd:\n{e}")

            self.waiting_for_url[user_id] = False

        if self.waiting_for_file.get(user_id) and message.attachments:
            attachment = message.attachments[0]
            filename = (attachment.filename or "").lower()

            if not filename.endswith(".csv"):
                await message.channel.send("❗ Wyślij plik .csv")
            else:
                try:
                    file_bytes = await attachment.read()

                    if len(file_bytes) > 5 * 1024 * 1024:
                        await message.channel.send("❗ Plik jest za duży (>5MB).")
                    else:
                        save_path = get_user_schedule_file(user_id)

                        if os.path.exists(save_path):
                            os.remove(save_path)

                        with open(save_path, "wb") as f:
                            f.write(file_bytes)

                        await message.channel.send("✅ Plik z planem zaktualizowany!")
                except Exception as e:
                    await message.channel.send(f"❌ Błąd:\n{e}")

            self.waiting_for_file[user_id] = False

        if message.attachments and not self.waiting_for_file.get(user_id):
            attachment = message.attachments[0]
            filename = (attachment.filename or "").lower()

            if filename.endswith(".csv"):
                try:
                    file_bytes = await attachment.read()
                    save_path = get_user_schedule_file(user_id)

                    if os.path.exists(save_path):
                        os.remove(save_path)

                    with open(save_path, "wb") as f:
                        f.write(file_bytes)

                    await message.channel.send("✅ Plik z planem przesłany.")
                except Exception as e:
                    await message.channel.send(f"❌ Błąd:\n{e}")

        await self.bot.process_commands(message)

    @commands.command()
    async def today(self, ctx: commands.Context):
        user_id = ctx.author.id
        today = datetime.date.today()
        text = await get_schedule_data_for_day(today, user_id)

        await ctx.send(f"**{today.isoformat()}**\n\n{text}", view=ScheduleButtons(user_id, today))

    @commands.command()
    async def tomorrow(self, ctx: commands.Context):
        user_id = ctx.author.id
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        text = await get_schedule_data_for_day(tomorrow, user_id)
        await ctx.send(f"**{tomorrow.isoformat()}**\n\n{text}", view=ScheduleButtons(user_id, tomorrow))


async def setup(bot: commands.Bot):
    await bot.add_cog(ScheduleCog(bot))
