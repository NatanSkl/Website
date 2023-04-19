from flask import Flask, render_template, request, redirect, url_for, session, abort
from flask_bcrypt import Bcrypt
from db import DBConnection
import re
import datetime
import string, random
from os import urandom

app = Flask(__name__)
bcrypt = Bcrypt(app)


#TODO make mydqldb return dicts and not lists, and fix all templates


@app.route("/")
def about():
    return render_template("about.html")


@app.route("/projects")
def projects():
    conn = DBConnection()
    cursor = conn.cursor
    db = conn.db
    cursor.execute("SELECT * FROM projects ORDER BY ID DESC")
    db.close()
    return render_template("projects.html", data=cursor.fetchall())


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        if request.form["name"] and request.form["message"]:
            conn = DBConnection()
            cursor = conn.cursor
            db = conn.db
            cursor.execute("INSERT INTO messages (name, email, message) VALUES (%s, %s, %s)", (request.form["name"], request.form["email"], request.form["message"]))
            db.commit()
            db.close()
            return redirect(url_for("about"))
    return render_template("contact.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST" and re.match("^[a-zA-Z0-9_]{3,20}$", request.form["username"]):
        conn = DBConnection()
        cursor = conn.cursor
        db = conn.db
        cursor.execute("SELECT * FROM users WHERE username=%s", (request.form["username"],))
        if not cursor.rowcount:
            hash = bcrypt.generate_password_hash(request.form["password"])
            cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", (request.form["username"], request.form["email"], hash))
            db.commit()
            cursor.execute("SELECT id FROM users WHERE username=%s", (request.form["username"],))
            id = cursor.fetchone()[0]
            db.close()
            session["id"] = id
            session["username"] = request.form["username"]
            return redirect(url_for("about"))
        else:
            db.close()
            return render_template("signup.html", error=True)
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        conn = DBConnection()
        cursor = conn.cursor
        db = conn.db
        cursor.execute("SELECT id, password, permission_id FROM users WHERE username=%s", (request.form["username"],))
        if cursor.rowcount:
            result = cursor.fetchone()
            id = result[0]
            hash = result[1]
            permission_id = result[2]
            if bcrypt.check_password_hash(hash, request.form["password"]):
                session["id"] = id
                session["username"] = request.form["username"]
                session["permission_id"] = permission_id
                db.close()
                return redirect(url_for("about"))
            else:
                db.close()
                return render_template("login.html", passError=True)
        else:
            db.close()
            return render_template("login.html", userError=True)
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("id", None)
    session.pop("username", None)
    return redirect(url_for("login"))


@app.route("/forums", methods=["GET", "POST"])
def forums():
    categoryError = False
    conn = DBConnection()
    cursor = conn.cursor
    db = conn.db
    if request.method == "POST" and session["username"] and request.form["category"] and request.form["desc"]:
        if request.form["category"]:
            cursor.execute("SELECT * FROM categories WHERE name=%s", (request.form["category"],))
            if cursor.rowcount == 0:
                cursor.execute("INSERT INTO categories (name, `desc`) VALUES (%s, %s)", (request.form["category"], request.form["desc"]))
                db.commit()
            else:
                categoryError = True
    cursor.execute("SELECT name, `desc` FROM categories ORDER BY RAND() LIMIT 0,10")
    list = cursor.fetchall()
    db.close()
    return render_template("forums.html", list=list, categoryError=categoryError)


@app.route("/forums/category/<category>/", methods=["GET", "POST"])
def specific_forum(category):
    data = []
    post_error = False
    category_error = False
    conn = DBConnection()
    cursor = conn.cursor
    db = conn.db
    user_id = session["id"] if session.get("id") else 0
    cursor.execute("SELECT id FROM categories WHERE name=%s", (category,))
    if cursor.rowcount:
        category_id = cursor.fetchone()[0]
    else:
        category_error = True
    if session.get("username"):
        if request.method == "POST":
            if not category_error:
                date = get_date()
                identifier = get_unique_id()
                cursor.execute("INSERT INTO posts (title, content, date, identifier, submitter_id, category_id) VALUES (%s, %s, %s, %s, %s, %s)", (request.form["title"], request.form["content"], date, identifier, user_id, category_id))
                db.commit()
    if not category_error:
        cursor.execute("""SELECT posts.title, posts.content, posts.date, users.username, posts.identifier,
                            IFNULL(SUM(votes.vote), 0) AS vote_count,
                            IFNULL((SELECT vote FROM votes WHERE votes.post_id = posts.id AND votes.user_id = %s), 0) AS own_vote
                        FROM posts
                            LEFT JOIN users ON posts.submitter_id = users.id
                            LEFT JOIN votes ON posts.id = votes.post_id
                        WHERE posts.parent_id IS NULL AND posts.category_id = %s
                        GROUP BY posts.id
                        ORDER BY posts.id DESC""", (user_id, category_id))
        data = cursor.fetchall()
        if not cursor.rowcount:
            post_error = True
    db.close()
    return render_template("specific_forum.html", data=data, postError=post_error, categoryError=category_error)


def get_unique_id():
    return ''.join(random.choice(string.ascii_uppercase + string.digits + string.ascii_lowercase) for _ in range(15))


def get_date():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@app.route("/forums/category/<category>/<identifier>", methods=["GET", "POST"])
def specific_post(category, identifier):
    conn = DBConnection()
    cursor = conn.cursor
    db = conn.db
    user_id = session["id"] if session.get("id") else 0
    cursor.execute("SELECT id FROM categories WHERE name=%s", (category,))
    if not cursor.rowcount:
        abort(404)
    category_id = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM posts WHERE identifier=%s AND category_id=%s", (identifier, category_id))
    post_id = cursor.fetchone()[0]

    if request.method == "POST" and request.form["reply"] and session.get("username"):
        cursor.execute("SELECT id FROM posts WHERE identifier = %s", (request.form["identifier"],))
        parent_id = cursor.fetchone()[0]
        date = get_date()
        cursor.execute("INSERT INTO posts (content, date, identifier, submitter_id, category_id, parent_id) VALUES (%s, %s, %s, %s, %s, %s)", (request.form["reply"], date, get_unique_id(), user_id, category_id, parent_id))
        db.commit()

    reply_query = """SELECT posts.content, posts.date, users.username, posts.identifier,
                        IFNULL(SUM(votes.vote), 0) AS vote_count,
                        IFNULL((SELECT vote FROM votes WHERE votes.post_id = posts.id AND votes.user_id = %s), 0) AS own_vote,
                        posts.id
                    FROM posts
                        LEFT JOIN users ON posts.submitter_id = users.id
                        LEFT JOIN votes ON votes.post_id = posts.id
                    WHERE posts.parent_id = %s
                    GROUP BY posts.id"""

    cursor.execute(reply_query, (user_id, post_id))
    parent_replies = cursor.fetchall()
    constructed_parents = []

    for reply in parent_replies:
        cursor.execute(reply_query, (user_id, reply[-1],))
        children = cursor.fetchall()
        parent = list(reply)
        parent.append(children)
        constructed_parents.append(parent)

    cursor.execute("""SELECT posts.title, posts.content, posts.date, users.username, posts.identifier,
                    IFNULL(SUM(votes.vote), 0) AS vote_count,
                    IFNULL((SELECT vote FROM votes WHERE votes.post_id = %s AND votes.user_id = %s), 0) AS own_vote
                    FROM posts
                        LEFT JOIN users ON posts.submitter_id = users.id
                        LEFT JOIN votes ON votes.post_id = posts.id
                    WHERE posts.parent_id IS NULL AND posts.id = %s""", (post_id, user_id, post_id))
    post = cursor.fetchone()

    if cursor.rowcount:
        return render_template("specific_post.html", post=post, replies=constructed_parents)
    else:
        abort(404)


@app.route("/forums/vote", methods=["POST", ])
def vote():
    vote = int(request.form["vote"])
    is_remove = request.form["isRemove"]
    identifier = request.form["identifier"]
    if vote and is_remove and identifier and session.get("username"):
        conn = DBConnection()
        cursor = conn.cursor
        db = conn.db
        cursor.execute("SELECT id FROM posts WHERE identifier=%s", (identifier,))
        post_id = cursor.fetchone()[0]
        cursor.execute("DELETE FROM votes WHERE post_id=%s AND user_id=%s", (post_id, session["id"]))
        if is_remove == "false":
            cursor.execute("INSERT INTO votes (user_id, post_id, vote) VALUES (%s, %s, %s)", (session["id"], post_id, vote))
        db.commit()
        db.close()
        return ""


@app.route("/forums/<identifier>/delete", methods=["POST", ])
def delete(identifier):
    conn = DBConnection()
    cursor = conn.cursor
    db = conn.db
    cursor.execute("SELECT id, submitter_id FROM posts WHERE identifier = %s", (identifier, ))
    result = cursor.fetchone()
    post_id = result[0]
    submitter_id = result[1]
    if session["username"] and (session["permission_id"] == 2 or session["id"] == submitter_id):
        delete_children(post_id, cursor)
    db.commit()
    db.close()
    return ""


def delete_children(id, cursor):
    cursor.execute("SELECT id FROM posts WHERE parent_id = %s", (id,))
    children = cursor.fetchall()
    for child in children:
        delete_children(child[0], cursor)
    cursor.execute("DELETE FROM posts WHERE id = %s", (id,))


@app.route("/forums/<identifier>/edit", methods=["POST", ])
def edit(identifier):
    conn = DBConnection()
    cursor = conn.cursor
    db = conn.db
    cursor.execute("SELECT id, submitter_id FROM posts WHERE identifier = %s", (identifier,))
    result = cursor.fetchone()
    post_id = result[0]
    submitter_id = result[1]
    if session["username"] and request.form["content"] and (session["permission_id"] == 2 or session["id"] == submitter_id):
        cursor.execute("UPDATE posts SET content = %s WHERE id = %s", (request.form["content"], post_id))
        db.commit()
    db.close()
    return redirect(redirect_to_prev())


def redirect_to_prev(default='/forums'):
    return request.args.get('next') or request.referrer or url_for(default)


@app.route("/gameoflife")
def game_of_life():
    return render_template("gameoflife.html")


@app.errorhandler(404)
def page_not_found(error):
    return render_template("page_not_found.html"), 404


@app.context_processor
def inject_now():
    return {'now': datetime.datetime.utcnow()}


app.secret_key = urandom(24)


if __name__ == "__main__":
    app.run(threaded=True, host="0.0.0.0", debug=True)