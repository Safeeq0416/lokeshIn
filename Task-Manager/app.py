from flask import Flask, request, render_template, redirect, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ctm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.secret_key = '1234567'  # Change this to a secure random key
db = SQLAlchemy(app)


class Projects(db.Model):
    project_id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(20))
    active = db.Column(db.Boolean)
    tasks = db.relationship('Tasks', backref='project', lazy=True)

    def __init__(self, project, active):
        self.project_name = project
        self.active = active

    def __repr__(self):
        return '<Project {}>'.format(self.project_name)


class Tasks(db.Model):
    task_id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.project_id'))
    task = db.Column(db.Text)
    status = db.Column(db.Boolean, default=False)

    def __init__(self, project_id, task, status=True):
        self.project_id = project_id
        self.task = task
        self.status = status

    def __repr__(self):
        return '<Task {}>'.format(self.task)

class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

    def __init__(self, username, password):
        self.username = username
        self.password = password


if __name__ == '__main__':
    with app.app_context():
        db.create_all()


    @app.route('/')
    def index():
        if 'user_id' not in session:
            return redirect('/login')

        active = None
        projects = Projects.query.all()
        tasks = Tasks.query.all()

        if len(projects) == 1:
            projects[0].active = True
            active = projects[0].project_id
            db.session.commit()

        if projects:
            for project in projects:
                if project.active:
                    active = project.project_id
            if not active:
                projects[0].active = True
                active = projects[0].project_id
        else:
            projects = None

        # Pass task as None to the template
        return render_template('index.html', tasks=tasks, projects=projects, active=active, task=None)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')

            # Check if the username is already taken
            existing_user = Users.query.filter_by(username=username).first()
            if existing_user:
                return render_template('register.html', error='Username already taken')

            # Create a new user
            new_user = Users(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()

            return redirect('/login')

        return render_template('register.html', error=None)

    @app.route('/add', methods=['POST'])
    def add_task():
        found = False
        project_id = None
        task = request.form.get('task', '')
        project = request.form.get('project', '')

        if not task:
            return redirect('/')

        if not project:
            project = 'Tasks'

        projects = Projects.query.all()

        for proj in projects:
            if proj.project_name == project:
                found = True

        if not found:
            add_project = Projects(project, True)
            db.session.add(add_project)
            db.session.commit()
            projects = Projects.query.all()

        for proj in projects:
            if proj.project_name == project:
                project_id = proj.project_id
                proj.active = True
            else:
                proj.active = False

        status = bool(int(request.form.get('status', 0)))

        new_task = Tasks(project_id, task, status)
        db.session.add(new_task)
        db.session.commit()
        return redirect('/')

    @app.route('/close/<int:task_id>')
    def close_task(task_id):
        """Changes the state of a task

        If the task is open, it closes it. If it's close, it opens it.
        Redirects to home page if the task does not exist.
        """
        task = Tasks.query.get(task_id)

        if not task:
            return redirect('/')

        if task.status:
            task.status = False
        else:
            task.status = True

        db.session.commit()
        return redirect('/')

    @app.route('/delete/<int:task_id>')
    def delete_task(task_id):
        """Deletes task by its ID

        If the task does not exist, redirects to home page.
        """
        task = Tasks.query.get(task_id)

        if not task:
            return redirect('/')

        db.session.delete(task)
        db.session.commit()
        return redirect('/')


    @app.route('/edit/', methods=['POST'])
    def edit_task():
        if 'user_id' not in session:
            return redirect('/login')

        if request.method == 'POST':
            task_id = request.form.get('editTaskId')  # Use 'editTaskId' instead of 'task_id'
            task = Tasks.query.get(task_id)

            if not task:
                return redirect('/')

            # Update task details with form data
            task.task = request.form.get('task', task.task)
            task.status = bool(int(request.form.get('status', 0)))

            # Commit changes to the database
            db.session.commit()

        return redirect('/')


    @app.route('/clear/<delete_id>')
    def clear_all(delete_id):
        """Dumps all tasks from the active tab and removes the project tab"""
        Tasks.query.filter(Tasks.project_id == delete_id).delete()
        Projects.query.filter(Projects.project_id == delete_id).delete()
        db.session.commit()

        return redirect('/')

    @app.route('/remove/<lists_id>')
    def remove_all(lists_id):
        """Dumps all tasks from the active tab"""
        Tasks.query.filter(Tasks.project_id == lists_id).delete()
        db.session.commit()

        return redirect('/')

    @app.route('/project/<tab>')
    def tab_nav(tab):
        """Switches between active tabs"""
        projects = Projects.query.all()

        for project in projects:
            if project.project_name == tab:
                project.active = True
            else:
                project.active = False

        db.session.commit()
        return redirect('/')


    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')

            # Check if the user exists in the database
            user = Users.query.filter_by(username=username, password=password).first()

            if user:
                session['user_id'] = user.id  # Set a user identifier
                return redirect('/')
            else:
                return render_template('login.html', error='Invalid credentials')

        return render_template('login.html', error=None)






    # Add a logout route
    @app.route('/logout')
    def logout():
        session.pop('user_id', None)
        return redirect('/login')

    if __name__ == '__main__':
        app.run(debug=True)
