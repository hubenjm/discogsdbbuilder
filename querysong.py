import scrapediscogs
import sqlite3
import sys

def main(argv):
	"""
	usage: python query.py songname <dbname.db>
	"""

	scrapediscogs.findSongLocal(argv[1], argv[2])


if __name__ == "__main__":
	main(sys.argv)
