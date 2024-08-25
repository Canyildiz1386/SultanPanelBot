import random
import asyncio
import math
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from deep_translator import GoogleTranslator
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone, timedelta
from config import (
    TOKEN,
    NOTIFICATION_CHANNEL_ID,
    API_KEY,
    API_URL,
    admin_usernames,
    SOCIAL_MEDIA_PLATFORMS,
    REPRESENTATIVES,
    languages
)

# Setting up SQLAlchemy ORM base class
Base = declarative_base()


# User model for storing user details
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(Integer)
    num_id = Column(Integer)
    profile_url = Column(String)
    preferred_language = Column(String)
    is_premium = Column(Boolean)
    is_bot = Column(Boolean)
    is_admin = Column(Boolean, default=False)
    join_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    used_credit = Column(Integer, default=0)
    remaining_credit = Column(Integer, default=1)
    referral_credit = Column(Integer, default=0)
    sub_transaction_earnings = Column(Integer, default=0)
    last_chance_time = Column(DateTime, default=lambda: datetime.now(timezone.utc) - timedelta(days=1))
    last_ticket_time = Column(DateTime, default=lambda: datetime.now(timezone.utc) - timedelta(minutes=10))
    referrer_id = Column(Integer, nullable=True)


# AgencyRequest model for handling agency requests
class AgencyRequest(Base):
    __tablename__ = "agency_requests"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    daily_sales = Column(String)
    status = Column(String, default="pending")


# Ticket model for storing support tickets
class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    title = Column(String)
    description = Column(String)
    status = Column(String, default="open")


# DiscountCode model for storing discount codes
class DiscountCode(Base):
    __tablename__ = "discount_codes"
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    discount_percent = Column(Integer, nullable=False)


# ConversionRate model for storing conversion rates
class ConversionRate(Base):
    __tablename__ = "conversion_rate"
    id = Column(Integer, primary_key=True)
    rate = Column(Integer, nullable=False, default=60000)


# Unit model for storing unit values
class Unit(Base):
    __tablename__ = "units"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    value = Column(Integer, nullable=False)  # Default value set to 1


# Order model for storing orders
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    order_id = Column(Integer, unique=True, nullable=False)
    service_id = Column(String)
    link = Column(String)
    quantity = Column(Integer)
    status = Column(String, default="Pending")
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# Database setup
engine = create_engine("sqlite:///telegram_bot.db")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


# Helper function to translate text based on user's preferred language
def translate_text(text, target_language):
    if target_language:
        return GoogleTranslator(source="auto", target=target_language).translate(text)
    return text


# The start command handler, responsible for initiating the bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    referrer_id = None

    if context.args:
        try:
            referrer_id = int(context.args[0])
        except ValueError:
            pass

    # Fetch user details from the database
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    if not user:
        is_admin = update.effective_user.username in admin_usernames
        # Create a new user if it doesn't exist in the database
        new_user = User(
            username=update.effective_user.username,
            first_name=update.effective_user.first_name,
            last_name=update.effective_user.last_name,
            num_id=update.effective_user.id,
            profile_url=f"https://unavatar.io/telegram/{update.effective_user.username}",
            is_premium=update.effective_user.is_premium,
            is_bot=update.effective_user.is_bot,
            is_admin=is_admin,
            referrer_id=referrer_id,
        )
        session.add(new_user)
        session.commit()

        # Handle referral logic
        if referrer_id:
            referrer = session.query(User).filter_by(num_id=referrer_id).first()
            if referrer:
                referrer.remaining_credit += 10
                new_user.remaining_credit += 10
                session.commit()
                await context.bot.send_message(
                    chat_id=referrer.num_id,
                    text=translate_text(
                        f"🎉 Your referral has been successful! You and {new_user.username} have both received 10 credits. 🤑",
                        referrer.preferred_language,
                    ),
                )
        
        # Notify admin of a new user
        await context.bot.send_message(
            chat_id=NOTIFICATION_CHANNEL_ID,
            text=f"🎉 New {'admin' if new_user.is_admin else 'user'} joined! 🎉\n\n"
            f"👤 Username: @{new_user.username}\n"
            f"🧑‍💻 First Name: {new_user.first_name}\n"
            f"🧑‍💻 Last Name: {new_user.last_name}\n"
            f"🆔 ID: {new_user.num_id}\n"
            f"🌐 Profile URL: {new_user.profile_url}\n"
            f"💎 Premium: {'Yes' if new_user.is_premium else 'No'}\n"
            f"🤖 Bot: {'Yes' if new_user.is_bot else 'No'}",
        
        )

        # Prompt the user to select a language
        await prompt_language_selection(update, context, new_user)
    else:
        await check_channel_membership(update, context)

    session.close()


# Function to prompt user for language selection
async def prompt_language_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user
):
    languages = {"🇬🇧 English": "en", "🇮🇷 فارسی": "fa", "🇸🇦 العربية": "ar"}
    
    keyboard = [
        [InlineKeyboardButton(lang, callback_data=lang)] for lang in languages.keys()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    language_prompt = (
        "🌍 Please choose your language 🗣️\n"
        "لطفا زبان خود را انتخاب کنید:\n"
        "يرجى اختيار لغتك:\n"
    )

    await update.message.reply_text(language_prompt, reply_markup=reply_markup)

# Handle language selection and save the user's choice
async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()
    selected_language = query.data

    if selected_language in languages:
        user.preferred_language = languages[selected_language]
        session.commit()
        translated_message = translate_text(
            "✅ Language set successfully! 🌟 Translating messages... 🌍",
            user.preferred_language,
        )
        await query.answer()
        await query.edit_message_text(translated_message)
        await check_channel_membership(update, context)

    session.close()


# Show the main menu after a user has selected their language and joined the channel
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    session = Session()

    if not session.is_active:
        session.begin()

    user = session.merge(user)

    # Translate menu items based on user preference
    settings_button = translate_text("⚙️ Settings", user.preferred_language)
    chance_circle_button = translate_text("🎯 Chance Circle", user.preferred_language)
    ticket_button = translate_text(f'🎫 {"Send ticket" if user.preferred_language == "en" else "ارسال تیکت"}', user.preferred_language)
    referral_link_button = translate_text(f"🔗 {'Subcategory Link' if user.preferred_language == 'en' else 'لینک زیر مجموعه گیری' }", user.preferred_language)
    increment_credit_button = translate_text(
        "💳 Increase Credit", user.preferred_language
    )
    manage_conversion_rate_button = translate_text(
        "💲 Manage Conversion Rate", user.preferred_language
    )

    add_order_button = translate_text("➕ Add Order", user.preferred_language)
    view_order_button = translate_text("🔍 View Order", user.preferred_language)

    # Admin-specific menu items
    if user.is_admin:
        account_info_button = translate_text(
            "ℹ️ Account Information", user.preferred_language
        )
        view_agencies_button = translate_text(
            "📊 View Agency Requests", user.preferred_language
        )
        view_tickets_button = translate_text("🎟️ View Tickets", user.preferred_language)


        manage_unit_value_button = translate_text(
            "💲 Manage Unit Value", user.preferred_language
        )
        broadcast_button = translate_text(
            "📢 Broadcast Message" if user.preferred_language == "en" else "📢 اطلاع رسانی پیام", user.preferred_language
        )
        keyboard = [
            [InlineKeyboardButton(add_order_button, callback_data="add_order")],
            [InlineKeyboardButton(view_order_button, callback_data="view_order")],
            [InlineKeyboardButton(account_info_button, callback_data="account_info")],
            [
                InlineKeyboardButton(
                    view_agencies_button, callback_data="view_agency_requests"
                )
            ],
            [InlineKeyboardButton(view_tickets_button, callback_data="view_tickets")],
            [InlineKeyboardButton(settings_button, callback_data="settings")],
            [InlineKeyboardButton(chance_circle_button, callback_data="chance_circle")],
            [InlineKeyboardButton(referral_link_button, callback_data="referral_link")],
            [
                InlineKeyboardButton(
                    increment_credit_button, callback_data="increment_credit"
                )
            ],
            [
                InlineKeyboardButton(
                    manage_unit_value_button, callback_data="manage_unit_value"
                )
            ],
            [InlineKeyboardButton(broadcast_button, callback_data="broadcast_message")],
        ]
        keyboard.append(
            [
                InlineKeyboardButton(
                    manage_conversion_rate_button,
                    callback_data="manage_conversion_rate",
                )
            ]
        )

    # Regular user-specific menu items
    else:
        account_info_button = translate_text(
            "ℹ️ Account Information", user.preferred_language
        )
        request_agency_button = translate_text(
            "🏢 Representation Request", user.preferred_language
        )
        keyboard = [
            [InlineKeyboardButton(add_order_button, callback_data="add_order")],
            [InlineKeyboardButton(view_order_button, callback_data="view_order")],
            [InlineKeyboardButton(account_info_button, callback_data="account_info")],
            [
                InlineKeyboardButton(
                    request_agency_button, callback_data="request_agency"
                )
            ],
            [InlineKeyboardButton(settings_button, callback_data="settings")],
            [InlineKeyboardButton(chance_circle_button, callback_data="chance_circle")],
            [InlineKeyboardButton(ticket_button, callback_data="create_ticket")],
            [InlineKeyboardButton(referral_link_button, callback_data="referral_link")],
            [
                InlineKeyboardButton(
                    increment_credit_button, callback_data="increment_credit"
                )
            ],
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_message = translate_text(
        "🎉 Welcome to the bot! 🎊\n\n"
        "We are thrilled to have you here! 🌟\n"
        "You can now enjoy all the features of our bot 🚀.\n"
        "If you need any help, feel free to ask! 🛠️\n\n"
        "Enjoy your experience! 😊",
        user.preferred_language,
    )

    if update.callback_query:
        await safe_edit_message_text(
            update, context, new_text=welcome_message, reply_markup=reply_markup
        )
    elif update.message:
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)

    session.close()  # Close the session here


# Safely edit a message without causing Telegram errors
async def safe_edit_message_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE, new_text: str, reply_markup=None
):
    try:
        current_message = update.callback_query.message.text
        if current_message != new_text:
            await update.callback_query.message.edit_text(
                text=new_text, reply_markup=reply_markup
            )
    except Exception as e:
        if "Message is not modified" not in str(e):
            raise


# Check if the user has joined the required channel
async def check_channel_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    try:
        member = await context.bot.get_chat_member(
            chat_id="@sultanpanel", user_id=user.num_id
        )

        if member.status in ["member", "administrator", "creator"]:
            await show_main_menu(update, context, user)
        else:
            await prompt_user_to_join(update, context, user.preferred_language)
    except Exception:
        await prompt_user_to_join(update, context, user.preferred_language)

    session.close()


# Prompt the user to join the required channel
async def prompt_user_to_join(
    update: Update, context: ContextTypes.DEFAULT_TYPE, language
):
    join_message = translate_text(
        "🔗 Please join our channel @sultanpanel to continue 😊", language
    )
    keyboard = [
        [InlineKeyboardButton("✅ Check Membership", callback_data="check_membership")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    new_text = f"{join_message}\n\n👉 [Click here to join the channel](https://t.me/sultanpanel)"

    if update.callback_query:
        current_message = update.callback_query.message
        if (
            current_message.text != new_text
            or current_message.reply_markup != reply_markup
        ):
            await update.callback_query.edit_message_text(
                new_text, reply_markup=reply_markup, parse_mode="Markdown"
            )
    else:
        await update.message.reply_text(
            new_text, reply_markup=reply_markup, parse_mode="Markdown"
        )


# Handle the settings menu where users can change their preferences
async def handle_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    keyboard = [
        [InlineKeyboardButton(lang, callback_data=lang)] for lang in languages.keys()
    ]
    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard.append([InlineKeyboardButton(back_button, callback_data="back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    settings_message = translate_text(
        "🌍 Please choose your language 🗣️:", user.preferred_language
    )

    await query.edit_message_text(settings_message, reply_markup=reply_markup)

    session.close()


# Handle the "Chance Circle" feature, where users can win extra credits daily
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

        reward_message = translate_text(
            f"🎉 Congratulations! You've received {credit_reward} units of credit! 💵",
            user.preferred_language,
        )
        await update.callback_query.edit_message_text(reward_message)
        await show_main_menu(update, context, user)
    else:
        wait_time = timedelta(days=1) - (now - user.last_chance_time)
        wait_hours = wait_time.total_seconds() // 3600
        wait_minutes = (wait_time.total_seconds() % 3600) // 60

        wait_message = translate_text(
            f"⏳ You can use the Chance Circle again in {int(wait_hours)} hours and {int(wait_minutes)} minutes. 🕒",
            user.preferred_language,
        )
        await update.callback_query.edit_message_text(wait_message)
        await show_main_menu(update, context, user)

    session.close()


import requests


# Fetch the current conversion rate from the database
async def get_dollar_to_toman_rate():
    session = Session()
    rate_entry = session.query(ConversionRate).first()
    if rate_entry:
        rate = rate_entry.rate
    else:
        # If no rate is set, use the default value
        rate = 60000
        # Save the default rate to the database
        new_rate = ConversionRate(rate=rate)
        session.add(new_rate)
        session.commit()

    session.close()
    return rate


# Handle the conversion rate management for admins
async def handle_manage_conversion_rate(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    if user.is_admin:
        await query.edit_message_text(
            translate_text(
                "💲 Please enter the new conversion rate (Toman per Dollar):",
                user.preferred_language,
            )
        )
        context.user_data["awaiting_conversion_rate"] = True
    else:
        await query.edit_message_text(
            translate_text(
                "❌ You do not have permission to perform this action.",
                user.preferred_language,
            )
        )

    session.close()


# Display the user's account information, including credits and earnings
async def handle_account_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    if user.join_date.tzinfo is None:
        user.join_date = user.join_date.replace(tzinfo=timezone.utc)

    membership_duration = (datetime.now(timezone.utc) - user.join_date).days
    dollar_to_toman_rate = await get_dollar_to_toman_rate()

    # Convert credits to dollars and tomans
    credit_dollars = user.remaining_credit / 100
    credit_toman = credit_dollars * dollar_to_toman_rate
    credit_info = f"{credit_dollars:.2f}$ ({int(credit_toman):,} Toman)"

    # Convert referral credits to dollars and tomans
    referral_dollars = user.referral_credit / 100
    referral_toman = referral_dollars * dollar_to_toman_rate
    referral_info = f'{referral_dollars:.2f}$ ({int(referral_toman):,} {"Toman" if user.preferred_language == "en" else "تومان"})'

    # Convert sub-transaction earnings to dollars and tomans
    sub_transaction_dollars = user.sub_transaction_earnings / 100
    sub_transaction_toman = sub_transaction_dollars * dollar_to_toman_rate
    sub_transaction_info = (
        f'{sub_transaction_dollars:.2f}$ ({int(sub_transaction_toman):,}  {"Toman" if user.preferred_language == "en" else "تومان"})'
    )

    # Convert used credits to dollars and tomans
    used_credit_dollars = user.used_credit / 100
    used_credit_toman = used_credit_dollars * dollar_to_toman_rate
    used_credit_info = f'{used_credit_dollars:.2f}$ ({int(used_credit_toman):,} {"Toman" if user.preferred_language == "en" else "تومان"})'

    # Form the account information text
    account_info_text = (
        f"ℹ️ Account Information:\n\n"
        f"📅 Membership Duration: {membership_duration} days 📅\n"
        f"💳 Used Credit: {used_credit_info}\n"  # Updated line
        f"💰 Remaining Credit: {credit_info}\n"
     )

    account_info_text = translate_text(account_info_text, user.preferred_language)
    back_button = translate_text("🔙 Back to Main Menu", user.preferred_language)
    keyboard = [[InlineKeyboardButton(back_button, callback_data="back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(account_info_text +    f'\n🎁 {"Credit from Subcategory:" if user.preferred_language == "en" else "سود حاصل از زیرمجموعه گیری:"} {referral_info}\n'
        f'💵 {"Credit from Subcategories charge:" if user.preferred_language == "en" else "سود حاصل از شارژ زیرمجموعه ها:"} {sub_transaction_info}'
    , reply_markup=reply_markup)
    session.close()


# Handle the agency request process for users
async def handle_request_agency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()
    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard = []
    keyboard.append([InlineKeyboardButton(back_button, callback_data="back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    request_text = translate_text(
        "💼 Please enter your daily sales (e.g., 200 dollars or 200 rials): 💼",
        user.preferred_language,
    )
    await query.message.edit_text(request_text)

    context.user_data["awaiting_sales_input"] = True
    session.close()


# Admin function to view pending agency requests
async def handle_view_agency_requests(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    session = Session()

    admin = (
        session.query(User)
        .filter_by(num_id=update.effective_user.id, is_admin=True)
        .first()
    )
    if admin:
        pending_requests = (
            session.query(AgencyRequest).filter_by(status="pending").all()
        )

        if pending_requests:
            keyboard = []
            message_text = translate_text(
                "📋 *Requests:*\n\n", admin.preferred_language
            )

            for request in pending_requests:
                user = session.query(User).filter_by(id=request.user_id).first()
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            f"💼 {request.daily_sales}", callback_data="noop"
                        ),
                        InlineKeyboardButton(
                            "✅", callback_data=f"approve_{request.id}"
                        ),
                        InlineKeyboardButton(
                            "❌", callback_data=f"reject_{request.id}"
                        ),
                    ]
                )

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(
                text=message_text, reply_markup=reply_markup, parse_mode="Markdown"
            )
        else:
            back_button = translate_text("🔙 Back", admin.preferred_language)
            keyboard = [[InlineKeyboardButton(back_button, callback_data="back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                translate_text(
                    "❌ There are no pending agency requests. ❌",
                    admin.preferred_language,
                ),
                reply_markup=reply_markup,
            )
    session.close()


# Handle the action of approving or rejecting an agency request
async def handle_agency_request_action(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    session = Session()

    action, request_id = query.data.split("_")
    request = session.query(AgencyRequest).filter_by(id=request_id).first()

    if request:
        user = session.query(User).filter_by(id=request.user_id).first()
        back_button = translate_text("🔙 Back", user.preferred_language)
        keyboard = []
        keyboard.append([InlineKeyboardButton(back_button, callback_data="back")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        if action == "approve":
            request.status = "approved"
            session.commit()
            await context.bot.send_message(
                chat_id=REPRESENTATIVES,  # Replace with your actual notification channel ID or chat ID
                text=(
                    f"📢 Agency Request Approved:\n"
                    f"👤 User: @{user.username}\n"
                    f"🆔 User ID: {user.num_id}\n"
                    f"💼 Daily Sales: {request.daily_sales}\n"
                    f"📅 Request ID: {request.id}"
                ),
            )

            await context.bot.send_message(chat_id=REPRESENTATIVES, text=user)
        elif action == "reject":
            request.status = "rejected"
            session.commit()
            await context.bot.send_message(
                chat_id=user.num_id,
                text=translate_text(
                    "❌ Your agency request has been rejected. ❌",
                    user.preferred_language,
                ),
            )

        session.delete(request)
        session.commit()

        await handle_view_agency_requests(update, context)
    session.close()


# Handle the "back" action, typically returning to the main menu
# Safely edit a message without causing Telegram errors
async def safe_edit_message_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE, new_text: str, reply_markup=None
):
    try:
        # Check if the message is a text message
        if update.callback_query.message.text:
            current_message = update.callback_query.message.text
            if current_message != new_text:
                await update.callback_query.message.edit_text(
                    text=new_text, reply_markup=reply_markup
                )
        else:
            # If the message is not a text message, send a new message instead
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=new_text,
                reply_markup=reply_markup
            )
    except Exception as e:
        if "Message is not modified" not in str(e):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Sorry, an error occurred while updating the message.",
            )
            print(f"Failed to edit message: {e}")

# Updated function to handle back action properly in the referral link section
async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    try:
        # Check if the callback query message exists and if it can be edited
        if query and query.message:
            if query.message.text:
                await show_main_menu(update, context, user)
            else:
                # If the message is not text, send a new message
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=translate_text("Returning to the main menu...", user.preferred_language)
                )
                await show_main_menu(update, context, user)
        else:
            # Fallback: Send a new message if editing the message isn't possible
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=translate_text("Returning to the main menu...", user.preferred_language)
            )
            await show_main_menu(update, context, user)
    except Exception as e:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="An error occurred. Please try again.",
        )
        print(f"Failed to handle back action: {e}")

    session.close()


# Handle the creation of support tickets
async def handle_create_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    can_send_ticket, message = check_ticket_time(user)

    if can_send_ticket:
        back_button = translate_text("🔙 Back", user.preferred_language)
        keyboard = []
        keyboard.append([InlineKeyboardButton(back_button, callback_data="back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            translate_text(
                "🎫 Please enter the title of your ticket: 📝", user.preferred_language
            ),
            reply_markup=reply_markup,
        )
        context.user_data["awaiting_ticket_title"] = True
        context.user_data["awaiting_ticket_description"] = False
    else:
        await update.callback_query.edit_message_text(message)
        await show_main_menu(update, context, user)

    session.close()



# Admin function to view open support tickets
async def handle_view_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()

    admin = (
        session.query(User)
        .filter_by(num_id=update.effective_user.id, is_admin=True)
        .first()
    )
    if admin:
        open_tickets = session.query(Ticket).filter_by(status="open").all()

        if open_tickets:
            keyboard = [
                [
                    InlineKeyboardButton(
                        ticket.title, callback_data=f"view_ticket_{ticket.id}"
                    )
                ]
                for ticket in open_tickets
            ]
            back_button = translate_text("🔙 Back", admin.preferred_language)
            keyboard.append([InlineKeyboardButton(back_button, callback_data="back")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                translate_text("🎟️ Open Tickets: 🎟️", admin.preferred_language),
                reply_markup=reply_markup,
            )
        else:
            back_button = translate_text("🔙 Back", admin.preferred_language)
            keyboard = [[InlineKeyboardButton(back_button, callback_data="back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                translate_text(
                    "❌ There are no open tickets. ❌", admin.preferred_language
                ),
                reply_markup=reply_markup,
            )

    session.close()
def check_ticket_time(user):
    current_time = datetime.now(timezone.utc)

    if user.last_ticket_time.tzinfo is None:
        user.last_ticket_time = user.last_ticket_time.replace(tzinfo=timezone.utc)

    time_since_last_ticket = current_time - user.last_ticket_time

    if time_since_last_ticket < timedelta(minutes=10):
        remaining_time = timedelta(minutes=10) - time_since_last_ticket
        minutes, seconds = divmod(remaining_time.seconds, 60)
        message = f"⏳ زمان تخمینی باقیمانده : {minutes} دقیقه و {seconds} ثانیه"
        return False, translate_text(message, user.preferred_language)
    else:
        message = "✍️ می‌توانید یک پیام جدید ارسال کنید"
        return True, translate_text(message, user.preferred_language)


# Handle viewing the details of an individual ticket
async def handle_view_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()

    admin = (
        session.query(User)
        .filter_by(num_id=update.effective_user.id, is_admin=True)
        .first()
    )

    if admin:
        print(admin)
        try:
            action, ticket_id = query.data.split("_", 1)
        except ValueError:
            await query.edit_message_text(
                "⚠️ Invalid data received, please try again. ⚠️"
            )
            return
        print(ticket_id,action)
        ticket_id = ticket_id.split("_")[1]
        ticket = session.query(Ticket).filter_by(id=ticket_id).first()
        print(ticket)
        if ticket:
            user = session.query(User).filter_by(id=ticket.user_id).first()
            context.user_data["responding_ticket_id"] = ticket.id
            context.user_data["awaiting_ticket_response"] = True

            # Prepare the ticket details message
            ticket_details = (
                f"👤 **User Details:**\n"
                f"• Username: @{user.username if user.username else 'N/A'}\n"
                f"• Numeric ID: {user.num_id}\n\n"
                f"🎟️ **Ticket Details:**\n"
                f"• Subject: {ticket.title}\n"
                f"• Description: {ticket.description}\n\n"
                f"📩 **Reply to this ticket:**"
            )

            # Translate the message
            translated_ticket_details = translate_text(ticket_details, admin.preferred_language)
            
            # Add a button to reply to the ticket
            keyboard = [[InlineKeyboardButton("📝 Reply", callback_data="reply_ticket")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                translated_ticket_details,
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )

    session.close()

# Handle ticket response from admin
async def handle_ticket_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()

    admin = (
        session.query(User)
        .filter_by(num_id=update.effective_user.id, is_admin=True)
        .first()
    )

    if admin and "responding_ticket_id" in context.user_data:
        ticket_id = context.user_data["responding_ticket_id"]
        ticket = session.query(Ticket).filter_by(id=ticket_id).first()

        if ticket:
            user = session.query(User).filter_by(id=ticket.user_id).first()

            # Ask the admin for the response message
            ask_response_message = translate_text(
                "📝 Please enter your reply to the user:", user.preferred_language
            )
            await query.edit_message_text(ask_response_message)

            context.user_data["awaiting_ticket_response_text"] = True
        else:
            await query.edit_message_text(
                translate_text(
                    "⚠️ Ticket not found, please try again.", admin.preferred_language
                )
            )

    session.close()


# General message handler to process various user inputs based on context
async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()
    broadcast_to = context.user_data.get("broadcast_to")
    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard = []
    keyboard.append([InlineKeyboardButton(back_button, callback_data="back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if context.user_data.get("awaiting_payment"):
        transaction_id = update.message.text.strip()

        # Simulate payment confirmation (here you should call the respective API to confirm the transaction)
        payment_confirmed = True  # Replace with actual API call

        if payment_confirmed:
            await add_credit_to_user(update, context, user)
            context.user_data["awaiting_payment"] = False
            await update.message.reply_text(
                translate_text(
                    "🎉 Payment confirmed! Your credits have been added successfully. 🎊",
                    user.preferred_language
                ),
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                translate_text(
                    "❌ Payment confirmation failed. Please check the transaction ID and try again. ❌",
                    user.preferred_language
                ),
                reply_markup=reply_markup
            )
    if context.user_data.get("awaiting_conversion_rate"):
        try:
            new_rate = int(update.message.text.strip())
            rate_entry = session.query(ConversionRate).first()

            if rate_entry:
                rate_entry.rate = new_rate
            else:
                new_rate_entry = ConversionRate(rate=new_rate)
                session.add(new_rate_entry)

            session.commit()

            success_message = translate_text(
                f"✅ Conversion rate updated to {new_rate} Toman per Dollar.",
                user.preferred_language,
            )
            await update.message.reply_text(success_message, reply_markup=reply_markup)
        except ValueError:
            await update.message.reply_text(
                translate_text(
                    "❌ Invalid rate. Please enter a valid number.",
                    user.preferred_language,
                ),
                reply_markup=reply_markup,
            )

        context.user_data["awaiting_conversion_rate"] = False
        await show_main_menu(update, context, user)
    # Handle custom credit increment input
    if context.user_data.get("awaiting_custom_increment"):
        try:
            custom_amount = float(update.message.text.strip())
            unit = session.query(Unit).filter_by(name="default").first()

            if not unit:
                await update.message.reply_text(
                    translate_text(
                        "❌ Unit value is not set. Please contact an admin. ❌",
                        user.preferred_language,
                    ),
                    reply_markup=reply_markup,
                )
                return

            unit_value_cents = unit.value
            dollar_to_toman_rate = await get_dollar_to_toman_rate()
            credit_amount_units = custom_amount * (100 / unit_value_cents)  # Convert dollars to units
            credit_amount_toman = custom_amount * dollar_to_toman_rate

            user.remaining_credit += credit_amount_units
            session.commit()

            success_message = translate_text(
                f"✅ {credit_amount_units:.2f} units have been added to your account!\n"
                f"💵 Equivalent to {custom_amount:.2f} dollars and {int(credit_amount_toman):,} Toman.",
                user.preferred_language,
            )
            await update.message.reply_text(success_message, reply_markup=reply_markup)
        except ValueError:
            await update.message.reply_text(
                translate_text(
                    "❌ Invalid amount. Please enter a valid number. ❌",
                    user.preferred_language,
                ),
                reply_markup=reply_markup,
            )

        context.user_data["awaiting_custom_increment"] = False
        await show_main_menu(update, context, user)


    # Broadcasting message to selected users or admins
    if context.user_data.get("awaiting_broadcast_message"):
        message = update.message.text
        if broadcast_to == "users":
            users = session.query(User).filter_by(is_bot=False).all()
        elif broadcast_to == "admins":
            users = session.query(User).filter_by(is_admin=True).all()
        else:
            users = []

        for user in users:
            try:
                await context.bot.send_message(chat_id=user.num_id, text=message)
            except Exception as e:
                print(f"⚠️ Failed to send message to {user.username}: {e}")

        await update.message.reply_text(
            f"✅ Message sent to all {broadcast_to}. 📨", reply_markup=reply_markup
        )
        context.user_data["awaiting_broadcast_message"] = False
        await show_main_menu(update, context, user)

    # Processing agency sales input from user
    if context.user_data.get("awaiting_sales_input"):
        daily_sales = update.message.text
        new_request = AgencyRequest(user_id=user.id, daily_sales=daily_sales)
        session.add(new_request)
        session.commit()

        request_id = new_request.id
        confirmation_text = translate_text(
            f"✅ Your request has been added. Admins will review it soon. Your request ID: #{request_id} 🎉",
            user.preferred_language,
        )

        await update.message.reply_text(confirmation_text, reply_markup=reply_markup)

        context.user_data["awaiting_sales_input"] = False
        await show_main_menu(update, context, user)

    # Handling discount code creation
    elif context.user_data.get("awaiting_off_code"):
        off_code = update.message.text.strip()
        context.user_data["off_code"] = off_code
        await update.message.reply_text(
            translate_text(
                "🎫 Please enter the discount percent (e.g., 20):",
                user.preferred_language,
            ),
            reply_markup=reply_markup,
        )
        context.user_data["awaiting_off_code"] = False
        context.user_data["awaiting_discount_percent"] = True

    # Saving discount percent for the created discount code
    elif context.user_data.get("awaiting_discount_percent"):
        discount_percent = int(update.message.text.strip())
        off_code = context.user_data.get("off_code")
        new_code = DiscountCode(code=off_code, discount_percent=discount_percent)
        session.add(new_code)
        session.commit()

        await update.message.reply_text(
            f"✅ Discount code {off_code} with {discount_percent}% discount has been added. 🎁",
            reply_markup=reply_markup,
        )
        context.user_data["awaiting_discount_percent"] = False
        context.user_data["off_code"] = None
        await show_main_menu(update, context, user)

    # Applying discount code to a credit increment
    elif context.user_data.get("awaiting_discount_code"):
        discount_code = update.message.text.strip()
        discount = session.query(DiscountCode).filter_by(code=discount_code).first()

        if discount:
            discounted_amount = context.user_data["selected_increment_amount"]
            user.remaining_credit += int(discounted_amount)
            session.commit()

            success_message = translate_text(
                f"✅ {int(discounted_amount)} units have been added to your credit! 💵",
                user.preferred_language,
            )
            await update.message.reply_text(success_message, reply_markup=reply_markup)
        else:
            invalid_code_message = translate_text(
                "❌ Invalid discount code. Adding full amount to your credit. ❌",
                user.preferred_language,
            )
            await update.message.reply_text(
                invalid_code_message, reply_markup=reply_markup
            )
            await add_credit_to_user(update, context, user)

        context.user_data["awaiting_discount_code"] = False
        await show_main_menu(update, context, user)

    # Handling ticket title input
    elif context.user_data.get("awaiting_ticket_title"):
        context.user_data["ticket_title"] = update.message.text
        await update.message.reply_text(
            translate_text(
                "🎫 Please enter the description of your ticket: 📝",
                user.preferred_language,
            ),
            reply_markup=reply_markup,
        )
        context.user_data["awaiting_ticket_title"] = False
        context.user_data["awaiting_ticket_description"] = True

    # Handling ticket description input and creating a new ticket
    elif context.user_data.get("awaiting_ticket_description"):
        ticket_description = update.message.text
        ticket_title = context.user_data.get("ticket_title")
        new_ticket = Ticket(
            user_id=user.id, title=ticket_title, description=ticket_description
        )
        session.add(new_ticket)
        user.last_ticket_time = datetime.now(timezone.utc)
        session.commit()

        await update.message.reply_text(
            translate_text(
                "✅ Your ticket has been created. Our support team will get back to you soon. 🎟️",
                user.preferred_language,
            ),
            reply_markup=reply_markup,
        )

        context.user_data["awaiting_ticket_description"] = False
        context.user_data["ticket_title"] = None
        await show_main_menu(update, context, user)

    elif context.user_data.get("awaiting_ticket_response_text"):
        response_text = update.message.text
        ticket_id = context.user_data.get("responding_ticket_id")
        ticket = session.query(Ticket).filter_by(id=ticket_id).first()

        if ticket:
            user = session.query(User).filter_by(id=ticket.user_id).first()
            await context.bot.send_message(
                chat_id=user.num_id,
                text=f"📩 Response to your ticket '{ticket.title}':\n\n{response_text}",
            )
            ticket.status = "closed"
            session.commit()

            await update.message.reply_text(
                translate_text(
                    "✅ The ticket has been closed and the response has been sent to the user. 📧",
                    user.preferred_language,
                )
            )

        context.user_data["awaiting_ticket_response_text"] = False
        await show_main_menu(update, context, user)



    # Handling custom order ID input
    elif context.user_data.get("awaiting_order_id_input"):
        order_id = update.message.text.strip()
        
        await process_order_status(update, context, order_id)
        context.user_data["awaiting_order_id_input"] = False

    # Handling service ID input for new orders
    elif context.user_data.get("awaiting_service_id"):
        service_id = update.message.text.strip()
        response = requests.post(API_URL, data={"key": API_KEY, "action": "services"})
        services = response.json()

        service = next((s for s in services if s["service"] == (service_id)), None)

        if service:
            context.user_data["service_id"] = service_id
            await update.message.reply_text(
                translate_text("🔗 Please enter the Link: (\nBut Please use the right link . if you want instagram post view please give us the link of post not the link of your page) 🌐", user.preferred_language),
                reply_markup=reply_markup,
            )
            context.user_data["awaiting_link"] = True
            context.user_data["awaiting_service_id"] = False
        else:
            await update.message.reply_text(
                translate_text(
                    "❌ Invalid Service ID. Please try again. ❌",
                    user.preferred_language,
                ),
                reply_markup=reply_markup,
            )
            context.user_data["awaiting_service_id"] = True

        # Handling link input for new orders
    elif context.user_data.get("awaiting_link"):
            link = update.message.text.strip()
            context.user_data["link"] = link

            # Fetch service details from the API
            service_id = context.user_data["selected_service_id"]
            response = requests.post(API_URL, data={"key": API_KEY, "action": "services"})
            services = response.json()
            service = next((s for s in services if s["service"] == service_id), None)

        
            min_quantity = int(service["min"])
            max_quantity = int(service["max"])
            service_rate_per_1000 = float(service["rate"])  # Cost per 1000 units
            unit = session.query(Unit).filter_by(name="default").first()
            # Fetch user's balance and calculate the maximum allowable quantity
            user_balance_units = user.remaining_credit  # User's balance in units
            dollar_to_toman_rate = await get_dollar_to_toman_rate()  # Fetch current conversion rate

            # Convert user's balance to Toman and Dollar
            unit_value_in_toman =  (unit.value / 100 ) * dollar_to_toman_rate # Assuming 1 unit = 1000 Toman for this example
            user_balance_toman = user_balance_units * unit_value_in_toman
            user_balance_dollar = user_balance_toman / dollar_to_toman_rate

            # Calculate the service rate in dollars
            service_rate_per_1000_dollars = service_rate_per_1000 / dollar_to_toman_rate

            max_orderable_quantity = int(user_balance_toman * 1000 / service_rate_per_1000)

            # Prepare the message to send to the user with emojis
            quantity_prompt = (
                f"🔢 *لطفاً تعداد بازدید مورد نظر خود را وارد کنید:*\n"
                f"💡 *بین* {min_quantity:,} *تا* {max_quantity:,} *بازدید می‌توانید انتخاب کنید.*\n\n"
                f"💰 *موجودی حساب شما:*\n"
                f"• {user_balance_toman:,} *تومان*\n"
                f"• {user_balance_dollar:.2f} *دلار*\n\n"
                f"🛒 *حداکثر تعداد سفارش بر اساس موجودی شما:* \n\n {max_orderable_quantity:,} *عدد*\n\n"
                f"💸 *هزینه هر 1000 عدد:*\n"
                f"• {service_rate_per_1000_dollars:.2f} *دلار*\n"
                f"• {service_rate_per_1000:,} *تومان*"
            )

            await update.message.reply_text(
                translate_text(quantity_prompt, user.preferred_language),
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )

            context.user_data["awaiting_quantity"] = True
            context.user_data["awaiting_link"] = False



    # Handling quantity input for new orders and processing the order
    elif context.user_data.get("awaiting_quantity"):
        session = Session()
        user = session.query(User).filter_by(num_id=update.effective_user.id).first()

        quantity = int(update.message.text.strip())
        service_id = context.user_data["selected_service_id"]
        link = context.user_data["link"]

        # Fetch service details
        response = requests.post(API_URL, data={"key": API_KEY, "action": "services"})
        services = response.json()
        service = next((s for s in services if s["service"] == service_id), None)

        if service and int(service["min"]) <= quantity <= int(service["max"]):
            toman_to_dollar_rate = await get_dollar_to_toman_rate()
            toman_rate = float(service["rate"]) * quantity / 1000
            dollar_amount = toman_rate / toman_to_dollar_rate

            unit = session.query(Unit).filter_by(name="default").first()
            if unit:
                unit_value_cents = unit.value
            else:
                await update.message.reply_text(
                    translate_text(
                        "❌ Unit value is not set. Please contact an admin. ❌",
                        user.preferred_language,
                    ),
                    reply_markup=reply_markup,
                )
                session.close()

                return

            total_cost_in_credits = dollar_amount * (100 / unit_value_cents)

            if user.remaining_credit >= total_cost_in_credits:
                user.remaining_credit -= total_cost_in_credits
                user.used_credit += total_cost_in_credits
                session.commit()

                # Placing the order via API
                add_order_response = requests.post(
                    API_URL,
                    data={
                        "key": API_KEY,
                        "action": "add",
                        "service": service_id,
                        "link": link,
                        "quantity": quantity,
                    },
                )

                order_response = add_order_response.json()
                order_id = order_response.get("order")

                if order_id:
                    # Save the order to the database
                    new_order = Order(
                        user_id=user.id,
                        order_id=order_id,
                        service_id=service_id,
                        link=link,
                        quantity=quantity,
                        status="Pending",
                    )
                    session.add(new_order)
                    session.commit()

                    await update.message.reply_text(
                        translate_text(
                            f"💰 {total_cost_in_credits:.2f} credits have been deducted from your account. 💸",
                            user.preferred_language,
                        )
                    )
                    await update.message.reply_text(
                        translate_text(
                            f"🛒 Order registered successfully!\n\n**Order ID:** `{order_id}` 📄",
                            user.preferred_language,
                        ),
                        parse_mode="Markdown",
                        reply_markup=reply_markup,
                    )
                    from config import ORDER_CHANNEL_ID

                    await context.bot.send_message(
                        chat_id=ORDER_CHANNEL_ID,  # Replace with your actual notification channel ID or chat ID
                        text=(
                            f"📢 New Order Received:\n"
                            f"👤 User: @{user.username}\n"
                            f"🆔 Order ID: {order_id}\n"
                            f"💼 Service: {service['name']}\n"
                            f"🔗 Link: {link}\n"
                            f"🔢 Quantity: {quantity}"
                        ),
                    )


                else:
                    await update.message.reply_text(
                        translate_text(
                            "❌ There was an issue placing your order. Please try again later. ❌",
                            user.preferred_language,
                        ),
                        reply_markup=reply_markup,
                    )
            else:
                back_button = translate_text("🔙 Back", user.preferred_language)
                increment_credit_button = translate_text(
                "💳 Increase Credit", user.preferred_language
                )
                keyboard = []
                keyboard.append([
                    InlineKeyboardButton(
                        increment_credit_button, callback_data="increment_credit"
                    )
                ])
                keyboard.append([InlineKeyboardButton(back_button, callback_data="back")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    translate_text(
                        "❌ Insufficient credit to place this order. Please add more credit and try again. ❌",
                        user.preferred_language,
                    ),
                    reply_markup=reply_markup,
                )
        else:

            await update.message.reply_text(
                translate_text(
                    f"❌ Invalid quantity or service ID. Please try again. ❌",
                    user.preferred_language,
                ),
                reply_markup=reply_markup,
            )

        context.user_data["awaiting_quantity"] = False
        session.close()


    # Handling custom unit value input from admin
    if context.user_data.get("awaiting_unit_value"):
        unit_value_dollars = float(update.message.text.strip())
        unit_value_cents = int(unit_value_dollars * 100)

        unit = session.query(Unit).filter_by(name="default").first()
        if unit:
            unit.value = unit_value_cents

        else:
            new_unit = Unit(name="default", value=unit_value_cents)
            session.add(new_unit)
    
        session.commit()

        await update.message.reply_text(
            translate_text(
                f"✅ Unit value set to ${unit_value_dollars}. 💲",
                user.preferred_language,
            ),
            reply_markup=reply_markup,
        )
        context.user_data["awaiting_unit_value"] = False
        await show_main_menu(update, context, user)

    # Handling discount code application prompt response
    elif context.user_data.get("awaiting_discount_response"):
        response = update.message.text.strip().lower()

        if response == "yes":
            ask_code_message = translate_text(
                "🎟️ Please enter your discount code: 💰", user.preferred_language
            )
            await update.message.reply_text(ask_code_message, reply_markup=reply_markup)
            context.user_data["awaiting_discount_code"] = True
        else:
            user.remaining_credit += int(context.user_data["selected_increment_amount"])
            session.commit()
            ask_code_message = translate_text(
                "✅ Unit added to account. 🤑", user.preferred_language
            )
            await update.message.reply_text(ask_code_message, reply_markup=reply_markup)
        await show_main_menu(update, context, user)

    # Handling discount code deletion input from admin
    elif context.user_data.get("awaiting_off_code_deletion"):
        off_code = update.message.text.strip()
        code_to_delete = session.query(DiscountCode).filter_by(code=off_code).first()

        if code_to_delete:
            session.delete(code_to_delete)
            session.commit()
            await update.message.reply_text(
                f"✅ Discount code {off_code} has been deleted. 🗑️"
            )
        else:
            await update.message.reply_text(
                f"❌ Discount code {off_code} not found. ❌"
            )

        context.user_data["awaiting_off_code_deletion"] = False
        await show_main_menu(update, context, user)

    session.close()


# Handle managing orders (viewing, adding, etc.)
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
        [InlineKeyboardButton(back_button, callback_data="back")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("🛒 Manage Order 🛠️", reply_markup=reply_markup)
    session.close()


# Function to add credit to user's account
async def add_credit_to_user(update, context, user):
    session = Session()

    try:
        user = session.query(User).filter_by(id=user.id).first()
        back_button = translate_text("🔙 Back", user.preferred_language)
        keyboard = []
        keyboard.append([InlineKeyboardButton(back_button, callback_data="back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        if user:
            increment_amount = context.user_data["selected_increment_amount"]
            user.remaining_credit += float(increment_amount) * 100
            session.commit()

            success_message = translate_text(
                f"✅ {increment_amount} units have been added to your credit! 💰",
                user.preferred_language,
            )
            await update.message.reply_text(success_message)
        else:
            await update.message.reply_text(
                translate_text(
                    "❌ Unable to find the user in the database. ❌",
                    user.preferred_language,
                )
            )

    except Exception as e:
        await update.message.reply_text(
            translate_text(
                "❌ An error occurred while adding credit. Please try again later. ❌",
                user.preferred_language,
            )
        )

    finally:
        session.close()


# Handle generating and displaying the user's referral link

# Updated function to handle referral link with improved error handling
async def handle_referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    referral_link = f"https://t.me/Sultanpanel_bot?start={user.num_id}"
    referral_message = translate_text(
        "⚡️ با سلطان پنل به راحتی رشد کنید\n\n"
        "👁‍🗨 افزایش بازدید ویدیو های شما\n"
        "👤 افزایش فالورهای شما\n"
        "❤️ افزایش لایک پست های شما\n"
        "🚀 سرعت بی نظیر سرویس ها\n"
        "🕓 استارت انی و سریع\n"
        "👥 زیرمجموعه گیری و دریافت هدیه\n"
        "💯 رایگان ، سریع ، بدون آفلاینی\n"
        "🔐 پرداخت مطمئن و 100% امن\n\n"
        "👇🏻 همین الان وارد این ربات فوق العاده شو\n\n"
        f"🔗 {referral_link}",
        user.preferred_language,
    )

    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard = [[InlineKeyboardButton(back_button, callback_data="back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        # Handle the case where the message might not be editable
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=open("icon.jpg", "rb"),  # Assuming icon.jpg is in the root directory
            caption=referral_message,
            reply_markup=reply_markup,
            parse_mode=None,
        )
    except Exception as e:
        print(f"Error sending referral link message: {e}")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=translate_text("Sorry, something went wrong. Please try again.", user.preferred_language)
        )

    session.close()




# Handle the admin management section, including adding and removing admins
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
        [InlineKeyboardButton(back_button, callback_data="back")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("🔧 Admin Management ⚙️", reply_markup=reply_markup)
    session.close()


# Handle the management of discount codes by admins
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
        [InlineKeyboardButton(back_button, callback_data="back")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("🔧 Manage Off Codes 🛠️", reply_markup=reply_markup)
    session.close()


# Handle adding new discount codes
async def handle_add_off_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()
    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard = []
    keyboard.append([InlineKeyboardButton(back_button, callback_data="back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        translate_text(
            "🎟️ Please enter the off code (e.g., SAVE20):", user.preferred_language
        ),
        reply_markup=reply_markup,
    )
    context.user_data["awaiting_off_code"] = True
    session.close()


# Handle viewing existing discount codes
async def handle_view_off_codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()

    admin = (
        session.query(User)
        .filter_by(num_id=update.effective_user.id, is_admin=True)
        .first()
    )
    back_button = translate_text("🔙 Back", admin.preferred_language)
    keyboard = []
    keyboard.append([InlineKeyboardButton(back_button, callback_data="back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if admin:
        off_codes = session.query(DiscountCode).all()

        if off_codes:
            code_list = "\n".join(
                [f"{code.code} - {code.discount_percent}%" for code in off_codes]
            )
            await query.message.reply_text(
                translate_text(
                    f"📋 Discount Codes:\n\n{code_list} 🎟️", admin.preferred_language
                )
            )
        else:
            await query.message.reply_text(
                translate_text(
                    "❌ No discount codes available. ❌", admin.preferred_language
                )
            )

    session.close()


# Handle deletion of discount codes by admin
async def handle_delete_off_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()
    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard = []
    keyboard.append([InlineKeyboardButton(back_button, callback_data="back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        translate_text(
            "🗑️ Please enter the off code you want to delete:", user.preferred_language
        ),
        reply_markup=reply_markup,
    )
    context.user_data["awaiting_off_code_deletion"] = True
    session.close()


# Handle broadcasting messages to users or admins
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
        [InlineKeyboardButton(back_button, callback_data="back")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("📢 Broadcast Message" if user.preferred_language == "en" else "📢 اطلاع رسانی پیام", reply_markup=reply_markup)
    session.close()


# Handle broadcasting messages to all users
async def handle_broadcast_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard = []
    keyboard.append([InlineKeyboardButton(back_button, callback_data="back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        translate_text(
            "📢 Please enter the message to broadcast to all users: 📨",
            context.user_data.get("preferred_language"),
        ),
        reply_markup=reply_markup,
    )
    context.user_data["broadcast_to"] = "users"
    context.user_data["awaiting_broadcast_message"] = True
    session.close()


# Handle broadcasting messages to all admins
async def handle_broadcast_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard = []
    keyboard.append([InlineKeyboardButton(back_button, callback_data="back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        translate_text(
            "📢 Please enter the message to broadcast to all admins: 📨",
            context.user_data.get("preferred_language"),
        ),
        reply_markup=reply_markup,
    )
    context.user_data["broadcast_to"] = "admins"
    context.user_data["awaiting_broadcast_message"] = True
    session.close()

# Handle incrementing the user's credit balance
async def handle_increment_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()
    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard = []
    keyboard.append([InlineKeyboardButton(back_button, callback_data="back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Predefined amounts in dollars (will be converted to units)
    unit = session.query(Unit).filter_by(name="default").first()
    if not unit:
        await query.edit_message_text(
            translate_text(
                "❌ Unit value is not set. Please contact an admin. ❌",
                user.preferred_language,
            ),
            reply_markup=reply_markup,
        )
        return

    unit_value_cents = unit.value
    amounts = [1, 5, 10, 50, 100]
    dollar_to_toman_rate = await get_dollar_to_toman_rate()
    keyboard = [
        [
            InlineKeyboardButton(
                f"{amount}$ ({int(amount * dollar_to_toman_rate):,} toman)",
                callback_data=f"increment_{amount}",
            )
        ]
        for amount in amounts
    ]
    custom_amount_button = translate_text(
        "🔢 Enter custom amount", user.preferred_language
    )
    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard.append(
        [InlineKeyboardButton(custom_amount_button, callback_data="custom_increment")]
    )
    keyboard.append([InlineKeyboardButton(back_button, callback_data="back")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    increment_message = translate_text(
        "💳 Please select the amount of credit you want to add: 🛒",
        user.preferred_language,
    )
    await query.edit_message_text(increment_message, reply_markup=reply_markup)
    session.close()

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
import random
import urllib.parse
import hashlib
# Flask server details (replace with your actual server address)
FLASK_SERVER_URL = "http://157.90.234.109:8000"

# Perfect Money account details
PAYEE_ACCOUNT = "U38406992"
PAYEE_NAME = "Mohamed Aduham"
PAYMENT_UNITS = "USD"

# Payeer account details
M_SHOP = "1769310266"
M_KEY = "123"  # Using '123' as the secret key as advised

def generate_perfect_money_url(payment_amount, payment_id, memo):
    payment_url = f"{FLASK_SERVER_URL}/payment-confirmed"
    nopayment_url = f"{FLASK_SERVER_URL}/payment-failed"
    status_url = f"{FLASK_SERVER_URL}/payment-status"

    perfect_money_url = (
        f"https://perfectmoney.is/api/step1.asp?"
        f"PAYEE_ACCOUNT={urllib.parse.quote(PAYEE_ACCOUNT)}&"
        f"PAYEE_NAME={urllib.parse.quote(PAYEE_NAME)}&"
        f"PAYMENT_UNITS={PAYMENT_UNITS}&"
        f"PAYMENT_AMOUNT={payment_amount:.2f}&"
        f"PAYMENT_ID={payment_id}&"
        f"PAYMENT_URL={urllib.parse.quote(payment_url)}&"
        f"NOPAYMENT_URL={urllib.parse.quote(nopayment_url)}&"
        f"STATUS_URL={urllib.parse.quote(status_url)}&"
        f"SUGGESTED_MEMO={urllib.parse.quote(memo)}"
    )
    return perfect_money_url

def generate_payeer_url(payment_amount, payment_id, description):
    amount = f"{payment_amount:.2f}"
    m_curr = "USD"
    m_desc = urllib.parse.quote(description)
    
    # Create the string to sign
    m_sign_string = f"{M_SHOP}:{payment_id}:{amount}:{m_curr}:{M_KEY}"
    
    # Generate the signature using sha256
    m_sign = hashlib.sha256(m_sign_string.encode('utf-8')).hexdigest().upper()

    payeer_url = (
        f"https://payeer.com/merchant/?"
        f"m_shop={M_SHOP}&"
        f"m_orderid={payment_id}&"
        f"m_amount={amount}&"
        f"m_curr={m_curr}&"
        f"m_desc={m_desc}&"
        f"m_sign={m_sign}&"
        f"lang=en"
    )
    return payeer_url


from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

# Handle the selection of predefined credit increment amounts
async def handle_increment_amount_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    action, amount = query.data.split("_")
    amount = float(amount)
    payment_id = str(random.randint(100000, 999999))  # Generate a unique payment ID
    memo = "Payment for credit increase"

    # Generate the Perfect Money payment URL
    perfect_money_url = generate_perfect_money_url(amount, payment_id, memo)

    # Generate the Payeer payment URL
    payeer_url = generate_payeer_url(amount, payment_id, memo)

    # Create web app buttons for both payment methods
    perfect_money_button = InlineKeyboardButton(
        translate_text("💵 Pay with Perfect Money", user.preferred_language),
        web_app=WebAppInfo(url=perfect_money_url)
    )

    payeer_button = InlineKeyboardButton(
        translate_text("💳 Pay with Payeer", user.preferred_language),
        web_app=WebAppInfo(url=payeer_url)
    )

    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard = [
        [perfect_money_button],
        [payeer_button],
        [InlineKeyboardButton(back_button, callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    payment_message = translate_text(
        f"💳 To increase your credit by {amount:.2f} USD, please complete the payment using one of the buttons below.",
        user.preferred_language
    )

    context.user_data["selected_increment_amount"] = amount
    context.user_data["awaiting_payment"] = True
    context.user_data["payment_id"] = payment_id

    await query.edit_message_text(payment_message, reply_markup=reply_markup, parse_mode="Markdown")
    session.close()

# Handle custom credit increment input
async def handle_custom_increment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    dollar_to_toman_rate = await get_dollar_to_toman_rate()

    custom_increment_message = translate_text(
        f"💵 Please enter the amount in dollars (e.g., 15):\n\n"
        f"💱 Current Dollar to Toman rate: {dollar_to_toman_rate:,} Toman per Dollar",
        user.preferred_language
    )
    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard = []
    keyboard.append([InlineKeyboardButton(back_button, callback_data="back")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(custom_increment_message, reply_markup=reply_markup)
    context.user_data["awaiting_custom_increment"] = True
    session.close()



# Handle managing orders (adding, viewing, custom order ID input)
async def handle_manage_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    add_order_button = translate_text("➕ Add Order", user.preferred_language)
    view_order_button = translate_text("🔍 View Order", user.preferred_language)
    custom_order_button = translate_text(
        "🔍 Enter Custom Order ID", user.preferred_language
    )
    back_button = translate_text("🔙 Back", user.preferred_language)

    keyboard = [
        [InlineKeyboardButton(add_order_button, callback_data="add_order")],
        [InlineKeyboardButton(view_order_button, callback_data="view_order")],
        [InlineKeyboardButton(custom_order_button, callback_data="custom_order_id")],
        [InlineKeyboardButton(back_button, callback_data="back")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("🛒 Manage Order 🛠️", reply_markup=reply_markup)
    session.close()


# Handle the process of checking the status of an order
async def process_order_status(
    update: Update, context: ContextTypes.DEFAULT_TYPE, order_id
):
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()
    order = session.query(Order).filter_by(order_id=order_id).first()
    response = requests.post(
        API_URL, data={"key": API_KEY, "action": "status", "order": order_id}
    )
    order_status = response.json()

    start_count = int(float(order_status.get("start_count") or 0))

    remains = float(order_status.get("remains", 0))
    charge = float(order_status.get("charge", 0))
    
    # Convert charge to Dollar
    dollar_to_toman_rate = await get_dollar_to_toman_rate()
    charge_dollar = charge / dollar_to_toman_rate
    
    total_count = start_count + order.quantity
    if total_count > 0:
        percentage_complete = ((total_count - remains) / total_count) * 100
    else:
        percentage_complete = 100

    percentage_complete = round(percentage_complete)

    battery_status = (
        "🔋"
        + "▓" * math.floor(percentage_complete / 10)
        + "░" * (10 - math.floor(percentage_complete / 10))
    )
    progress_message = f"{battery_status} {percentage_complete}%"

    status_mapping = {
        "Pending": "🟡",
        "In Progress": "🔵",
        "Completed": "🟢",
        "Canceled": "🔴",
    }

    status = order_status.get("status", "Unknown")
    status_emoji = status_mapping.get(status, "❓")

    status_message = (
        
        f"🔍 **Order Status:**\n\n"
        f"**Order id:** `{order_id}` 📄\n"
        f"💵 **Order cost:** {charge:,.0f} Toman ({charge_dollar:,.2f} $)\n"  # Formatted values
        f"📊 **Start Count:** {start_count}\n"
        f"{progress_message}\n"
        f"⏳ **Remains:** {remains} pcs\n"
        f"{status_emoji} **Status:** {status}\n"
        f"💸 **Currency:** {order_status.get('currency', 'N/A')}"
    )

    # Update the order status in the database
    order = session.query(Order).filter_by(order_id=order_id).first()
    if order and order.status != status:
        order.status = status
        session.commit()

    translated_message = translate_text(status_message, user.preferred_language)
    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard = []
    keyboard.append([InlineKeyboardButton(back_button, callback_data="back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Check if the update is a callback query or a regular message
    if update.callback_query:
        await update.callback_query.message.reply_text(
            translated_message, parse_mode="Markdown", reply_markup=reply_markup
        )
    elif update.message:
        await update.message.reply_text(
            translated_message, parse_mode="Markdown", reply_markup=reply_markup
        )

    context.user_data["awaiting_order_id"] = False

    session.close()



# Handle custom order ID input
async def handle_custom_order_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()
    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard = []
    keyboard.append([InlineKeyboardButton(back_button, callback_data="back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        translate_text("🔢 Please enter the Order ID: 📄", user.preferred_language),
        reply_markup=reply_markup,
    )
    context.user_data["awaiting_order_id_input"] = True
    session.close()



# Function to strip emojis for filtering
def strip_emoji(text):
    return ''.join(c for c in text if c.isalnum() or c.isspace())

# Handle adding a new order by selecting platform, service, and quantity
async def handle_add_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    response = requests.post(API_URL, data={"key": API_KEY, "action": "services"})
    services = response.json()
    
    platforms = {platform: [] for platform in SOCIAL_MEDIA_PLATFORMS}
    for service in services:
        for platform, platform_key in SOCIAL_MEDIA_PLATFORMS.items():
            if platform_key in service["category"]:
                platforms[platform].append(service)
                break
    
    platforms = {platform: services for platform, services in platforms.items() if services}

    keyboard = [
        [InlineKeyboardButton(translate_text(platform,user.preferred_language), callback_data=f"platform_{i}")]
        for i, platform in enumerate(platforms.keys())
    ]
    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard.append([InlineKeyboardButton(back_button, callback_data="back")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        translate_text(
            "🌐 Please select a social media platform: 📱", user.preferred_language
        ),
        reply_markup=reply_markup,
    )

    context.user_data["platforms"] = list(platforms.items())
    session.close()

# Handle platform selection when adding a new order
async def handle_platform_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    platform_index = int(query.data.split("_")[1])
    platform, services = context.user_data["platforms"][platform_index]

    context.user_data["platform_index"] = platform_index

    categories = {}
    for service in services:
        category = service["category"]
        if category not in categories:
            categories[category] = []
        categories[category].append(service)

    keyboard = [
        [InlineKeyboardButton(translate_text(category[:80],user.preferred_language), callback_data=f"category_{i}")]
        for i, category in enumerate(categories.keys())
    ]
    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard.append([InlineKeyboardButton(back_button, callback_data="add_order")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        translate_text(
            f"📂 Please select a category under {platform}: 📂", user.preferred_language
        ),
        reply_markup=reply_markup,
    )

    context.user_data["categories"] = list(categories.items())
    session.close()


# Handle category selection when adding a new order
async def handle_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    category_index = int(query.data.split("_")[1])
    category, services = context.user_data["categories"][category_index]

    platform_index = context.user_data["platform_index"]

    keyboard = [
        [
            InlineKeyboardButton(
                translate_text(service["name"][:80],user.preferred_language), callback_data=f"service_{service['service']}"
            )
        ]
        for service in services
    ]
    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard.append(
        [InlineKeyboardButton(back_button, callback_data=f"platform_{platform_index}")]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        translate_text(
            f"📄 Please select a service in {category}: 📄", user.preferred_language
        ),
        reply_markup=reply_markup,
    )
    session.close()


# Handle service selection when adding a new order
async def handle_service_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    service_id = query.data.split("_")[1]
    context.user_data["selected_service_id"] = service_id
    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard = []
    keyboard.append([InlineKeyboardButton(back_button, callback_data="back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        translate_text("🔗 Please enter the Link: \n(But Please use the right link . if you want instagram post comment please give us the link of post not the link of your page) 🌐", user.preferred_language),
        reply_markup=reply_markup,
    )
    context.user_data["awaiting_link"] = True
    session.close()


# Handle viewing user's past orders and paginating through them
async def handle_view_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    orders = (
        session.query(Order)
        .filter_by(user_id=user.id)
        .order_by(Order.timestamp.desc())
        .all()
    )
    orders_per_page = 10  # Number of orders to display per page
    context.user_data["total_orders"] = len(orders)
    context.user_data["current_page"] = 0

    await show_orders_page(update, context, user, orders, 0)
    session.close()


# Show orders page with pagination
async def show_orders_page(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user, orders, page_number
):
    orders_per_page = 10
    start_index = page_number * orders_per_page
    end_index = min(start_index + orders_per_page, len(orders))

    keyboard = [
        [
            InlineKeyboardButton(
                f"Order ID: {order.order_id}",
                callback_data=f"view_order_{order.order_id}",
            )
        ]
        for order in orders[start_index:end_index]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    back_button = translate_text("🔙 Back", user.preferred_language)
    custom_order_button = translate_text(
        "🔍 Enter Custom Order ID", user.preferred_language
    )
    keyboard.append(
        [InlineKeyboardButton(custom_order_button, callback_data="custom_order_id")]
    )
    keyboard.append([InlineKeyboardButton(back_button, callback_data=f"back")])
    if start_index > 0:
        keyboard.append(
            [InlineKeyboardButton("⬅️ Back", callback_data="previous_orders_page")]
        )
    if end_index < len(orders):
        keyboard.append(
            [InlineKeyboardButton("➡️ Next", callback_data="next_orders_page")]
        )
    back_button = translate_text("🔙 Back", user.preferred_language)

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(
        translate_text("📦 Your Orders:", user.preferred_language),
        reply_markup=reply_markup,
    )


# Handle pagination for orders
async def handle_order_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    orders = (
        session.query(Order)
        .filter_by(user_id=user.id)
        .order_by(Order.timestamp.desc())
        .all()
    )

    if query.data == "next_orders_page":
        context.user_data["current_page"] += 1
    elif query.data == "previous_orders_page":
        context.user_data["current_page"] -= 1

    await show_orders_page(
        update, context, user, orders, context.user_data["current_page"]
    )
    session.close()


# Handle viewing the details of an individual order
async def handle_individual_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()

    order_id = query.data.split("_")[2]
    order = session.query(Order).filter_by(order_id=order_id, user_id=user.id).first()

    if order:
        # Fetching order status and details
        response = requests.post(
            API_URL, data={"key": API_KEY, "action": "status", "order": order_id}
        )
        order_status = response.json()

        start_count = int(float(order_status.get("start_count") or 0))
        remains = float(order_status.get("remains", 0))
        charge = float(order_status.get("charge", 0))
        
        # Convert charge to Dollar
        dollar_to_toman_rate = await get_dollar_to_toman_rate()
        charge_dollar = charge / dollar_to_toman_rate

        total_count = start_count + order.quantity

        if total_count > 0:
            percentage_complete = ((total_count - remains) / total_count) * 100
        else:
            percentage_complete = 100

        percentage_complete = round(percentage_complete)

        battery_status = (
            "🔋"
            + "▓" * math.floor(percentage_complete / 10)
            + "░" * (10 - math.floor(percentage_complete / 10))
        )
        progress_message = f"{battery_status} {percentage_complete}%"

        status_mapping = {
            "Pending": "🟡",
            "In Progress": "🔵",
            "Completed": "🟢",
            "Canceled": "🔴",
        }

        status = order_status.get("status", "Unknown")
        status_emoji = status_mapping.get(status, "❓")

        status_message = (
        
        f"🔍 **Order Status:**\n\n"
        f"**Order id:** `{order_id}` 📄\n"
        f"💵 **Order cost:** {charge:,.0f} Toman ({charge_dollar:,.2f} $)\n"  # Formatted values
        f"📊 **Start Count:** {start_count}\n"
        f"{progress_message}\n"
        f"⏳ **Remains:** {remains} pcs\n"
        f"{status_emoji} **Status:** {status}\n"
        f"💸 **Currency:** {order_status.get('currency', 'N/A')}"
        )

        translated_message = translate_text(status_message, user.preferred_language)

        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="view_order")]]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            translated_message, reply_markup=reply_markup, parse_mode="Markdown"
        )
    session.close()



# Handle checking order status by order ID
async def handle_check_order_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    order_id = query.data.split("_")[3]

    # Process the status check similar to the process_order_status function provided earlier
    await process_order_status(update, context, order_id)


# Handle the management of unit value (conversion rate for credits)
async def handle_manage_unit_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = Session()
    user = session.query(User).filter_by(num_id=update.effective_user.id).first()
    back_button = translate_text("🔙 Back", user.preferred_language)
    keyboard = []
    keyboard.append([InlineKeyboardButton(back_button, callback_data="back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        translate_text(
            "💲 Please enter the unit value in dollars (e.g., 0.1): 💰",
            user.preferred_language,
        ),
        reply_markup=reply_markup,
    )
    context.user_data["awaiting_unit_value"] = True
    session.close()


# The main function that sets up the Telegram bot and all the handlers
def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_messages)
    )
    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        CallbackQueryHandler(
            handle_language_selection, pattern="^(" + "|".join(languages.keys()) + ")$"
        )
    )
    application.add_handler(
        CallbackQueryHandler(handle_account_info, pattern="^account_info$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_request_agency, pattern="^request_agency$")
    )
    application.add_handler(
        CallbackQueryHandler(
            handle_view_agency_requests, pattern="^view_agency_requests$"
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            handle_agency_request_action, pattern=r"^(approve|reject)_\d+$"
        )
    )
    application.add_handler(
        CallbackQueryHandler(check_channel_membership, pattern="^check_membership$")
    )
    application.add_handler(CallbackQueryHandler(handle_back, pattern="^back$"))
    application.add_handler(CallbackQueryHandler(handle_settings, pattern="^settings$"))
    application.add_handler(
        CallbackQueryHandler(handle_chance_circle, pattern="^chance_circle$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_create_ticket, pattern="^create_ticket$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_view_tickets, pattern="^view_tickets$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_view_ticket, pattern=r"^view_ticket_\d+$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_referral_link, pattern="^referral_link$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_admin_management, pattern="^admin_management$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_manage_off_codes, pattern="^manage_off_codes$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_add_off_code, pattern="^add_off_code$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_view_off_codes, pattern="^view_off_codes$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_delete_off_code, pattern="^delete_off_code$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_broadcast_message, pattern="^broadcast_message$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_broadcast_users, pattern="^broadcast_users$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_broadcast_admins, pattern="^broadcast_admins$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_increment_credit, pattern="^increment_credit$")
    )
    application.add_handler(
        CallbackQueryHandler(
            handle_increment_amount_selection, pattern=r"^increment_\d+$"
        )
    )
    application.add_handler(
        CallbackQueryHandler(handle_manage_order, pattern="^manage_order$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_add_order, pattern="^add_order$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_view_order, pattern="^view_order$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_manage_unit_value, pattern="^manage_unit_value$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_platform_selection, pattern=r"^platform_.+$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_category_selection, pattern=r"^category_.+$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_service_selection, pattern=r"^service_.+$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_custom_increment, pattern="^custom_increment$")
    )
    application.add_handler(
        CallbackQueryHandler(handle_individual_order, pattern=r"^view_order_\d+$")
    )
    application.add_handler(
        CallbackQueryHandler(
            handle_order_pagination,
            pattern=r"^(next_orders_page|previous_orders_page)$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            handle_check_order_status, pattern=r"^check_order_status_\d+$"
        )
    )

    # Add the new handlers here
    application.add_handler(
        CallbackQueryHandler(handle_custom_order_id, pattern="^custom_order_id$")
    )

    application.add_handler(
        CallbackQueryHandler(
            handle_manage_conversion_rate, pattern="^manage_conversion_rate$"
        )
    )
    application.add_handler(
        CallbackQueryHandler(handle_ticket_response, pattern="^reply_ticket$")
    )

    application.run_polling()


if __name__ == "__main__":
    main()
