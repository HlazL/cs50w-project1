import os
import csv

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

DATABASE_URL='postgres://zkhvdbkfcysgnt:bc3c8db75fa52d6b2e5b9aa7e73403c9aaaaf6e54c5d2db60360f980877bea02@ec2-52-23-14-156.compute-1.amazonaws.com:5432/dcr1n8gv7kvaqv'
# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    #db.execute(" CREATE table users (id SERIAL PRIMARY KEY, username VARCHAR NOT NULL UNIQUE, password VARCHAR NOT NULL)")
    #db.execute("create table books (isbn varchar not null, title varchar not null, author varchar not null, year varchar not null)")
    db.execute(" CREATE table reviews (user_id int, book_id VARCHAR NOT NULL, review VARCHAR NOT NULL, rating int not null)")
    db.commit()
    """file=open("books.csv")
    reader = csv.reader(file)

    for isbn, title, author, year in reader:
        db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
        {"isbn": isbn,
        "title": title,
        "author": author,
        "year":year})

        print(f"Added a book {title} into db")


    db.commit()"""


if __name__=='__main__':
    main()
