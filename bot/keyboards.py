import string
import random
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

import os
import json
import pymongo
import logging
import threading
from dotenv import load_dotenv
import time
from utils import *
load_dotenv()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.DEBUG)
client = pymongo.MongoClient(os.getenv('DB_URL'))
db = client[os.getenv('DB_NAME')]

def build_menu(buttons,
               n_cols,
               header_buttons=None,
               footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, [header_buttons])
    if footer_buttons:
        menu.append([footer_buttons])
    return menu

def pickup_lines_category_keyboard():
    categories = db.pick_up_lines.distinct('category')
    keyboard_button  = [KeyboardButton(text=x) for x in categories]
    keyboard_menu = ReplyKeyboardMarkup(build_menu(keyboard_button,2),
                                        resize_keyboard=True,one_time_keyboard=True)
    return keyboard_menu
def book_category_keyboard():
    unclean_category = db.books.distinct('category')
    categories = [ clean_text(i) for i in unclean_category]
    inline_keyboard_button = [InlineKeyboardButton(i , callback_data=unclean_category[categories.index(i)]) for i in categories]
    inline_keyboard_markup = InlineKeyboardMarkup(build_menu(inline_keyboard_button,2))
    return inline_keyboard_markup
if __name__=='__main__':
    print(book_category_keyboard())