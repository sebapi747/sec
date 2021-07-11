''' ---------------------------------------------------------------------------------------------
 Performance display website using flask
'''
from flask import Flask, request, session, g, redirect, abort, render_template, flash, Markup, url_for
from werkzeug.utils import secure_filename
import markdown
import config
import numpy as np
import pandas as pd
import os
import datetime as dt
import sqlite3
from contextlib import closing
import re
import uuid, hashlib
import requests
from itsdangerous import URLSafeTimedSerializer
import config

DATABASE= "perf.db"
BASEDIR = config.webdir
DEBUG = config.DEBUG
DATABASE =  'sec.db'
UPLOAD_FOLDER =  'static/pics'
ZIP_FOLDER = BASEDIR + 'zip'
ALLOWED_EXTENSIONS = set(['txt', 'pdf','dvi', 'png', 'jpg', 'jpeg', 'gif', 'zip'])
SECRET_KEY = config.SECRET_KEY
SECURITY_PASSWORD_SALT = config.SECURITY_PASSWORD_SALT

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)

def connect_db():
    print("opening %s" % app.config['DATABASE'])
    return sqlite3.connect(app.config['DATABASE'])

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

''' ---------------------------------------------------------------------------------------------
 SQLite utils
'''
def cursor_col_names(cursor):
    return [description[0] for description in cursor.description]

def sql_select_to_dict(cursor, key):
    col = cursor_col_names(cursor)
    found_idx = -1
    for i,col_name in enumerate(col):
            if (col_name==key):
                    found_idx = i
                    break
    out = dict()
    for res in cursor.fetchall():
        out[res[found_idx]] = dict(zip(col, res))
    return out

def sql_select_to_dictarray(cursor):
    col = cursor_col_names(cursor)
    return [dict(zip(col, res)) for res in cursor.fetchall()]

''' ---------------------------------------------------------------------------------------------
 app
 '''
@app.route('/')
def index():
    query = "SELECT cik, max(name) as name FROM sec_filer group by 1 order by 1"
    df = pd.read_sql_query(query,g.db)
    namelist = list(df['name'])
    return render_template('index.html', namelist=namelist)

''' ------------------------------------------------------------------------------------------------
   blog
'''
@app.route('/blog/<int:rowid>')
def blog(rowid):
    cur = g.db.execute('select rowid, * from blogentries where rowid=?', [rowid])
    entry = sql_select_to_dictarray(cur)[-1]
    entry['content'] = Markup(markdown.markdown(entry['text']))
    cur = g.db.execute('select rowid, * from blogentries order by entrydate desc')
    entries = sql_select_to_dictarray(cur)
    for e in entries:
        e['content'] = Markup(markdown.markdown(e['text']))
    session['blogrowid'] = rowid
    return render_template('blog.html', entries=entries, entry=entry)


@app.route('/blog', methods=['GET', 'POST'])
def blogindex():
    if request.method == 'GET':
        session.pop('blogrowid', None)
        cur = g.db.execute('select rowid, title, coverlink, entrydate from blogentries order by entrydate desc')
        entries = sql_select_to_dictarray(cur)
        # for e in entries:
        #    e['content'] = Markup(markdown.markdown(e['text']))
        return render_template('blog.html', entries=entries)
    if not session.get('logged_in'):
        abort(401)
    action = request.form['action']
    if action == 'Add':
        cur = g.db.execute('insert into blogentries (title, text, coverlink, entrydate) values (?,?,?,?)',
                           [request.form['title'], request.form['text'], request.form['coverlink'],
                            dt.datetime.utcnow()])
        flash('entry created.', 'info')
    elif action == 'Modify':
        cur = g.db.execute('update blogentries set text=?, title=?, coverlink=? where rowid=?',
                           [request.form['text'], request.form['title'], request.form['coverlink'],
                            session['blogrowid']])
        session.pop('blogrowid', None)
        flash('entry modified.', 'info')
    elif action == 'Delete':
        cur = g.db.execute('delete from blogentries where rowid=?', [session['blogrowid']])
        session.pop('blogrowid', None)
        flash('entry deleted.', 'info')
    else:
        flash('unknown action: ' + action, 'error')
        abort(400)
    g.db.commit()
    return redirect('blog')

''' ------------------------------------------------------------------------------------------------
   wiki wiki web
'''
def wikitext(title):
    cur = g.db.execute('select title from entries order by title')
    alltitles = sql_select_to_dictarray(cur)
    pics = os.listdir(app.config['UPLOAD_FOLDER'])
    cur = g.db.execute('select text from entries where title=?', [title])
    entries = [row[0] for row in cur.fetchall()]
    if len(entries) == 0:
        text = 'Page "' + title + '" is empty. This entry would sure be helpful, maybe you should propose a page about this topic.'
    else:
        text = entries[0]
    content = Markup(markdown.markdown(text))
    return {'text': text, 'content': content, 'title': title, 'alltitles': alltitles, 'pics': pics}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def remove_file(oldfile, tin):
    if allowed_file(oldfile) and os.path.exists(oldfile):
        if str(tin) in os.path.dirname(oldfile):
            flash('file  ' + os.path.basename(oldfile) + ' removed.', 'info')
            os.remove(oldfile)
        else:
            flash('file  ' + os.path.basename(oldfile) + ' not removed as it belongs to another tin.', 'info')


@app.route('/wiki/<title>')
def wiki(title):
    data = wikitext(title)
    return render_template('wiki.html', content=data['content'], title=title, newtitle=title, text=data['text'],
                           alltitles=data['alltitles'], pics=data['pics'])


@app.route('/wiki', methods=['GET','POST'])
def wikiedit():
    if request.method == 'GET':
        return redirect('/wiki/index')
    if not session.get('logged_in'):
        abort(401)
    targeturl = request.form.get('targeturl')
    action = request.form['action']
    if re.match(r"^Upload", action):
        file = request.files['file']
        if not file:
            flash('No file received.', 'error')
        elif not allowed_file(file.filename):
            flash('File name not allowed.', 'error')
        else:
            filename = secure_filename(file.filename)
            if action == 'Upload':
                file.save(app.config['UPLOAD_FOLDER'] + '/' + filename)
            else:
                file.save(app.config['ZIP_FOLDER'] + '/' + filename)
            flash('file  ' + filename + ' succeded.', 'info')
        return redirect(targeturl)
        return redirect(targeturl)
    newtitle = request.form['newtitle']
    if not re.match(r"^[A-Za-z0-9]+$", newtitle):
        flash('title ' + newtitle + ' must only contain alphanumeric characters.', 'error')
        abort(400)
    entrydate = dt.datetime.utcnow()
    if targeturl is None:
        targeturl = '/wiki/' + newtitle
    if action == 'Add':
        g.db.execute('insert into entries (title, text, entrydate) values (?,?,?)',
                           [newtitle, request.form['text'], entrydate])
        flash('entry ' + newtitle + ' created.', 'info')
    elif action == 'Modify':
        g.db.execute('update entries set text=? where title=?', [request.form['text'], newtitle])
        flash('entry ' + newtitle + ' modified.', 'info')
    elif action == 'Delete':
        g.db.execute('delete from entries where title=?', [newtitle])
        flash('entry ' + newtitle + ' deleted.', 'info')
    else:
        flash('unknown action: ' + action, 'error')
        abort(400)
    g.db.commit()
    return redirect(targeturl)

def redirect_url(default='index'):
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

@app.route('/file/<string:filename>')
def file(filename):
    if session.get('iseditor') is not None:
        return redirect('/static/pics/'+filename)
    else:
        flash("This url is restricted to the site's editors.", 'error')
        return redirect(redirect_url())

''' ---------------------------------------------------------------------------------------------
 authenticaltion
 '''
def hash_password(password):
    # uuid is used to generate a random number
    salt = uuid.uuid4().hex
    return hashlib.sha256(salt.encode() + password.encode()).hexdigest() + ':' + salt

def check_password(hashed_password, user_password):
    password, salt = hashed_password.split(':')
    return password == hashlib.sha256(salt.encode() + user_password.encode()).hexdigest()

def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])

def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt=app.config['SECURITY_PASSWORD_SALT'],
            max_age=expiration
        )
    except:
        return False
    return email

def send_confirm_email(email, token):
    flash(
        'Your email address needs to be verified. A verification email has just been sent to %s. Please check you email for verification.' % email,
        'error')
    confirm_url = url_for('confirm_email', token=token, _external=True)
    return requests.post(
        config.MAILGUN_MSG,
        auth=("api", config.MAILGUN_APIKEY),
        data={"from": "admin <admin@mg.aquanthus.club>",
              "to": email,
              "cc": "admin@mg.aquanthus.club",
              "subject": "email address validation for Aquanthus pnl and risk",
              "text": "Click on this link:%s to verify your email address." % confirm_url})

def send_reset_email(email, token):
    flash('A password reset email has just been sent to %s. Please check you email.' % email, 'error')
    reset_url = url_for('reset_with_token', token=token, _external=True)
    return requests.post(
        config.MAILGUN_MSG,
        auth=("api", config.MAILGUN_APIKEY),
        data={"from": "admin <admin@mg.aquanthus.club>",
              "to": email,
              "subject": "password reset for aquanthus.club",
              "text": "Click on this link:%s to reset yout password." % reset_url})

''' ---------------------------------------------------------------------------------------------
 login and passwd management
 '''
@app.route('/login', methods=['GET', 'POST'])
def login():
    cur = g.db.execute('select * from user')
    persons = sql_select_to_dict(cur, 'account_number')
    error = None
    if request.method == 'POST':
        if request.form['account_number'] not in persons.keys():
            error = 'Invalid username'
            flash(error, 'error')
        elif persons[request.form['account_number']]['confirmed'] != 1:
            email = request.form['email']
            error = 'User not confirmed. email sent to %s' % email
            flash(error, 'error')
            token = generate_confirmation_token(email)
            send_confirm_email(email, token)
        elif check_password(persons[request.form['account_number']]['passwd'], request.form['password']) != True:
            error = 'Invalid password'
            flash(error, 'error')
        else:
            session['logged_in'] = True
            session['email'] = persons[request.form['account_number']]['email']
            session['account_number'] = persons[request.form['account_number']]['account_number']
            session['iseditor'] = True if persons[request.form['account_number']]['iseditor'] else False
            flash('You were logged in as %s' % session['email'])
            return redirect('/')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('email', None)
    session.pop('iseditor', None)
    session.pop('account_number', None)
    flash('You were logged out')
    return redirect('/')

@app.route('/create_login', methods=['GET', 'POST'])
def create_login():
    error = None
    if request.method == 'GET':
        return render_template('create_login.html')
    if not re.match(r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$", request.form['email']):
        error = "Please provide email address in the name@domain format."
        flash(error, 'error')
        return render_template('create_login.html', error=error)
    if request.form['action'] == "Forgot Passwd":
        email = request.form['email']
        token = generate_confirmation_token(email)
        send_reset_email(email, token)
        return render_template('create_login.html')
    if len(request.form['password']) < 8:
        error = "Password must be at least 8 character."
        flash(error, 'error')
        return render_template('create_login.html')
    hpasswd = hash_password(request.form['password'])
    cur = g.db.execute('select * from user')
    tablekeys = cursor_col_names(cur)
    formkeys = request.form.keys()
    relevantkeys = list(set(formkeys) & set(tablekeys))
    relevantdict = dict()
    for key in relevantkeys:
        relevantdict[key] = request.form[key]
    relevantdict['registered_on'] = dt.datetime.utcnow()
    relevantdict['passwd'] = hpasswd
    relevantdict['confirmed'] = 0
    relevantdict['iseditor'] = 0 if relevantdict['account_number']!="50166" else 1
    try:
        sqlcmd = 'insert into user (' + ','.join(relevantdict.keys()) + ') values (' + ','.join(
            ['?'] * len(relevantdict)) + ')'
        g.db.execute(sqlcmd, list(relevantdict.values()))
        g.db.commit()
    except Exception as e:
        error = 'could not create user %s: %s' % (request.form['email'], str(e))
        flash(error, 'error')
        return render_template('create_login.html')
    else:
        flash("user created. validation email sent to %s" % request.form['email'])
    token = generate_confirmation_token(request.form['email'])
    send_confirm_email(request.form['email'], token)
    return render_template('login.html')

@app.route('/confirm_email/<token>')
def confirm_email(token):
    try:
        email = confirm_token(token)
    except:
        flash('The confirmation link is invalid or has expired.', 'danger')
    registered_on = dt.datetime.utcnow()
    g.db.execute('update user set confirmed=1, confirmed_on=? where email=?', [registered_on, email])
    g.db.commit()
    flash('You have verified your email. You can login now.', 'success')
    return redirect('/login')

@app.route('/reset/<token>', methods=["GET", "POST"])
def reset_with_token(token):
    try:
        email = confirm_token(token)
    except:
        abort(404)
    if request.method == 'GET':
        return render_template('reset_with_token.html', token=token)

    if len(request.form['password']) < 8:
        flash("Password must be at least 8 character.", "error")
        return redirect('/login')
    if not re.match(r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$", email):
        flash("Email address must be in the name@domain format.", "error")
        return redirect('/login')
    hpasswd = hash_password(request.form['password'])
    try:
        g.db.execute("update user set passwd=? where email=? and confirmed=1", [hpasswd, email])
        g.db.commit()
    except Exception as e:
        flash('could not update passwd for email %s: %s' % (email, type(e)), "error")
        return redirect('/login')
    flash('You have modified you passwd. You can login now.', 'success')
    return redirect('/login')

''' ---------------------------------------------------------------------------------------------
 main
 '''
def init_db(filename):
    with closing(connect_db()) as db:
        with app.open_resource(filename, mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

if __name__ == '__main__':
    #init_db('sql/schema.sql')
    app.run()
