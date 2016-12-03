from scrapediscogs import MusicDatabase

music_db = MusicDatabase('test.db', 85)
#music_db.add_data('albumsinput.txt')

#r = music_db.find_albums_by_artist('David Sanborn')
#print len(r)
#print r[-1]

#for r in music_db.find_album(album_title = "The Call"):
#	print r

for r in music_db.find_songs_by_album_artist('Seamus'):
	print r

