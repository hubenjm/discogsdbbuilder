import discogs_client
import sqlite3
import csv
import re
from colors import colors
import progressbar

#change the token in 'token.txt' as needed
TOKEN = open('./token.txt').readline().strip()

def loadList(filename):
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

def findAlbum(d, artist, album):
	"""
	d: discog_client.Client object
	artist: string
	album: string
	
	returns: discogs_client.models.Release
	"""
	
	results = d.search(artist + ", " + album, type='release')
	#could spice this up by choosing the search result that includes the most meta data
	#for now it just returns the first result which has the artist string listed in the artists tag and matching title
	for j in range(len(results)):
		#print results[j].title, results[j].artists[0], type(results[j].artists)
		if re.search(album, results[j].title) and artist in [results[j].artists[k].name for k in range(len(results[j].artists))]:
			return results[j]

	print("findAlbum: Album '{}' not found.".format(artist + " - " + album))
	return None

def findArtist(d, artist):
	results = d.search(artist, type='artist')
	m = len(results)
	for j in xrange(m):
		if re.search(artist, results[j].name):
			return results[j]

	print("findArtist: Artist '{}' not found.".format(artist))
	return None

#	return results[0]

def getClient(token):
	return discogs_client.Client('MusicDBCreater/0.1', user_token=token)
	
def testsearch(filename):
	d = getClient(TOKEN)
	artists, albums = loadList(filename)
	assert len(artists) == len(albums)

	for j in range(len(artists)):
		release = findAlbum(d, artists[j], albums[j])
		print type(release)
		print artists[j] + " - " + release.title + ":"
		print release.formats[0]['name']
		print ', '.join(release.genres)
		print release.id
		for k in range(len(release.tracklist)):
			track = release.tracklist[k]
			print track.position + ": " + track.title + " - " + track.duration
		
		print "Credits:"
		for k in range(len(release.credits)):
			print release.credits[k].name
			print release.credits[k].id

		print "Notes:"
		print release.notes
		print type(release.notes)
		
		print "Companies:"
		print release.companies
		print type(release.companies)
		print ""

		print "Tracklist:"
		print type(release.tracklist)

		print type(release.id), type(release.formats[0]['name']), type(release.title), type(', '.join(release.genres)), type(release.year)


def populateDB(filename):
	conn = sqlite3.connect('example.db')
	
	c = conn.cursor()
	c.execute('''CREATE TABLE album
				(albumID int, title text, artistID int, artist text, year int,
					genres text, notes text, formats text,
					tracklist text, trackdurations text, companies text) ''')

#	c.execute('''CREATE TABLE artist
#				(artistID int, name text) ''')
#	
	c.execute('''CREATE TABLE track
				(title text, artistID int, albumID int, credits text, duration text, position text) ''')
	
	#get client
	d = getClient(TOKEN)

	#read entries from albumlistfile
	artists, albums = loadList(filename)
	m = len(albums)
	for j in range(m):
		release = findAlbum(d, artists[j], albums[j])
		release_artist = findArtist(d, artists[j])
		if release_artist is None:
			#just use first artist on list of artists given in release
			release_artist = release.artists[0]

		if release is None:
			print("populateDB: error, no album found for artist = {}, album = {}".format(artists[j], albums[j]))
		else:
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

			c.execute("INSERT INTO album (albumID, title, artistID, artist, year, genres, notes, formats, tracklist, trackdurations, companies) VALUES (?,?,?,?,?,?,?,?,?,?,?)", albumdata)

			for k in range(len(release.tracklist)):
				trackcredits = ", ".join([a.name for a in release.tracklist[k].credits])
				trackdata = [release.tracklist[k].title, release_artist.id, release.id, trackcredits, release.tracklist[k].duration, release.tracklist[k].position]
				c.execute("INSERT INTO track (title, artistID, albumID, credits, duration, position) VALUES (?,?,?,?,?,?)", trackdata)

			progressbar.printProgress(j+1, m, prefix = 'populateDB: adding album {}...'.format(j+1), suffix = '', decimals = 2, barLength = 50, printEnd = True)
	
	conn.commit()
	
#	for row in c.execute('SELECT * FROM album ORDER BY albumID'):
#		printAlbumEntry(row)
#		print ""

#	for row in c.execute('SELECT * FROM track ORDER BY title'):
#		print row

	conn.close()

def printTrackEntry(row):
	"""
	row is a tuple object with format (str, int, int, str, str, str)
	(title text, artistID int, albumID int, credits text, duration text, position text)

	"""

	print colors.bold + "track title: " + colors.endc, row[0]
	print colors.bold + "artist ID: " + colors.endc, row[1]
	print colors.bold + "album ID: " + colors.endc, row[2]
	print colors.bold + "credits: " + colors.endc, row[3]
	print colors.bold + "duration: " + colors.endc, row[4]
	print colors.bold + "position: " + colors.endc, row[5]

def printAlbumEntry(row):
	"""
	row is a tuple object with format (int, str, int, str, int, str, str, str, str, str, str)
	
	elements of tuple are in the order:
	1. albumID
	2. album title
	3. artistID
	4. artist name
	5. year
	6. genres
	7. notes
	8. formats
	9. track list
	10. track durations
	11. companies
	"""
	print colors.bold + "album ID: " + colors.endc, row[0]
	print colors.bold + "album title: " + colors.endc, row[1]
	print colors.bold + "artist ID: " + colors.endc, row[2]
	print colors.bold + "artist name: " + colors.endc, row[3]
	print colors.bold + "year: " + colors.endc, row[4]
	print colors.bold + "genres: " + colors.endc, row[5]
	print colors.bold + "notes: " + colors.endc, row[6]
	print colors.bold + "formats: " + colors.endc, row[7]
	print colors.bold + "track list: " + colors.endc, row[8]
	print colors.bold + "track durations: " + colors.endc, row[9]
	print colors.bold + "companies: " + colors.endc, row[10]

def findSongLocal(song, dbfile):
	conn = sqlite3.connect(dbfile)
	c = conn.cursor()

	data = c.execute("SELECT * FROM track WHERE title LIKE '%" + song + "%'")
	for row in data:
		printTrackEntry(row)

#		print ""
#		stuff = c.execute('SELECT * FROM album WHERE albumID=?', (row[2], ))
#		for a in stuff:
#			printAlbumEntry(a)

	conn.close()

def findAlbumLocal(title, dbfile):
	conn = sqlite3.connect(dbfile)
	c = conn.cursor()

	data = c.execute("SELECT * FROM album WHERE title LIKE '%" + title + "%'")
	for row in data:
		printAlbumEntry(row)

def executeSQLstatement(statement, dbfile):
	conn = sqlite3.connect(dbfile)
	c = conn.cursor()

	for row in c.execute('SELECT artist FROM album ORDER BY albumID'):
		print row

	conn.close()

if __name__ == "__main__":
#	testsearch('./albumsinput.txt')
	populateDB('./albumsinput.txt')
#	findSongLocal("Craigonometry", "example.db")
#	findAlbumLocal("Endless Fingers", "example.db")
