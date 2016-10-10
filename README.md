# discogsdbbuilder
Music SQL database builder and query framework based on the discogs API

This is a relatively simple program that reads in a text file containing the artist name and album title for a collection of albums in csv format.
The program **scrapealbuminfo.py** goes through each line of the text input and searches www.discogs.com using their Python API.
It then scrapes the different meta data for the given album and populates an SQL database using sqlite.

Once the database has been constructed, the user can then run standard SQL queries on the data.

# Instructions

To get started, you must obtain a token ID in order to make queries to www.discogs.com through their API. To do this, see https://www.discogs.com/developers/#page:authentication,header:authentication-request-token-url.
Essentially, you need to register an account there and then go to https://www.discogs.com/settings/developers.

# Design

All of the core functionality is included in the file scrapediscogs.py.

# Usage

```python createdb.py <albumsinput.txt> <dbname.db>```
```python querysong.py songname <dbname.db>```

# Future

* Add more specialized SQL calls and perhaps incorporate into query.py module
* Clean up, turn into bonafide app, and submit to PyPi
* If <dbname.db> already exists, fix createdb.py so that it overwrites or just updates with new entries
* Improve print output for search queries


