# -*- coding: utf-8 -*-

import urlparse
import re
import time

NAME = 'NHL GameCenter'
ART  = 'art-default.jpg'
ICON = 'icon.png'

PREFIX = '/video/nhlgamecenter'

UA = [
	'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Trident/6.0; Xbox; Xbox One)',
	'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0; Xbox)'
	'Roku/DVP-4.3 (024.03E01057A), Mozilla/5.0(iPad; U; CPU iPhone OS 3_2 like Mac OS X; en-us) AppleWebKit/531.21.10 (KHTML, like Gecko) Version/4.0.4 Mobile/7B314 Safari/531.21.10'
]

TEAMS = ["Anaheim Ducks", "Arizona Coyotes", "Boston Bruins", "Buffalo Sabres", "Carolina Hurricanes", "Columbus Blue Jackets", "Calgary Flames", "Chicago Blackhawks", "Colorado Avalanche", "Dallas Stars", "Detroit Red Wings", "Edmonton Oilers", "Florida Panthers", "Los Angeles Kings", "Minnesota Wild", "Montréal Canadiens", "New Jersey Devils", "Nashville Predators", "New York Islanders", "New York Rangers", "Ottawa Senators", "Philadelphia Flyers", "Pittsburgh Penguins", "San Jose Sharks", "St. Louis Blues", "Tampa Bay Lightning", "Toronto Maple Leafs", "Vancouver Canucks", "Winnipeg Jets", "Washington Capitals"]
CODE = ["ANA", "ARI", "BOS", "BUF", "CAR", "CBJ", "CGY", "CHI", "COL", "DAL", "DET", "EDM", "FLA", "LAK", "MIN", "MTL", "NJD", "NSH", "NYI", "NYR", "OTT", "PHI", "PIT", "SJS", "STL", "TBL", "TOR", "VAN", "WPG", "WSH"]

####################################################################################################

def Start():
	ObjectContainer.title1 = NAME
	ObjectContainer.art = R(ART)
	ObjectContainer.no_cache = True
	DirectoryObject.thumb = R(ICON)
	DirectoryObject.art = R(ART)
	HTTP.Headers['User-agent'] = Util.RandomItemFromList(UA)

	teams = JSON.ObjectFromString(Resource.Load(R('teams.json')))
	Log.Debug(teams)
	Dict['teams'] = {}
	for i in teams:
		Dict['teams'][i['code']] = teams[i]

@handler(PREFIX, NAME, thumb=ICON, art=ART)
def MainMenu():
	oc = ObjectContainer()
	oc.add(DirectoryObject(key = Callback(LiveGames), title="Live Games", summary="Watch live games for today."))
	oc.add(DirectoryObject(key = Callback(ArchivedGames), title="Archived Games", summary="Watch archived games as far back as the 2011/2012 season."))
	oc.add(DirectoryObject(key = Callback(LeagueVideos), title="Latest Videos", summary="Watch the latest videos around the league."))
	#other videos
	oc.add(DirectoryObject(key = Callback(Videos, id = 2188, name = Prefs['team'], type = 7, type_id = 2), title=Prefs['team'], summary="%s latest videos" %Prefs['team'], thumb = R(CODE[TEAMS.index(Prefs['team'])] + ".png")))
	menuItems = HTTP.Request(url='http://smb.cdnak.neulion.com/fs/nhl/player/173.js', cacheTime=CACHE_1DAY * 7).content
	menuItems = JSON.ObjectFromString(menuItems.replace("var g_menu=", ""))
	for mi in menuItems['menus']:
		id = mi['id']
		name = mi['name']
		type = mi['type']
		type_id = mi['type_id']
		if name == 'Liked Team':
			continue
		oc.add(DirectoryObject(key = Callback(Videos, id = id, name = name, type = type, type_id = type_id), title=name, summary=name))

	oc.add(PrefsObject(title="Preferences", summary="Configure the channel.", thumb=R("icon-prefs.png")))
	return oc


@route(PREFIX + '/vod', id=int, name=str, type=int, type_id=int, start=int)
def Videos(id, name, type, type_id, start = 0):
	oc = ObjectContainer(title2=name)
	tag = CODE[TEAMS.index(Prefs['team'])]
	if type == 0:
		url = 'http://neulionms.hs.llnwd.net/solr/nhlvc/selectproxy/?wt=json&sort=releaseDate+desc&q=catId:%d&start=%d&rows=20' %(type_id, start)
	elif type == 1:
		url = 'http://neulionms.hs.llnwd.net/solr/nhlvc/selectproxy/?wt=json&sort=releaseDate+desc&q=dailyPlaylistId:%d&start=%d&rows=20' %(type_id, start)
	elif type == 7 and type_id == 2:
		url = 'http://neulionms.hs.llnwd.net/solr/nhlvc/selectproxy/?wt=json&sort=releaseDate+desc&q=tags:%s&start=%d&rows=20' %(tag, start)
	elif type == 700 and type_id == 0:
		url = 'http://neulionms.hs.llnwd.net/solr/nhlvc/selectproxy/?wt=json&sort=releaseDate+desc&q=range2:30day&start=%d&rows=20' %start
	elif type == 701 and type_id == 1:
		url = 'http://neulionms.hs.llnwd.net/solr/nhlvc/selectproxy/?wt=json&sort=releaseDate+desc&q=range1:15min&start=%d&rows=20' %start

	videos = JSON.ObjectFromString(HTTP.Request(url=url).content.replace("\\'", ""))
	for v in videos['response']['docs']:
		oc.add(CreateVideoObject(
			url = v['publish_point'],
			format = v['formats'],
			title = v['name'],
			thumb = v['thumbnail_mobile'].replace('es', 'eb'),
			summary = v['description']
		))

	numFound = videos['response']['numFound']
	if start < numFound:
		oc.add(NextPageObject(key = Callback(Videos, id = id, name = name, type = type, type_id = type_id, start = start + 20), title='More...'))
	return oc


@route(PREFIX + '/leaguevideos')
def LeagueVideos(url = 'http://live.nhl.com/latest/league/CA.json'):
	oc = ObjectContainer(title2="Latest Videos", no_cache=True)
	videos = JSON.ObjectFromString(HTTP.Request(url=url).content.replace("\\'", ""))
	for c in videos['cells']:
		if c['cellType'] != 'video':
			continue
		v = c['videoInformation']
		oc.add(CreateVideoObject(
			url = 'http://video.nhl.com/videocenter/servlets/playlist?format=json&ids=%d' %v['videoId'],
			format = None,
			title = v['videoTitle'],
			thumb = v['videoThumbnail'],
			summary = v['videoDescription']
		))

	if 'lmu' in videos and len(videos['lmu'].strip()) > 0:
		oc.add(NextPageObject(
			key = Callback(LeagueVideos, url = videos['lmu'].strip()),
			title = "More..."
		))
	return oc


@route(PREFIX + '/archivedgames')
def ArchivedGames():
	oc = ObjectContainer(title2="Archived Games")

	now = Datetime.Now()
	offset = 0
	if now.month < 9:
		offset = -1

	for i in range(now.year + offset, 2010, -1):
		s = "%d%d" %(i, i+1)
		oc.add(DirectoryObject(key = Callback(ArchivedSeason, season=s), title=s))

	return oc


@route(PREFIX + '/archivedseason')
def ArchivedSeason(season):
	now = str(Datetime.Now().year)

	#we can heavily cache the season schedule, if it's not the current season
	cacheTime = CACHE_1DAY * 30
	if now in season:
		cacheTime = 0

	schedule = JSON.ObjectFromURL('http://live.nhl.com/GameData/SeasonSchedule-%s.json' %season, cacheTime=cacheTime)

	sortedGames = {}
	for d in schedule:
		key = str(d['est'][:8])
		if key in sortedGames:
			games = sortedGames[key]
		else:
			games = []
		games.append(d)
		sortedGames[key] = games

	oc = ObjectContainer(title2=season)
	for i in sorted(sortedGames):
		oc.add(DirectoryObject(key = Callback(ArchivedGamesForDate, season=season, date=i), title="%s-%s-%s" %(i[:4], i[4:6], i[6:])))

	return oc

@route(PREFIX + '/archivedgamesfordate')
def ArchivedGamesForDate(season, date):
	now = str(Datetime.Now().year)
	#we can heavily cache the season schedule, if it's not the current season
	cacheTime = CACHE_1DAY * 30
	if now in season:
		cacheTime = 0

	schedule = JSON.ObjectFromURL('http://live.nhl.com/GameData/SeasonSchedule-%s.json' %season, cacheTime=cacheTime)
	oc = ObjectContainer(title2="%s-%s-%s" %(date[:4], date[4:6], date[6:]))
	for g in schedule:
		if g['est'].startswith(date):
			id = g['id']
			a = g['a']
			h = g['h']
			#title = "%s vs %h" %(Dict['teams'][a]['name'], Dict['teams'][h]['name'])
			title = "%s vs %s" %(a, h)
			oc.add(DirectoryObject(key = Callback(ArchivedGameMenu, id=id, away=a, home=h), title=title))

	return oc


@route(PREFIX + '/archivedgamemenu')
def ArchivedGameMenu(id, away, home):
	title = "%s vs %s" %(away, home)
	#oc = ObjectContainer(title2="%s vs %s" %(Dict['teams'][a]['name'], Dict['teams'][h]['name']))
	oc = ObjectContainer(title2=title)
	#image fix
	if away == 'PHX':
		away = 'ARI'

	#TODO - CHECK WHAT FEEDS WE HAVE AND ADD IT
	oc.add(CreateGameObject(
		url = 'http://gamecenter.nhl.com/nhlgc/servlets/publishpoint?type=game&id=%s&gs=archive&ft=2&nt=1' %id,
		title = title,
		thumb = R(home + ".png"),
		summary = 'Whole game replay'
	))
	oc.add(CreateGameObject(
		url = 'http://gamecenter.nhl.com/nhlgc/servlets/publishpoint?type=game&id=%s&gs=condensed&ft=2&nt=1' %id,
		title = title,
		thumb = R(home + ".png"),
		summary = 'Condensed game replay'
	))
	oc.add(CreateGameObject(
		url = 'http://gamecenter.nhl.com/nhlgc/servlets/publishpoint?type=game&id=%s&gs=archive&ft=4&nt=1' %id,
		title = title,
		thumb = R(away + ".png"),
		summary = 'Whole game replay'
	))
	oc.add(CreateGameObject(
		url = 'http://gamecenter.nhl.com/nhlgc/servlets/publishpoint?type=game&id=%s&gs=condensed&ft=4&nt=1' %id,
		title = title,
		thumb = R(away + ".png"),
		summary = 'Condensed game replay'
	))
	return oc

@route(PREFIX + '/livegames')
def LiveGames():

	oc = ObjectContainer(title2="Live Games", no_cache=True)
	today = Datetime.Now()

	url = today.strftime('http://f.nhl.com/livescores/nhl/leagueapp/20142015/scores/%Y-%m-%d_O2T1.json')
	schedule = JSON.ObjectFromURL(url)

	for g in schedule['games']:
		gameInformation = g['gameInformation']
		title = '%s vs. %s' %(gameInformation['awayTeam']['teamName'], gameInformation['homeTeam']['teamName'])
		if gameInformation['gs'] < 3:
			summary = gameInformation['easternGameTime']
		else:
			summary = gameInformation['currentGameTime']
		if 'gameStory' in g:
			oc.add(DirectoryObject(key = Callback(LiveGameFeeds, game=g), title=title, summary=summary, thumb=g['gameStory']['storyThumbnail']))
		else:
			oc.add(DirectoryObject(key = Callback(LiveGameFeeds, game=g), title=title, summary=summary))
	return oc


@route(PREFIX + '/livegamefeeds', game=dict)
def LiveGameFeeds(game):
	title = '%s vs %s' %(game['gameInformation']['awayTeam']['teamName'], game['gameInformation']['homeTeam']['teamName'])
	oc = ObjectContainer(title2=title)
	#game preview and what not - there's a gap where it does not exist, usually after the game ends for about 5 to 10mins
	if 'gameStory' in game:
		gameStory = game['gameStory']
		oc.add(CreateVideoObject(
			url = 'http://video.nhl.com/videocenter/servlets/playlist?format=json&ids=%d' %gameStory['storyVideoId'],
			format = None,
			title = gameStory['storyTitle'],
			thumb = gameStory['storyThumbnail'],
			summary = gameStory['storyDesc']
		))

	#http://gamecenter.nhl.com/nhlgc/servlets/game?format=xml&app=true&season=2010&type=03&gid=0146&iap
	gs = game['gameInformation']['gs']
	gameLiveVideo = game['gameLiveVideo']
	if gs > 1 and gs < 6:
		oc.add(CreateGameObject(
			url = 'http://gamecenter.nhl.com/nhlgc/servlets/publishpoint?type=game&id=%d&gs=live&ft=2&nt=1' %(game['gameInformation']['gameId']),
			title = title,
			summary = 'Home Feed',
			thumb = R(game['gameInformation']['homeTeam']['teamAbb'] + ".png")
		))
		oc.add(CreateGameObject(
			url = 'http://gamecenter.nhl.com/nhlgc/servlets/publishpoint?type=game&id=%d&gs=live&ft=4&nt=1' %(game['gameInformation']['gameId']),
			title = title,
			summary = 'Away Feed',
			thumb = R(game['gameInformation']['awayTeam']['teamAbb'] + ".png")
		))
		if gameLiveVideo['hasLiveFrenchVideo']:
			oc.add(CreateGameObject(
				url = 'http://gamecenter.nhl.com/nhlgc/servlets/publishpoint?type=game&id=%d&gs=live&ft=8&nt=1' %(game['gameInformation']['gameId']),
				title = title,
				summary = 'French Feed',
				thumb = R(game['gameInformation']['homeTeam']['teamAbb'] + ".png")
			))
		#add NBC, goalie cam1/2, rogers cam1/2/3

	#game ended - no more live streams of game...
	elif gs > 5:
		#whole
		oc.add(CreateGameObject(
			url = 'http://gamecenter.nhl.com/nhlgc/servlets/publishpoint?type=game&id=%d&gs=archive&ft=2&nt=1' %(game['gameInformation']['gameId']),
			title = title,
			thumb = R(game['gameInformation']['homeTeam']['teamAbb'] + ".png"),
			summary = 'Whole game replay'
		))
		oc.add(CreateGameObject(
			url = 'http://gamecenter.nhl.com/nhlgc/servlets/publishpoint?type=game&id=%d&gs=archive&ft=4&nt=1' %(game['gameInformation']['gameId']),
			title = title,
			thumb = R(game['gameInformation']['awayTeam']['teamAbb'] + ".png"),
			summary = 'Whole game replay'
		))
		#condensed
		oc.add(CreateGameObject(
			url = 'http://gamecenter.nhl.com/nhlgc/servlets/publishpoint?type=game&id=%d&gs=condensed&ft=2&nt=1' %(game['gameInformation']['gameId']),
			title = title,
			thumb = R(game['gameInformation']['homeTeam']['teamAbb'] + ".png"),
			summary = 'Condensed replay'
		))
		oc.add(CreateGameObject(
			url = 'http://gamecenter.nhl.com/nhlgc/servlets/publishpoint?type=game&id=%d&gs=condensed&ft=4&nt=1' %(game['gameInformation']['gameId']),
			title = title,
			thumb = R(game['gameInformation']['awayTeam']['teamAbb'] + ".png"),
			summary = 'Condensed replay'
		))
		if gameLiveVideo['hasLiveFrenchVideo']:
			oc.add(CreateGameObject(
				url = 'http://gamecenter.nhl.com/nhlgc/servlets/publishpoint?type=game&id=%d&gs=archive&ft=8&nt=1' %(game['gameInformation']['gameId']),
				title = title,
				thumb = R(game['gameInformation']['homeTeam']['teamAbb'] + ".png"),
				summary = 'Whole game replay'
			))

	return oc


@route(PREFIX + '/creategameobject')
def CreateGameObject(url, title, summary, thumb, include = False):
	bitrate = Prefs['bitrate']
	if bitrate == 'Auto':
		bitrate = 5000

	VidRes = '720'
	if Prefs['bitrate'] == "3000" or Prefs['bitrate'] == "2400":
		VidRes = '540'
	elif Prefs['bitrate'] == "1600" or Prefs['bitrate'] == "1200":
		VidRes = '360'

	v = VideoClipObject(
			key = Callback(CreateGameObject, url = url, title=title, summary=summary, thumb=thumb, include = True),
			rating_key = url,
			title = title,
			summary = summary,
			thumb = thumb,
			items = [
				MediaObject(
					optimized_for_streaming = True,
					protocol = 'hls',
					container = 'mpegts',
					video_codec = VideoCodec.H264,
					parts = [PartObject(key = Callback(PlayEncryptedVideo, url = url, bitrate = bitrate))]
				)
			]
		)

	if include:
		return ObjectContainer(objects=[v])
	return v


@route(PREFIX + '/createvideoobject')
def CreateVideoObject(url, format, title, summary, thumb, include = False):
	v = VideoClipObject(
			key = Callback(CreateVideoObject, url = url, format=format, title=title, summary=summary, thumb=thumb, include = True),
			rating_key = url,
			title = title,
			summary = summary,
			thumb = thumb,
			items = [
				MediaObject(
					optimized_for_streaming = True,
					parts = [PartObject(key = Callback(PlayVideo, format = format, url = url))]
				)
			]
		)

	if include:
		return ObjectContainer(objects=[v])
	return v


@indirect
@route(PREFIX + '/playvideo')
def PlayVideo(format, url):
	if url.startswith('http://video.nhl.com/videocenter/servlets/playlist'):
		video = JSON.ObjectFromString(HTTP.Request(url=url).content.replace("\\'", ""))
		format = video[0]['formats']
		url = video[0]['publishPoint']

	format = int(format)
	if '/s/' in url:
		url = url.replace('/s/', '/u/')
	if format == 1:
		url = url.replace('.mp4', '_sd.mp4')
	elif format == 2:
		url = url.replace('.mp4', '_sh.mp4')
	elif format != 0:
		url = url.replace('.mp4', '_hd.mp4')

	Log.Debug("PLAYING: " + url)
	return IndirectResponse(VideoClipObject, key=HTTPLiveStreamURL(url))


@indirect
@route(PREFIX + '/playencryptedvideo')
def PlayEncryptedVideo(url, bitrate):
	if 'auth' not in Dict:
		Authenticate()

	path = XML.ElementFromURL(url, headers = {'User-Agent': Util.RandomItemFromList(UA), 'Cookie': Dict['auth']})
	path = path.xpath("//path/text()")[0]
	if Prefs['bitrate'] != 'Auto':
		path = path.replace('ced', Prefs['bitrate'])
	return IndirectResponse(VideoClipObject, key=HTTPLiveStreamURL(path))


def Authenticate():
	Log.Debug("logging in...")
	data = {
		"username": Prefs['username'],
		"password": Prefs['password']
	}
	if Prefs['rogers']:
		data['rogers'] = 'true'

	login = HTTP.Request(url='https://gamecenter.nhl.com/nhlgc/secure/login', values=data, headers = {'Content-type': 'application/x-www-form-urlencoded', 'User-Agent': Util.RandomItemFromList(UA)}, cacheTime=0).content
	Dict['auth'] = login.headers['Set-Cookie']


def ValidatePrefs():
	Log.Debug("Preferences changed, re-authenticating...")
	Authenticate()
