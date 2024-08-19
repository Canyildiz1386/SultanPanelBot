# 📱 Sultan Panel Telegram Bot 🤖

Welcome to the **Sultan Panel Bot** project! This Telegram bot is a powerful tool for managing and selling virtual services across multiple social media platforms. With features for both regular users and administrators, this bot simplifies the process of ordering services, managing accounts, and handling support requests.

## 🛠️ Features

### 🌍 Multi-Language Support
- **English 🇬🇧**
- **Farsi 🇮🇷**

### 🚀 Fast and Reliable
- The bot is built for speed and reliability, ensuring that tasks are completed efficiently and effectively.

### 📊 Analytics
- Get detailed analytics on your social media performance to help make informed decisions.

### 🔗 Multi-Platform Support
- Manage services across multiple social media platforms from a single interface, including Instagram, Twitter, and more.

### 🎯 Targeted Actions
- Customize actions based on specific targets to achieve the best results.

### 🎰 Chance Circle
- Daily opportunity to earn credits by spinning the Chance Circle.

### 🔐 Account Management
- **Admins** can manage users, view agency requests, manage off codes, and broadcast messages to users.
- **Users** can view their account information, manage orders, and request services.

### 🎫 Support Ticket System
- Users can create tickets for support requests, and admins can manage and respond to them easily.

### 🎉 Referral System
- Users can generate referral links to invite others to the bot and earn credits.

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- A Telegram Bot Token from [BotFather](https://core.telegram.org/bots#botfather)
- SQLite (for local database)
- Basic knowledge of Python and Telegram Bot API

### 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Canyildiz1386/SultanPanelBot.git
   cd SultanPanelBot
   ```

2. **Install the required Python packages:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up the configuration:**
   - Create a `config.py` file in the project root and add your bot token and other configurations:
     ```python
     TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
     NOTIFICATION_CHANNEL_ID = -100XXXXXXXXX
     API_URL = "https://followeriha.com/api/v2"
     API_KEY = "your_api_key"
     admin_usernames = ["admin1", "admin2"]
     SOCIAL_MEDIA_PLATFORMS = [
         "Instagram",
         "TikTok",
         "YouTube",
         "Twitter",
         "Telegram",
         "Rubika"
     ]
     ```

4. **Run the bot:**
   ```bash
   python main.py
   ```

## 🗂️ Project Structure

- **main.py**: The main script that runs the bot.
- **config.py**: Configuration file containing bot tokens and API keys.
- **telegram_bot.db**: SQLite database used for storing user data and transactions.
- **requirements.txt**: List of Python dependencies.

## 📝 Usage

### 🧑‍💻 User Commands
- `/start` - Start interacting with the bot and choose your preferred language.
- `/account_info` - View your account information, including credits and transaction history.
- `/manage_order` - Manage your orders, add new ones, or view existing orders.
- `/create_ticket` - Create a support ticket.

### 🔧 Admin Commands
- `/broadcast_message` - Broadcast a message to all users or admins.
- `/manage_off_codes` - Add, view, or delete discount codes.
- `/view_agency_requests` - View and manage agency requests from users.

### 🔁 Callback Handlers
The bot uses inline keyboards for seamless interaction. Callback handlers manage different actions like language selection, viewing agency requests, and more.

## 🖼️ Screenshots

![Main Menu](https://yourimageurl.com/main-menu.png)
*Main menu for users with various options.*

![Agency Requests](https://yourimageurl.com/agency-requests.png)
*Admin view of pending agency requests.*

## 📬 Contact
Feel free to reach out for support or contributions:
- **Email**: support@sultanpanelbot.com
- **Telegram**: [Sultan Panel Bot](https://t.me/Sultanpanel_bot)

## 🎉 Contributing
Contributions are welcome! Please fork this repository and submit a pull request if you have any enhancements or bug fixes.

---

⚠️ **Disclaimer**: This bot is for managing virtual services and is intended for use by administrators with the appropriate permissions. The bot should be used responsibly and in compliance with Telegram's terms of service.

---

© 2024 Sultan Panel Bot. All rights reserved.