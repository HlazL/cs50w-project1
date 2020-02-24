import os, json

from flask import Flask, session, render_template, request, redirect, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from werkzeug.security import check_password_hash, generate_password_hash

import requests

from helpers import login_required

app = Flask(__name__)
DATABASE_URL='postgres://zkhvdbkfcysgnt:bc3c8db75fa52d6b2e5b9aa7e73403c9aaaaf6e54c5d2db60360f980877bea02@ec2-52-23-14-156.compute-1.amazonaws.com:5432/dcr1n8gv7kvaqv'
# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/login", methods=["POST", "GET"])
def login():

    # Forget any user_id
    session.clear()
    username = request.form.get("username")
    password = request.form.get("password")

    if request.method == "POST":
        #ensure username and password were submitted
        if not request.form.get('username'):
            return render_template("error.html", message = "username required")
        elif not request.form.get('password'):
            return render_template("error.html", message = "password required" )

        uname = db.execute("SELECT * from users where username = :username", {"username" : username}).fetchone()

        #username is in db and password is correct
        if uname == None:
            return render_template("error.html", message = "incorrect username")
        elif not check_password_hash(uname["password"], password):
            return render_template("error.html", message = "incorrect password")
        else:
            #remember which user logged in
            session["user_id"] = uname[0]
            session["user_name"] = uname[1]
            #redirecting to the home page
            return redirect("/")
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear() #forget any user id
    return redirect("/")

@app.route("/register", methods=["POST", "GET"])
def register():

    session.clear()
    username = request.form.get("username")

    if request.method=="POST":

        if not request.form.get("username"):
            return render_template("error.html", message = "username is required")
        elif not request.form.get('password'):
            return render_template("error.html", message = "password is required" )
        # Ensure confirmation wass submitted
        elif not request.form.get("confirmation"):
            return render_template("error.html", message="must confirm password")
        # Check passwords are equal
        elif not request.form.get("password") == request.form.get("confirmation"):
            return render_template("error.html", message="passwords didn't match")

        uname = db.execute("SELECT username from users where username = :username", {"username": username}).fetchone()

        if uname:
            return  render_template("error.html", message = "username already exists")
        else:
            # Hash user's password to store in DB
            hashedPassword = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)
            db.execute("INSERT into users (username, password) VALUES (:username, :password)", {"username": username, "password": hashedPassword})
            db.commit()

            uname = db.execute("SELECT * from users where username = :username", {"username" : username}).fetchone()
            session["user_id"] = uname[0]
            session["user_name"] = uname[1]
            return redirect("/")

    else:
        return render_template("register.html")

@app.route("/search", methods=["GET"])
@login_required
def search():

    if not request.args.get("book"):
        return render_template("error.html", message =  " what book are you looking for??")

    query = "%"+ request.args.get("book")+"%"
    query= query.title()
    books= db.execute("SELECT * from books where \
        isbn like :query or \
        title like :query or\
        author like :query limit 15", {"query": query})

    if books.rowcount ==0:
        return render_template("error.html", message = "we couldn't find your book")

    books = books.fetchall()

    return render_template("books.html", books= books)

@app.route("/book/<isbn>", methods = ["GET", "POST"])
@login_required
def book(isbn):
    if request.method == "POST":

        currentUser = session["user_id"]

        #get data from the form
        rating = request.form.get("rating")
        comment = request.form.get("comment")

        #get book id by isbn
        row= db.execute("SELECT isbn from books where isbn =:isbn", {"isbn": isbn}).fetchone()
        bookId = row[0]

        #check whether it's the first review on this book for current user
        first_rev = db.execute("SELECT * from reviews where user_id=:user_id and book_id=:book_id", {"user_id":currentUser, "book_id":bookId })

        if first_rev.rowcount == 1:
            return render_template("error.html", message =  "You've already submitted a review for this book")

        rating = int(rating)

        db.execute("INSERT INTO reviews (user_id, book_id, review, rating) VALUES \
                    (:user_id, :book_id, :review, :rating)",
                    {"user_id": currentUser, "book_id": bookId, "review": comment, "rating": rating})
        db.commit()
        return redirect("/book/"+isbn)

        #GET request
    else:
        book = db.execute("SELECT * from books where isbn=:isbn", {"isbn": isbn}).fetchall()

        """GOODREADS REVIEWS"""
        key = os.getenv("GOODREADS_KEY")

        #query the api with key and isbn as parameters
        query = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": key, "isbns": isbn})

        #convert to json format
        response = query.json()

        #get right to the dictionary of query
        response = response['books'][0]

        book.append(response)

        """users reviews"""

        book_rev = db.execute("SELECT * from books where isbn=:isbn", {"isbn": isbn}).fetchone()
        book_rev=book_rev[0]

        #fetch book reviews
        reviews =  db.execute("SELECT users.username, review, rating from users \
                    inner join reviews on users.id = reviews.user_id \
                    where book_id = :book", {"book": book_rev}).fetchall()


    return render_template("book.html", book= book, reviews = reviews)

@app.route("/api/<isbn>", methods = ["GET"])
@login_required
def api_call(isbn):

    book_info = db.execute("SELECT title, author, year, isbn, \
                count(reviews.user_id) as review_count, \
                avg(reviews.rating) as average_score\
                from books inner join reviews \
                on books.isbn = reviews.book_id\
                where isbn = :isbn \
                group by title, author, isbn, year", {"isbn": isbn})

    #error checking
    if book_info.rowcount !=1:
        return jsonify({"Error":"Invalid isbn" }), 422

    #fetch result
    b_inf= book_info.fetchone()

    #convert to dictionary
    result= dict(b_inf.items())
    result['average_score'] = float('%.2f'%(result['average_score']))


    return jsonify(result)
