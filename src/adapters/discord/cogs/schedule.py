
from __future__ import annotations

import os
import logging
import datetime
import discord
from discord.ext import commands

# (!) Эти импорты должны существовать. Ниже дам заглушки, если их нет.
from src.core.url_store import set_user_url, load_urls
from src.core.storage import get_user_schedule_file
from src.core.parser import download_schedule
from src.core.services.schedule_service import get_schedule_data_for_day  # переместил под src/core/services

log = logging.getLogger("discord.schedule")


class ScheduleButtons(discord.ui.View):
    def __init__(self, user_id: int, current_date: datetime.date):
        super().__init__(timeout=None)  # можно сделать timeout=60, если не нужна persistent view
        self.user_id = user_id
        self.current_date = current_date

    @discord.ui.button(label="← Вчера", style=discord.ButtonStyle.secondary)
    async def prev_day(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Проверка, что нажимает владелец панели
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Эта панель не для вас.", ephemeral=True)
            return

        new_date = self.current_date - datetime.timedelta(days=1)
        schedule = await get_schedule_data_for_day(new_date, self.user_id)

        await interaction.response.edit_message(
            content=f"**{new_date.isoformat()}**\n\n{schedule}",
            view=ScheduleButtons(self.user_id, new_date),
        )

    @discord.ui.button(label="Сегодня", style=discord.ButtonStyle.primary)
    async def today(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Эта панель не для вас.", ephemeral=True)
            return

        new_date = datetime.date.today()
        schedule = await get_schedule_data_for_day(new_date, self.user_id)

        await interaction.response.edit_message(
            content=f"**{new_date.isoformat()}**\n\n{schedule}",
            view=ScheduleButtons(self.user_id, new_date),
        )

    @discord.ui.button(label="Завтра →", style=discord.ButtonStyle.secondary)
    async def next_day(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Эта панель не для вас.", ephemeral=True)
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
        self.waiting_for_url: dict[int, bool] = {}  # перенесли из глобальной переменной

    @commands.command()
    async def start(self, ctx: commands.Context):
        await ctx.send(
            "Привет! Я бот расписания.\n"
            "Команды:\n"
            "`!today` — расписание на сегодня\n"
            "`!tomorrow` — на завтра\n"
            "`!seturl <url>` — сохранить ссылку\n"
            "`!update` — скачать расписание по сохранённой ссылке\n"
            "`!upload` — загрузить .csv вручную\n"
        )

    @commands.command(name="seturl")
    async def seturl(self, ctx: commands.Context, url: str):
        # простая валидация
        if not url.startswith(("http://", "https://")):
            await ctx.send("❗ Укажи корректный URL, например: https://example.com/schedule.csv")
            return

        set_user_url(ctx.author.id, url)
        await ctx.send("Ссылка сохранена. Используйте `!update`.")

    @commands.command(name="update")
    async def update_schedule(self, ctx: commands.Context):
        user_id = ctx.author.id
        links = load_urls()

        if str(user_id) in links:
            url = links[str(user_id)]
            file_path = get_user_schedule_file(user_id)

            msg = await ctx.send("⏳ Обновляю расписание...")

            try:
                if os.path.exists(file_path):
                    os.remove(file_path)

                # Ожидаем, что download_schedule — async (иначе убрать await)
                await download_schedule(url, file_path)

                await msg.edit(content="✅ Расписание обновлено.")
            except Exception as e:
                await msg.edit(content=f"❌ Ошибка:\n{e}")
            return

        # если ссылки нет — запросим у пользователя
        self.waiting_for_url[user_id] = True
        await ctx.send("Вставьте ссылку на расписание в следующем сообщении.")

    @commands.command(name="upload")
    async def upload(self, ctx: commands.Context):
        self.waiting_for_file[ctx.author.id] = True
        await ctx.send("Отправьте CSV-файл одним сообщением.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        user_id = message.author.id
        content = (message.content or "").strip()

        # Обработка ссылки, если ждём её
        if self.waiting_for_url.get(user_id):
            file_path = get_user_schedule_file(user_id)
            url = content

            msg = await message.channel.send("⏳ Загружаю расписание...")

            try:
                set_user_url(user_id, url)

                if os.path.exists(file_path):
                    os.remove(file_path)

                await download_schedule(url, file_path)

                await msg.edit(content="✅ Расписание обновлено.")
            except Exception as e:
                await msg.edit(content=f"❌ Ошибка:\n{e}")

            self.waiting_for_url[user_id] = False
            # не возвращаемся сразу, позволяем командам обработаться
            # но безопаснее всё же return после update
            # return

        # Обработка ожидаемого файла
        if self.waiting_for_file.get(user_id) and message.attachments:
            attachment = message.attachments[0]
            filename = (attachment.filename or "").lower()

            if not filename.endswith(".csv"):
                await message.channel.send("❗ Отправьте файл .csv")
            else:
                try:
                    file_bytes = await attachment.read()
                    # можно добавить ограничение размера
                    if len(file_bytes) > 5 * 1024 * 1024:
                        await message.channel.send("❗ Файл слишком большой (>5MB).")
                    else:
                        save_path = get_user_schedule_file(user_id)

                        if os.path.exists(save_path):
                            os.remove(save_path)

                        with open(save_path, "wb") as f:
                            f.write(file_bytes)

                        await message.channel.send("✅ Файл расписания обновлён!")
                except Exception as e:
                    await message.channel.send(f"❌ Ошибка:\n{e}")

            self.waiting_for_file[user_id] = False
            # return

        # Автоматическая загрузка одиночного CSV (без режима ожидания)
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

                    await message.channel.send("✅ Файл расписания загружен.")
                except Exception as e:
                    await message.channel.send(f"❌ Ошибка:\n{e}")
                # return

        # ВАЖНО: чтобы команды с префиксом продолжали работать
        await self.bot.process_commands(message)

    @commands.command()
    async def today(self, ctx: commands.Context):
        user_id = ctx.author.id
        today = datetime.date.today()
        text = await get_schedule_data_for_day(today, user_id)
        # Кнопки
        await ctx.send(f"**{today.isoformat()}**\n\n{text}", view=ScheduleButtons(user_id, today))

    @commands.command()
    async def tomorrow(self, ctx: commands.Context):
        user_id = ctx.author.id
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        text = await get_schedule_data_for_day(tomorrow, user_id)
        await ctx.send(f"**{tomorrow.isoformat()}**\n\n{text}", view=ScheduleButtons(user_id, tomorrow))


async def setup(bot: commands.Bot):
    await bot.add_cog(ScheduleCog(bot))
