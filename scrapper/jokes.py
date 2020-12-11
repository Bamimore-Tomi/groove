import requests
from bs4 import BeautifulSoup as BS
import json
import html
def beano_jokes():
    data = []
    req = requests.get('https://www.beano.com/categories/jokes')
    soup = BS(req.content,'lxml')
    layer1 = soup.find_all('div', {'class':'Shelf-tileWrap-1T8aF'})
    base_url = 'https://www.beano.com'
    for i in layer1:
        href = i.find('a').attrs['href']
        joke_class = i.find('span',{'class':'PostTile-title-mdmgM'}).text
        sub_url = base_url+href
        deep_req = requests.get(sub_url)
        deep_soup = BS(deep_req.content, 'lxml')
        layer2 = deep_soup.find_all('div',{'class':'Joke-root-xaR-u'})
        print(len(layer2))
        for j in layer2:
            question = j.find('div',{'class':'Joke-questionWrap-2U5zC'}).text
            answer = j.find('p',{'class','Joke-answer-Ll8-J'}).text
            try:
                img_link = j.findAll('img').attrs['src']
                print('Found')
            except:
                image_link = 'NA'
            data.append({'joke_class':joke_class.replace(' ','_').replace('.','__'),'joke_question':question, 'joke_answer':answer, 'joke_image':image_link})
#data = beano_jokes()          
#file = open('jokes.json','w')
#w = json.dump(data,file)

def pickup_line():
    data = []
    base_url = 'https://pickup-lines.net'
    req = requests.get(base_url)
    soup = BS(req.content,'lxml')
    layer = soup.find('ul',{'id':'menu-categories'})
    lis = layer.find_all('li')
    for i in lis:
        link = i.find('a').attrs['href']
        category = i.find('a').text 
        deep_req = requests.get(link)
        deep_soup = BS(deep_req.content, 'lxml')
        texts = deep_soup.find_all('article')
        for i in texts:
            data.append({'category':category,'pick_up_line':html.unescape(i.text).replace('\n\n\nLoading...','').strip().replace('\n','').replace('\u2019',"'")})
    return data
