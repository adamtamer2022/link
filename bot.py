import json
import re
import requests
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from bs4 import BeautifulSoup
import hashlib
from datetime import datetime

BOT_TOKEN = "8084055929:AAGRIXHmx1sQ9yKrifQf6JtSPxWX5A4YR_Q"
POSTS_FILE = 'posts.json'
IMAGES_DIR = 'images'

# قاموس لتخزين حالة التعديل المؤقتة
user_edit_state = {}

# إنشاء مجلد الصور لو مش موجود
if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR)

# وظيفة لتحميل الصور من البوست
def download_images(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        images = []
        
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            img_url = og_image.get('content')
            img_filename = download_single_image(img_url)
            if img_filename:
                images.append(img_filename)
        
        for img_tag in soup.find_all('img'):
            img_url = img_tag.get('src')
            if img_url and 'scontent' in img_url:
                img_filename = download_single_image(img_url)
                if img_filename and img_filename not in images:
                    images.append(img_filename)
                    if len(images) >= 5:
                        break
        
        return images
    except Exception as e:
        print(f"خطأ في تحميل الصور: {e}")
        return []

# وظيفة لتحميل صورة واحدة
def download_single_image(img_url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(img_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            img_hash = hashlib.md5(img_url.encode()).hexdigest()[:10]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            ext = 'jpg'
            if 'png' in img_url.lower():
                ext = 'png'
            elif 'gif' in img_url.lower():
                ext = 'gif'
            
            filename = f"{timestamp}_{img_hash}.{ext}"
            filepath = os.path.join(IMAGES_DIR, filename)
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            return filename
        return None
    except Exception as e:
        print(f"خطأ في حفظ الصورة: {e}")
        return None

# حفظ صورة من التلجرام
def save_telegram_image(file_obj, bot):
    try:
        file = bot.get_file(file_obj.file_id)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_hash = hashlib.md5(file_obj.file_id.encode()).hexdigest()[:10]
        
        ext = 'jpg'
        filename = f"{timestamp}_{file_hash}.{ext}"
        filepath = os.path.join(IMAGES_DIR, filename)
        
        file.download(filepath)
        return filename
    except Exception as e:
        print(f"خطأ في حفظ صورة التلجرام: {e}")
        return None

# وظيفة لاستخراج نص البوست من Facebook
def extract_post_title(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title = None
        
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            title = og_desc.get('content')
        
        if not title:
            desc = soup.find('meta', attrs={'name': 'description'})
            if desc and desc.get('content'):
                title = desc.get('content')
        
        if not title:
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                title = og_title.get('content')
        
        if title:
            title = title.strip()
            lines = [line.strip() for line in title.split('\n') if line.strip()]
            if lines:
                return '\n'.join(lines)
            return title
        
        return None
    except Exception as e:
        print(f"خطأ في استخراج النص: {e}")
        return None

# وظيفة للتحقق من صحة رابط Facebook
def is_valid_facebook_url(url):
    fb_patterns = [
        r'https?://(www\.)?facebook\.com/',
        r'https?://fb\.watch/',
        r'https?://m\.facebook\.com/'
    ]
    return any(re.match(pattern, url) for pattern in fb_patterns)

# قراءة البوستات
def load_posts():
    try:
        with open(POSTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

# حفظ البوستات
def save_posts(posts):
    with open(POSTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(posts, f, ensure_ascii=False, indent=4)

# وظيفة لإضافة بوست
def add_post(url, title=None):
    posts = load_posts()

    if not title:
        title = extract_post_title(url)
    
    if not title:
        title = url
    
    images = download_images(url)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    posts.append({
        'id': len(posts),
        'url': url, 
        'title': title, 
        'images': images,
        'date': timestamp
    })

    save_posts(posts)
    return len(posts) - 1

# أمر /start
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🤖 مرحباً! أنا بوت حفظ بوستات الفيسبوك\n\n"
        "📝 ببساطة، أرسل لي رابط أي بوست فيسبوك وأنا هخزنه\n"
        "✨ هستخرج عنوان البوست والصور تلقائياً\n\n"
        "الأوامر المتاحة:\n"
        "/start - عرض هذه الرسالة\n"
        "/list - عرض قائمة البوستات المحفوظة\n"
        "/count - عرض عدد البوستات\n"
        "/edit [رقم] - تعديل بوست معين\n"
        "/delete [رقم] - حذف بوست معين\n"
        "/clear - مسح كل البوستات"
    )

# أمر لعرض قائمة البوستات
def list_posts(update: Update, context: CallbackContext):
    posts = load_posts()
    
    if not posts:
        update.message.reply_text("📭 لا توجد بوستات محفوظة حالياً")
        return
    
    message = "📚 قائمة البوستات المحفوظة:\n\n"
    
    for i, post in enumerate(posts):
        title_preview = post['title'][:50] + "..." if len(post['title']) > 50 else post['title']
        images_count = len(post.get('images', []))
        
        message += f"🔹 البوست #{i}\n"
        message += f"📝 {title_preview}\n"
        message += f"🖼️ {images_count} صورة\n"
        message += f"📅 {post.get('date', 'غير محدد')}\n\n"
    
    message += "💡 استخدم /edit [رقم] لتعديل أي بوست"
    update.message.reply_text(message)

# أمر لعرض عدد البوستات
def count_posts(update: Update, context: CallbackContext):
    posts = load_posts()
    update.message.reply_text(f"📊 عدد البوستات المحفوظة: {len(posts)}")

# أمر لبدء تعديل بوست
def edit_post_command(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    if not context.args or not context.args[0].isdigit():
        update.message.reply_text(
            "⚠️ استخدم الأمر بهذا الشكل:\n"
            "/edit [رقم البوست]\n\n"
            "مثال: /edit 0\n"
            "استخدم /list لعرض أرقام البوستات"
        )
        return
    
    post_id = int(context.args[0])
    posts = load_posts()
    
    if post_id < 0 or post_id >= len(posts):
        update.message.reply_text(f"❌ البوست #{post_id} غير موجود")
        return
    
    post = posts[post_id]
    
    # حفظ حالة التعديل
    user_edit_state[user_id] = {
        'post_id': post_id,
        'action': 'menu'
    }
    
    # إنشاء لوحة مفاتيح التحكم
    keyboard = [
        [InlineKeyboardButton("✏️ تعديل النص", callback_data=f"edit_text_{post_id}"),
         InlineKeyboardButton("🖼️ إضافة صور", callback_data=f"add_images_{post_id}")],
        [InlineKeyboardButton("🗑️ حذف صور", callback_data=f"delete_images_{post_id}"),
         InlineKeyboardButton("👁️ عرض البوست", callback_data=f"view_post_{post_id}")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_edit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    title_preview = post['title'][:100] + "..." if len(post['title']) > 100 else post['title']
    
    update.message.reply_text(
        f"🔧 تعديل البوست #{post_id}\n\n"
        f"📝 النص الحالي:\n{title_preview}\n\n"
        f"🖼️ عدد الصور: {len(post.get('images', []))}\n\n"
        f"اختر العملية:",
        reply_markup=reply_markup
    )

# معالج الأزرار
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    
    data = query.data
    
    if data == "cancel_edit":
        if user_id in user_edit_state:
            del user_edit_state[user_id]
        query.edit_message_text("❌ تم إلغاء عملية التعديل")
        return
    
    if data.startswith("edit_text_"):
        post_id = int(data.split("_")[2])
        user_edit_state[user_id] = {
            'post_id': post_id,
            'action': 'edit_text'
        }
        query.edit_message_text(
            "✏️ أرسل النص الجديد للبوست\n\n"
            "💡 يمكنك:\n"
            "- كتابة نص جديد تماماً\n"
            "- أو إضافة نص للنص الموجود\n\n"
            "استخدم /cancel للإلغاء"
        )
    
    elif data.startswith("add_images_"):
        post_id = int(data.split("_")[2])
        user_edit_state[user_id] = {
            'post_id': post_id,
            'action': 'add_images'
        }
        query.edit_message_text(
            "🖼️ أرسل الصور التي تريد إضافتها\n\n"
            "📌 يمكنك:\n"
            "- إرسال صورة واحدة\n"
            "- إرسال عدة صور واحدة تلو الأخرى\n\n"
            "عند الانتهاء اكتب: /done\n"
            "للإلغاء: /cancel"
        )
    
    elif data.startswith("delete_images_"):
        post_id = int(data.split("_")[2])
        posts = load_posts()
        post = posts[post_id]
        
        if not post.get('images'):
            query.edit_message_text("ℹ️ لا توجد صور في هذا البوست")
            return
        
        keyboard = []
        for i, img in enumerate(post['images']):
            keyboard.append([InlineKeyboardButton(f"🗑️ حذف الصورة {i+1}", callback_data=f"del_img_{post_id}_{i}")])
        keyboard.append([InlineKeyboardButton("✅ تم", callback_data="cancel_edit")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            f"🗑️ اختر الصور التي تريد حذفها:\n\n"
            f"عدد الصور الحالي: {len(post['images'])}",
            reply_markup=reply_markup
        )
    
    elif data.startswith("del_img_"):
        parts = data.split("_")
        post_id = int(parts[2])
        img_index = int(parts[3])
        
        posts = load_posts()
        if post_id < len(posts) and img_index < len(posts[post_id].get('images', [])):
            img_to_delete = posts[post_id]['images'][img_index]
            img_path = os.path.join(IMAGES_DIR, img_to_delete)
            
            # حذف الصورة من الملف
            if os.path.exists(img_path):
                os.remove(img_path)
            
            # حذف الصورة من القائمة
            posts[post_id]['images'].pop(img_index)
            save_posts(posts)
            
            query.answer("✅ تم حذف الصورة")
            
            # تحديث القائمة
            if not posts[post_id].get('images'):
                query.edit_message_text("✅ تم حذف جميع الصور من البوست")
                return
            
            keyboard = []
            for i, img in enumerate(posts[post_id]['images']):
                keyboard.append([InlineKeyboardButton(f"🗑️ حذف الصورة {i+1}", callback_data=f"del_img_{post_id}_{i}")])
            keyboard.append([InlineKeyboardButton("✅ تم", callback_data="cancel_edit")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text(
                f"🗑️ اختر الصور التي تريد حذفها:\n\n"
                f"عدد الصور الحالي: {len(posts[post_id]['images'])}",
                reply_markup=reply_markup
            )
    
    elif data.startswith("view_post_"):
        post_id = int(data.split("_")[2])
        posts = load_posts()
        post = posts[post_id]
        
        message = f"👁️ البوست #{post_id}\n\n"
        message += f"📝 النص:\n{post['title']}\n\n"
        message += f"🖼️ عدد الصور: {len(post.get('images', []))}\n"
        message += f"📅 التاريخ: {post.get('date', 'غير محدد')}\n"
        message += f"🔗 الرابط: {post['url']}"
        
        query.edit_message_text(message)

# أمر /done لإنهاء إضافة الصور
def done_command(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    if user_id in user_edit_state and user_edit_state[user_id]['action'] == 'add_images':
        post_id = user_edit_state[user_id]['post_id']
        posts = load_posts()
        
        update.message.reply_text(
            f"✅ تم الانتهاء من إضافة الصور\n\n"
            f"🖼️ عدد الصور الكلي: {len(posts[post_id].get('images', []))}"
        )
        del user_edit_state[user_id]
    else:
        update.message.reply_text("ℹ️ لا توجد عملية تحرير نشطة")

# أمر /cancel للإلغاء
def cancel_command(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    if user_id in user_edit_state:
        del user_edit_state[user_id]
        update.message.reply_text("❌ تم إلغاء عملية التعديل")
    else:
        update.message.reply_text("ℹ️ لا توجد عملية تحرير نشطة")

# أمر لحذف بوست
def delete_post_command(update: Update, context: CallbackContext):
    if not context.args or not context.args[0].isdigit():
        update.message.reply_text(
            "⚠️ استخدم الأمر بهذا الشكل:\n"
            "/delete [رقم البوست]\n\n"
            "مثال: /delete 0"
        )
        return
    
    post_id = int(context.args[0])
    posts = load_posts()
    
    if post_id < 0 or post_id >= len(posts):
        update.message.reply_text(f"❌ البوست #{post_id} غير موجود")
        return
    
    # حذف صور البوست
    for img in posts[post_id].get('images', []):
        img_path = os.path.join(IMAGES_DIR, img)
        if os.path.exists(img_path):
            os.remove(img_path)
    
    posts.pop(post_id)
    save_posts(posts)
    
    update.message.reply_text(f"✅ تم حذف البوست #{post_id} بنجاح")

# أمر لمسح كل البوستات
def clear_posts(update: Update, context: CallbackContext):
    save_posts([])
    update.message.reply_text("🗑️ تم مسح كل البوستات بنجاح!")

# معالج الصور
def handle_photo(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    if user_id not in user_edit_state or user_edit_state[user_id]['action'] != 'add_images':
        update.message.reply_text("ℹ️ استخدم /edit [رقم] واختر إضافة صور أولاً")
        return
    
    post_id = user_edit_state[user_id]['post_id']
    posts = load_posts()
    
    if post_id >= len(posts):
        update.message.reply_text("❌ البوست غير موجود")
        return
    
    # حفظ الصورة
    photo = update.message.photo[-1]  # أعلى جودة
    filename = save_telegram_image(photo, context.bot)
    
    if filename:
        if 'images' not in posts[post_id]:
            posts[post_id]['images'] = []
        
        posts[post_id]['images'].append(filename)
        save_posts(posts)
        
        update.message.reply_text(
            f"✅ تم إضافة الصورة بنجاح!\n\n"
            f"🖼️ عدد الصور الكلي: {len(posts[post_id]['images'])}\n\n"
            f"أرسل المزيد من الصور أو اكتب /done للانتهاء"
        )
    else:
        update.message.reply_text("❌ فشل حفظ الصورة")

# وظيفة التعامل مع الرسائل النصية
def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # التحقق من حالة التعديل
    if user_id in user_edit_state:
        if user_edit_state[user_id]['action'] == 'edit_text':
            post_id = user_edit_state[user_id]['post_id']
            posts = load_posts()
            
            if post_id >= len(posts):
                update.message.reply_text("❌ البوست غير موجود")
                return
            
            # تعديل النص
            posts[post_id]['title'] = text
            save_posts(posts)
            
            update.message.reply_text(
                f"✅ تم تعديل نص البوست #{post_id} بنجاح!\n\n"
                f"📝 النص الجديد:\n{text[:100]}{'...' if len(text) > 100 else ''}"
            )
            del user_edit_state[user_id]
            return
    
    # إذا لم يكن في وضع التعديل، تحقق من رابط Facebook
    if not is_valid_facebook_url(text):
        update.message.reply_text(
            "⚠️ من فضلك أرسل رابط بوست فيسبوك صحيح\n"
            "مثال: https://www.facebook.com/share/p/..."
        )
        return
    
    waiting_msg = update.message.reply_text("⏳ جاري حفظ البوست واستخراج المحتوى والصور...")
    
    try:
        post_id = add_post(text)
        posts = load_posts()
        last_post = posts[post_id]
        
        title_preview = last_post['title']
        if len(title_preview) > 100:
            title_display = title_preview[:100] + "..."
        else:
            title_display = title_preview
        
        images_count = len(last_post.get('images', []))
        
        waiting_msg.edit_text(
            f"✅ تم حفظ البوست #{post_id} بنجاح!\n\n"
            f"📝 المحتوى:\n{title_display}\n\n"
            f"🖼️ عدد الصور المحفوظة: {images_count}\n"
            f"📅 التاريخ: {last_post.get('date', 'غير محدد')}\n\n"
            f"💡 استخدم /edit {post_id} لتعديل البوست وإضافة المزيد من الصور"
        )
    except Exception as e:
        waiting_msg.edit_text(f"❌ حدث خطأ: {e}")

# إعداد البوت
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # إضافة المعالجات
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("list", list_posts))
    dp.add_handler(CommandHandler("count", count_posts))
    dp.add_handler(CommandHandler("edit", edit_post_command))
    dp.add_handler(CommandHandler("delete", delete_post_command))
    dp.add_handler(CommandHandler("clear", clear_posts))
    dp.add_handler(CommandHandler("done", done_command))
    dp.add_handler(CommandHandler("cancel", cancel_command))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.photo, handle_photo))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    print("🤖 البوت شغال...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()