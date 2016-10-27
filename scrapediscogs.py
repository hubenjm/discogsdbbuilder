import discogs_client
import sqlite3
import csv
import re
#from fuzzywuzzy import fuzz
from unidecode import unidecode
import os

#change the token in 'token.txt' as needed
TOKEN = open('./token.txt').readline().strip()

# album table entry positions
_ALBUM_ID = 0
_ALBUM_TITLE = 1
_ALBUM_ARTIST_ID = 2
_ALBUM_ARTIST_NAME = 3
_ALBUM_YEAR = 4
_ALBUM_GENRES = 5
_ALBUM_NOTES = 6
_ALBUM_FORMATS = 7
_ALBUM_TRACK_LIST = 8
_ALBUM_TRACK_DURATIONS = 9
_ALBUM_COMPANIES = 10

# track table entry positions
_TRACK_TITLE = 0
_TRACK_ARTIST_ID = 1
_TRACK_ARTIST_NAME = 2
_TRACK_ALBUM_ID = 3
_TRACK_ALBUM_TITLE = 4
_TRACK_CREDITS = 5
_TRACK_DURATION = 6
_TRACK_POSITION = 7

# artist table entry positions
_ARTIST_ID = 0
_ARTIST_NAME = 1

class MusicDatabase(object):
	def __init__(self, music_db_filename):
		self._music_db_filename = music_db_filename
		self._directory = os.path.dirname(os.path.abspath(__file__))
		self._music_db_location = os.path.join(self._directory, self._music_db_filename)
		self._conn = sqlite3.connect(self._music_db_location)
		self._cur = self._conn.cursor()

	def __del__(self):
		self._conn.close()

	def find_song(self, song_name, artist_name = None):
		song_results = []
		if artist_name is None:
			statement = "SELECT * FROM track WHERE title LIKE '%" + song_name + "%'"
		else:
			statement = "SELECT * FROM track WHERE title LIKE '%" + song_name + "%'" + "AND artist LIKE '%" + artist_name + "%'"
		data = self._cur.execute(statement)
		for entry in data:
			song_results.append(Track(entry))

		return song_results

	def find_artist(self, artist_name):
		"""
		parameters:
		artist_name (str)

		returns: list of Artist objects
		"""
		artist_results = []
		statement = "SELECT * FROM artist WHERE name LIKE '%" + artist_name + "%'"

		data = self._cur.execute(statement)
		for entry in data:
			artist_results.append(Artist(entry))

		return artist_results


	def find_album(self, album_title = None, artist_name = None):
		"""
		parameters:
		album_name (str)
		artist_name (str)

		returns: list of Album objects
		"""
		assert album_title is not None

		album_results = []
		if artist_name is None:
			statement = "SELECT * FROM album WHERE title LIKE '%" + album_title + "%'"
		else:
			statement = "SELECT * FROM album WHERE title LIKE '%" + album_title + "%'" + "AND artist LIKE '%" + artist_name + "%;"

		data = self._cur.execute(statement)
		for entry in data:
			album_results.append(Album(entry))

		return album_results

	def find_composer(self, composer_name):
		"""
		searches through track table of database for any track with credits specifying the writer is equal to the given composer_name
		"""
		pass

	def find_albums_by_artist(self, artist_name):
		"""
		"""
		albums = []
		for album_entry in self._cur.execute("SELECT * FROM album WHERE artist LIKE '%" + artist_name + "%'"):
			albums.append(Album(album_entry))

		return albums

	def find_songs_by_album_artist(self, artist_name):
		tracks = []
		for track_entry in self._cur.execute("SELECT * FROM track WHERE artist LIKE '%" + artist_name + "%'"):
			tracks.append(Track(track_entry))
		return tracks

	def _execute_sqlite3_statement(self, statement):
		return self._cur.execute(statement)

	def add_data(self, albums_input_location):
		"""
		"""
		#create tables if they don't yet exist
		self._cur.execute('''CREATE TABLE IF NOT EXISTS album
					(albumID int, title text, artistID int, artist text, year int,
						genres text, notes text, formats text,
						tracklist text, trackdurations text, companies text, UNIQUE(albumID))''')

		self._cur.execute('''CREATE TABLE IF NOT EXISTS artist (ID int, name text, UNIQUE(ID))''')
		
		self._cur.execute('''CREATE TABLE IF NOT EXISTS track
					(title text, artistID int, artist text, albumID int, album txt, credits text, duration text, position text, UNIQUE(title, artistID, albumID))''')
	
		#get discogs client
		d = get_discogs_client(TOKEN)

		#read entries from albumlistfile
		artists, albums = load_album_list(albums_input_location)
		m = len(albums)
		for j in xrange(m):
			release = find_album_discogs(d, artists[j], albums[j])
			if release is None:
				print("add_data: no album found for artist = {}, album = {}. skipping...".format(artists[j], albums[j])) #incorporate logging here?
				continue

			#release_artist = release.artists[0]
			release_artist = match_artist(release.artists, artists[j])
			if release_artist is None:
				print("add_data: no album found for artist = {}, album = {}. skipping...".format(artists[j], albums[j]))
				continue

			print "add_data: {}/{} - ".format(j+1, m) + str(release)
			#insert artist into database if not yet present
			self._cur.execute("INSERT OR IGNORE INTO artist (ID, name) VALUES (?,?)", [release_artist.id, release_artist.name])

			#process release.tracklist
			tracknames = [release.tracklist[k].title for k in range(len(release.tracklist))]
			tracklengths = [release.tracklist[k].duration for k in range(len(release.tracklist))]

			if release.companies is not None and len(release.companies) > 0:
				companies = [release.companies[k].name for k in range(len(release.companies))]
				companies_text = ", ".join(companies)
			else:
				companies_text = ""

			if release.notes is None:
				notes_text = ""
			else:
				notes_text = release.notes.strip()

			albumdata = [release.id, release.title, release_artist.id, release_artist.name, release.year, ", ".join(release.genres), notes_text, release.formats[0]['name'], ", ".join(tracknames),
				", ".join(tracklengths), companies_text]

			self._cur.execute("INSERT OR IGNORE INTO album (albumID, title, artistID, artist, year, genres, notes, formats, tracklist, trackdurations, companies) VALUES (?,?,?,?,?,?,?,?,?,?,?)", albumdata)
			for k in xrange(len(release.tracklist)):
				trackcredits = ", ".join([str(a.id) + " - " + a.name for a in release.tracklist[k].credits])
				trackdata = [release.tracklist[k].title, release_artist.id, release_artist.name, release.id, release.title, trackcredits, release.tracklist[k].duration, release.tracklist[k].position]
				self._cur.execute("INSERT OR IGNORE INTO track (title, artistID, artist, albumID, album, credits, duration, position) VALUES (?,?,?,?,?,?,?,?)", trackdata)

		self._conn.commit()

class Album(object):
	"""The Album entry object."""
	def __init__(self, sql_album_tuple):
		self.id = sql_album_tuple[_ALBUM_ID]
		self.title = sql_album_tuple[_ALBUM_TITLE]
		self.artist_id = sql_album_tuple[_ALBUM_ARTIST_ID]
		self.artist_name = sql_album_tuple[_ALBUM_ARTIST_NAME]
		self.year = sql_album_tuple[_ALBUM_YEAR]
		#below are lists
		self.genres = sql_album_tuple[_ALBUM_GENRES].split(', ')
		self.notes = sql_album_tuple[_ALBUM_NOTES].split(', ')
		self.formats = sql_album_tuple[_ALBUM_FORMATS].split(', ')
		self.track_list = sql_album_tuple[_ALBUM_TRACK_LIST].split(', ')
		self.track_durations = sql_album_tuple[_ALBUM_TRACK_DURATIONS].split(', ')
		self.companies = sql_album_tuple[_ALBUM_COMPANIES].split(', ')
	
	def __unicode__(self):
		s = u"album ID: " + unicode(self.id) + '\n'\
			+ u"album title: " + unicode(self.title) + '\n'\
			+ u"artist ID: " + unicode(self.artist_id) + '\n'\
			+ u"artist name: " + unicode(self.artist_name) + '\n'\
			+ u"year: " + unicode(self.year) + '\n'\
			+ u"genres: " + unicode(", ".join(self.genres)) + '\n'\
			+ u"notes: " + unicode(", ".join(self.notes)) + '\n'\
			+ u"formats: " + unicode(", ".join(self.formats)) + '\n'\
			+ u"track list: " + unicode(", ".join(self.track_list)) + '\n'\
			+ u"track durations: " + unicode(", ".join(self.track_durations)) + '\n'\
			+ u"companies: " + unicode(", ".join(self.companies))

		return s

	def __str__(self):
		return unicode(self).encode('utf-8')

class Track(object):
	"""The Track entry object."""
	def __init__(self, sql_track_tuple):
		self.title = sql_track_tuple[_TRACK_TITLE]
		self.artist_id = sql_track_tuple[_TRACK_ARTIST_ID]
		self.artist_name = sql_track_tuple[_TRACK_ARTIST_NAME]
		self.album_id = sql_track_tuple[_TRACK_ALBUM_ID]
		self.album_title = sql_track_tuple[_TRACK_ALBUM_TITLE]
		self.credits = sql_track_tuple[_TRACK_CREDITS].split(', ')
		self.duration = sql_track_tuple[_TRACK_DURATION]
		self.position = sql_track_tuple[_TRACK_POSITION]

	def __unicode__(self):
		s = u"track title: " + self.title + '\n'\
			+ u"artist ID: " + unicode(self.artist_id) + '\n'\
			+ u"artist name: " + unicode(self.artist_name) + '\n'\
			+ u"album ID: " + unicode(self.album_id) + '\n'\
			+ u"album title: " + unicode(self.album_title) + '\n'\
			+ u"credits: " + unicode(", ".join(self.credits)) + '\n'\
			+ u"duration: " + unicode(self.duration) + '\n'\
			+ u"position: " + unicode(self.position)
		return s

	def __str__(self):
		return unicode(self).encode('utf-8')

class Artist(object):
	"""The Artist entry object."""
	def __init__(self, sql_artist_tuple):
		self.id = sql_artist_tuple[_ARTIST_ID]
		self.name = sql_artist_tuple[_ARTIST_NAME]

	def __unicode__(self):
		s = u"artist ID: " + unicode(self.id) + '\n'\
			+ u"artist name: " + unicode(self.name)
		return s

	def __str__(self):
		return unicode(self).encode('utf-8')
		

def load_album_list(filename):
	"""
	assume csv values, two columns
	artist, albumtitle

	returns a list of strings in the form "artist, album title"
	They will be used to search through the discogs database
	"""
	albums = []
	artists = []
	with open(filename, 'rb') as csvfile:
		data = csv.reader(csvfile, delimiter='|')
		for row in data:
			assert len(row) == 2, "loadList: error, row does not have sufficient entries"
			artists.append(unicode(row[0]))
			albums.append(unicode(row[1]))

	return artists, albums

def find_album_discogs(d, artist, album, max_depth = 25):
	"""
	d: discog_client.Client object
	artist: string
	album: string
	
	returns: discogs_client.models.Release
	"""
	results = d.search(artist + " - " + album, type='release')
	#could spice this up by choosing the search result that includes the most meta data
	#for now it just returns the first result which has the artist string listed in the artists tag and matching title
	for j in xrange(min(len(results), max_depth)):
		if validate_release(results[j], artist, album):
			return results[j]

	#if no results, try searching for just album name
	results = d.search(album, type='release')
	for j in xrange(min(len(results), max_depth)):
		if validate_release(results[j], artist, album):
			return results[j]	

	return None

def validate_release(discogs_release, artist_name, album_title):
	# check that given artist appears in discogs_release.artists list
	# check that album_title appears in release.title
	if unidecode(artist_name.lower()) in ', '.join([unidecode(discogs_release.artists[k].name.lower()) for k in range(len(discogs_release.artists))]):
		if unidecode(album_title.lower()) in unidecode(discogs_release.title.lower()):
			return True
		else:
			return False	
	else:
		return False

def match_artist(discogs_artists, artist_name):
	#discogs_artists is a list of discogs Artists objects, each with a name attribute
	#return the first Artist on the list that matches artist_name
	for j in xrange(len(discogs_artists)):
		if unidecode(artist_name.lower()) in unidecode(discogs_artists[j].name.lower()):
			return discogs_artists[j]

	return None

def find_artist_discogs(d, artist):
	results = d.search(artist, type='artist')
	m = len(results)
	for j in xrange(m):
		if re.search(artist, results[j].name):
			return results[j]

	print("findArtist: Artist '{}' not found.".format(artist))
	return None

def get_discogs_client(token):
	return discogs_client.Client('MusicDBCreater/0.1', user_token=token)
	
