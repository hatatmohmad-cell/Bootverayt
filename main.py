import asyncio
import re
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import stealth_async

# التوكن الخاص بك تم وضعه هنا
BOT_TOKEN = "8936209936:AAFSqTluMwpqogS3OYY8G7a9Qs-AEHm_qqE"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

VLESS_UUID = "110cc6a9-ab28-4cdf-99d7-e962c639b2d4"
DOCKER_IMAGE = "docker.io/mohmghjuy/gcp-v2ray:latest"
VLESS_PATH = "%2F%40dososdrido464-vless"
SNI = "youtube.com"

@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer("👋 أهلاً بك!\nأرسل رابط Google SSO للبدء في نشر الخدمة عبر المتصفح المخفي (Stealth).")

@dp.message()
async def handle_sso_link(message: Message):
    url = message.text
    
    if "skills.google" not in url and "google.com" not in url:
        await message.answer("⚠️ يرجى إرسال رابط SSO صالح.")
        return

    status_msg = await message.answer("✅ تم استلام الرابط. جاري التنفيذ الآن...\n\n[1] ⏳ تجهيز المتصفح القوي (Stealth)...")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-infobars'
                ]
            )
            
            context = await browser.new_context(
                viewport={'width': 1366, 'height': 768},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = await context.new_page()
            await stealth_async(page)
            page.set_default_timeout(180000) 

            await page.goto(url)
            await status_msg.edit_text(f"{status_msg.text}\n[2] ⏳ انتظار تسجيل الدخول (10 ثوانٍ)...")
            await page.wait_for_timeout(10000)
            
            await status_msg.edit_text(f"{status_msg.text}\n[3] ⏳ التوجه لصفحة Cloud Run...")
            await page.goto("https://console.cloud.google.com/run/create")
            await page.wait_for_load_state("networkidle")
            
            await page.wait_for_selector("input[placeholder*='gcr.io/']", timeout=120000)
            
            await status_msg.edit_text(f"{status_msg.text}\n[4] ✅ فتح Cloud Run\n[5] ⏳ تعبئة الإعدادات (Image, Public Access)...")

            await page.locator("input[placeholder*='gcr.io/']").fill(DOCKER_IMAGE)
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(2000)

            await page.get_by_text("Allow public access", exact=False).click()
            
            await status_msg.edit_text(f"{status_msg.text}\n[6] ✅ تعبئة الموارد (Memory, CPU, Timeout)...")

            expand_button = page.get_by_text("Container(s), Volumes, Networking, Security")
            if await expand_button.is_visible():
                await expand_button.click()
            else:
                await page.locator("button:has-text('Container')").first.click()
            
            await page.wait_for_timeout(1500)

            await page.locator('mat-select[aria-label*="Memory"]').click()
            await page.get_by_text("2 GiB", exact=True).click()
            
            timeout_input = page.locator('input[aria-label*="Request timeout"]')
            await timeout_input.fill("3600")

            concurrency_input = page.locator('input[aria-label*="Maximum concurrent requests"]')
            await concurrency_input.fill("1000")

            await page.get_by_text("Second generation", exact=False).click()

            min_instances = page.locator('input[aria-label*="Minimum number of instances"]')
            await min_instances.fill("0")
            max_instances = page.locator('input[aria-label*="Maximum number of instances"]')
            await max_instances.fill("10")

            await status_msg.edit_text(f"{status_msg.text}\n[7] ✅ الإعدادات جاهزة. ⏳ جاري النقر على Create...")

            await page.get_by_role("button", name=re.compile(r"^Create$", re.IGNORECASE)).first.click()

            await status_msg.edit_text(f"{status_msg.text}\n[8] ⏳ جاري النشر (قد يستغرق 3 دقائق)...")

            await page.wait_for_selector("a[href*='.run.app']", timeout=240000) 
            
            element = await page.query_selector("a[href*='.run.app']")
            final_url = await element.get_attribute("href")
            host = final_url.replace("https://", "").replace("/", "")

            vless_config = (
                f"vless://{VLESS_UUID}@{host}:443"
                f"?security=tls&encryption=none&type=ws&host={host}"
                f"&path={VLESS_PATH}&sni={SNI}#VLESS-WS-US"
            )

            final_message = (
                f"🎉 **تم النشر بنجاح!**\n\n"
                f"🔗 **الرابط:**\n{final_url}\n\n"
                f"📄 **VLESS:**\n`{vless_config}`"
            )
            
            await status_msg.edit_text(final_message, parse_mode="Markdown")
            await browser.close()

    except PlaywrightTimeoutError:
        await page.screenshot(path="error_screenshot.png")
        error_photo = FSInputFile("error_screenshot.png")
        await message.answer_photo(error_photo, caption="❌ توقف المتصفح (Timeout). هذه صورة توضح أين توقف المتصفح:")
        await status_msg.edit_text("❌ حدث خطأ: انتهت مهلة الانتظار ولم يكتمل التحميل.")
        if 'browser' in locals(): await browser.close()
        
    except Exception as e:
        await status_msg.edit_text(f"❌ حدث خطأ غير متوقع:\n`{str(e)}`", parse_mode="Markdown")
        if 'browser' in locals(): await browser.close()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
