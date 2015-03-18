# -*- coding: utf-8 -*-

import urllib
import re
import time
import datetime

NAME = 'NBA GameTime'
ART  = 'art-default.jpg'
ICON = 'logo.jpg'

PREFIX = '/video/nbagametime'

UA = [
	'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Trident/6.0; Xbox; Xbox One)',
	'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0; Xbox)'
	'Roku/DVP-4.3 (024.03E01057A), Mozilla/5.0(iPad; U; CPU iPhone OS 3_2 like Mac OS X; en-us) AppleWebKit/531.21.10 (KHTML, like Gecko) Version/4.0.4 Mobile/7B314 Safari/531.21.10'
]


####################################################################################################

def Start():
	ObjectContainer.title1 = NAME
	ObjectContainer.art = R(ART)
	ObjectContainer.no_cache = True
	DirectoryObject.thumb = R(ICON)
	DirectoryObject.art = R(ART)
	HTTP.Headers['User-agent'] = Util.RandomItemFromList(UA)

	teams = JSON.ObjectFromURL('http://nlmobile.cdnak.neulion.com/nba/config/2014/teams.json', cacheTime = CACHE_1DAY * 365)
	Dict['teams'] = teams['teams']
	favTeam = Prefs['team']

	for t in teams['teams']:
		if favTeam is not None and teams['teams'][t]['cityname'] in favTeam:
			Dict['favTeamCode'] = t
			break


@handler(PREFIX, NAME, thumb=ICON, art=ART)
def MainMenu():
	oc = ObjectContainer(no_cache=True)
	oc.add(DirectoryObject(key = Callback(LiveGames), title="Live Games", summary="Watch live games for today."))

	cats = HTTP.Request(url='http://smb.cdnak.neulion.com/fs/nba/feeds/common/cats.js', cacheTime=CACHE_1DAY * 30).content.replace("var g_vodcats=", "")
	cats = JSON.ObjectFromString(cats)
	query = ''
	thumb = ''
	#fav team goes first
	if 'favTeamCode' in Dict:
		for r in ['east', 'west']:
			for d in cats['teams'][r]:
				for x in cats['teams'][r][d]:
					if x['id'] == Dict['favTeamCode']:
						thumb = x['id'] + '.png'
						query = x['q']
						break
	if query != '':
		if thumb == '':
			oc.add(DirectoryObject(key = Callback(Videos, name=Prefs['team'], query=query), title=Prefs['team'], summary="%s" %Prefs['team']))
		else:
			oc.add(DirectoryObject(key = Callback(Videos, name=Prefs['team'], query=query), title=Prefs['team'], summary="%s" %Prefs['team'], thumb = R(thumb)))

	oc.add(DirectoryObject(key = Callback(CreateNbaLiveObject, include=False), title='NBA TV', summary='NBA TV'))
	#highlights
	oc.add(DirectoryObject(key = Callback(Videos, name='Highlights', query='game_i:3'), title='highlights', summary='Watch game highlights.'))
	#videos
	for c in cats['cats']:
		name = c['name']
		q = c['q']
		oc.add(DirectoryObject(key = Callback(Videos, name=name, query=q), title=name, summary=name))

	#prefs
	oc.add(PrefsObject(title="Preferences", summary="Configure the channel.", thumb=R("icon-prefs.png")))
	return oc


@route(PREFIX + '/vod', start = int)
def Videos(name, query, start = 0):
	oc = ObjectContainer(title2=name)
	url = 'http://smbsolr.cdnak.neulion.com/solr/NBA/select/?wt=json&fl=name,description,image,runtime,releaseDate,path_ced&sort=releaseDate+desc&rows=20&start=%d&q=%s' %(start, query)

	videos = JSON.ObjectFromURL(url, cacheTime=0)
	numFound = videos['response']['numFound']
	for v in videos['response']['docs']:
		description = v['description']
		image = 'http://smb.cdnllnwnl.neulion.com/u/nba/nba/thumbs/' + v['image'].replace('es', 'eb')
		runtime = v['runtime']
		name = v['name']
		path = v['path_ced'].replace('ced', '3000')
		oc.add(CreateVideoObject(url=path, runtime=runtime, title=name, summary=description, thumb=image, include=False))
	if start < numFound:
		oc.add(NextPageObject(key = Callback(Videos, name=name, query=query, start = start + 20), title='More...'))
	return oc


@route(PREFIX + '/livegames')
def LiveGames():
	oc = ObjectContainer(title2="Live Games", no_cache=True)
	today = Datetime.Now()
	monday = today - datetime.timedelta(days=today.weekday())
	schedule = HTTP.Request(url=monday.strftime('http://smb.cdnak.neulion.com/fs/nba/feeds_s2012/schedule/%Y/%-m_%-d.js'), cacheTime=CACHE_1DAY*6).content.replace('var g_schedule=', '')
	schedule = JSON.ObjectFromString(schedule)
	for s in schedule['games'][today.weekday()]:
		id = s['id']
		v = Dict['teams'][s['v']]
		h = Dict['teams'][s['h']]
		gs = s['gs']
		d = s['d']
		status = d[11:16] + " EST"
		if gs == 1 or gs == 2:
			status = 'IN PROGRESS'
		elif gs == 3:
			status = 'FINAL'
		oc.add(DirectoryObject(key=Callback(LiveGameFeeds, game=s), title="%s vs %s" %(v['teamname'], h['teamname']), summary=status))
	return oc


@route(PREFIX + '/livegamefeeds', game=dict)
def LiveGameFeeds(game):
	v = Dict['teams'][game['v']]
	h = Dict['teams'][game['h']]

	title="%s vs %s" %(v['teamname'], h['teamname'])
	oc = ObjectContainer(title2=title)

	oc.add(CreateGameObject(
		data = {'type': 'game', 'nt': '1', 'id': game['id'], 'format': 'xml', 'gt': 'live'},
		title = title,
		summary = 'Away Feed',
		thumb = R(game['v'] + ".png")
	))

	oc.add(CreateGameObject(
		data = {'type': 'game', 'nt': '1', 'id': game['id'], 'format': 'xml', 'gt': 'liveaway'},
		title = title,
		summary = 'Home Feed',
		thumb = R(game['h'] + ".png")
	))

	return oc


@route(PREFIX + '/nbalive')
def CreateNbaLiveObject(include = False):
	bitrate = Prefs['bitrate']
	if bitrate == 'Auto':
		bitrate = 5000

	VidRes = '720'
	if Prefs['bitrate'] == "3000" or Prefs['bitrate'] == "2400":
		VidRes = '540'
	elif Prefs['bitrate'] == "1600" or Prefs['bitrate'] == "1200":
		VidRes = '360'

	v = VideoClipObject(
			key = Callback(CreateNbaLiveObject, include = True),
			rating_key = 'nbalive',
			title = 'NBA Live',
			summary = '',
			thumb = R('nbatv.jpg'),
			items = [
				MediaObject(
					optimized_for_streaming = True,
					protocol = 'hls',
					container = 'mpegts',
					video_codec = VideoCodec.H264,
					parts = [PartObject(key = Callback(PlayEncryptedVideo, data = {'id': '0', 'type': 'channel', 'bitrate': bitrate}))]
				)
			]
		)

	if include:
		return ObjectContainer(objects=[v])
	return v

@route(PREFIX + '/creategameobject', data=dict)
def CreateGameObject(data, title, summary, thumb, include = False):
	bitrate = Prefs['bitrate']
	if bitrate == 'Auto':
		bitrate = 5000

	VidRes = '720'
	if Prefs['bitrate'] == "3000" or Prefs['bitrate'] == "2400":
		VidRes = '540'
	elif Prefs['bitrate'] == "1600" or Prefs['bitrate'] == "1200":
		VidRes = '360'

	data['bitrate'] = bitrate
	v = VideoClipObject(
			key = Callback(CreateGameObject, data = data, title=title, summary=summary, thumb=thumb, include = True),
			rating_key = "%s%s" %(data['id'], data['gt']),
			title = title,
			summary = summary,
			thumb = thumb,
			items = [
				MediaObject(
					optimized_for_streaming = True,
					protocol = 'hls',
					container = 'mpegts',
					video_codec = VideoCodec.H264,
					parts = [PartObject(key = Callback(PlayEncryptedVideo, data = data))]
				)
			]
		)

	if include:
		return ObjectContainer(objects=[v])
	return v


@route(PREFIX + '/createvideoobject')
def CreateVideoObject(url, runtime, title, summary, thumb, include = False):
	v = VideoClipObject(
			key = Callback(CreateVideoObject, url = url, runtime=runtime, title=title, summary=summary, thumb=thumb, include = True),
			rating_key = url,
			title = title,
			summary = summary,
			duration = int(runtime) * 1000,
			thumb = thumb,
			items = [
				MediaObject(
					optimized_for_streaming = True,
					parts = [PartObject(key = Callback(PlayVideo, url = url))]
				)
			]
		)

	if include:
		return ObjectContainer(objects=[v])
	return v


@indirect
@route(PREFIX + '/playvideo')
def PlayVideo(url):
	return IndirectResponse(VideoClipObject, key=HTTPLiveStreamURL(url))


@indirect
@route(PREFIX + '/playencryptedvideo', data = dict)
def PlayEncryptedVideo(data):
	bitrate = data['bitrate']
	del data['bitrate']

	if 'auth' not in Dict:
		Authenticate()

	path = XML.ElementFromURL('http://watch.nba.com/nba/servlets/publishpoint',
		data = urllib.urlencode(data),
		headers = {'User-Agent': Util.RandomItemFromList(UA), 'Cookie': Dict['auth']}
	)

	path = path.xpath("//path/text()")[0]

	if Prefs['bitrate'] != 'Auto':
		path = path.replace('ced', Prefs['bitrate'])
	Log.Debug("GOT URL: " + path)

	return IndirectResponse(VideoClipObject, key=HTTPLiveStreamURL(path))


def Authenticate():
	Log.Debug("logging in...")
	data = {
		"username": Prefs['username'],
		"password": Prefs['password']
	}

	login = HTTP.Request(url='https://watch.nba.com/nba/secure/login', values=data, headers = {'Content-type': 'application/x-www-form-urlencoded', 'User-Agent': Util.RandomItemFromList(UA)}, cacheTime=0)
	login.load()
	Dict['auth'] = login.headers['Set-Cookie']


def ValidatePrefs():
	Log.Debug("Preferences changed, re-authenticating...")
	Authenticate()
