import asyncio
from playwright.async_api import async_playwright
import logging
from playwright_stealth import stealth_async


async def download_schedule(url: str, save_path: str) -> str:
    logging.info("▶ Старт скачивания расписания")

    chromium_args = [
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-gpu",
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
        "--disable-blink-features=AutomationControlled",
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=chromium_args
        )

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            java_script_enabled=True,
        )

        page = await context.new_page()
        await stealth_async(page)

        # --- Загружаем страницу ---
        logging.info("Открываем страницу...")
        try:
            await page.goto(url, wait_until="load", timeout=120000)
        except Exception:
            await page.screenshot(path="debug_goto_failed.png")
            raise Exception("❌ Сайт не загрузился — вероятная блокировка серверного IP")

        # --- Проверяем, что HTML не пустой ---
        html = await page.content()
        if len(html) < 50000:
            await page.screenshot(path="debug_empty_html.png")
            raise Exception("❌ Страница загрузилась частично — сайт блокирует headless браузер")

        # --- Cookies ---
        try:
            await page.locator("button:has-text('Zezwól')").click(timeout=3000)
            logging.info("Cookies приняты")
        except:
            logging.info("Cookies нет")

        # --- Фильтр: Cały semestr ---
        try:
            labels = page.locator("label.custom-control-label")
            count = await labels.count()

            for i in range(count):
                text = (await labels.nth(i).inner_text()).strip()
                if text == "Cały semestr":
                    await labels.nth(i).click()
                    logging.info("Выбран фильтр Cały semestr")
                    break
        except Exception as e:
            logging.error(f"Ошибка выбора фильтра: {e}")

        # --- Кнопка Szukaj ---
        html_before = len(await page.content())
        
        try:
            button = page.locator("#SzukajLogout")
            await button.wait_for(state="visible", timeout=90000)

            try:
                await button.click()
            except:
                await button.evaluate("el => el.click()")

            logging.info("Нажата кнопка Szukaj")

            await asyncio.sleep(22)
            
        except Exception as e:
            await page.screenshot(path="debug_szukaj.png")
            raise Exception(f"❌ Ошибка клика Szukaj: {e}")

        # ============================================================
        # 🔥 Новый блок: ждём, пока таблица ОБНОВИТСЯ после фильтра
        # ============================================================
        
        loaded = False
        
        for i in range(30):  # максимум 30 секунд
            await asyncio.sleep(1)
            html_now = len(await page.content())
            logging.info(f"html before = {html_before} and html now = {html_now}")
        
            if html_now > html_before:
                loaded = True
                logging.info("Таблица загружена полностью")
                break
        
        if not loaded:
            logging.warning("Таблица могла не успеть обновиться. Все равно продолжаем.")

        # ============================================================

        # --- Скачивание CSV ---
        try:
            link = page.locator("a[href*='WydrukTokuCsv']")
            await link.wait_for(state="visible", timeout=120000)

            async with page.expect_download(timeout=180000) as dl:
                try:
                    await link.click()
                except:
                    await link.evaluate("el => el.click()")

            download = await dl.value
            await download.save_as(save_path)

            logging.info("CSV скачан УСПЕШНО")
        except Exception as e:
            await page.screenshot(path="debug_download.png")
            raise Exception(f"❌ Ошибка скачивания CSV: {e}")

        await browser.close()
        return save_path
