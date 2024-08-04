import logging
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

TOKEN = "7120665237:AAHfUL5xgyEsZe9af1mdSr4FwiLoVl1vcP8"
CHANNEL_USERNAME = '@sultanpanel'
NOTIFICATION_CHANNEL_ID = -1002147674595

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

Base = declarative_base()
engine = create_engine('sqlite:///bot_users.db')
Session = sessionmaker(bind=engine)
session = Session()

class User(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    language = Column(String)
    is_admin = Column(Boolean, default=False)
    notified = Column(Boolean, default=False)
    credit = Column(Float, default=0.0)
    membership_days = Column(Integer, default=0)
    account_status = Column(String, default='active')
    used_credit = Column(Float, default=0.0)
    remaining_credit = Column(Float, default=0.0)
    earned_from_invites = Column(Float, default=0.0)
    earned_from_transactions = Column(Float, default=0.0)

class AgencyRequest(Base):
    __tablename__ = 'agency_requests'
    request_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    daily_sales = Column(String)
    status = Column(String, default='pending')

Base.metadata.create_all(engine)

languages = {'English 🇬🇧': 'en', 'فارسی 🇮🇷': 'fa', 'العربية 🇸🇦': 'ar'}
language_emoji = {'en': '🇬🇧', 'fa': '🇮🇷', 'ar': '🇸🇦'}
translations = {
    'en': {
        'welcome_admin': 'Welcome, Admin! 🌟👋',
        'welcome_user': 'Welcome, {}! 🌟👋',
        'choose_language': 'Please choose your language 🌐:',
        'language_set': 'Language set to {} 🎉',
        'admin_management': 'Admin Management 👨‍💼⚙️',
        'settings': 'Settings ⚙️',
        'broadcast': 'Broadcast Message 📢',
        'broadcast_prompt': 'Who do you want to broadcast to? 📢',
        'admins': 'Admins 👨‍💼',
        'users': 'Users 👥',
        'back': 'Back 🔙',
        'add_admin': 'Add Admin 👨‍💼➕',
        'remove_admin': 'Remove Admin 👨‍💼➖',
        'view_admins': 'View Admins 👨‍💼👀',
        'enter_username': 'Please enter the username (@username) 📝:',
        'join_channel': 'Please join our channel to use the bot 🙏🌟',
        'join_button': 'Join Channel 🌐',
        'verify_button': 'Verify Membership ✅',
        'account_info': 'Account information 📄',
        'credit': 'Credit: {} 💳',
        'membership_days': 'Membership Days: {} 📅',
        'account_status': 'Account Status: {} 🟢',
        'used_credit': 'Used Credit: {} 💸',
        'remaining_credit': 'Remaining Credit: {} 🏦',
        'earned_from_invites': 'Earned from Invites: {} 🎁',
        'earned_from_transactions': 'Earned from Transactions: {} 💰',
        'request_agency': 'Request Agency 🤝',
        'enter_sales': 'Please enter your daily sales (e.g., 200$) 📝:',
        'agency_request_received': 'Your agency request has been queued and will be processed shortly. Your request number is #{} 📄',
        'agency_requests': 'Agency Requests 📄',
        'approve_request': 'Approve Request ✅',
        'reject_request': 'Reject Request ❌',
        'request_approved': 'Your agency request has been approved! 🎉',
        'request_rejected': 'Your agency request has been rejected. 🚫'
    },
    'fa': {
        'welcome_admin': 'خوش آمدید، ادمین! 🌟👋',
        'welcome_user': 'خوش آمدید، {}! 🌟👋',
        'choose_language': 'لطفا زبان خود را انتخاب کنید 🌐:',
        'language_set': 'زبان تنظیم شد به {} 🎉',
        'admin_management': 'مدیریت ادمین 👨‍💼⚙️',
        'settings': 'تنظیمات ⚙️',
        'broadcast': 'ارسال پیام همگانی 📢',
        'broadcast_prompt': 'به چه کسی می‌خواهید پیام همگانی ارسال کنید؟ 📢',
        'admins': 'ادمین‌ها 👨‍💼',
        'users': 'کاربران 👥',
        'back': 'بازگشت 🔙',
        'add_admin': 'اضافه کردن ادمین 👨‍💼➕',
        'remove_admin': 'حذف ادمین 👨‍💼➖',
        'view_admins': 'دیدن ادمین‌ها 👨‍💼👀',
        'enter_username': 'لطفا نام کاربری (مثلاً @username) را وارد کنید 📝:',
        'join_channel': 'لطفا برای استفاده از ربات به کانال ما بپیوندید 🙏🌟',
        'join_button': 'پیوستن به کانال 🌐',
        'verify_button': 'تایید عضویت ✅',
        'account_info': 'اطلاعات حساب شما 📄',
        'credit': 'اعتبار: {} 💳',
        'membership_days': 'روزهای عضویت: {} 📅',
        'account_status': 'وضعیت حساب: {} 🟢',
        'used_credit': 'اعتبار استفاده شده: {} 💸',
        'remaining_credit': 'اعتبار باقی‌مانده: {} 🏦',
        'earned_from_invites': 'کسب شده از دعوت‌ها: {} 🎁',
        'earned_from_transactions': 'کسب شده از تراکنش‌ها: {} 💰',
        'request_agency': 'درخواست نمایندگی 🤝',
        'enter_sales': 'لطفا فروش روزانه خود را وارد کنید (مثلا 200$) 📝:',
        'agency_request_received': 'درخواست نمایندگی شما در صف قرار گرفت و در سریعترین زمان توسط ما بررسی و برای شما پنل همراه تخفیف نمایندگی فعال خواهد شد. شماره درخواست شما #{} 📄',
        'agency_requests': 'درخواست‌های نمایندگی 📄',
        'approve_request': 'تایید درخواست ✅',
        'reject_request': 'رد درخواست ❌',
        'request_approved': 'درخواست نمایندگی شما قبول شد! 🎉',
        'request_rejected': 'درخواست نمایندگی شما رد شد. 🚫'
    },
    'ar': {
        'welcome_admin': 'مرحباً، مشرف! 🌟👋',
        'welcome_user': 'مرحباً، {}! 🌟👋',
        'choose_language': 'يرجى اختيار لغتك 🌐:',
        'language_set': 'تم تعيين اللغة إلى {} 🎉',
        'admin_management': 'إدارة المشرفين 👨‍💼⚙️',
        'settings': 'الإعدادات ⚙️',
        'broadcast': 'رسالة جماعية 📢',
        'broadcast_prompt': 'من تريد إرسال الرسالة إليه؟ 📢',
        'admins': 'مشرفين 👨‍💼',
        'users': 'مستخدمين 👥',
        'back': 'رجوع 🔙',
        'add_admin': 'إضافة مشرف 👨‍💼➕',
        'remove_admin': 'إزالة مشرف 👨‍💼➖',
        'view_admins': 'عرض المشرفين 👨‍💼👀',
        'enter_username': 'يرجى إدخال اسم المستخدم (@username) 📝:',
        'join_channel': 'يرجى الانضمام إلى قناتنا لاستخدام الروبوت 🙏🌟',
        'join_button': 'انضم إلى القناة 🌐',
        'verify_button': 'تحقق من العضوية ✅',
        'account_info': 'معلومات حسابك 📄',
        'credit': 'الرصيد: {} 💳',
        'membership_days': 'أيام العضوية: {} 📅',
        'account_status': 'حالة الحساب: {} 🟢',
        'used_credit': 'الرصيد المستخدم: {} 💸',
        'remaining_credit': 'الرصيد المتبقي: {} 🏦',
        'earned_from_invites': 'تم الكسب من الدعوات: {} 🎁',
        'earned_from_transactions': 'تم الكسب من المعاملات: {} 💰',
        'request_agency': 'طلب الوكالة 🤝',
        'enter_sales': 'يرجى إدخال مبيعاتك اليومية (على سبيل المثال ، 200$) 📝:',
        'agency_request_received': 'تم وضع طلب الوكالة الخاص بك في قائمة الانتظار وسيتم معالجته في أقرب وقت. رقم طلبك هو #{} 📄',
        'agency_requests': 'طلبات الوكالة 📄',
        'approve_request': 'الموافقة على الطلب ✅',
        'reject_request': 'رفض الطلب ❌',
        'request_approved': 'تمت الموافقة على طلب الوكالة الخاص بك! 🎉',
        'request_rejected': 'تم رفض طلب الوكالة الخاص بك. 🚫'
    }
}

def set_user_language(user_id, language):
    user = session.query(User).filter_by(user_id=user_id).first()
    if user:
        user.language = language
    else:
        user = User(user_id=user_id, language=language)
        session.add(user)
    session.commit()

def get_user_language(user_id):
    user = session.query(User).filter_by(user_id=user_id).first()
    return user.language if user else None

def is_admin(username):
    user = session.query(User).filter_by(username=username).first()
    return user.is_admin if user else False

def add_or_update_user(user_id, username):
    user = session.query(User).filter_by(username=username).first()
    if user:
        user.user_id = user_id
    else:
        user = User(user_id=user_id, username=username)
        session.add(user)
    session.commit()

async def check_membership(user_id, context):
    member_status = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
    return member_status.status in ['member', 'administrator', 'creator']

async def notify_channel(context, user):
    message = f"""
    🚀 **New user joined**:
    - **ID**: `{user.id}` 🆔
    - **Username**: @{user.username} 👤
    - **First Name**: `{user.first_name}` 🧑
    - **Last Name**: `{user.last_name}` 👥
    - [**Profile**](https://unavatar.io/telegram/{user.username}) 🌐
    """
    await context.bot.send_message(chat_id=NOTIFICATION_CHANNEL_ID, text=message, parse_mode='Markdown')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    last_name = update.effective_user.last_name

    if not username:
        await update.message.reply_text("Please set a username in your Telegram settings to use this bot. ⚠️")
        return

    user = session.query(User).filter_by(user_id=user_id).first()
    new_user = False

    if not user:
        user = User(user_id=user_id, username='@' + username)
        session.add(user)
        session.commit()
        new_user = True

    language = get_user_language(user_id)
    if not language:
        keyboard = [[InlineKeyboardButton(lang, callback_data=languages[lang])] for lang in languages.keys()]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(translations['en']['choose_language'], reply_markup=reply_markup)
    elif not await check_membership(user_id, context):
        join_button = InlineKeyboardButton(translations[language]['join_button'], url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
        verify_button = InlineKeyboardButton(translations[language]['verify_button'], callback_data='verify_membership')
        keyboard = [[join_button], [verify_button]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(translations[language]['join_channel'], reply_markup=reply_markup)
    else:
        await proceed_with_bot(update, context, first_name)

    if new_user:
        await notify_channel(context, update.effective_user)

async def proceed_with_bot(update: Update, context: ContextTypes.DEFAULT_TYPE, first_name):
    user_id = update.effective_user.id if isinstance(update, Update) else update.from_user.id
    username = update.effective_user.username if isinstance(update, Update) else update.from_user.username
    language = get_user_language(user_id)
    if language:
        if is_admin('@' + username):
            welcome_message = translations[language]['welcome_admin']
            keyboard = [
                [InlineKeyboardButton(translations[language]['settings'], callback_data='settings')],
                [InlineKeyboardButton(translations[language]['broadcast'], callback_data='broadcast')],
                [InlineKeyboardButton(translations[language]['admin_management'], callback_data='admin_management')],
                [InlineKeyboardButton(translations[language]['agency_requests'], callback_data='agency_requests')]
            ]
        else:
            welcome_message = translations[language]['welcome_user'].format(first_name)
            keyboard = [
                [InlineKeyboardButton(translations[language]['settings'], callback_data='settings')],
                [InlineKeyboardButton(translations[language]['account_info'], callback_data='account_info')],
                [InlineKeyboardButton(translations[language]['request_agency'], callback_data='request_agency')]
            ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if isinstance(update, Update):
            await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.edit_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        keyboard = [[InlineKeyboardButton(lang, callback_data=languages[lang])] for lang in languages.keys()]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if isinstance(update, Update):
            await update.message.reply_text(translations['en']['choose_language'], reply_markup=reply_markup)
        else:
            await update.message.edit_text(translations['en']['choose_language'], reply_markup=reply_markup)

async def verify_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    first_name = update.callback_query.from_user.first_name
    last_name = update.callback_query.from_user.last_name
    username = update.callback_query.from_user.username
    if await check_membership(user_id, context):
        await proceed_with_bot(update.callback_query, context, first_name)
        user = User(user_id=user_id, username=username, first_name=first_name, last_name=last_name)
        await notify_channel(context, update.effective_user)
    else:
        await update.callback_query.answer("You are not a member of the channel yet. 🚫", show_alert=True)

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    keyboard = [[InlineKeyboardButton(lang, callback_data=languages[lang])] for lang in languages.keys()]
    keyboard.append([InlineKeyboardButton(translations[language]['back'], callback_data='main_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(translations[language]['choose_language'], reply_markup=reply_markup)

async def admin_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    keyboard = [
        [InlineKeyboardButton(translations[language]['add_admin'], callback_data='add_admin')],
        [InlineKeyboardButton(translations[language]['remove_admin'], callback_data='remove_admin')],
        [InlineKeyboardButton(translations[language]['view_admins'], callback_data='view_admins')],
        [InlineKeyboardButton(translations[language]['back'], callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(translations[language]['admin_management'], reply_markup=reply_markup)

async def view_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admins = session.query(User).filter_by(is_admin=True).all()
    admin_list = '\n'.join([f'@{admin.username}' for admin in admins])
    language = get_user_language(update.effective_user.id)
    keyboard = [[InlineKeyboardButton(translations[language]['back'], callback_data='admin_management')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(f"**Admins**:\n{admin_list}", reply_markup=reply_markup, parse_mode='Markdown')

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.username
    data = query.data
    if not username:
        await query.message.reply_text("Please set a username in your Telegram settings to use this bot. ⚠️", parse_mode='Markdown')
        return

    if data == 'settings':
        await settings(update, context)
    elif data == 'admin_management':
        await admin_management(update, context)
    elif data == 'main_menu' or data == 'back':
        await show_main_menu(query, user_id, username, context)
    elif data == 'add_admin':
        context.user_data['admin_action'] = 'add'
        await query.message.reply_text(translations[get_user_language(user_id)]['enter_username'], parse_mode='Markdown')
    elif data == 'remove_admin':
        context.user_data['admin_action'] = 'remove'
        await query.message.reply_text(translations[get_user_language(user_id)]['enter_username'], parse_mode='Markdown')
    elif data == 'view_admins':
        await view_admins(update, context)
    elif data == 'broadcast':
        await show_broadcast_options(query, user_id, context)
    elif data == 'verify_membership':
        await verify_membership(update, context)
    elif data == 'account_info':
        await account_info(query, context)
    elif data == 'request_agency':
        await request_agency(query, context)
    elif data == 'agency_requests':
        await show_agency_requests(query, context)
    elif data.startswith('approve_request_'):
        await approve_agency_request(query, context, int(data.split('_')[-1]))
    elif data.startswith('reject_request_'):
        await reject_agency_request(query, context, int(data.split('_')[-1]))
    elif data in ['broadcast_admins', 'broadcast_users']:
        context.user_data['broadcast_target'] = data
        context.user_data['awaiting_broadcast_message'] = True
        await query.message.reply_text("Please send the message you want to broadcast. 📝", parse_mode='Markdown')
    else:
        await set_language_and_show_main_menu(data, query, user_id, username, context)

async def show_main_menu(query, user_id, username, context):
    language = get_user_language(user_id)
    first_name = query.from_user.first_name
    if is_admin('@' + username):
        welcome_message = translations[language]['welcome_admin']
        keyboard = [
            [InlineKeyboardButton(translations[language]['settings'], callback_data='settings')],
            [InlineKeyboardButton(translations[language]['broadcast'], callback_data='broadcast')],
            [InlineKeyboardButton(translations[language]['admin_management'], callback_data='admin_management')],
            [InlineKeyboardButton(translations[language]['agency_requests'], callback_data='agency_requests')]
        ]
    else:
        welcome_message = translations[language]['welcome_user'].format(first_name)
        keyboard = [
            [InlineKeyboardButton(translations[language]['settings'], callback_data='settings')],
            [InlineKeyboardButton(translations[language]['account_info'], callback_data='account_info')],
            [InlineKeyboardButton(translations[language]['request_agency'], callback_data='request_agency')]
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

async def show_broadcast_options(query, user_id, context):
    language = get_user_language(user_id)
    keyboard = [
        [InlineKeyboardButton(translations[language]['admins'], callback_data='broadcast_admins')],
        [InlineKeyboardButton(translations[language]['users'], callback_data='broadcast_users')],
        [InlineKeyboardButton(translations[language]['back'], callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(translations[language]['broadcast_prompt'], reply_markup=reply_markup, parse_mode='Markdown')

async def set_language_and_show_main_menu(language_code, query, user_id, username, context):
    set_user_language(user_id, language_code)
    language = language_code
    first_name = query.from_user.first_name
    if is_admin('@' + username):
        welcome_message = translations[language]['welcome_admin']
        keyboard = [
            [InlineKeyboardButton(translations[language]['settings'], callback_data='settings')],
            [InlineKeyboardButton(translations[language]['broadcast'], callback_data='broadcast')],
            [InlineKeyboardButton(translations[language]['admin_management'], callback_data='admin_management')],
            [InlineKeyboardButton(translations[language]['agency_requests'], callback_data='agency_requests')]
        ]
    else:
        welcome_message = translations[language]['welcome_user'].format(first_name)
        keyboard = [
            [InlineKeyboardButton(translations[language]['settings'], callback_data='settings')],
            [InlineKeyboardButton(translations[language]['account_info'], callback_data='account_info')],
            [InlineKeyboardButton(translations[language]['request_agency'], callback_data='request_agency')]
        ]
    await query.answer()
    await query.edit_message_text(text=f"{translations[language]['language_set'].format(language_emoji[language])} 🎉", parse_mode='Markdown')
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    if not username:
        await update.message.reply_text("Please set a username in your Telegram settings to use this bot. ⚠️", parse_mode='Markdown')
        return

    if context.user_data.get('awaiting_broadcast_message'):
        message = update.message.text
        target = context.user_data.get('broadcast_target')
        if is_admin('@' + username):
            if target == 'broadcast_admins':
                users = session.query(User).filter_by(is_admin=True).all()
            else:
                users = session.query(User).all()

            for user in users:
                try:
                    await context.bot.send_message(chat_id=user.user_id, text=message, parse_mode='Markdown')
                    time.sleep(0.1)
                except Exception as e:
                    logging.error(f"Error sending message to {user.user_id}: {e}")

            context.user_data['broadcast_target'] = None
            context.user_data['awaiting_broadcast_message'] = False
            await update.message.reply_text("Broadcast message sent successfully. 📢✅", parse_mode='Markdown')
            await show_main_menu(update.message, user_id, username, context)
        else:
            await update.message.reply_text("You are not authorized to send broadcast messages. 🚫", parse_mode='Markdown')
    elif is_admin('@' + username) and 'admin_action' in context.user_data:
        await handle_admin_action(update, context, user_id, username)

async def handle_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, username):
    admin_action = context.user_data['admin_action']
    new_username = update.message.text
    if not new_username.startswith('@'):
        await update.message.reply_text("Please enter a valid username starting with '@'. 📝", parse_mode='Markdown')
        return
    try:
        target_user = session.query(User).filter_by(username=new_username).first()

        if admin_action == 'add':
            if target_user:
                target_user.is_admin = True
                target_user.user_id = None
            else:
                target_user = User(username=new_username, is_admin=True)
                session.add(target_user)
            session.commit()
            await update.message.reply_text(
                f"User {new_username} has been added as an admin. They need to start the bot to complete the setup. ✅👨‍💼", parse_mode='Markdown')
        elif admin_action == 'remove':
            if target_user and target_user.is_admin:
                target_user.is_admin = False
                session.commit()
                await update.message.reply_text(f"User {new_username} has been removed from admins. ❌👨‍💼", parse_mode='Markdown')
            else:
                await update.message.reply_text(f"User {new_username} is not an admin. 🚫👨‍💼", parse_mode='Markdown')

        context.user_data['admin_action'] = None
        await show_main_menu(update.message, user_id, username, context)
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e} ❗", parse_mode='Markdown')

async def account_info(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(update_or_query, Update):
        user_id = update_or_query.effective_user.id
    else:
        user_id = update_or_query.from_user.id

    user = session.query(User).filter_by(user_id=user_id).first()
    if user:
        language = get_user_language(user_id)
        account_info_message = f"""
        **{translations[language]['account_info']}**
        - {translations[language]['credit'].format(user.credit)}
        - {translations[language]['membership_days'].format(user.membership_days)}
        - {translations[language]['account_status'].format(user.account_status)}
        - {translations[language]['used_credit'].format(user.used_credit)}
        - {translations[language]['remaining_credit'].format(user.remaining_credit)}
        - {translations[language]['earned_from_invites'].format(user.earned_from_invites)}
        - {translations[language]['earned_from_transactions'].format(user.earned_from_transactions)}
        """
        keyboard = [[InlineKeyboardButton(translations[language]['back'], callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if isinstance(update_or_query, Update):
            await update_or_query.message.edit_text(account_info_message, reply_markup=reply_markup,
                                                     parse_mode='Markdown')
        else:
            await update_or_query.message.edit_text(account_info_message, reply_markup=reply_markup,
                                                     parse_mode='Markdown')
    else:
        if isinstance(update_or_query, Update):
            await update_or_query.message.edit_text("User not found. ⚠️", parse_mode='Markdown')
        else:
            await update_or_query.message.edit_text("User not found. ⚠️", parse_mode='Markdown')

async def request_agency(query, context):
    user_id = query.from_user.id
    language = get_user_language(user_id)
    context.user_data['request_agency'] = True
    await query.message.reply_text(translations[language]['enter_sales'], parse_mode='Markdown')

async def handle_agency_request(update, context):
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    daily_sales = update.message.text

    if 'request_agency' in context.user_data:
        request = AgencyRequest(user_id=user_id, daily_sales=daily_sales)
        session.add(request)
        session.commit()
        request_number = request.request_id
        await update.message.reply_text(translations[language]['agency_request_received'].format(request_number), parse_mode='Markdown')
        context.user_data['request_agency'] = None

async def show_agency_requests(query, context):
    requests = session.query(AgencyRequest).filter_by(status='pending').all()
    language = get_user_language(query.from_user.id)
    if requests:
        for req in requests:
            user = session.query(User).filter_by(user_id=req.user_id).first()
            username = user.username if user else 'Unknown'
            request_info = f"Request #{req.request_id}\nUser: {username}\nDaily Sales: {req.daily_sales}"
            keyboard = [
                [InlineKeyboardButton(translations[language]['approve_request'], callback_data=f'approve_request_{req.request_id}')],
                [InlineKeyboardButton(translations[language]['reject_request'], callback_data=f'reject_request_{req.request_id}')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(request_info, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await query.message.reply_text("No pending requests.", parse_mode='Markdown')

async def approve_agency_request(query, context, request_id):
    request = session.query(AgencyRequest).filter_by(request_id=request_id).first()
    if request:
        request.status = 'approved'
        session.commit()
        user = session.query(User).filter_by(user_id=request.user_id).first()
        if user:
            language = get_user_language(user.user_id)
            await context.bot.send_message(chat_id=user.user_id, text=translations[language]['request_approved'], parse_mode='Markdown')
        await query.message.delete()
        await query.message.reply_text("Request approved and removed from the list.", parse_mode='Markdown')

async def reject_agency_request(query, context, request_id):
    request = session.query(AgencyRequest).filter_by(request_id=request_id).first()
    if request:
        request.status = 'rejected'
        session.commit()
        user = session.query(User).filter_by(user_id=request.user_id).first()
        if user:
            language = get_user_language(user.user_id)
            await context.bot.send_message(chat_id=user.user_id, text=translations[language]['request_rejected'], parse_mode='Markdown')
        await query.message.delete()
        await query.message.reply_text("Request rejected and removed from the list.", parse_mode='Markdown')

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("account_info", account_info))
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_agency_request))
    app.run_polling()

if __name__ == "__main__":
    main()
