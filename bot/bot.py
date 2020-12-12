from telegram.ext import Updater
from telegram.ext import CommandHandler , MessageHandler, Filters , ConversationHandler,CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
import telegram 

import os
import json
import pymongo
import logging
import threading
from dotenv import load_dotenv
import time
from utils import *
import keyboards
load_dotenv()

TOKEN = os.getenv('TOKEN')
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.ERROR)
config = json.load(open("config.json"))
client = pymongo.MongoClient(os.getenv('DB_URL'))
db = client[os.getenv('DB_NAME')]

ASK_PICKUP_OPTIONS, ASK_BOOK_CATEGORY, ASK_BOOK_NAME= range(3)


def start(update, context):
    chat_id = update.effective_chat.id
    if db.users.find_one({'user_id':chat_id})==None:
        db.users.insert_one({'user_id':chat_id,'first_name':update.message.chat.first_name,
                             'last_name':update.message.chat.last_name,'user_name':update.message.chat.username})
    context.bot.send_message(chat_id=chat_id , text='text')
    context.user_data['session_id'] = random_string(16)
    db.session.insert_one({'session_id':context.user_data['session_id'], 'user_id':chat_id,'time':time.time()})
def ask_pickup_options(update,context):
    chat_id = update.effective_chat.id
    context.bot.send_message(chat_id=chat_id, 
                             text=config['messages']['pickup_options'],
                             reply_markup=keyboards.pickup_lines_category_keyboard())
    return ASK_PICKUP_OPTIONS

def pickup_line(update, context):
    chat_id = update.effective_chat.id
    category = update.message.text.strip()
    pickup_lines = get_pick_up_line(category=category)
    for i in pickup_lines:
        context.bot.send_message(chat_id=chat_id,
                                 text=i
        )
def ask_book_category(update,context):
    chat_id = update.effective_chat.id
    context.bot.send_message(chat_id=chat_id,
                             text=config['messages']['book_options'],
                             reply_markup=keyboards.book_category_keyboard(),
                             parse_mode=telegram.ParseMode.MARKDOWN)
    return ASK_BOOK_CATEGORY

def ask_book_name(update, context):
    chat_id = update.effective_chat.id 
    query_data = update.callback_query.data
    context.user_data['book_category']=clean_text_reverse(query_data)
    context.bot.send_message(
        chat_id=chat_id,
        text=config['messages']['book_name'],
        parse_mode=telegram.ParseMode.MARKDOWN
    )
    return ASK_BOOK_NAME
    
def send_books(update, context):
    chat_id = update.effective_chat.id
    keyword = ''.join([i for i in update.message.text if i.isalnum() or i==''])
    print(keyword,context.user_data['book_category'])
    status, books_ = get_books(chat_id=chat_id,category=context.user_data['book_category'], keyword=keyword)
    #book_paginator(update,context,chat_id=chat_id,page=1)
    thread = threading.Thread(target=book_paginator , args=[update,context],kwargs={'chat_id':chat_id,'page':1})
    thread.start()
    context.user_data['last_page']=1
    #for i in range(int(len(books_)*0.25)):
    #    context.bot.send_photo(
    #    chat_id=chat_id,
    #    photo = books_[i]['book_image']
    #)
    return -1
def send_books_from_pagination(update,context):
    chat_id = update.effective_chat.id 
    if context.user_data['last_page']<=4:
        page_to_send=context.user_data['last_page']+1
        book_paginator(update,context,chat_id=chat_id,page=page_to_send)
        context.user_data['last_page']=page_to_send
    else:
        context.bot.send_message(
            chat_id=chat_id,
            text = config['messages']['end_of_book_result']
        )
def main():
    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    entry = CommandHandler('start',start)

    pickup_conv = ConversationHandler(
        entry_points = [CommandHandler('pickuplines', ask_pickup_options)],
        states = {
            ASK_PICKUP_OPTIONS: [MessageHandler(Filters.regex(r'Funny|Best|Cute|Cheesy'),pickup_line)],          
        },
        fallbacks = [CommandHandler('start', start)]
    )
    book_conv = ConversationHandler(
        entry_points = [CommandHandler('books', ask_book_category), CallbackQueryHandler(ask_book_name)],
        states={
            ASK_BOOK_CATEGORY: [CallbackQueryHandler(ask_book_name)],
            ASK_BOOK_NAME:[MessageHandler(Filters.regex(r'[a-zA-Z0-9]+'),send_books)]
        },
        allow_reentry=True,
        conversation_timeout = 120,
        fallbacks= [CommandHandler('books',ask_book_category)]
    )
    more_book_result_command=CommandHandler('more_book_search_result',send_books_from_pagination)
    
    dispatcher.add_handler(entry)
    dispatcher.add_handler(pickup_conv)
    dispatcher.add_handler(book_conv)
    dispatcher.add_handler(more_book_result_command)
    
    updater.start_polling()
    updater.idle()
if __name__=='__main__':
    main()