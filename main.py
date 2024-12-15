import os
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import openai

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("OPENAPI_KEY")
)

# Replace with your actual Telegram bot token
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Initialize a dictionary to store messages by group_id (chat_id)
message_history = {}


def message_collector(update: Update, context: CallbackContext):
    """Collect messages from the group chat by group_id and include group name and sender details."""
    message = update.message.text
    chat_id = update.effective_chat.id  # Get the unique chat ID (group_id)
    chat_name = update.effective_chat.title  # Get the group name (None for private chats)
    user = update.message.from_user  # Get the sender's details

    # Extract sender details
    sender_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    sender_username = f"@{user.username}" if user.username else "No username"

    if message:
        if chat_id not in message_history:
            message_history[chat_id] = []  # Initialize a list for this group
        
        # Record message with sender information
        message_history[chat_id].append(f"{sender_name} ({sender_username}): {message}")
        
        # Limit the history to the last 1000 messages per group
        if len(message_history[chat_id]) > 10000:
            message_history[chat_id].pop(0)
        
        # Log message with group name and sender details
        if chat_name:
            logging.info(f"Collected message from group '{chat_name}' (ID: {chat_id}): {sender_name} ({sender_username}): {message}")
        else:
            logging.info(f"Collected message from private chat (ID: {chat_id}): {sender_name} ({sender_username}): {message}")

def summarize(update: Update, context: CallbackContext):
    """Summarize the last N messages for the current group."""
    chat_id = update.effective_chat.id
    chat_name = update.effective_chat.title
    args = context.args

    try:
        num_messages = int(args[0]) if args else 100
    except ValueError:
        update.message.reply_text('Please provide a valid number of messages to summarize.')
        return

    if chat_id not in message_history or not message_history[chat_id]:
        update.message.reply_text('No messages to summarize for this group.')
        return

    messages_to_summarize = message_history[chat_id][-num_messages:]
    text_to_summarize = '\n'.join(messages_to_summarize)

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Hãy tóm tắt lại đoạn hội thoại của người dùng thành viên trong nhóm bằng tiếng Việt. Các group thường bàn luận về chủ đề crypto, tiền điện tử, bạn hay lấy kiến thức tài chính, \
                 finance và crypto nói chung nhé. Tóm tắt nội dung nên ghi ra cả tên của thành viên là tốt nhất,\
                 Ngoài ra lúc trả lời đừng thêm dấu @ vào cầu trả lời nữa, vì như thế sẽ thành 1 hành động tag username, thông báo làm phiền người khác\
                 Mỗi 1 người gửi ứng Với tên người gửi sender, để 1 dòng nhé cho dễ đọc, nói chung đừng để wall of text khó đọc lắm, với văn phong cho nó vui vẻ cũng được\
                 "},
                {"role": "user", "content": text_to_summarize}
            ],
            model="gpt-4o",
        )

        # Process the summary to escape only essential characters
        summary = response.choices[0].message.content

        # Escape reserved MarkdownV2 characters only
        reserved_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in reserved_chars:
            summary = summary.replace(char, f"\\{char}")

        # Send the summary with MarkdownV2 parse mode
        update.message.reply_text(summary, parse_mode="MarkdownV2")

        if chat_name:
            logging.info(f"Sent summary to group '{chat_name}' (ID: {chat_id}).")
        else:
            logging.info(f"Sent summary to private chat (ID: {chat_id}).")
    except Exception as e:
        logging.error(f"OpenAI API error: {e}")
        update.message.reply_text('An error occurred while summarizing the messages.')

def main():
    """Start the bot."""
    # Ensure the Telegram token is available
    if not TELEGRAM_TOKEN:
        logging.error("TELEGRAM_TOKEN environment variable not set.")
        return

    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Add handlers
    dispatcher.add_handler(CommandHandler('short', summarize))
    dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), message_collector))

    # Start the bot
    updater.start_polling()
    logging.info("Bot started")
    updater.idle()


if __name__ == '__main__':
    main()