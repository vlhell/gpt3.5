import sqlite3

import openai
import telebot
import sqlite3 as sl


openai.api_key = ""
bot = telebot.TeleBot("")


con = sl.connect('example.db', check_same_thread=False)
with con:
    try:
        con.execute("""
            CREATE TABLE USER_HISTORY (
                row_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                role TEXT,
                content TEXT
            );
        """)
    except sqlite3.OperationalError as e:
        if str(e) != 'table USER_HISTORY already exists':
            raise


print('Bot was started')


@bot.message_handler(content_types=['text'])
def msg(message):
    message_text = message.text

    if message_text == '/start':
        message_text = 'Привет'

    if message.chat.type != 'private' \
            and 'Name' not in message_text \
            and '@bot_name' not in message.text \
            and not (
                message.reply_to_message
                and message.reply_to_message.from_user
                and message.reply_to_message.from_user.id == bot.user.id
            ):
        return

    message_from_chat_id = message.chat.id

    if message_text == '/clear':
        return bot.send_message(chat_id=message_from_chat_id, text='Ниче я очищать не буду')

    if message_text == '/clr':
        con.execute("DELETE FROM USER_HISTORY WHERE chat_id = %s" % message_from_chat_id)
        return bot.send_message(chat_id=message_from_chat_id, text='История очищена')

    bot.send_chat_action(chat_id=message_from_chat_id, action='typing')

    messages_with_history = []
    raw_messages_with_history = []
    with con:
        data = con.execute("SELECT * FROM USER_HISTORY WHERE chat_id = %s ORDER BY row_id" % message_from_chat_id)
        for row in data:
            raw_messages_with_history.append(
                {"role": row[2], "content": row[3]}
            )
        start_idx = max(0, len(raw_messages_with_history) - 10)
        for row in raw_messages_with_history[start_idx:]:
            messages_with_history.append(row)

    bot.send_chat_action(chat_id=message_from_chat_id, action='typing')

    messages_with_history.append(
        {"role": "user", "content": message_text}
    )

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0301",
        messages=messages_with_history,
        presence_penalty=1)

    bot.send_chat_action(chat_id=message_from_chat_id, action='typing')

    bot_answer = completion.choices[0].message["content"]
    if bot_answer[:7] == 'Ответ: ':
        bot_answer = bot_answer[7:]

    bot.send_message(chat_id=message_from_chat_id, text=bot_answer)

    sql = 'INSERT INTO USER_HISTORY (chat_id, role, content) values(?, ?, ?)'
    data = [
        (message_from_chat_id, "user", message_text),
        (message_from_chat_id, "assistant", bot_answer),
    ]

    with con:
        con.executemany(sql, data)


bot.infinity_polling()
