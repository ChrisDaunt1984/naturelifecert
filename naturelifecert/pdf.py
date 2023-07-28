from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from naturelifecert.auth import login_required
from naturelifecert.db import get_db

bp = Blueprint('pdf', __name__)

@bp.route('/')
def index():
    db = get_db()
    #Don't expose email address to the wild :)
    posts = db.execute(
        'SELECT p.id, first_name, last_name, country, donation, currency, created'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()
    return render_template('pdf/index.html', posts=posts)

#TODO: Create and update could be bundled together
@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    print(request)
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name =  request.form['last_name']
        country =    request.form['country']
        donation =   request.form['donation']
        currency =   request.form['currency']
        email =   request.form['email']
        error = None

        for key in ['first_name',
                    'last_name',
                    'country',
                    'donation',
                    'currency',
                    'email']:
            if not locals()[key]:
                #TODO: Check for real currency values
                #TODO: Check if real email
                error = f'{key} is required'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO post (first_name, last_name, country, donation, currency, author_id, created)'
                ' VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)',
                (first_name, last_name, country, donation, currency, g.user['id'])
            )
            db.commit()
            return redirect(url_for('pdf.index'))

    return render_template('pdf/create.html')

def get_post(id, check_author=True):
    post = get_db().execute(
        'SELECT p.id, first_name, last_name, country, donation, currency, author_id'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()

    if post is None:
        abort(404, f"Post id {id} doesn't exist.")

    if check_author and post['author_id'] != g.user['id']:
        abort(403)

    return post

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_post(id)

    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        country = request.form['country']
        donation = request.form['donation']
        currency = request.form['currency']
        error = None

        for key in ['first_name',
                    'last_name',
                    'country',
                    'donation',
                    'currency']:
            if not locals()[key]:
                #TODO: Check for real currency values
                error = f'{key} is required'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE post SET first_name = ?, last_name = ?, country = ?, donation = ?, currency = ?, created=CURRENT_TIMESTAMP'
                ' WHERE id = ?',
                (first_name, last_name, country, donation, currency, id)
            )
            #db.commit()
            return redirect(url_for('pdf.index'))

    return render_template('pdf/update.html', post=post)

@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    db = get_db()
    db.execute('DELETE FROM post WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('pdf.index'))