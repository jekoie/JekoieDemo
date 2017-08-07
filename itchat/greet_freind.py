#coding=utf8
import itchat, time
import traceback
import requests
import os
import sys
from itchat.content import *
reload(sys)
sys.setdefaultencoding('utf-8')

KEY = '1d1c46dee01e40319fbe0bdb6e946ce0'

def get_response(msg):
    apiUrl = 'http://www.tuling123.com/openapi/api'
    data = {
        'key'    : KEY,
        'info'   : msg,
        'userid' : 'wechat-robot',
    }
    try:
        r = requests.post(apiUrl, data=data).json()
        if r['code'] == 100000:
            return r.get('text')
        elif r['code'] == 200000:
            return '{}\n{}'.format(r['text'], r['url'] )
        elif r['code'] in [302000,  308000]:
            info = '{}\n\n'.format(r['text'])
            for i, item in enumerate(msg['list']):
                info += u'{}\n文章：{}\n来源{}\n地址：{}\n{}\n'.format('-'*10, item['article'], item['source'], item['detailurl'], '-'*10)
            return  info
    except Exception as e:
        print traceback.format_exc()
        return

@itchat.msg_register([TEXT, MAP, CARD, NOTE, SHARING, PICTURE, RECORDING, ATTACHMENT, VIDEO])
def text_reply(msg):
    if msg['FileName'] != '':
       # msg['Text'](msg['FileName'])
       #itchat.send(u'', msg['FromUserName'])
        return
    info = get_response(msg['Text'])
    itchat.send(info , msg['FromUserName'] )

@itchat.msg_register(FRIENDS)
def add_friend(msg):
    itchat.add_friend(**msg['Text'])
    itchat.send_msg('Nice to meet you!', msg['RecommendInfo']['UserName'])

def greet_friend():
    cwd = os.getcwd()
    greet_file = os.path.join(cwd, 'greet.txt')
    if os.path.exists(greet_file):
        return
    with open(greet_file, 'w+') as f:
        f.write(u'If file existing, greeting msg will not send; if you want send greeting againg, delete the this file')

    for friend in itchat.get_friends(True):
        name =  friend['RemarkName'] or friend['NickName'] or  friend['DisplayName']
        msg = 'Hi, {}:\n'.format(name)
        msg += u'八一友谊大比武开始了!甩一筐关怀的手雷，炸掉烦恼的暗堡;扔一箱问候的炸弹，摧毁忧愁的要塞;投一枚友情的核弹，释放快乐的原子。祝建军节开心!'
      #  itchat.send(msg, friend['UserName'])
        if name in [u'风']:
            continue
        else:
            itchat.send(msg, friend['UserName'])

itchat.auto_login(hotReload=True)
itchat.run()
