import json
import os.path
import os
import logging
import argparse
import sqlite3
from credentials import *
from time import sleep
from dateutil.relativedelta import relativedelta
import datetime
import calendar

try:
    from instagram_private_api import (
        Client, __version__ as client_version)
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from instagram_private_api import (
        Client, __version__ as client_version)


def from_json(json_object):
    if '__class__' in json_object and json_object['__class__'] == 'bytes':
        return codecs.decode(json_object['__value__'].encode(), 'base64')
    return json_object

conn = sqlite3.connect('instagram.db')
conn.execute('create table if not exists old_posts (id integer primary key, media_id text, code text, like_count int, comment_count int, image_url text, created_at timestamp)')

settings_file = "/Users/alfaridi/.igcookies"
with open(settings_file) as file_data:
    cached_settings = json.load(file_data, object_hook=from_json)
print('Reusing settings: {0!s}'.format(settings_file))

device_id = cached_settings.get('device_id')

api = Client(user_name, password, settings=cached_settings)

posts = []
uuid = api.generate_uuid()
results = api.user_feed(user_id)

posts.extend(results.get('items', []))

next_max_id = results.get('next_max_id')
while next_max_id:
    results = api.user_feed(user_id, max_id=next_max_id)
    posts.extend(results.get('items', []))
    next_max_id = results.get('next_max_id')
    sleep(2)

with open('posts.json', 'w') as file:
     file.write(json.dumps(posts))

posts.sort(key=lambda x: x['pk'])

for post in posts:
   try:
        caption = post['caption']['text']
   except:
        caption = ''
   pk = int(post['pk'])
   media_id = post['id']
   code = post['code']
   comment_count = int(post['comment_count'])
   like_count = int(post['like_count'])

   try:
       created_at = int(post['caption']['created_at'])
   except:
       created_at = 0

   try:
        image_url = post['image_versions2']['candidates'][0]['url']
   except:
        image_url = ''

   data = (pk, media_id, code, like_count, comment_count, image_url, created_at)
   conn.execute('insert into old_posts values (?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING', data)

conn.commit()

MAX_YEARS = 3
max_time = datetime.datetime.now() - relativedelta(years=MAX_YEARS)
min_date = calendar.timegm(max_time.utctimetuple())
old_medias = conn.execute('select media_id,code from old_posts where created_at < %d order by created_at desc;' % min_date)
conn.commit

for media in old_medias:
    print('%s -> %s' % (media[0], media[1]))
    api.delete_media(media[0])
    conn.execute('delete from old_posts where code = ?', (media[1],))
    conn.commit()
    sleep(5)

conn.close()
os.remove('instagram.db')
os.remove('posts.json')
