import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from deep_translator import GoogleTranslator
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone, timedelta

TOKEN = "7120665237:AAHfUL5xgyEsZe9af1mdSr4FwiLoVl1vcP8"
NOTIFICATION_CHANNEL_ID = -1002147674595

languages = {
    "🇬🇧 English": "en",
    "🇮🇷 فارسی": "fa"
}

admin_usernames = ["Canyildiz13816", "followergir_support"]

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

engine = create_engine('sqlite:///telegram_bot.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def translate_text(text, target_language):
    if target_language:
        return GoogleTranslator(source='auto', target=target_language).translate(text)
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
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
            is_admin=is_admin
        )
        session.add(new_user)
        session.commit()

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
        await show_main_menu(update, context, new_user)
    else:
        await check_channel_membership(update, context)

    session.close()

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    settings_button = translate_text("⚙️ Settings", user.preferred_language)
    chance_circle_button = translate_text("🎯 Chance Circle", user.preferred_language)
    ticket_button = translate_text("🎫 Create Ticket", user.preferred_language)

    if user.is_admin:
        account_info_button = translate_text("ℹ️ Account Information", user.preferred_language)
        view_agencies_button = translate_text("📊 View Agency Requests", user.preferred_language)
        view_tickets_button = translate_text("🎟️ View Tickets", user.preferred_language)
        keyboard = [
            [InlineKeyboardButton(account_info_button, callback_data="account_info")],
            [InlineKeyboardButton(view_agencies_button, callback_data="view_agency_requests")],
            [InlineKeyboardButton(view_tickets_button, callback_data="view_tickets")],
            [InlineKeyboardButton(settings_button, callback_data="settings")],
            [InlineKeyboardButton(chance_circle_button, callback_data="chance_circle")]
        ]
    else:
        account_info_button = translate_text("ℹ️ Account Information", user.preferred_language)
        request_agency_button = translate_text("🏢 Request Agency", user.preferred_language)
        keyboard = [
            [InlineKeyboardButton(account_info_button, callback_data="account_info")],
            [InlineKeyboardButton(request_agency_button, callback_data="request_agency")],
            [InlineKeyboardButton(settings_button, callback_data="settings")],
            [InlineKeyboardButton(chance_circle_button, callback_data="chance_circle")],
            [InlineKeyboardButton(ticket_button, callback_data="create_ticket")]
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
    except telegram.error.BadRequest as e:
        if str(e) != "Message is not modified: specified new message content and reply markup are exactly the same as a current content and reply markup of the message":
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

        await asyncio.sleep(2)

        await show_main_menu(update, context, user)

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
    await query.message.reply_text(translate_text("Please enter the title of your ticket:", user.preferred_language))
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
            action, ticket_id = query.data.split('_', 1)  # Only split into two parts
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

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    if context.user_data.get('awaiting_ticket_title'):
        # Handle ticket title
        context.user_data['ticket_title'] = update.message.text
        await update.message.reply_text(translate_text("Please enter the description of your ticket:", user.preferred_language))
        context.user_data['awaiting_ticket_title'] = False
        context.user_data['awaiting_ticket_description'] = True

    elif context.user_data.get('awaiting_ticket_description'):
        # Handle ticket description
        ticket_description = update.message.text
        ticket_title = context.user_data.get('ticket_title')
        new_ticket = Ticket(user_id=user.id, title=ticket_title, description=ticket_description)
        session.add(new_ticket)
        session.commit()

        await update.message.reply_text(translate_text("✅ Your ticket has been created. Our support team will get back to you soon.", user.preferred_language))

        context.user_data['awaiting_ticket_description'] = False
        context.user_data['ticket_title'] = None

    elif context.user_data.get('awaiting_ticket_response'):
        # Handle ticket response (for admins)
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

def main():
    application = ApplicationBuilder().token(TOKEN).build()

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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))

    application.run_polling()

if __name__ == '__main__':
    main()
