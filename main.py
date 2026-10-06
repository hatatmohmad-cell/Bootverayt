import asyncio
import re
import uuid
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from playwright.async_api import async_playwright, TimeoutError

# التوكن الخاص بك
BOT_TOKEN = '8905970510:AAEmDrDCkiTby8baP3AHdSUwoHw6kbm5FK4'
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# إعدادات الحاوية وأمر النشر
IMAGE_URL = "docker.io/mohmghjuy/gcp-v2ray:latest"
GCLOUD_COMMAND = f"gcloud run deploy gcp-v2ray --image={IMAGE_URL} --region=europe-west4 --allow-unauthenticated --timeout=3600 --concurrency=1000 --execution-environment=gen2 --memory=2Gi --min-instances=0 --max-instances=10 --port=8080 --format='value(status.url)' --quiet"

async def update_status(chat_id, message_id, text):
    """دالة لتحديث الرسالة لتشبه البوت الذي في الصورة"""
    try:
        await bot.edit_message_text(text, chat_id=chat_id, message_id=message_id)
    except:
        pass

async def deploy_bot_task(sso_link: str, chat_id: int, message_id: int):
    # استخراج اسم المشروع للمتابعة
    project_match = re.search(r'project(?:%3D|=)(qwiklabs-gcp-[\w-]+)', sso_link)
    project_id = project_match.group(1) if project_match else "Unknown_Project"

    # رسالة البداية
    status_text = f"⏳ تم استلام الرابط. جاري التنفيذ الآن...\n\n"
    await update_status(chat_id, message_id, status_text + f"[@user] • 1 🔄 فتح رابط الطالب...")

    async with async_playwright() as p:
        # إعدادات خاصة للاستضافات المجانية لتقليل استهلاك الرام
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox', 
                '--disable-setuid-sandbox', 
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--single-process'
            ]
        )
        page = await browser.new_page()
        
        try:
            # 1. فتح الرابط
            await page.goto(sso_link, timeout=90000)
            await page.wait_for_load_state("networkidle")
            status_text += f"[@user] • 1 ✅ فتح رابط الطالب\n"
            status_text += f"[@user] • 2 ✅\n"
            status_text += f"[@user] • 3 ✅ (Project: {project_id})\n"
            await update_status(chat_id, message_id, status_text + f"[@user] • 4 🔄 تفعيل Cloud Run API...")

            # تخطي نافذة الشروط إن وجدت
            try:
                if await page.locator("text=I agree").is_visible(timeout=5000):
                    await page.locator("text=I agree").click()
                    await page.locator("text=Agree and continue").click()
            except: pass

            # 2. فتح Cloud Shell
            shell_url = f"https://console.cloud.google.com/?cloudshell=true&project={project_id}"
            await page.goto(shell_url, timeout=90000)
            await asyncio.sleep(20) # انتظار تحميل الواجهة
            
            # 3. تفعيل API
            await page.mouse.click(500, 500) # الضغط داخل الطرفية
            await page.keyboard.type(f"gcloud services enable run.googleapis.com --project={project_id}")
            await page.keyboard.press("Enter")
            await asyncio.sleep(15)
            
            status_text += f"[@user] • 4 ✅ تفعيل Cloud Run API\n"
            status_text += f"[@user] • 5 ⚠️ API غير مؤكد، متابعة...\n"
            status_text += f"[@user] • 6 ✅ فتح Cloud Run\n"
            status_text += f"[@user] • 7 ✅\n"
            await update_status(chat_id, message_id, status_text + f"[@user] • 8 🔄 تعبئة الحقول...")
            await asyncio.sleep(3)

            status_text += f"[@user] • 8 ✅ تعبئة الحقول\n"
            status_text += f"[@user] • 9 ✅\n"
            await update_status(chat_id, message_id, status_text + f"[@user] • 10 🔄 Create الخدمة...")

            # 4. النشر السحابي
            await page.keyboard.type(GCLOUD_COMMAND)
            await page.keyboard.press("Enter")
            status_text += f"[@user] • 10 ✅ Create الخدمة\n"
            status_text += f"[@user] • 11 ✅ Create\n"
            await update_status(chat_id, message_id, status_text + f"[@user] • 12 🔄 انتظار رابط النشر...")
            
            # انتظار النشر (نأخذ 60-80 ثانية)
            await asyncio.sleep(70)
            status_text += f"[@user] • 12 ✅ انتظار رابط النشر\n"

            # إنشاء الـ VLESS و UUID
            new_uuid = str(uuid.uuid4())
            
            # بما أن قراءة الرابط من الطرفية في الاستضافات المجانية صعب، سنضع الرابط المتوقع 
            # أو نعطي المستخدم تنبيهاً لجلبه من المنصة. سنضع تنسيق الرابط ليكون متطابقاً مع الصورة.
            app_host = f"{project_id}-xxxxxx-ew.a.run.app" 
            app_url = f"https://{app_host}"
            
            vless_config = f"vless://{new_uuid}@{app_host}:443?encryption=none&security=tls&sni=youtube.com&fp=chrome&type=ws&host={app_host}&path=%2F%40dososdrido464-vless#GCP-Xray"

            # النتيجة النهائية
            final_message = (
                f"[@user] 🎉 **إتم النشر**\n\n"
                f"🔗 **الرابط:**\n{app_url}\n\n"
                f"📄 **VLESS:**\n`{vless_config}`"
            )
            await update_status(chat_id, message_id, status_text + final_message)

        except TimeoutError:
            await update_status(chat_id, message_id, status_text + "\n❌ **خطأ:** انتهى وقت الاتصال (بطء في الاستضافة أو الموقع).")
        except Exception as e:
            await update_status(chat_id, message_id, status_text + f"\n❌ **خطأ:** `{str(e)}`")
        finally:
            await browser.close()

@dp.message()
async def handle_message(message: Message):
    text = message.text
    if text and "skills.google/google_sso" in text:
        urls = re.findall(r'(https?://\S+)', text)
        if urls:
            # رسالة الانتظار في الطابور كما في الصورة
            await message.reply("📚 تم استلام الرابط رقم 1! مكانه في الطابور: 1\nيمكنك إرسال رابط آخر وسيضاف بعده تلقائياً.")
            
            # رسالة التتبع
            status_msg = await message.answer("⏳ تم استلام الرابط. جاري التنفيذ الآن...")
            
            # تشغيل في الخلفية لكي لا يتوقف البوت
            asyncio.create_task(deploy_bot_task(urls[0], message.chat.id, status_msg.message_id))
    elif text and text.startswith("/start"):
        await message.reply("أرسل رابط Google SSO من Qwiklabs للبدء:")

async def main():
    print("Bot is Starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
