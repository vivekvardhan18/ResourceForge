from flask import Flask, request, render_template, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import pandas as pd
import os
from ml_recommender import AcademicRecommender

# --- App and Recommender Initialization ---
app = Flask(__name__)
app.secret_key = 'your_super_secret_key' # Replace with a real secret key
recommender = AcademicRecommender()

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- User Model and Loader ---
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

def load_all_users():
    try:
        df = pd.read_csv('users.csv')
        return {str(row['id']): User(str(row['id']), row['username']) for _, row in df.iterrows()}
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return {}

@login_manager.user_loader
def load_user(user_id):
    users = load_all_users()
    return users.get(user_id)

# --- Main Routes ---
@app.route('/')
def search_page():
    levels = sorted(recommender.df['level'].unique().tolist())
    types = sorted(recommender.df['type'].unique().tolist())
    return render_template('index.html', levels=levels, types=types)

@app.route('/recommend', methods=['POST'])
def recommend_resources():
    topic_query = request.form.get('topic_query', '')
    level = request.form.get('level', '')
    resource_type = request.form.get('type', '')
    full_query = f"{topic_query} {level} {resource_type}"
    recommendations = recommender.recommend(full_query, top_n=10)
    
    paths = []
    if current_user.is_authenticated:
        user_id = int(current_user.id)
        try:
            paths_df = pd.read_csv('learning_paths.csv')
            paths = paths_df[paths_df['user_id'] == user_id].to_dict('records')
        except (FileNotFoundError, pd.errors.EmptyDataError):
            paths = []

    for rec in recommendations:
        rec['paid_status'] = 'Paid' if rec.get('paid') else 'Free'
        
    return render_template('results.html', recommendations=recommendations, query_topic=topic_query, query_level=level, query_type=resource_type, paths=paths)

@app.route('/personalized_recommendations')
@login_required
def personalized_recommendations():
    recs = recommender.get_personalized_recommendations(current_user.id)
    for rec in recs:
        rec['paid_status'] = 'Paid' if rec.get('paid') else 'Free'
    return render_template('results.html', recommendations=recs, query_topic="For You", query_level="Personalized", query_type="based on your saved items")

# --- Authentication Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('search_page'))
    if request.method == 'POST':
        users_df = pd.read_csv('users.csv')
        username = request.form['username']
        password = request.form['password']
        user_row = users_df[(users_df['username'] == username) & (users_df['password'] == password)]
        if not user_row.empty:
            user_id = str(user_row.iloc[0]['id'])
            user = User(user_id, username)
            login_user(user)
            return redirect(url_for('search_page')) 
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        users_df = pd.read_csv('users.csv')
        username = request.form['username']
        password = request.form['password']
        if username in users_df['username'].values:
            flash('Username already exists.', 'warning')
            return redirect(url_for('signup'))
        new_id = users_df['id'].max() + 1 if not users_df.empty else 1
        with open('users.csv', 'a', newline='') as f:
            f.write(f"\n{new_id},{username},{password}")
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('search_page'))

# --- Bookmarking & Learning Path Routes ---
@app.route('/save_to_path', methods=['POST'])
@login_required
def save_to_path():
    path_id_str = request.form.get('path_id')
    resource_title = request.form.get('resource_title')

    if not path_id_str:
        flash('You must select a learning path.', 'warning')
        return redirect(request.referrer or url_for('search_page'))
    
    path_id = int(path_id_str)

    path_resources_df = pd.read_csv('path_resources.csv')
    current_path_resources = path_resources_df[path_resources_df['path_id'] == path_id]
    
    if resource_title in current_path_resources['resource_title'].values:
        flash(f"'{resource_title}' is already in this path.", 'warning')
        return redirect(url_for('search_page'))

    new_order = current_path_resources['order'].max() + 1 if not current_path_resources.empty else 1
    with open('path_resources.csv', 'a', newline='') as f:
        f.write(f"\n{path_id},\"{resource_title}\",not_started,{new_order}")
    
    bookmarks_df = pd.read_csv('bookmarks.csv')
    user_id = int(current_user.id)
    if not bookmarks_df[(bookmarks_df['user_id'] == user_id) & (bookmarks_df['resource_title'] == resource_title)].empty:
        pass
    else:
        with open('bookmarks.csv', 'a', newline='') as f:
            f.write(f"\n{user_id},\"{resource_title}\"")

    flash(f"Resource saved to your learning path!", 'success')
    return redirect(url_for('search_page'))

@app.route('/my_paths')
@login_required
def my_paths():
    user_id = int(current_user.id)
    try:
        paths_df = pd.read_csv('learning_paths.csv')
        user_paths = paths_df[paths_df['user_id'] == user_id]
    except (FileNotFoundError, pd.errors.EmptyDataError):
        user_paths = pd.DataFrame(columns=['path_id', 'user_id', 'path_name'])
    return render_template('my_paths.html', paths=user_paths.to_dict('records'))

@app.route('/create_path', methods=['POST'])
@login_required
def create_path():
    path_name = request.form['path_name']
    user_id = int(current_user.id)
    paths_df = pd.read_csv('learning_paths.csv')
    new_path_id = paths_df['path_id'].max() + 1 if not paths_df.empty else 1
    with open('learning_paths.csv', 'a', newline='') as f:
        f.write(f"\n{new_path_id},{user_id},{path_name}")
    flash(f"Learning Path '{path_name}' created!", 'success')
    return redirect(url_for('my_paths'))

@app.route('/path/<int:path_id>')
@login_required
def path_detail(path_id):
    try:
        path_resources_df = pd.read_csv('path_resources.csv')
        path_specific_resources = path_resources_df[path_resources_df['path_id'] == path_id]
        if path_specific_resources.empty:
            resources_with_details = pd.DataFrame()
        else:
            main_resources_df = recommender.df
            resources_with_details = pd.merge(
                path_specific_resources,
                main_resources_df[['title', 'url']],
                left_on='resource_title',
                right_on='title',
                how='left'
            ).sort_values('order')
    except (FileNotFoundError, pd.errors.EmptyDataError):
        resources_with_details = pd.DataFrame()
    
    resources = resources_with_details
    if resources.empty:
        total = 0
        completed = 0
        next_resource = None
    else:
        total = len(resources)
        completed = len(resources[resources['status'] == 'completed'])
        not_completed_resources = resources[resources['status'] != 'completed']
        next_resource = not_completed_resources.iloc[0].to_dict() if not not_completed_resources.empty else None
    progress = (completed / total * 100) if total > 0 else 0
    return render_template('path_detail.html', resources=resources.to_dict('records'), progress=progress, next_resource=next_resource, path_id=path_id)

@app.route('/add_to_path/<int:path_id>')
@login_required
def add_to_path_page(path_id):
    user_id = int(current_user.id)
    bookmarks_df = pd.read_csv('bookmarks.csv')
    user_bookmarks = bookmarks_df[bookmarks_df['user_id'] == user_id]
    path_resources_df = pd.read_csv('path_resources.csv')
    path_resources = path_resources_df[path_resources_df['path_id'] == path_id]
    available_bookmarks = user_bookmarks[~user_bookmarks['resource_title'].isin(path_resources['resource_title'])]
    return render_template('add_to_path.html', bookmarks=available_bookmarks.to_dict('records'), path_id=path_id)
    
@app.route('/add_resource_to_path', methods=['POST'])
@login_required
def add_resource_to_path():
    path_id = int(request.form.get('path_id'))
    resource_title = request.form.get('resource_title')
    path_resources_df = pd.read_csv('path_resources.csv')
    current_path_resources = path_resources_df[path_resources_df['path_id'] == path_id]
    new_order = current_path_resources['order'].max() + 1 if not current_path_resources.empty else 1
    with open('path_resources.csv', 'a', newline='') as f:
        f.write(f"\n{path_id},\"{resource_title}\",not_started,{new_order}")
    flash(f"'{resource_title}' added to your path.", 'success')
    return redirect(url_for('path_detail', path_id=path_id))
    
@app.route('/update_status', methods=['POST'])
@login_required
def update_status():
    path_id = int(request.form.get('path_id'))
    resource_title = request.form.get('resource_title')
    new_status = request.form.get('status')
    path_resources_df = pd.read_csv('path_resources.csv')
    mask = (path_resources_df['path_id'] == path_id) & (path_resources_df['resource_title'] == resource_title)
    path_resources_df.loc[mask, 'status'] = new_status
    path_resources_df.to_csv('path_resources.csv', index=False)
    flash('Resource status updated!', 'info')
    return redirect(url_for('path_detail', path_id=path_id))

# --- NEW DELETE ROUTES ---
@app.route('/delete_path/<int:path_id>', methods=['POST'])
@login_required
def delete_path(path_id):
    paths_df = pd.read_csv('learning_paths.csv')
    paths_df = paths_df[paths_df['path_id'] != path_id]
    paths_df.to_csv('learning_paths.csv', index=False)

    resources_df = pd.read_csv('path_resources.csv')
    resources_df = resources_df[resources_df['path_id'] != path_id]
    resources_df.to_csv('path_resources.csv', index=False)
    
    flash('Learning path and all its resources have been deleted.', 'success')
    return redirect(url_for('my_paths'))

@app.route('/delete_resource_from_path', methods=['POST'])
@login_required
def delete_resource_from_path():
    path_id = int(request.form.get('path_id'))
    resource_title = request.form.get('resource_title')

    resources_df = pd.read_csv('path_resources.csv')
    index_to_delete = resources_df[
        (resources_df['path_id'] == path_id) & 
        (resources_df['resource_title'] == resource_title)
    ].index
    
    resources_df.drop(index_to_delete, inplace=True)
    resources_df.to_csv('path_resources.csv', index=False)
    
    flash(f"'{resource_title}' was removed from your path.", 'success')
    return redirect(url_for('path_detail', path_id=path_id))

if __name__ == '__main__':
    for f in ['users.csv', 'bookmarks.csv', 'learning_paths.csv', 'path_resources.csv']:
        if not os.path.exists(f):
            if f == 'users.csv':
                pd.DataFrame(columns=['id', 'username', 'password']).to_csv(f, index=False)
            elif f == 'bookmarks.csv':
                pd.DataFrame(columns=['user_id', 'resource_title']).to_csv(f, index=False)
            elif f == 'learning_paths.csv':
                pd.DataFrame(columns=['path_id', 'user_id', 'path_name']).to_csv(f, index=False)
            elif f == 'path_resources.csv':
                pd.DataFrame(columns=['path_id', 'resource_title', 'status', 'order']).to_csv(f, index=False)
    app.run(debug=True)
    