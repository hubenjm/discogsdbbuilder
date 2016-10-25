import discogs_client
import sqlite3
import csv
import re
import os
from colors import colors
import progressbar

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
		#first look up artist in db and retrieve artist id
		#then search through albums db and match by artist id
		albums = []
		artist_results = self.find_artist(artist_name)
		for artist in artist_results:
			batch = self._cur.execute("SELECT * FROM album WHERE artistID = " + str(artist.id))
			for album_entry in batch:
				albums.append(Album(album_entry))

		return albums

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

			release_artist = find_artist_discogs(d, artists[j]) #at this point assumes that the input_album_list.txt correctly lists the album artist
			if release_artist is None: #failsafe in case user-given album artist yields no results
				#just use first artist on list of artists given in release
				release_artist = release.artists[0]

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
				trackcredits = ", ".join([a.name for a in release.tracklist[k].credits])
				trackdata = [release.tracklist[k].title, release_artist.id, release_artist.name, release.id, release.title, trackcredits, release.tracklist[k].duration, release.tracklist[k].position]
				self._cur.execute("INSERT OR IGNORE INTO track (title, artistID, artist, albumID, album, credits, duration, position) VALUES (?,?,?,?,?,?,?,?)", trackdata)

			progressbar.printProgress(j+1, m, prefix = 'add_data: adding album {}...'.format(j+1), suffix = '', decimals = 2, barLength = 40, printEnd = True)

		self._conn.commit()

class Album(object):
	"""The Album entry object."""
	def __init__(self, sql_album_tuple):
		self.id = sql_album_tuple[_ALBUM_ID]
		self.title = sql_album_tuple[_ALBUM_TITLE]
		self.artist_id = sql_album_tuple[_ALBUM_ARTIST_ID]
		self.artist_name = sql_album_tuple[_ALBUM_ARTIST_NAME]
		self.year = sql_album_tuple[_ALBUM_YEAR]
		self.genres = sql_album_tuple[_ALBUM_GENRES].split(', ')
		self.notes = sql_album_tuple[_ALBUM_NOTES].split(', ')
		self.formats = sql_album_tuple[_ALBUM_FORMATS].split(', ')
		self.track_list = sql_album_tuple[_ALBUM_TRACK_LIST].split(', ')
		self.track_durations = sql_album_tuple[_ALBUM_TRACK_DURATIONS].split(', ')
		self.companies = sql_album_tuple[_ALBUM_COMPANIES].split(', ')
	
	def __str__(self):
		s = colors.bold + "album ID: " + colors.endc + str(self.id) + '\n'\
			+ colors.bold + "album title: " + colors.endc + self.title + '\n'\
			+ colors.bold + "artist ID: " + colors.endc + str(self.artist_id) + '\n'\
			+ colors.bold + "artist name: " + colors.endc + self.artist_name + '\n'\
			+ colors.bold + "year: " + colors.endc + str(self.year) + '\n'\
			+ colors.bold + "genres: " + colors.endc + ", ".join(self.genres) + '\n'\
			+ colors.bold + "notes: " + colors.endc + ", ".join(self.notes) + '\n'\
			+ colors.bold + "formats: " + colors.endc + ", ".join(self.formats) + '\n'\
			+ colors.bold + "track list: " + colors.endc + ", ".join(self.track_list) + '\n'\
			+ colors.bold + "track durations: " + colors.endc + ", ".join(self.track_durations) + '\n'\
			+ colors.bold + "companies: " + colors.endc + ", ".join(self.companies)
		return s

class Track(object):
	"""The Track entry object."""
	def __init__(self, sql_track_tuple):
		self.title = sql_track_tuple[_TRACK_TITLE]
		self.artist_id = sql_track_tuple[_TRACK_ARTIST_ID]
		self.artist_name = sql_track_tuple[_TRACK_ARTIST_NAME]
		self.album_id = sql_track_tuple[_TRACK_ALBUM_ID]
		self.album_title = sql_track_tuple[_TRACK_ALBUM_TITLE]
		self.credits = sql_track_tuple[_TRACK_CREDITS]
		self.duration = sql_track_tuple[_TRACK_DURATION]
		self.position = sql_track_tuple[_TRACK_POSITION]

	def __str__(self):
		s = colors.bold + "track title: " + colors.endc + self.title + '\n'\
			+ colors.bold + "artist ID: " + colors.endc + str(self.artist_id) + '\n'\
			+ colors.bold + "artist name: " + colors.endc + self.artist_name + '\n'\
			+ colors.bold + "album ID: " + colors.endc + str(self.album_id) + '\n'\
			+ colors.bold + "album title: " + colors.endc + self.album_title + '\n'\
			+ colors.bold + "credits: " + colors.endc + ", ".join(self.credits) + '\n'\
			+ colors.bold + "duration: " + colors.endc + self.duration + '\n'\
			+ colors.bold + "position: " + colors.endc + self.position
		return s

class Artist(object):
	"""The Artist entry object."""
	def __init__(self, sql_artist_tuple):
		self.id = sql_artist_tuple[_ARTIST_ID]
		self.name = sql_artist_tuple[_ARTIST_NAME]

	def __str__(self):
		s = colors.bold + "artist ID: " + colors.endc + str(self.id) + '\n'\
			+ colors.bold + "artist name: " + colors.endc + self.name
		return s
		

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
		data = csv.reader(csvfile, delimiter=',')
		for row in data:
			assert len(row) == 2, "loadList: error, row does not have sufficient entries"
			artists.append(row[0])
			albums.append(row[1])

	return artists, albums

def find_album_discogs(d, artist, album):
	"""
	d: discog_client.Client object
	artist: string
	album: string
	
	returns: discogs_client.models.Release
	"""
	results = d.search(artist + ", " + album, type='release')
	#could spice this up by choosing the search result that includes the most meta data
	#for now it just returns the first result which has the artist string listed in the artists tag and matching title
	for j in xrange(len(results)):
		#print results[j].title, results[j].artists[0], type(results[j].artists)
		if re.search(album, results[j].title) and artist in [results[j].artists[k].name for k in range(len(results[j].artists))]:
			return results[j]

	print("findAlbum: Album '{}' not found.".format(artist + " - " + album))
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

if __name__ == "__main__":
	music_db = MusicDatabase('example.db')
#	music_db.add_data('albumsinput.txt')
	for r in music_db.find_albums_by_artist('Seamus Blake'):
		print r
		print ""

	for r in music_db.find_album(album_title = "The Call"):
		print r
		print ""

	
