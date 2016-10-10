import scrapediscogs
import sys

def main(argv):
	"""
	usage: python createdb.py <albumsinput.txt> <dbname.db>
	"""

	assert len(argv) >= 2
	if len(argv) == 3:
		dbfilename = 'example.db'
	else:
		dbfilename = argv[2]

	scrapediscogs.populateDB(argv[1], dbfilename)

if __name__ == "__main__":
	main(sys.argv)
