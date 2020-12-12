import string
import random
from typing import Optional
import os
import json
import pymongo
import logging
import threading
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import requests
from dotenv import load_dotenv
import time
from utils import *
load_dotenv()

#logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.ERROR)
client = pymongo.MongoClient(os.getenv('DB_URL'))
config = json.load(open("config.json"))
db = client[os.getenv('DB_NAME')]

def random_string(length=12):
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    letters = lowercase + uppercase
    secret = ''.join(random.choice(letters) for i in range(length))
    return secret

def get_pick_up_line(category : Optional[str] = None, count : Optional[int]=1 ):
    if category !=None:
        try:
            lines = [ i for i in db.pick_up_lines.aggregate([{ '$match':{'category':category}},{'$sample': { 'size': count } }])]
            return [i['pick_up_line'] for  i in lines]
        except:
            lines = [ i for i in db.pick_up_lines.aggregate([{ '$sample': { 'size': count } }])]
            return [i['pick_up_line'] for  i in lines]
    else:
        lines = [ i for i in db.pick_up_lines.aggregate([{ '$sample': { 'size': count } }])]
        return [i['pick_up_line'] for  i in lines]
def format_book_response(book : dict):
    try:
        if 'book_image' in book.keys():
            if book['book_image'].startswith('http') is False:
                book['book_image'] = 'http://library.lol'+book['book_image']
        if 'file_detail' in book.keys():
            book['file_detail'] = book['file_detail'].replace(u'\xa0',u'')
        if 'book_authors' in book.keys():
            book['book_authors']=','.join(i.replace(',','') for i in book['book_authors'])
        try:
            book.pop('_id')
            return book
        except:
            return book
    except Exception as e:
        print(e)
        try:
            book.pop('_id')
            return book
        except:
            return book
        
def get_books( chat_id : int, category: Optional[str]=None, language: Optional[str]='English',keyword : Optional[str]=None):
    reducer = lambda x : x if len(x)<60 else x[0:60]
    try:
        if keyword and category is not None:
            try:
                books = [format_book_response(i) for i  in db.books.find({'book_language': language, 'category':category, '$text':{'$search':keyword}})]
                if len(books)!=0:
                    db.book_cache.insert_one({'chat_id':chat_id,'category':category,'keyword':keyword,'timestamp':time.time(),'search_result':books})
                    return 1, reducer(books)
                else:
                    books = [format_book_response(i) for i  in db.books.find({'category':category, '$text':{'$search':keyword}})]
                    if len(books)!=0:
                        return 1, reducer(books)
            except Exception as e:
                db.search_error.insert_one({'chat_id':chat_id,'time':time.time(),'origin':'book_search','error':e})
        if keyword!=None:
            print('here')
            try:
                books= [format_book_response(i) for i  in db.books.find({'book_language': language,'$text':{'$search':keyword}})]
                db.book_cache.insert_one({'chat_id':chat_id, 'keyword':keyword,'timestamp':time.time(),'search_result':books})
                if len(books)!=0:
                    return 1, reducer(books)
                else:
                    books = [format_book_response(i) for i  in db.books.find({'$text':{'$search':keyword}})]
                    if len(books)!=0:
                        return 1, reducer(books)
            except Exception as e:
                db.search_error.insert_one({'chat_id':chat_id,'time':time.time(),'origin':'book_search','error':e})
        books= [ format_book_response(i) for i in db.books.aggregate([{ '$match':{'category':category}},{'$sample': { 'size': 10}}])]
        for i in books:
            if 'book_language' in i.keys():
                if i['book_language']!=language:
                    books.remove(i)
        db.book_cache.insert_one({'chat_id':chat_id,'category':category,'timestamp':time.time(),'search_result':books})
        return 0, reducer(books)
    except:
        return 0,0
        
def book_paginator(update,context,chat_id: int,page : int ):
    chat_id = update.effective_chat.id
    last_search= [ i for i in db.book_cache.find({'chat_id':chat_id})][-1]['search_result']
    if len(last_search) < 15:
        page_content = last_search
        context.user_data['last_page']=4
    else:
        page_content = last_search[int(0.25*(page-1)*len(last_search))+1:int(0.25*page*len(last_search))]
    for i in page_content:
        if 'file_detail' in i.keys():
            checker = lambda x : i[x] if x in i.keys() else 'NA'
            url_shortner = lambda url : requests.get('https://maphor.herokuapp.com/api/',params={'url':url}).text.replace('"','')
            context.bot.send_photo(
                    chat_id=chat_id,
                    photo = i['book_image']
                    )
            context.bot.send_message(chat_id=chat_id,
                                    text = config['messages']['book_result_complete'].format(i['book_title'],
                                                                                            checker('book_publisher'),
                                                                                            checker('book_year'),
                                                                                            checker('book_pages'),
                                                                                            checker('book_language'),
                                                                                            checker('book_authors'),
                                                                                            checker('file_detail')),
                                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Download Book', url=str(url_shortner(i['download_link'])) )]]),
                                    parse_mode=telegram.ParseMode.MARKDOWN)
        else:
            context.bot.send_photo(
                chat_id=chat_id,
                photo = i['book_image']
                )
            context.bot.send_message(
                chat_id=chat_id,
                text = config['messages']['book_result_pdfdrive'].format(i['book_title'],'English'),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text='Download Book', url=url_shortner(i['download_link']) )]]),
                parse_mode=telegram.ParseMode.MARKDOWN
                )

    context.bot.send_message(
        chat_id=chat_id,
        text = 'Click on /more_book_search_result to view the next set of your search result.\n\nTo perform a new search /books'
    )
    
def clean_text(text : str):
    try:
        text_list = text.replace('_',' ').split(' ')
        text_list_clean = [i[0].upper()+i[1:] for i in text_list]
        text_clean = ' '.join(text_list_clean)
        return text_clean
    except:
        text = text.replace('_',' ')
        return text
def clean_text_reverse(text: str):
    text_list= text.split(' ')
    text_list_unclean = [i[0].lower()+i[1:] for i in text_list]
    text_unclean = '_'.join(text_list_unclean)
    return text_unclean
if __name__=='__main__':
    print(get_pick_up_line('wassup'))