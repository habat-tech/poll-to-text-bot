from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.constants import ParseMode
import logging
from PIL import Image, ImageEnhance
import pytesseract
import io
import arabic_reshaper
from bidi.algorithm import get_display
import asyncio
import cachetools
import fitz  # PyMuPDF

class PollBot:
    def __init__(self):
        self.TOKEN = "7819506348:AAG7c8kTqPLmmPc8oL8xs7Fs5F4PcOzzzos"
        self.setup_logging()
        self.menu_keyboard = self.create_menu_keyboard()
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        
    def setup_logging(self) -> None:
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )
        self.logger = logging.getLogger(__name__)
        
    def create_menu_keyboard(self) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            [[KeyboardButton("القائمة الرئيسية")]], 
            resize_keyboard=True,
            is_persistent=True
        )

    def format_arabic_text(self, text: str) -> str:
        try:
            if any('\u0600' <= c <= '\u06FF' for c in text):
                reshaped_text = arabic_reshaper.reshape(text, delete_harakat=False)
                bidi_text = get_display(reshaped_text, base_dir='R')
                return bidi_text
            return text
        except Exception as e:
            self.logger.error(f"خطأ في معالجة النص العربي: {e}")
            return text

    async def set_commands(self, app):
        """Set up bot commands in the menu"""
        commands = [
            ("start", "بدء استخدام البوت"),
            ("create_poll", "إنشاء استطلاع"),
            ("extract_text", "استخراج نص من صورة"),
            ("extract_pdf", "استخراج نص من PDF"),
            ("help", "المساعدة"),
            ("settings", "الإعدادات")
        ]
        await app.bot.set_my_commands(commands)

    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        welcome_message = """👋 <b>مرحباً بك في بوت الاستطلاعات!</b>

الأوامر المتاحة:
/create_poll - إنشاء استطلاع رأي
/extract_text - استخراج النص من الصور
/extract_pdf - استخراج النص من ملفات PDF
/help - الحصول على المساعدة
/settings - الإعدادات"""

        try:
            await update.message.reply_text(
                welcome_message,
                parse_mode=ParseMode.HTML,
                reply_markup=self.menu_keyboard
            )
        except Exception as e:
            self.logger.error(f"خطأ في عرض القائمة: {e}")

    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        settings_text = """⚙️ <b>الإعدادات</b>

الإعدادات المتاحة:
- لا توجد إعدادات متاحة حالياً"""

        await update.message.reply_text(
            settings_text,
            parse_mode=ParseMode.HTML
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        help_text = """<b>كيفية استخدام البوت:</b>

1️⃣ لإنشاء استطلاع جديد:
   - اضغط على زر "إنشاء استطلاع"
   - اتبع التعليمات

2️⃣ لاستخراج نص من صورة:
   - اضغط على زر "استخراج نص من صورة"
   - أرسل الصورة مباشرة

3️⃣ لاستخراج نص من ملف PDF:
   - اضغط على زر "استخراج نص من PDF"
   - أرسل ملف PDF مباشرة

4️⃣ للمساعدة:
   - اضغط على زر "المساعدة"

للعودة للقائمة الرئيسية، اضغط على "القائمة الرئيسية" 🏠"""

        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.HTML,
            reply_markup=self.menu_keyboard
        )

    async def handle_poll_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            message = update.message
            poll = message.poll

            if not poll:
                return

            question = self.format_arabic_text(poll.question)
            text = f"📊 {question}\n\n"
            
            for i, option in enumerate(poll.options, 1):
                option_text = self.format_arabic_text(option.text)
                text += f"{i}. {option_text}\n"

            await message.reply_text(
                text,
                reply_markup=self.menu_keyboard
            )

        except Exception as e:
            self.logger.error(f"خطأ في معالجة الاستطلاع: {e}")
            await message.reply_text("عذراً، حدث خطأ في معالجة الاستطلاع")

    async def handle_menu_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            if update.message.text == "القائمة الرئيسية":
                await self.show_menu(update, context)
        except Exception as e:
            self.logger.error(f"خطأ في معالجة ضغطة القائمة: {e}")

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            processing_message = await update.message.reply_text("جاري معالجة الصورة...")
            
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            photo_data = await file.download_as_bytearray()
            
            # تحسين جودة الصورة
            image = Image.open(io.BytesIO(photo_data))
            image = image.convert('L')  # تحويل إلى تدرج رمادي
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)  # زيادة التباين
            
            # استخراج النص
            text_ara = pytesseract.image_to_string(image, lang='ara')
            text_eng = pytesseract.image_to_string(image, lang='eng')
            combined_text = (text_ara + "\n" + text_eng).strip()
            
            if combined_text:
                formatted_text = self.format_arabic_text(combined_text)
                await processing_message.delete()
                await update.message.reply_text(
                    f"النص المستخرج من الصورة:\n\n{formatted_text}"
                )
            else:
                await processing_message.delete()
                await update.message.reply_text("لم يتم العثور على نص في الصورة")

        except Exception as e:
            self.logger.error(f"خطأ في معالجة الصورة: {e}")
            await update.message.reply_text("عذراً، حدث خطأ أثناء استخراج النص من الصورة")

    async def handle_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            processing_message = await update.message.reply_text("جاري معالجة ملف PDF...")
            
            pdf_file = await update.message.document.get_file()
            pdf_data = await pdf_file.download_as_bytearray()
            
            # استخراج النص من PDF
            pdf_text = ""
            with fitz.open(stream=pdf_data, filetype="pdf") as doc:
                for page in doc:
                    pdf_text += page.get_text()
            
            if pdf_text:
                formatted_text = self.format_arabic_text(pdf_text)
                await processing_message.delete()
                await update.message.reply_text(
                    f"النص المستخرج من PDF:\n\n{formatted_text}"
                )
            else:
                await processing_message.delete()
                await update.message.reply_text("لم يتم العثور على نص في ملف PDF.")

        except Exception as e:
            self.logger.error(f"خطأ في معالجة ملف PDF: {e}")
            await update.message.reply_text("عذراً، حدث خطأ أثناء استخراج النص من ملف PDF.")

    async def init_app(self):
        """Initialize the application with proper settings"""
        builder = Application.builder()
        builder.token(self.TOKEN)
        # Disable job queue and persistence to avoid weak reference issues
        builder.job_queue(None)
        builder.persistence(None)
        builder.arbitrary_callback_data(True)
        app = builder.build()

        # Add handlers
        app.add_handler(CommandHandler("start", self.show_menu))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(MessageHandler(
            filters.TEXT & filters.Regex('^القائمة الرئيسية$'),
            self.handle_menu_click
        ))
        app.add_handler(MessageHandler(
            filters.POLL | (filters.FORWARDED & filters.POLL),
            self.handle_poll_message
        ))
        app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        app.add_handler(MessageHandler(filters.Document.PDF, self.handle_pdf))

        return app

    def run(self):
        """Run the bot"""
        try:
            # Set event loop policy for Windows
            if asyncio.get_event_loop_policy().__class__.__name__ == 'WindowsProactorEventLoopPolicy':
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

            # Initialize and run the application
            self.logger.info("🤖 جاري تشغيل البوت...")
            app = Application.builder().token(self.TOKEN).job_queue(None).build()
            
            # Set up commands
            asyncio.get_event_loop().run_until_complete(self.set_commands(app))
            
            # Add handlers
            app.add_handler(CommandHandler("start", self.show_menu))
            app.add_handler(CommandHandler("help", self.help_command))
            app.add_handler(CommandHandler("settings", self.settings_command))
            app.add_handler(CommandHandler("create_poll", lambda u, c: u.message.reply_text("سيتم إضافة ميزة إنشاء الاستطلاعات قريباً!")))
            app.add_handler(CommandHandler("extract_text", lambda u, c: u.message.reply_text("أرسل الصورة لاستخراج النص منها.")))
            app.add_handler(CommandHandler("extract_pdf", lambda u, c: u.message.reply_text("أرسل ملف PDF لاستخراج النص منه.")))
            app.add_handler(MessageHandler(
                filters.TEXT & filters.Regex('^القائمة الرئيسية$'),
                self.handle_menu_click
            ))
            app.add_handler(MessageHandler(
                filters.POLL | (filters.FORWARDED & filters.POLL),
                self.handle_poll_message
            ))
            app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
            app.add_handler(MessageHandler(filters.Document.PDF, self.handle_pdf))

            # Run the bot
            app.run_polling(allowed_updates=Update.ALL_TYPES)

        except Exception as e:
            self.logger.error(f"❌ خطأ في تشغيل البوت: {e}")
            raise

if __name__ == "__main__":
    bot = PollBot()
    bot.run()
