import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from deep_translator import GoogleTranslator
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone, timedelta
import requests

TOKEN = "7120665237:AAHfUL5xgyEsZe9af1mdSr4FwiLoVl1vcP8"
NOTIFICATION_CHANNEL_ID = -1002147674595
API_URL = "https://followeriha.com/api/v2"
API_KEY = "5fa6f085fb10db47fec23f3f74eb4c97"

languages = {
    "🇬🇧 English": "en",
    "🇮🇷 فارسی": "fa"
}

admin_usernames = ["Canyildiz1386", "followergir_support"]

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    num_id = Column(Integer)
    profile_url = Column(String)
    preferred_language = Column(String)
    is_premium = Column(Boolean)
    is_bot = Column(Boolean)
    is_admin = Column(Boolean, default=False)
    join_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    used_credit = Column(Integer, default=0)
    remaining_credit = Column(Integer, default=0)
    referral_credit = Column(Integer, default=0)
    sub_transaction_earnings = Column(Integer, default=0)
    last_chance_time = Column(DateTime, default=lambda: datetime.now(timezone.utc) - timedelta(days=1))
    referrer_id = Column(Integer, nullable=True)
    unit_value = Column(Integer, default=10)  # Store unit value in cents

class AgencyRequest(Base):
    __tablename__ = 'agency_requests'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    daily_sales = Column(String)
    status = Column(String, default='pending')

class Ticket(Base):
    __tablename__ = 'tickets'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    title = Column(String)
    description = Column(String)
    status = Column(String, default='open')

class DiscountCode(Base):
    __tablename__ = 'discount_codes'
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    discount_percent = Column(Integer, nullable=False)
class Unit(Base):
    __tablename__ = 'units'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    value = Column(Integer, nullable=False)  # Stored in cents



engine = create_engine('sqlite:///telegram_bot.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def translate_text(text, target_language):
    if target_language:
        return GoogleTranslator(source='auto', target=target_language).translate(text)
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    referrer_id = None

    if context.args:
        try:
            referrer_id = int(context.args[0])
        except ValueError:
            pass

    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    if not user:
        is_admin = update.effective_user.username in admin_usernames
        new_user = User(
            username=update.effective_user.username,
            first_name=update.effective_user.first_name,
            last_name=update.effective_user.last_name,
            num_id=update.effective_user.id,
            profile_url=f'https://unavatar.io/telegram/{update.effective_user.username}',
            is_premium=update.effective_user.is_premium,
            is_bot=update.effective_user.is_bot,
            is_admin=is_admin,
            referrer_id=referrer_id
        )
        session.add(new_user)
        session.commit()

        if referrer_id:
            referrer = session.query(User).filter_by(num_id=referrer_id).first()
            if referrer:
                referrer.remaining_credit += 10
                new_user.remaining_credit += 10
                session.commit()
                await context.bot.send_message(
                    chat_id=referrer.num_id,
                    text=f"🎉 Your referral has been successful! You and {new_user.username} have both received 10 credits."
                )

        await context.bot.send_message(
            chat_id=NOTIFICATION_CHANNEL_ID,
            text=f"🎉 New {'admin' if new_user.is_admin else 'user'} joined! 🎉\n\n"
                 f"👤 Username: @{new_user.username}\n"
                 f"🧑‍💻 First Name: {new_user.first_name}\n"
                 f"🧑‍💻 Last Name: {new_user.last_name}\n"
                 f"🆔 ID: {new_user.num_id}\n"
                 f"🌐 Profile URL: {new_user.profile_url}\n"
                 f"💎 Premium: {'Yes' if new_user.is_premium else 'No'}\n"
                 f"🤖 Bot: {'Yes' if new_user.is_bot else 'No'}"
        )

        await prompt_language_selection(update, context, new_user)
    else:
        await check_channel_membership(update, context)

    session.close()

async def prompt_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    keyboard = [[InlineKeyboardButton(lang, callback_data=lang)] for lang in languages.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    language_prompt = "Please choose your language / لطفا زبان خود را انتخاب کنید:"
    await update.message.reply_text(language_prompt, reply_markup=reply_markup)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    settings_button = translate_text("⚙️ Settings", user.preferred_language)
    chance_circle_button = translate_text("🎯 Chance Circle", user.preferred_language)
    ticket_button = translate_text("🎫 Create Ticket", user.preferred_language)
    referral_link_button = translate_text("🔗 Referral Link", user.preferred_language)
    increment_credit_button = translate_text("💳 Increase Credit", user.preferred_language)
    manage_order_button = translate_text("🛒 Manage Order", user.preferred_language)

    if user.is_admin:
        account_info_button = translate_text("ℹ️ Account Information", user.preferred_language)
        view_agencies_button = translate_text("📊 View Agency Requests", user.preferred_language)
        view_tickets_button = translate_text("🎟️ View Tickets", user.preferred_language)
        admin_management_button = translate_text("🔧 Admin Management", user.preferred_language)
        manage_off_codes_button = translate_text("🔧 Manage Off Codes", user.preferred_language)
        manage_unit_value_button = translate_text("💲 Manage Unit Value", user.preferred_language)
        broadcast_button = translate_text("📢 Broadcast Message", user.preferred_language)
        keyboard = [
            [InlineKeyboardButton(account_info_button, callback_data="account_info")],
            [InlineKeyboardButton(view_agencies_button, callback_data="view_agency_requests")],
            [InlineKeyboardButton(view_tickets_button, callback_data="view_tickets")],
            [InlineKeyboardButton(settings_button, callback_data="settings")],
            [InlineKeyboardButton(chance_circle_button, callback_data="chance_circle")],
            [InlineKeyboardButton(referral_link_button, callback_data="referral_link")],
            [InlineKeyboardButton(increment_credit_button, callback_data="increment_credit")],
            [InlineKeyboardButton(admin_management_button, callback_data="admin_management")],
            [InlineKeyboardButton(manage_off_codes_button, callback_data="manage_off_codes")],
            [InlineKeyboardButton(manage_unit_value_button, callback_data="manage_unit_value")],
            [InlineKeyboardButton(broadcast_button, callback_data="broadcast_message")]
        ]
    else:
        account_info_button = translate_text("ℹ️ Account Information", user.preferred_language)
        request_agency_button = translate_text("🏢 Request Agency", user.preferred_language)
        keyboard = [
            [InlineKeyboardButton(account_info_button, callback_data="account_info")],
            [InlineKeyboardButton(request_agency_button, callback_data="request_agency")],
            [InlineKeyboardButton(settings_button, callback_data="settings")],
            [InlineKeyboardButton(chance_circle_button, callback_data="chance_circle")],
            [InlineKeyboardButton(ticket_button, callback_data="create_ticket")],
            [InlineKeyboardButton(referral_link_button, callback_data="referral_link")],
            [InlineKeyboardButton(increment_credit_button, callback_data="increment_credit")],
            [InlineKeyboardButton(manage_order_button, callback_data="manage_order")]
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_message = translate_text(
        "🎉 Welcome to the bot! 🎊\n\n"
        "We are thrilled to have you here! 🌟\n"
        "You can now enjoy all the features of our bot 🚀.\n"
        "If you need any help, feel free to ask! 🛠️\n\n"
        "Enjoy your experience! 😊",
        user.preferred_language
    )

    if update.callback_query:
        await safe_edit_message_text(update, context, new_text=welcome_message, reply_markup=reply_markup)
    elif update.message:
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def safe_edit_message_text(update: Update, context: ContextTypes.DEFAULT_TYPE, new_text: str, reply_markup=None):
    try:
        current_message = update.callback_query.message.text
        if current_message != new_text:
            await update.callback_query.message.edit_text(text=new_text, reply_markup=reply_markup)
    except Exception as e:
        if "Message is not modified" not in str(e):
            raise

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()
    selected_language = query.data

    if selected_language in languages:
        user.preferred_language = languages[selected_language]
        session.commit()
        translated_message = translate_text("✅ Language set successfully! 🌟 Translating messages... 🌍", user.preferred_language)
        await query.answer()
        await safe_edit_message_text(update, context, new_text=translated_message)
        await show_main_menu(update, context, user)

    session.close()

async def handle_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    keyboard = [[InlineKeyboardButton(lang, callback_data=lang)] for lang in languages.keys()]
    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard.append([InlineKeyboardButton(back_button, callback_data="back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    settings_message = translate_text("🌍 Please choose your language 🗣️:", user.preferred_language)

    await query.edit_message_text(settings_message, reply_markup=reply_markup)

    session.close()

async def handle_chance_circle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()
    now = datetime.now(timezone.utc)

    if user.last_chance_time.tzinfo is None:
        user.last_chance_time = user.last_chance_time.replace(tzinfo=timezone.utc)

    if now - user.last_chance_time >= timedelta(days=1):
        user.last_chance_time = now
        credit_reward = random.randint(10, 100)
        user.remaining_credit += credit_reward
        session.commit()

        reward_message = translate_text(f"🎉 Congratulations! You've received {credit_reward} units of credit!", user.preferred_language)
        await update.callback_query.message.reply_text(reward_message)
    else:
        wait_time = timedelta(days=1) - (now - user.last_chance_time)
        wait_hours = wait_time.total_seconds() // 3600
        wait_minutes = (wait_time.total_seconds() % 3600) // 60

        wait_message = translate_text(f"⏳ You can use the Chance Circle again in {int(wait_hours)} hours and {int(wait_minutes)} minutes.", user.preferred_language)
        await update.callback_query.message.reply_text(wait_message)

    await show_main_menu(update, context, user)
    session.close()

async def handle_account_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    if user.join_date.tzinfo is None:
        user.join_date = user.join_date.replace(tzinfo=timezone.utc)

    membership_duration = (datetime.now(timezone.utc) - user.join_date).days

    account_info_text = (
        f"ℹ️ Account Information:\n\n"
        f"📅 Membership Duration: {membership_duration} days\n"
        f"💳 Used Credit: {user.used_credit} units\n"
        f"💰 Remaining Credit: {user.remaining_credit} units\n"
        f"🎁 Credit from Referrals: {user.referral_credit} units\n"
        f"💵 Earnings from Sub-transactions: {user.sub_transaction_earnings} units"
    )

    if user.preferred_language == "fa":
        account_info_text = translate_text(account_info_text, "fa")

    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard = [[InlineKeyboardButton(back_button, callback_data="back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.answer()
    await query.edit_message_text(account_info_text, reply_markup=reply_markup)
    session.close()

async def handle_request_agency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    request_text = translate_text("💼 Please enter your daily sales (e.g., 200 dollars or 200 rials):", user.preferred_language)
    await query.message.edit_text(request_text)

    context.user_data['awaiting_sales_input'] = True
    session.close()

async def handle_sales_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    if context.user_data.get('awaiting_sales_input'):
        daily_sales = update.message.text
        new_request = AgencyRequest(user_id=user.id, daily_sales=daily_sales)
        session.add(new_request)
        session.commit()

        request_id = new_request.id
        confirmation_text = translate_text(f"✅ Your request has been added. Admins will review it soon. Your request ID: #{request_id} 🎉", user.preferred_language)

        await update.message.reply_text(confirmation_text)

        for admin in session.query(User).filter_by(is_admin=True).all():
            await context.bot.send_message(
                chat_id=admin.num_id,
                text=f"📩 New agency request from @{user.username}:\n\n💼 Daily Sales: {daily_sales}\n🆔 Request ID: #{request_id}"
            )

        context.user_data['awaiting_sales_input'] = False

    session.close()

async def handle_view_agency_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()

    admin = session.query(User).filter_by(num_id=update.effective_user.id, is_admin=True).first()
    if admin:
        pending_requests = session.query(AgencyRequest).filter_by(status='pending').all()

        if pending_requests:
            for request in pending_requests:
                user = session.query(User).filter_by(id=request.user_id).first()
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Approve", callback_data=f"approve_{request.id}"),
                        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{request.id}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.reply_text(
                    f"🆔 Request ID: #{request.id}\n👤 User: @{user.username}\n💼 Daily Sales: {request.daily_sales}",
                    reply_markup=reply_markup
                )
        else:
            await query.message.reply_text("❌ There are no pending agency requests.")

    session.close()

async def handle_agency_request_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()

    action, request_id = query.data.split('_')
    request = session.query(AgencyRequest).filter_by(id=request_id).first()

    if request:
        user = session.query(User).filter_by(id=request.user_id).first()

        if action == "approve":
            request.status = 'approved'
            session.commit()
            await context.bot.send_message(chat_id=user.num_id, text="🎉 Your agency request has been approved! ✅")
            await query.message.reply_text(f"Request #{request_id} has been approved. ✅")

        elif action == "reject":
            request.status = 'rejected'
            session.commit()
            await context.bot.send_message(chat_id=user.num_id, text="❌ Your agency request has been rejected.")
            await query.message.reply_text(f"Request #{request_id} has been rejected. ❌")

        session.delete(request)
        session.commit()

    session.close()

async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()
    await show_main_menu(update, context, user)
    session.close()

async def check_channel_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    try:
        member = await context.bot.get_chat_member(chat_id="@sultanpanel", user_id=user.num_id)

        if member.status in ["member", "administrator", "creator"]:
            await show_main_menu(update, context, user)
        else:
            await prompt_user_to_join(update, context, user.preferred_language)
    except Exception:
        await prompt_user_to_join(update, context, user.preferred_language)

    session.close()

async def prompt_user_to_join(update: Update, context: ContextTypes.DEFAULT_TYPE, language):
    join_message = translate_text("🔗 Please join our channel @sultanpanel to continue 😊", language)
    keyboard = [
        [InlineKeyboardButton("✅ Check Membership", callback_data="check_membership")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.message.edit_text(f"{join_message}\n\n👉 [Click here to join the channel](https://t.me/sultanpanel)", reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(f"{join_message}\n\n👉 [Click here to join the channel](https://t.me/sultanpanel)", reply_markup=reply_markup, parse_mode='Markdown')

async def handle_create_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()
    await query.edit_message_text(translate_text("Please enter the title of your ticket:", user.preferred_language))
    context.user_data['awaiting_ticket_title'] = True
    context.user_data['awaiting_ticket_description'] = False
    session.close()

async def handle_ticket_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    if context.user_data.get('awaiting_ticket_title'):
        context.user_data['ticket_title'] = update.message.text
        await update.message.reply_text(translate_text("Please enter the description of your ticket:", user.preferred_language))
        context.user_data['awaiting_ticket_title'] = False
        context.user_data['awaiting_ticket_description'] = True
    session.close()

async def handle_ticket_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    if context.user_data.get('awaiting_ticket_description'):
        ticket_description = update.message.text
        ticket_title = context.user_data.get('ticket_title')
        new_ticket = Ticket(user_id=user.id, title=ticket_title, description=ticket_description)
        session.add(new_ticket)
        session.commit()

        await update.message.reply_text(translate_text("✅ Your ticket has been created. Our support team will get back to you soon.", user.preferred_language))
        
        context.user_data['awaiting_ticket_description'] = False
        context.user_data['ticket_title'] = None

    session.close()

async def handle_view_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()

    admin = session.query(User).filter_by(num_id=update.effective_user.id, is_admin=True).first()
    if admin:
        open_tickets = session.query(Ticket).filter_by(status='open').all()

        if open_tickets:
            keyboard = [[InlineKeyboardButton(ticket.title, callback_data=f"view_ticket_{ticket.id}")] for ticket in open_tickets]
            back_button = translate_text("🔙 Back", admin.preferred_language)
            keyboard.append([InlineKeyboardButton(back_button, callback_data="back")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("🎟️ Open Tickets:", reply_markup=reply_markup)
        else:
            await query.message.reply_text("❌ There are no open tickets.")

    session.close()

async def handle_view_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()

    admin = session.query(User).filter_by(num_id=update.effective_user.id, is_admin=True).first()
  
    if admin:
        try:
            action, ticket_id = query.data.split('_', 1)
        except ValueError:
            await query.message.reply_text("Invalid data received, please try again.")
            return

        ticket = session.query(Ticket).filter_by(id=ticket_id.split('_')[1]).first()

        if ticket:
            await query.message.reply_text(f"🎟️ Ticket Title: {ticket.title}\n📝 Description: {ticket.description}")
            context.user_data['responding_ticket_id'] = ticket.id
            context.user_data['awaiting_ticket_response'] = True

    session.close()

async def handle_ticket_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    admin = session.query(User).filter_by(num_id=update.effective_user.id, is_admin=True).first()

    if context.user_data.get('awaiting_ticket_response'):
        response = update.message.text
        ticket_id = context.user_data.get('responding_ticket_id')
        ticket = session.query(Ticket).filter_by(id=ticket_id).first()

        if ticket:
            user = session.query(User).filter_by(id=ticket.user_id).first()
            await context.bot.send_message(chat_id=user.num_id, text=f"📩 Response to your ticket '{ticket.title}':\n\n{response}")
            ticket.status = 'closed'
            session.commit()

            await update.message.reply_text("✅ The ticket has been closed and the response has been sent to the user.")
        
        context.user_data['awaiting_ticket_response'] = False

    session.close()


async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    if context.user_data.get('awaiting_sales_input'):
        daily_sales = update.message.text
        new_request = AgencyRequest(user_id=user.id, daily_sales=daily_sales)
        session.add(new_request)
        session.commit()

        request_id = new_request.id
        confirmation_text = translate_text(f"✅ Your request has been added. Admins will review it soon. Your request ID: #{request_id} 🎉", user.preferred_language)

        await update.message.reply_text(confirmation_text)

        for admin in session.query(User).filter_by(is_admin=True).all():
            await context.bot.send_message(
                chat_id=admin.num_id,
                text=f"📩 New agency request from @{user.username}:\n\n💼 Daily Sales: {daily_sales}\n🆔 Request ID: #{request_id}"
            )

        context.user_data['awaiting_sales_input'] = False

    elif context.user_data.get('awaiting_off_code'):
        off_code = update.message.text.strip()
        context.user_data['off_code'] = off_code
        await update.message.reply_text(translate_text("Please enter the discount percent (e.g., 20):", user.preferred_language))
        context.user_data['awaiting_off_code'] = False
        context.user_data['awaiting_discount_percent'] = True

    elif context.user_data.get('awaiting_discount_percent'):
        discount_percent = int(update.message.text.strip())
        off_code = context.user_data.get('off_code')
        new_code = DiscountCode(code=off_code, discount_percent=discount_percent)
        session.add(new_code)
        session.commit()

        await update.message.reply_text(f"✅ Discount code {off_code} with {discount_percent}% discount has been added.")
        context.user_data['awaiting_discount_percent'] = False
        context.user_data['off_code'] = None

    elif context.user_data.get('awaiting_discount_code'):
        discount_code = update.message.text.strip()
        discount = session.query(DiscountCode).filter_by(code=discount_code).first()

        if discount:
            discounted_amount = context.user_data['selected_increment_amount'] * (1 - discount.discount_percent / 100)
            user.remaining_credit += int(discounted_amount)
            session.commit()

            success_message = translate_text(f"✅ {int(discounted_amount)} units have been added to your credit!", user.preferred_language)
            await update.message.reply_text(success_message)
        else:
            invalid_code_message = translate_text("❌ Invalid discount code. Adding full amount to your credit.", user.preferred_language)
            await update.message.reply_text(invalid_code_message)
            await add_credit_to_user(update, context, user)

        context.user_data['awaiting_discount_code'] = False

    elif context.user_data.get('awaiting_ticket_title'):
        context.user_data['ticket_title'] = update.message.text
        await update.message.reply_text(translate_text("Please enter the description of your ticket:", user.preferred_language))
        context.user_data['awaiting_ticket_title'] = False
        context.user_data['awaiting_ticket_description'] = True

    elif context.user_data.get('awaiting_ticket_description'):
        ticket_description = update.message.text
        ticket_title = context.user_data.get('ticket_title')
        new_ticket = Ticket(user_id=user.id, title=ticket_title, description=ticket_description)
        session.add(new_ticket)
        session.commit()

        await update.message.reply_text(translate_text("✅ Your ticket has been created. Our support team will get back to you soon.", user.preferred_language))

        context.user_data['awaiting_ticket_description'] = False
        context.user_data['ticket_title'] = None

    elif context.user_data.get('awaiting_ticket_response'):
        response = update.message.text
        ticket_id = context.user_data.get('responding_ticket_id')
        ticket = session.query(Ticket).filter_by(id=ticket_id).first()

        if ticket:
            user = session.query(User).filter_by(id=ticket.user_id).first()
            await context.bot.send_message(chat_id=user.num_id, text=f"📩 Response to your ticket '{ticket.title}':\n\n{response}")
            ticket.status = 'closed'
            session.commit()

            await update.message.reply_text("✅ The ticket has been closed and the response has been sent to the user.")
        
        context.user_data['awaiting_ticket_response'] = False

    elif context.user_data.get('awaiting_order_id'):
        order_id = update.message.text.strip()
        response = requests.post(API_URL, data={"key": API_KEY, "action": "status", "order": order_id})
        order_status = response.json()

        status_message = (
            f"Order Status:\n"
            f"Charge: {order_status.get('charge')}\n"
            f"Start Count: {order_status.get('start_count')}\n"
            f"Status: {order_status.get('status')}\n"
            f"Remains: {order_status.get('remains')}\n"
            f"Currency: {order_status.get('currency')}"
        )

        await update.message.reply_text(translate_text(status_message, user.preferred_language))

        context.user_data['awaiting_order_id'] = False

    elif context.user_data.get('awaiting_service_id'):
        service_id = update.message.text.strip()
        response = requests.post(API_URL, data={"key": API_KEY, "action": "services"})
        services = response.json()

        
        service = next((s for s in services if s['service'] == (service_id)), None)

        if service:
            context.user_data['service_id'] = service_id
            await update.message.reply_text(translate_text("Please enter the Link:", user.preferred_language))
            context.user_data['awaiting_link'] = True
            context.user_data['awaiting_service_id'] = False
        else:
            await update.message.reply_text(translate_text("Invalid Service ID. Please try again.", user.preferred_language))
            context.user_data['awaiting_service_id'] = True

    elif context.user_data.get('awaiting_link'):
        link = update.message.text.strip()
        context.user_data['link'] = link
        await update.message.reply_text(translate_text("Please enter the Quantity:", user.preferred_language))
        context.user_data['awaiting_quantity'] = True
        context.user_data['awaiting_link'] = False

    elif context.user_data.get('awaiting_quantity'):
        quantity = int(update.message.text.strip())
        response = requests.post(API_URL, data={"key": API_KEY, "action": "services"})
        services = response.json()

        service = next((s for s in services if s['service'] == (context.user_data['service_id'])), None)
        if service and int(service['min']) <= quantity <= int(service['max']):
            # Convert Toman to Dollar
            toman_to_dollar_rate = 42000  # Example conversion rate: 1 USD = 42,000 Toman
            toman_rate = float(service['rate']) * quantity / 1000
            dollar_amount = toman_rate / toman_to_dollar_rate
            
            # Retrieve the current unit value
            unit = session.query(Unit).filter_by(name="default").first()
            if unit:
                unit_value_cents = unit.value
            else:
                await update.message.reply_text("Unit value is not set. Please contact an admin.")
                session.close()
                return

            # Convert Dollar to User's Unit Value (credit)
            total_cost_in_credits = dollar_amount * (100 / unit_value_cents)  # Convert dollar amount to credit units
            print(total_cost_in_credits)
            print(user.remaining_credit)
            if user.remaining_credit >= total_cost_in_credits:
                # Deduct the cost from user's credit
                user.remaining_credit -= total_cost_in_credits
                session.commit()

                add_order_response = requests.post(API_URL, data={
                    "key": API_KEY,
                    "action": "add",
                    "service": context.user_data['service_id'],
                    "link": context.user_data['link'],
                    "quantity": quantity
                })

                order_response = add_order_response.json()
                order_id = order_response.get('order')

                await update.message.reply_text(f"Order placed successfully! Order ID: {order_id}")
                await update.message.reply_text(f"{total_cost_in_credits:.2f} credits have been deducted from your account.")
            else:
                await update.message.reply_text("Insufficient credit to place this order. Please add more credit and try again.")
        else:
            await update.message.reply_text(translate_text("Invalid quantity or service ID. Please try again.", user.preferred_language))

        context.user_data['awaiting_quantity'] = False

    elif context.user_data.get('awaiting_unit_value'):
        unit_value_dollars = float(update.message.text.strip())
        unit_value_cents = int(unit_value_dollars * 100)

        unit = session.query(Unit).filter_by(name="default").first()
        print(unit)
        if unit:
            unit.value = unit_value_cents
            
        else:
            new_unit = Unit(name="default", value=unit_value_cents)
            print(new_unit)
            session.add(new_unit)
        
        session.commit()

        await update.message.reply_text(translate_text(f"Unit value set to ${unit_value_dollars}.", user.preferred_language))
        context.user_data['awaiting_unit_value'] = False

    elif context.user_data.get('awaiting_discount_response'):
        response = update.message.text.strip().lower()

        if response == 'yes':
            ask_code_message = translate_text("Please enter your discount code:", user.preferred_language)
            await update.message.reply_text(ask_code_message)
            context.user_data['awaiting_discount_code'] = True

    elif context.user_data.get('awaiting_off_code_deletion'):
        off_code = update.message.text.strip()
        code_to_delete = session.query(DiscountCode).filter_by(code=off_code).first()

        if code_to_delete:
            session.delete(code_to_delete)
            session.commit()
            await update.message.reply_text(f"✅ Discount code {off_code} has been deleted.")
        else:
            await update.message.reply_text(f"❌ Discount code {off_code} not found.")

        context.user_data['awaiting_off_code_deletion'] = False

    session.close()

async def handle_manage_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    add_order_button = translate_text("➕ Add Order", user.preferred_language)
    view_order_button = translate_text("🔍 View Order", user.preferred_language)
    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard = [
        [InlineKeyboardButton(add_order_button, callback_data="add_order")],
        [InlineKeyboardButton(view_order_button, callback_data="view_order")],
        [InlineKeyboardButton(back_button, callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("🛒 Manage Order", reply_markup=reply_markup)
    session.close()


async def add_credit_to_user(update, context, user):
    session = Session()

    try:
        user = session.query(User).filter_by(id=user.id).first()

        if user:
            increment_amount = context.user_data['selected_increment_amount']
            user.remaining_credit += increment_amount
            session.commit()

            success_message = translate_text(f"✅ {increment_amount} units have been added to your credit!", user.preferred_language)
            await update.message.reply_text(success_message)
        else:
            await update.message.reply_text("❌ Unable to find the user in the database.")

    except Exception as e:
        print(f"Error adding credit: {e}")
        await update.message.reply_text("❌ An error occurred while adding credit. Please try again later.")

    finally:
        session.close()

async def handle_referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    referral_link = f"https://t.me/Sultanpanel_bot?start={user.num_id}"
    referral_message = translate_text(f"🔗 Your referral link is:\n{referral_link}", user.preferred_language)

    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard = [[InlineKeyboardButton(back_button, callback_data="back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(referral_message, reply_markup=reply_markup)
    session.close()

async def handle_admin_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    add_admin_button = translate_text("➕ Add Admin", user.preferred_language)
    delete_admin_button = translate_text("➖ Delete Admin", user.preferred_language)

    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard = [
        [InlineKeyboardButton(add_admin_button, callback_data="add_admin")],
        [InlineKeyboardButton(delete_admin_button, callback_data="delete_admin")],
        [InlineKeyboardButton(back_button, callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("🔧 Admin Management", reply_markup=reply_markup)
    session.close()

async def handle_manage_off_codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    add_code_button = translate_text("➕ Add Off Code", user.preferred_language)
    view_codes_button = translate_text("📋 View Off Codes", user.preferred_language)
    delete_code_button = translate_text("➖ Delete Off Code", user.preferred_language)
    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard = [
        [InlineKeyboardButton(add_code_button, callback_data="add_off_code")],
        [InlineKeyboardButton(view_codes_button, callback_data="view_off_codes")],
        [InlineKeyboardButton(delete_code_button, callback_data="delete_off_code")],
        [InlineKeyboardButton(back_button, callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("🔧 Manage Off Codes", reply_markup=reply_markup)
    session.close()

async def handle_add_off_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    await query.edit_message_text(translate_text("Please enter the off code (e.g., SAVE20):", user.preferred_language))
    context.user_data['awaiting_off_code'] = True
    session.close()

async def handle_view_off_codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()

    admin = session.query(User).filter_by(num_id=update.effective_user.id, is_admin=True).first()
    if admin:
        off_codes = session.query(DiscountCode).all()

        if off_codes:
            code_list = "\n".join([f"{code.code} - {code.discount_percent}%" for code in off_codes])
            await query.message.reply_text(f"📋 Discount Codes:\n\n{code_list}")
        else:
            await query.message.reply_text("❌ No discount codes available.")

    session.close()

async def handle_delete_off_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    await query.edit_message_text(translate_text("Please enter the off code you want to delete:", user.preferred_language))
    context.user_data['awaiting_off_code_deletion'] = True
    session.close()

async def handle_off_code_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    if context.user_data.get('awaiting_off_code'):
        off_code = update.message.text.strip()
        context.user_data['off_code'] = off_code
        await update.message.reply_text(translate_text("Please enter the discount percent (e.g., 20):", context.user_data.get('preferred_language')))
        context.user_data['awaiting_off_code'] = False
        context.user_data['awaiting_discount_percent'] = True

    elif context.user_data.get('awaiting_discount_percent'):
        discount_percent = int(update.message.text.strip())
        off_code = context.user_data.get('off_code')
        new_code = DiscountCode(code=off_code, discount_percent=discount_percent)
        session.add(new_code)
        session.commit()

        await update.message.reply_text(f"✅ Discount code {off_code} with {discount_percent}% discount has been added.")
        context.user_data['awaiting_discount_percent'] = False
        context.user_data['off_code'] = None

    elif context.user_data.get('awaiting_off_code_deletion'):
        off_code = update.message.text.strip()
        code_to_delete = session.query(DiscountCode).filter_by(code=off_code).first()

        if code_to_delete:
            session.delete(code_to_delete)
            session.commit()
            await update.message.reply_text(f"✅ Discount code {off_code} has been deleted.")
        else:
            await update.message.reply_text(f"❌ Discount code {off_code} not found.")

        context.user_data['awaiting_off_code_deletion'] = False

    session.close()

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    users_button = translate_text("👥 Users", user.preferred_language)
    admins_button = translate_text("👤 Admins", user.preferred_language)
    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard = [
        [InlineKeyboardButton(users_button, callback_data="broadcast_users")],
        [InlineKeyboardButton(admins_button, callback_data="broadcast_admins")],
        [InlineKeyboardButton(back_button, callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("📢 Broadcast Message", reply_markup=reply_markup)
    session.close()

async def handle_broadcast_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text(translate_text("Please enter the message to broadcast to all users:", context.user_data.get('preferred_language')))
    context.user_data['broadcast_to'] = 'users'
    context.user_data['awaiting_broadcast_message'] = True

async def handle_broadcast_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text(translate_text("Please enter the message to broadcast to all admins:", context.user_data.get('preferred_language')))
    context.user_data['broadcast_to'] = 'admins'
    context.user_data['awaiting_broadcast_message'] = True

async def handle_broadcast_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    broadcast_to = context.user_data.get('broadcast_to')
    print(broadcast_to)
    if context.user_data.get('awaiting_broadcast_message'):
        message = update.message.text
        if broadcast_to == 'users':
            users = session.query(User).filter_by(is_bot=False).all()
        elif broadcast_to == 'admins':
            users = session.query(User).filter_by(is_admin=True).all()
        else:
            users = []

        for user in users:
            try:
                await context.bot.send_message(chat_id=user.num_id, text=message)
            except Exception as e:
                print(f"Failed to send message to {user.username}: {e}")

        await update.message.reply_text(f"✅ Message sent to all {broadcast_to}.")
        context.user_data['awaiting_broadcast_message'] = False

    session.close()

async def handle_increment_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    amounts = [20, 40, 60, 80, 100]
    keyboard = [[InlineKeyboardButton(f"{amount} units", callback_data=f"increment_{amount}")] for amount in amounts]
    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard.append([InlineKeyboardButton(back_button, callback_data="back")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    increment_message = translate_text("Please select the amount of credit you want to add:", user.preferred_language)
    await query.edit_message_text(increment_message, reply_markup=reply_markup)
    session.close()

async def handle_increment_amount_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    action, amount = query.data.split('_')
    context.user_data['selected_increment_amount'] = int(amount)

    ask_discount_message = translate_text("Do you have a discount code? (Yes/No)", user.preferred_language)
    await query.edit_message_text(ask_discount_message)
    context.user_data['awaiting_discount_response'] = True
    session.close()

async def handle_discount_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    if context.user_data.get('awaiting_discount_response'):
        response = update.message.text.strip().lower()

        if response == 'yes':
            ask_code_message = translate_text("Please enter your discount code:", user.preferred_language)
            await update.message.reply_text(ask_code_message)
            context.user_data['awaiting_discount_code'] = True
            context.user_data['awaiting_discount_response'] = False

    session.close()

async def handle_manage_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    add_order_button = translate_text("➕ Add Order", user.preferred_language)
    view_order_button = translate_text("🔍 View Order", user.preferred_language)
    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard = [
        [InlineKeyboardButton(add_order_button, callback_data="add_order")],
        [InlineKeyboardButton(view_order_button, callback_data="view_order")],
        [InlineKeyboardButton(back_button, callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("🛒 Manage Order", reply_markup=reply_markup)
    session.close()

async def handle_view_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    await query.edit_message_text(translate_text("Please enter the Order ID:", user.preferred_language))
    context.user_data['awaiting_order_id'] = True
    session.close()

async def handle_order_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    if context.user_data.get('awaiting_order_id'):
        order_id = update.message.text.strip()
        response = requests.post(API_URL, data={"key": API_KEY, "action": "status", "order": order_id})
        order_status = response.json()

        status_message = (
            f"Order Status:\n"
            f"Charge: {order_status.get('charge')}\n"
            f"Start Count: {order_status.get('start_count')}\n"
            f"Status: {order_status.get('status')}\n"
            f"Remains: {order_status.get('remains')}\n"
            f"Currency: {order_status.get('currency')}"
        )

        await update.message.reply_text(translate_text(status_message, user.preferred_language))

        context.user_data['awaiting_order_id'] = False

    session.close()

async def handle_add_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    await query.edit_message_text(translate_text("Please enter the Service ID:", user.preferred_language))
    context.user_data['awaiting_service_id'] = True
    session.close()

async def handle_service_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    if context.user_data.get('awaiting_service_id'):
        service_id = update.message.text.strip()
        response = requests.post(API_URL, data={"key": API_KEY, "action": "services"})
        services = response.json()

        service = next((s for s in services if s['service'] == (service_id)), None)

        if service:
            context.user_data['service_id'] = service_id
            await update.message.reply_text(translate_text("Please enter the Link:", user.preferred_language))
            context.user_data['awaiting_link'] = True
        else:
            await update.message.reply_text(translate_text("Invalid Service ID. Please try again.", user.preferred_language))
            context.user_data['awaiting_service_id'] = True

    session.close()

async def handle_link_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    if context.user_data.get('awaiting_link'):
        link = update.message.text.strip()
        context.user_data['link'] = link
        await update.message.reply_text(translate_text("Please enter the Quantity:", user.preferred_language))
        context.user_data['awaiting_quantity'] = True

    session.close()

async def handle_quantity_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    if context.user_data.get('awaiting_quantity'):
        quantity = int(update.message.text.strip())
        response = requests.post(API_URL, data={"key": API_KEY, "action": "services"})
        services = response.json()

        service = next((s for s in services if s['service'] == int(context.user_data['service_id'])), None)

        if service and service['min'] <= quantity <= service['max']:
            toman_rate = float(service['rate']) * quantity / 1000
            dollar_rate = toman_rate / (user.unit_value / 100)
            add_order_response = requests.post(API_URL, data={
                "key": API_KEY,
                "action": "add",
                "service": context.user_data['service_id'],
                "link": context.user_data['link'],
                "quantity": quantity
            })

            order_response = add_order_response.json()
            order_id = order_response.get('order')

            await update.message.reply_text(translate_text(f"Order placed successfully! Order ID: {order_id}", user.preferred_language))

        else:
            await update.message.reply_text(translate_text("Invalid quantity or service ID. Please try again.", user.preferred_language))

        context.user_data['awaiting_quantity'] = False

    session.close()

async def handle_manage_unit_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    await query.edit_message_text(translate_text("Please enter the unit value in dollars (e.g., 0.1):", user.preferred_language))
    context.user_data['awaiting_unit_value'] = True
    session.close()

async def handle_unit_value_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    if context.user_data.get('awaiting_unit_value'):
        unit_value_dollars = float(update.message.text.strip())
        unit_value_cents = int(unit_value_dollars * 100)

        unit = session.query(Unit).filter_by(name="default").first()
        print(unit)
        if unit:
            unit.value = unit_value_cents
            
        else:
            new_unit = Unit(name="default", value=unit_value_cents)
            print(new_unit)
            session.add(new_unit)
        
        session.commit()

        await update.message.reply_text(translate_text(f"Unit value set to ${unit_value_dollars}.", user.preferred_language))
        context.user_data['awaiting_unit_value'] = False

    session.close()


def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_messages))
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(handle_language_selection, pattern='^(' + '|'.join(languages.keys()) + ')$'))
    application.add_handler(CallbackQueryHandler(handle_account_info, pattern='^account_info$'))
    application.add_handler(CallbackQueryHandler(handle_request_agency, pattern='^request_agency$'))
    application.add_handler(CallbackQueryHandler(handle_view_agency_requests, pattern='^view_agency_requests$'))
    application.add_handler(CallbackQueryHandler(handle_agency_request_action, pattern=r'^(approve|reject)_\d+$'))
    application.add_handler(CallbackQueryHandler(check_channel_membership, pattern='^check_membership$'))
    application.add_handler(CallbackQueryHandler(handle_back, pattern='^back$'))
    application.add_handler(CallbackQueryHandler(handle_settings, pattern='^settings$'))
    application.add_handler(CallbackQueryHandler(handle_chance_circle, pattern='^chance_circle$'))
    application.add_handler(CallbackQueryHandler(handle_create_ticket, pattern='^create_ticket$'))
    application.add_handler(CallbackQueryHandler(handle_view_tickets, pattern='^view_tickets$'))
    application.add_handler(CallbackQueryHandler(handle_view_ticket, pattern=r'^view_ticket_\d+$'))
    application.add_handler(CallbackQueryHandler(handle_referral_link, pattern='^referral_link$'))
    application.add_handler(CallbackQueryHandler(handle_admin_management, pattern='^admin_management$'))
    application.add_handler(CallbackQueryHandler(handle_manage_off_codes, pattern='^manage_off_codes$'))
    application.add_handler(CallbackQueryHandler(handle_add_off_code, pattern='^add_off_code$'))
    application.add_handler(CallbackQueryHandler(handle_view_off_codes, pattern='^view_off_codes$'))
    application.add_handler(CallbackQueryHandler(handle_delete_off_code, pattern='^delete_off_code$'))
    application.add_handler(CallbackQueryHandler(handle_broadcast_message, pattern='^broadcast_message$'))
    application.add_handler(CallbackQueryHandler(handle_broadcast_users, pattern='^broadcast_users$'))
    application.add_handler(CallbackQueryHandler(handle_broadcast_admins, pattern='^broadcast_admins$'))
    application.add_handler(CallbackQueryHandler(handle_increment_credit, pattern='^increment_credit$'))
    application.add_handler(CallbackQueryHandler(handle_increment_amount_selection, pattern=r'^increment_\d+$'))
    application.add_handler(CallbackQueryHandler(handle_manage_order, pattern='^manage_order$'))
    application.add_handler(CallbackQueryHandler(handle_add_order, pattern='^add_order$'))
    application.add_handler(CallbackQueryHandler(handle_view_order, pattern='^view_order$'))
    application.add_handler(CallbackQueryHandler(handle_manage_unit_value, pattern='^manage_unit_value$'))

    application.run_polling()

if __name__ == '__main__':
    main()
