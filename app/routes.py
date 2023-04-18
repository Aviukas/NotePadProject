from flask import render_template, flash, redirect, url_for, request, send_from_directory
from app import app, db
from app.forms import LoginForm, RegistrationForm, NoteForm, CategoryForm, SearchForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, Category, Note
from werkzeug.urls import url_parse
from werkzeug.utils import secure_filename
import os

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
@app.route('/index')
@login_required
def index():
    categories = current_user.categories.all()
    notes = current_user.notes.all()
    search_form = SearchForm()
    return render_template('index.html', categories=categories, notes=notes, search_form=search_form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/search', methods=['POST'])
@login_required
def search():
    form = SearchForm()
    if form.validate_on_submit():
        query = form.search.data
        notes = current_user.notes.filter(Note.title.contains(query)).all()
        return render_template('search.html', notes=notes, search_form=form)
    return redirect(url_for('index'))

@app.route('/filter_notes_by_category/<int:category_id>')
@login_required
def filter_notes_by_category(category_id):
    category = Category.query.get(category_id)
    if category and category.user_id == current_user.id:
        notes = category.notes.all()
    else:
        flash('Category not found.')
        notes = []
    search_form = SearchForm()
    return render_template('search.html', notes=notes, search_form=search_form)

@app.route('/create_category', methods=['GET', 'POST'])
@login_required
def create_category():
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(name=form.name.data, user_id=current_user.id)
        db.session.add(category)
        db.session.commit()
        flash('Category created.')
        return redirect(url_for('index'))
    return render_template('create_category.html', title='Create Category', form=form)

@app.route('/create_edit_note', defaults={'note_id': None}, methods=['GET', 'POST'])
@app.route('/create_edit_note/<int:note_id>', methods=['GET', 'POST'])
@login_required
def create_edit_note(note_id):
    note = Note.query.get(note_id) if note_id else None

    if note and note.user_id != current_user.id:
        flash('Note not found.')
        return redirect(url_for('index'))

    form = NoteForm(obj=note)
    
    form.category.choices = [(c.id, c.name) for c in Category.query.filter_by(user_id=current_user.id).all()]

    if form.validate_on_submit():
        if note is None:
            note = Note(user_id=current_user.id)
            db.session.add(note)

        note.title = form.title.data
        note.content = form.content.data
        note.category_id = form.category.data if form.category.data else None

        if form.image.data:
            if note.image_path and os.path.exists(os.path.join(app.static_folder, note.image_path)):
                os.remove(os.path.join(app.static_folder, note.image_path))

            image_filename = secure_filename(form.image.data.filename)
            image_path = os.path.join('uploads', str(current_user.id), image_filename)
            os.makedirs(os.path.join(app.static_folder, 'uploads', str(current_user.id)), exist_ok=True)
            form.image.data.save(os.path.join(app.static_folder, image_path))
            note.image_path = image_path

        db.session.commit()
        flash(f'Note { "updated" if note_id else "created" }.')
        return redirect(url_for('index'))

    return render_template('note_create_edit.html', note_form=form, note_id=note_id, mode='Edit' if note_id else 'Create')

@app.route('/edit_category/<int:category_id>', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    category = Category.query.get(category_id)

    if not category or category.user_id != current_user.id:
        flash('Category not found.')
        return redirect(url_for('index'))

    form = CategoryForm(obj=category)

    if form.validate_on_submit():
        category.name = form.name.data
        db.session.commit()
        flash('Category updated successfully.')
        return redirect(url_for('index'))

    return render_template('edit_category.html', title='Edit Category', form=form, category=category, category_id=category_id)


@app.route('/delete_category/<int:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    category = Category.query.get(category_id)
    if category and category.user_id == current_user.id:
        db.session.delete(category)
        db.session.commit()
        flash('Category deleted.')
    else:
        flash('Category not found.')
    return redirect(url_for('index'))

@app.route('/delete_note/<int:note_id>', methods=['POST'])
@login_required
def delete_note(note_id):
    note = Note.query.get_or_404(note_id)
    if note.user_id != current_user.id:
        abort(403)
    db.session.delete(note)
    db.session.commit()
    flash('Note has been deleted.', 'success')
    return redirect(url_for('index'))