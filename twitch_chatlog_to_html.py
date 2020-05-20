import json
import sqlite3
import re
import codecs
import urllib.request
import urllib.parse
import time
import random
import argparse
import functools
import re
import os

colors = ['#FF0000',
'#0000FF',
'#008000',
'#B22222',
'#FF7F50',
'#9ACD32',
'#FF4500',
'#2E8B57',
'#DAA520',
'#D2691E',
'#5F9EA0',
'#1E90FF',
'#FF69B4',
'#8A2BE2',
'#00FF7F']

emoteCache = {}
unameColors = {}

def getUserColor(username):
	if not unameColors.get(username,False):
		return colors[random.randint(0,len(colors)-1)]
	else:
		return unameColors[username]

def getEmoteUrl(ident,type,url):
	if type == "TWITCH":
		return "https://static-cdn.jtvnw.net/emoticons/v1/{0}/1.0".format(ident)
	elif type == "BTTV":
		return "https://cdn.betterttv.net/emote/{0}/1x".format(ident)
	elif type == "FFZ":
		return "https:"+url
	else:
		return ""

def emoteContainer(url):
	return "<span class='emote'><img src='{0}'></span>".format(url)

def messageContainer(username,content,user_color):
	
	return '''
	<div class='msg'>
		<span class='msg--uname' style='color:{2}'>{0}:</span>
		<div class='msg--container'>{1}</div>
	</div>'''.format(username,content,user_color);

def intoTemplate(filename,content):
	with codecs.open(filename, encoding='utf-8') as f:
		return f.read().format(content);

def findEmote(word,full = True):
	if isinstance(word,re.Match): 
		emoteCode = word.group(0)
	else:
		emoteCode = word
	if( len(emoteCode) < 3): return emoteCode

	if not emoteCache.get(emoteCode,False):
		conn = sqlite3.connect('cached_data.db')
		c = conn.cursor()
		if not full:
			query = '''SELECT emote_id,"BTTV","" FROM bttv_emotes WHERE code = '{0}' UNION
				   SELECT emote_id,"FFZ",url FROM ffz_emotes WHERE code = '{0}' '''.format(emoteCode)
		else:
			query = '''SELECT emote_id,"BTTV","" FROM bttv_emotes WHERE code = '{0}' UNION
					   SELECT emote_id,"FFZ",url FROM ffz_emotes WHERE code = '{0}' UNION
					   SELECT id,"TWITCH","" FROM twitch_emotes WHERE code = '{0}' '''.format(emoteCode)
		res = c.execute(query)
		emote = res.fetchone()
		if emote is not None:
			emoteCache[emoteCode] = emote
			return emoteContainer(getEmoteUrl(emote[0],emote[1],emote[2]))
		else:
			emoteCache[emoteCode] = emoteCode
			return emoteCode
	else:
		cached = emoteCache[emoteCode]
		if isinstance(cached,str):
			#print('Caching a string',word)
			return cached
		else:
			return emoteContainer(getEmoteUrl(cached[0],cached[1],cached[2]))

def toEmoteCache(fragments):
	for frag in fragments:
		code = frag['text']

		if frag.get('emoticon',False):
			_id = frag['emoticon']['emoticon_id']
			emoteCache[code] = (_id,"TWITCH","")

def parseRawLog(log_name,out_file):
	fullEmoteLog = ""
	with codecs.open(log_name, encoding='utf-8') as f:
		for line in f:
			if line[0] == '#': continue
			matches = re.search(r"^(\[[\d:]*\])?\s*([\w\s]*):(.*)$",line)
			#print(matches)
			if matches is None: continue

			if len(matches.groups()) == 3:
				username = matches.group(2)
				content = matches.group(3)
			if len(matches.groups()) == 2:
				username = matches.group(1)
				content = matches.group(2)

			content = re.sub(r"[a-zA-Z0-9]{1,20}",findEmote,content)
			fullEmoteLog += messageContainer(username,content,getUserColor(username))
	#Output
	with codecs.open(out_file,mode='w+',encoding='utf-8') as f:
		f.write(intoTemplate('template.html',fullEmoteLog))

def parseTwitchLog(log_name,out_file):
	fullEmoteLog = ""
	with codecs.open(log_name, encoding='utf-8') as f:
		comments = json.loads(f.read())

		for cmt in comments:
			username = cmt['commenter']['display_name']
			content = cmt['message']['body']
			
			#drop non chat messages
			if cmt['message']['is_action']: continue
			
			#somehow grey names dont have a color LULW
			user_color = cmt['message'].get('user_color','#53535f')
			emotes = cmt['message']['fragments']
			toEmoteCache(emotes)

			partialFindEmote = functools.partial(findEmote,full = False)
			content = re.sub(r"[a-zA-Z0-9]{1,20}",partialFindEmote,content)
			
			fullEmoteLog += messageContainer(username,content,user_color)

	#Output
	with codecs.open(out_file,mode='w+',encoding='utf-8') as f:
		f.write(intoTemplate('template.html',fullEmoteLog))

def addUserDB(username,uid):
	conn = sqlite3.connect('cached_data.db')
	c = conn.cursor()
	c.execute("INSERT OR REPLACE INTO users(id,username) VALUES ({0},'{1}')".format(uid,username))
	conn.commit()

def addFFZEmotes(uid,emotes):
	conn = sqlite3.connect('cached_data.db')
	c = conn.cursor()
	for emote in emotes:
		c.execute("INSERT OR REPLACE INTO ffz_emotes(uid,emote_id,code,url,url2,url3) VALUES ({0},{1},'{2}','{3}','{4}','{5}')"
			.format(int(uid),int(emote['id']),emote['name'],emote['urls'].get('1',''),emote['urls'].get('2',''),emote['urls'].get('4','')))
	conn.commit()

def addBTTVEmotes(uid,emotes):
	conn = sqlite3.connect('cached_data.db')
	c = conn.cursor()
	for emote in emotes:
			c.execute("INSERT OR REPLACE INTO bttv_emotes(uid,emote_id,code,type) VALUES ({0},'{1}','{2}','{3}')"
				.format(uid,emote['id'],emote['code'].replace("'","''"),emote['imageType']))
	conn.commit()

def getFFZChannelEmotes(ch):
	f = urllib.request.urlopen("https://api.frankerfacez.com/v1/room/%s" % ch)
	data = json.loads(f.read().decode('utf-8'))
	twitch_id = data['room']['twitch_id']
	current_set = data['room']['set']
	emotes = data['sets'][str(current_set)]['emoticons']
	
	addUserDB(ch,twitch_id)
	addFFZEmotes(twitch_id,emotes)

def getBTTVChannelEmotes(ch_id):
	f = urllib.request.urlopen("https://api.betterttv.net/3/cached/users/twitch/%s" % ch_id)
	data = json.loads(f.read().decode('utf-8'))
	channelEmotes = data['channelEmotes']
	sharedEmotes = data['sharedEmotes']
	emotes = channelEmotes + sharedEmotes
	addBTTVEmotes(ch_id,emotes)

def getBTTVGlobalEmotes():
	f = urllib.request.urlopen("https://api.betterttv.net/3/cached/emotes/global")
	data = json.loads(f.read().decode('utf-8'))
	addBTTVEmotes(0,data)

def getFFZGlobalEmotes():
	f = urllib.request.urlopen("https://api.frankerfacez.com/v1/set/global")
	data = json.loads(f.read().decode('utf-8'))
	sets = data['default_sets']
	emotes = []
	for s in sets:
		emotes.extend(data['sets'][str(s)]['emoticons'])
	addFFZEmotes(0,emotes)

def getChannelID(ch_name):
	conn = sqlite3.connect('cached_data.db')
	c = conn.cursor()
	res = c.execute("SELECT id FROM users WHERE username = '{0}' LIMIT 1".format(ch_name))
	return int(res.fetchone()[0])


def updateTwitchEmotes(json_input):
	conn = sqlite3.connect("cached_data.db")
	c = conn.cursor()
	with open(json_input) as f:
		data = f.read()
		emotes = json.loads(data)
		for emote in emotes['emoticons']:
			if emote['emoticon_set'] == 0: continue
			prefix = re.match(r"([a-z0-9]*)(.*)",emote['code']).group(1);
			c.execute("INSERT OR IGRNORE INTO twitch_emotes VALUES ({0},'{1}','{2}',{3})".format(emote['id'],prefix,emote['code'],emote['emoticon_set']))
		conn.commit()

def downloadVODLog(vod_id,client_id,log_file):
	comments = []

	params = urllib.parse.urlencode({'client_id':client_id})
	while True:
		f = urllib.request.urlopen("https://api.twitch.tv/v5/videos/{0}/comments?{1}".format(vod_id,params))
		data = json.loads(f.read().decode('utf-8'))
		nextCursor = data.get('_next',False)
		comments.extend(data.get('comments',[]))
		if nextCursor:
			params = urllib.parse.urlencode({'client_id':client_id,'cursor': nextCursor})
		else:
			break
	with open(log_file,'w+') as f:
		json.dump(comments,f)

def downloadTwitchEmotes(output):
	urllib.request.urlretrieve("https://api.twitch.tv/kraken/chat/emoticon_images",output)
	

def fetchExternalEmotes(ch_name):
	try:
		getFFZChannelEmotes(ch_name)
		ch_id = getChannelID(ch_name)
		getBTTVChannelEmotes(ch_id)
		getBTTVGlobalEmotes()
		getFFZGlobalEmotes()
		#clear all emotes?
	except Exception as e:
		print('[Error]Invalid channel name/Channel not found')
		


helptext = '''Generate html from twitch/raw logs,
download emote data and cache it to replace in logs
*[Twitch logs dont require the download of all twitch emotes]
*[Raw logs have random colors for users because there is no way to fetch it]
'''
parser = argparse.ArgumentParser(description=helptext)
parser.add_argument('--update_emotes', dest='update_emotes',default="",metavar='CHANNEL_NAME',
                   help='Download and cache emotes from ffz/bttv for the selected channel')

parser.add_argument('--twitch_emotes', dest='twitch_emotes',default=False,const=True,action='store_const',
                   help='Download the entirety of twitch emotes')

parser.add_argument('--vod', dest='vod_id',default=0,type=int,
                   help='Download the chat replay from a Twitch VOD, requires a client_id')
parser.add_argument('--client_id', dest='client_id',default="",
                   help='(Required) for downloading from twitch')

parser.add_argument('--input', dest='input_file',default="",
                   help='Input twitch/raw log file')
parser.add_argument('--output', dest='output_file',default="",
                   help='HTML file thats generated')


args = parser.parse_args()

if args.vod_id:
	if args.client_id:
		if not args.output_file:
			print('No Output destination selected')
		else:
			print('Downloading chat for VOD := ',args.vod_id)
			downloadVODLog(args.vod_id,args.client_id,args.output_file)
			print('Saved logs into ',args.output_file)
	else:
		print('Client ID is required')
	exit()

if args.input_file:
	if not os.path.isfile(args.input_file):
		print('Invalid input file')
	else:
		if not args.output_file:
			print('No Output destination selected')
		else:
			if os.path.splitext(args.input_file)[1] == 'json':
				parseTwitchLog(args.input_file,args.output_file)
			else:
				parseRawLog(args.input_file,args.output_file)
			print('Generating output...')
		exit()
	exit()

if args.twitch_emotes:
	print("[Slow]Downloading ALL twitch emotes (big download)")
	downloadTwitchEmotes("all_twitch_emotes_by_set.json")
	print("[Slow] Adding Twitch emotes to the database cache...")
	updateTwitchEmotes("all_twitch_emotes_by_set.json")
	exit()

if args.update_emotes:
	print("Downloading FFZ/BTTV Emotes for channel",args.update_emotes)
	fetchExternalEmotes(args.update_emotes)
	exit()
else:
	print('No channel name selected')
	exit()