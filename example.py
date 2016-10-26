from scrapediscogs import MusicDatabase

music_db = MusicDatabase('example.db')
music_db.add_data('albumsinput.txt')
for r in music_db.find_albums_by_artist('David Sanborn'):
	print r
	print ""

for r in music_db.find_album(album_title = "The Call"):
	print r
	print ""

for r in music_db.find_song('Yeti'):
	print r
	print ""

for r in music_db.find_songs_by_album_artist('Seamus'):
	print r
	print ""

