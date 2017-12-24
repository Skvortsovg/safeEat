# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
from datetime import timedelta, datetime
from nltk import FreqDist
import pymorphy2
from random import choice, sample
from string import punctuation
import requests
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
from random import choice
from scipy.cluster.hierarchy import fcluster, linkage
from newspaper import Article
import re
import logging
from .botan import *
from .decorators import async


log = logging.getLogger(__name__)


from settings import KREMLIN_NEWS_LOCATION, ALL_KREMLIN_NEWS_LOCATION, MEGAFON_NEWS_LOCATION, ALL_MEGAFON_NEWS_LOCATION



exclude = "[" + punctuation + "'0123456789[]—«»–]"
alt_normal_forms = {"газа":"газ", "Песков":"песков"}
cands = ['NOUN']
stopwords = ['россия', 'сша']


def represent_news(text):
    words = text.split()
    if len(words[0]) > 7:
        news_start = words[0]
        news_other = ' '.join(words[1:])
    else:
        news_start = ' '.join(words[:2])
        news_other = ' '.join(words[2:])
    return news_start, news_other


def normal_form(text):
    text = re.sub(r'([^\s\w])', '', text)
    news_text = text.split()
    nouns = []

    morph = pymorphy2.MorphAnalyzer()

    for word in news_text:
        word_cleaned = ''.join(ch for ch in word if ch not in exclude)
        if word_cleaned != '':
            gram_info = morph.parse(word)[0]
            if 'NOUN' in gram_info.tag or 'VERB' in gram_info.tag or 'ADJF' in gram_info.tag:
                try:
                    nouns.append(morph.parse(word)[0].normal_form)
                except:
                    pass
    return ' '.join(nouns)


def clean_text(text):
    return text.replace('&quot', '').replace('\n', '').replace('\xa0',' ')


def parse_rss(rss_url):
    new = []

    raw_html = requests.get(rss_url).text
    soup = BeautifulSoup(raw_html, 'html.parser')
    news = soup.find_all('item')
    for item in news:
        try:
            news_title = clean_text(item.title.getText())
            news_description = ''
            if item.description is not None:
                news_description = clean_text(item.description.getText())
            news_pubdate = ''.join(item.pubdate.getText()[:-6].split(',')[1:]).strip()
            news_link = item.link.getText()
            news_source = re.findall('/([a-z.]+).(io|com|ru)', rss_url)[0][0].split('.')[-1].capitalize()
            new.append([news_title, normal_form(news_title), news_link,
                     news_description, normal_form(news_description), news_pubdate, news_source])
        except:
            pass
    return new


def _upb_news(category, medias):
    if category == 'Kremlin':
        NEWS_LOCATION = KREMLIN_NEWS_LOCATION
        ALL_NEWS_LOCATION = ALL_KREMLIN_NEWS_LOCATION
    else:
        NEWS_LOCATION = MEGAFON_NEWS_LOCATION
        ALL_NEWS_LOCATION = ALL_MEGAFON_NEWS_LOCATION

    try:
        news_file = pd.read_csv(NEWS_LOCATION, header=0)
    except:
        news_file = pd.DataFrame(columns=['header', 'header_preproc', 'link', 'text', 'text_preproc', 'date', 'source',
            'full_text', 'full_text_preproc'])


    counter = 0
    for c, news in enumerate(medias):
        if not news[2] in news_file['link'].values:
            if datetime.now() - datetime.strptime(news[5], "%d %b %Y %H:%M:%S") < timedelta(days=1):
                article = Article(news[2], language='ru')
                article.download()
                try:
                    article.parse()
                except:
                    pass
                news.append(article.text)
                news.append(normal_form(article.text))
                if (('cluster' in news_file.columns) & ('hot_topic' in news_file.columns)):
                    news += [0,0]
                news_file.loc[len(news_file)]=news
                counter += 1

    news_file.drop_duplicates('link', inplace = True)
    news_file['date'] = news_file['date'].astype('str')
    news_file = news_file[[len(date) > 7 for date in news_file['date'].values]]
    news_file['date'] = pd.to_datetime(news_file['date'])
    news_file['date'] = pd.to_datetime(news_file['date'])
    news_file = news_file[news_file['date'] > datetime.now() - timedelta(days=1)]

    news_file.to_csv(NEWS_LOCATION, index=False)
    print('Added %d news' % counter)

    try:
        all_time_news_file = pd.read_csv(ALL_NEWS_LOCATION, header=0)
    except:
        all_time_news_file = pd.DataFrame(columns=['header', 'header_preproc', 'link', 'text', 'text_preproc', 'date', 'source',
            'full_text', 'full_text_preproc'])
    all_time_news_file = all_time_news_file.append(news_file)
    all_time_news_file.drop_duplicates('link', inplace=True)
    all_time_news_file['date'] = pd.to_datetime(all_time_news_file['date'])
    all_time_news_file.to_csv(ALL_NEWS_LOCATION, index=False)



def upd_news():
    log.info('____________ updating news _________________')

    meduza_news = parse_rss('https://meduza.io/rss/news')
    interfax_news = parse_rss('http://interfax.ru/rss.asp')
    lenta_news = parse_rss('https://lenta.ru/rss')
    tass_news = parse_rss('http://tass.ru/rss/v2.xml')
    rambler_news = parse_rss('https://news.rambler.ru/rss/head/')
    russia_today_news = parse_rss('https://russian.rt.com/rss')
    vedomosti_news = parse_rss('https://vedomosti.ru/rss/news')
    radio_svoboda_news = parse_rss('https://www.svoboda.org/api/z-pqpiev-qpp')
    kommersant_news = parse_rss('https://www.kommersant.ru/RSS/news.xml')
    republic_news = parse_rss('https://republic.ru/export/news.xml')
    raintv_news = parse_rss('https://tvrain.ru/export/rss/programs/1018.xml')

    kremlin_news = interfax_news + lenta_news + tass_news + rambler_news + russia_today_news
    megafon_news = meduza_news + vedomosti_news + radio_svoboda_news + kommersant_news + republic_news + raintv_news


    _upb_news('Kremlin', kremlin_news)
    _upb_news('Megafon', megafon_news)

    log.info('============= UPDATED NEWS ================')


def get_hot_news(category='Kremlin'):
    if category == 'Kremlin':
        NEWS_LOCATION = KREMLIN_NEWS_LOCATION
    else:
        NEWS_LOCATION = MEGAFON_NEWS_LOCATION
    df = pd.read_csv(NEWS_LOCATION, header=0)
    hot = df[df['hot_topic'] > 3].sort_values('hot_topic', ascending=False).values
    news = []
    for c in range(len(hot)):
        news_start, news_other = represent_news(hot[c][0])
        news.append('▶ <a href="%s">%s</a> %s' % (hot[c][2], news_start, news_other))
    return '\n\n'.join(news)


def get_other_hot_news(category='Kremlin'):
    if category == 'Kremlin':
        NEWS_LOCATION = KREMLIN_NEWS_LOCATION
    else:
        NEWS_LOCATION = MEGAFON_NEWS_LOCATION
    df = pd.read_csv(NEWS_LOCATION, header=0)
    hot = df[(df['hot_topic'] < 4) & (df['hot_topic'] > 0)].sort_values('hot_topic', ascending=False).values
    news = []
    for c in range(len(hot)):
        news_start, news_other = represent_news(hot[c][0])
        news.append('▶ <a href="%s">%s</a> %s' % (hot[c][2], news_start, news_other))
    return '\n\n'.join(news)


def update_clusters(category='Kremlin'):
    if category == 'Kremlin':
        NEWS_LOCATION = KREMLIN_NEWS_LOCATION
    else:
        NEWS_LOCATION = MEGAFON_NEWS_LOCATION
    df = pd.read_csv(NEWS_LOCATION)
    df = df.fillna('')
    df['date'] = pd.to_datetime(df['date'])
    headers = df['header'].values
    norm_texts = (df['header_preproc'] + df['text_preproc'] + df['full_text_preproc']).values

    for c in range(len(norm_texts)):
        norm_texts[c] = norm_texts[c].replace('\xa0', ' ')
    tf = TfidfVectorizer()
    texts_transformed = tf.fit_transform(norm_texts)

    Z = linkage(texts_transformed.todense(), 'ward')
    clusters = fcluster(Z, 1.4, criterion='distance')
    for c in np.unique(clusters):
        df.loc[clusters == c, 'cluster'] = c
    df.to_csv(NEWS_LOCATION, index=False)
    log.info('Clusters updated')


def set_hot_news(category='Kremlin'):
    if category == 'Kremlin':
        NEWS_LOCATION = KREMLIN_NEWS_LOCATION
    else:
        NEWS_LOCATION = MEGAFON_NEWS_LOCATION
    df = pd.read_csv(NEWS_LOCATION)
    df['date'] = pd.to_datetime(df['date'])
    df['hot_topic'] = 0
    cluster_sizes = df.groupby('cluster').count()['header'].values
    avg_time = []
    sources = []
    for c in np.unique(df['cluster']):
        avg_time.append((datetime.now() - df[df['cluster'] == c]['date']).astype('m8[ms]').mean())
        sources.append(np.unique(df[df['cluster'] == c]['source'].values).shape[0])
    time_ind = np.array(avg_time)/max(avg_time)
    news_rate = np.array(cluster_sizes) * np.array((3-time_ind))*(1+np.array(sources)/7)
    clust_rating = np.argsort(news_rate)[::-1] + 1
    for i, cluster in enumerate((clust_rating[:10])):
        df.set_value(df[df['header'] == (get_cl(df[df['cluster'] == cluster]['header'].values))].index.values[0], 'hot_topic', 10-i)
    df.to_csv(NEWS_LOCATION, index=False)
    log.info('Hot news updated')


def get_cl(cluster):
    distances = np.zeros(shape=(len(cluster), len(cluster)))
    for c in range(len(cluster)):
        for d in range(len(cluster)):
            distances[c][d] = distance(cluster[c], cluster[d])
    a = distances.sum(axis=1)
    return cluster[np.argmin(a)]


def distance(a, b):
    "Calculates the Levenshtein distance between a and b."
    n, m = len(a), len(b)
    if n > m:
        a, b = b, a
        n, m = m, n

    current_row = range(n+1)
    for i in range(1, m+1):
        previous_row, current_row = current_row, [i]+[0]*n
        for j in range(1,n+1):
            add, delete, change = previous_row[j]+1, current_row[j-1]+1, previous_row[j-1]
            if a[j-1] != b[i-1]:
                change += 1
            current_row[j] = min(add, delete, change)

    return current_row[n]


def get_random_news(category='Kremlin'):
    if category == 'Kremlin':
        NEWS_LOCATION = KREMLIN_NEWS_LOCATION
    else:
        NEWS_LOCATION = MEGAFON_NEWS_LOCATION
    news_file = pd.read_csv(NEWS_LOCATION, header=0)
    news_file['date'] = pd.to_datetime(news_file['date'])
    news_file = news_file.sort_values('date', ascending=False).head(30)
    rand_news = news_file.sample().values[0]
    news_start, news_other = represent_news(rand_news[0])
    news_words = rand_news[7].split()
    full_text = '    ' + ' '.join(news_words[:100])
    if len(news_words) > 100:
        full_text += '... <a href="%s">Читать далее</a>' % (rand_news[2])
    return '🆕 %s, %s: <a href="%s">%s</a> %s \n\n%s' % (rand_news[5].strftime('%Y-%m-%d %H:%M'), rand_news[6],
        rand_news[2], news_start, news_other,  full_text)


def get_rare(chat_id=None, category='Kremlin'):
    if category == 'Kremlin':
        NEWS_LOCATION = KREMLIN_NEWS_LOCATION
    else:
        NEWS_LOCATION = MEGAFON_NEWS_LOCATION

    df = pd.read_csv(NEWS_LOCATION, header=0)
    df = df.fillna('')
    df = df[~df['text'].str.contains('Порошенко|Украин|Трамп')]
    df['date'] = pd.to_datetime(df['date'])
    rand_news =  df[df['cluster'] == choice(np.argsort(np.unique(df['cluster'].values, return_counts=True)[1])[:10])].sample().values[0]
    news_start, news_other = represent_news(rand_news[0])
    news_words = rand_news[7].split()
    full_text = '    ' + ' '.join(news_words[:100])
    if len(news_words) > 100:
        full_text += '... <a href="%s">Читать далее</a>' % (rand_news[2])
    return '🆕 %s, %s: <a href="%s">%s</a> %s \n\n%s' % (rand_news[5].strftime('%Y-%m-%d %H:%M'), rand_news[6],
        rand_news[2], news_start, news_other,  full_text)