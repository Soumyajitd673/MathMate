from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy import JSON
import time

app = Flask(__name__)
app.secret_key = '01010011'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///MathMateDatabase.db'
db = SQLAlchemy(app)


@app.route('/')
@app.route('/signup', methods=["POST", "GET"])
def signup_page():
    if request.method == "POST":
        name = request.form.get('name')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        if (not name) or (not password1) or (not password2): 
            flash("Invalid input")
            return redirect(url_for('signup_page'))
        existing_user = User.query.filter_by(Name=name).first()
        if existing_user:
            flash("This user name already exists.")
            return redirect(url_for('signup_page'))
        if password1 != password2 : 
            flash("Invalid password input.")
            return redirect(url_for('signup_page'))
        else: 
            user = User(Name=name, Password=password1)
            db.session.add(user)
            db.session.commit()
            session['user_name'] = user.Name
            return redirect(url_for('home_page'))
    else:
        return render_template('signup.html')


@app.route('/login', methods=["POST", "GET"])
def login_page():
    if request.method == "POST":
        name = request.form.get('name')
        entered_password = request.form.get('password')
        if (not name) or (not entered_password):
            flash("Invalid input")
            return redirect(url_for('login_page')) 
        user = User.query.filter_by(Name=name).first()
        if not user:
            flash("This account does not exist.")
            return redirect(url_for('login_page'))
        password = user.Password
        if entered_password != password :
            flash("Wrong password.")
            return redirect(url_for('login_page'))
        else:
            session['user_name'] = user.Name
            return redirect(url_for('home_page'))
    else:    
        return render_template('login.html')


@app.route('/home')
def home_page():
    if 'user_name' in session:
        return render_template('home.html')

@app.route('/quizzes')
def Quiz_page():
    topics = Topic.query.all()
    user_name = session['user_name']
    user = User.query.filter_by(Name=user_name).first()
    for t in topics:
        column_name = "_".join(t.topic.split())
        session[t.topic] = getattr(user, column_name)

    return render_template('Quizzes.html', topics=topics, user=user)

@app.route('/<topic>/<int:idx>', methods=["POST", "GET"])
def show_question(topic, idx):
    questions = Question.query.filter_by(topic=topic).order_by(Question.id).all()
    if idx>len(questions) :
        end_time = time.time()
        time_taken = round(end_time - session["start_time"])
        selected_option = request.form.get("option")
        answer_list = session.get("user_answers")
        answer_list.append(selected_option)
        session["user_answers"] = answer_list
        result_list = process_user_answers(topic, time_taken)
        if len(result_list[1])!=0:
            return render_template ('result.html', topic=topic, result=result_list, first_attempt=False)
        else:
            return render_template ('result.html', topic=topic, result=result_list, first_attempt=True)
    
    q = questions[idx-1]

    if request.method == "POST":
        selected_option = request.form.get("option")
        answer_list = session.get("user_answers")
        answer_list.append(selected_option)
        session["user_answers"] = answer_list
    else:
        session["user_answers"] = []
        session["start_time"] = time.time()

    return render_template('questions.html', q=q, topic=topic, index=idx)


def process_user_answers(topic, time_taken):
    questions = Question.query.filter_by(topic=topic).order_by(Question.id).all()
    attempted = 0
    right = 0
    wrong = 0
    answer_list = session["user_answers"]
    for i in range (len(questions)):
        if answer_list[i]==None: continue
        else:
            attempted += 1
            q = questions[i]
            if answer_list[i]==q.answer: right += 1
            else: wrong += 1
            
    user_name = session["user_name"]
    user = User.query.filter_by(Name=user_name).first()
    column_name = "_".join(topic.split())
    new_list = [attempted, right, wrong, time_taken]
    old_list = getattr(user, column_name)
    setattr(user, column_name, new_list)
    db.session.commit()
    return (new_list, old_list)

@app.route('/logout')
def logout_page():
    session.clear()
    flash("Logout Sucessful")
    return redirect(url_for('signup_page'))

@app.route('/delete_account', methods=["POST", "GET"])
def delete_account_conformation_page():
    if request.method == "GET":
        return render_template('delete_account.html')
    if request.method == "POST":
        user_name = session["user_name"]
        user = User.query.filter_by(Name=user_name).first()
        password = request.form.get("password")
        correct_password = user.Password
        if password == correct_password:
            db.session.delete(user)
            db.session.commit()
            flash("Account deleted")
            return redirect(url_for('signup_page'))
        else:
            flash("Wrong Password")
            return redirect(url_for('delete_account_conformation_page'))



@app.route('/<topic>/analysis', methods=["GET"])
def analysis_page(topic):
    questions = Question.query.filter_by(topic=topic).order_by(Question.id).all()
    answer_list = session.get("user_answers")
    user_ans = []
    correct_ans = []
    assesment = []
    for i in range (len(answer_list)):
        q = questions[i]
        if answer_list[i] != None:
            if (answer_list[i]==q.answer):
                assesment.append("Correct Answer")
            else:
                assesment.append("Wrong Answer")
            col_name = "option_"+answer_list[i]
            ans = getattr(q, col_name)
            user_ans.append(ans)
        else: 
            user_ans.append(None)
            assesment.append("Unattempted")
        col_name = "option_" + q.answer
        ans = getattr(q, col_name)
        correct_ans.append(ans)

    return render_template('analysis.html', questions=questions, user_ans=user_ans, correct_ans=correct_ans, assesment=assesment, topic=topic)

class Question(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    topic = db.Column(db.String(50), nullable=False)
    question = db.Column(db.String(1000), nullable=False)
    option_A = db.Column(db.Text, nullable=False)
    option_B = db.Column(db.Text, nullable=False)
    option_C = db.Column(db.Text, nullable=False)
    option_D = db.Column(db.Text, nullable=False)
    answer = db.Column(db.String(), nullable=False)

class Topic (db.Model):
    topic = db.Column(db.String(50), nullable=False, primary_key=True)
    no_of_ques = db.Column(db.Integer(), nullable=False)

    def __repr__(self):
        return f'Topic: {self.topic}'
    
class User(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    Name = db.Column(db.String(50), nullable=False, unique=True)
    Password = db.Column(db.String(20), nullable=False)
    Fraction = db.Column(MutableList.as_mutable(JSON), default=[])
    Geometry = db.Column(MutableList.as_mutable(JSON), default=[])
    Trigonometry = db.Column(MutableList.as_mutable(JSON), default=[])
    Quadratic_Equations = db.Column(MutableList.as_mutable(JSON), default=[])
    Probability = db.Column(MutableList.as_mutable(JSON), default=[])
    Straight_Line = db.Column(MutableList.as_mutable(JSON), default=[])
    Circle = db.Column(MutableList.as_mutable(JSON), default=[])
    Vectors = db.Column(MutableList.as_mutable(JSON), default=[])

    def __repr__(self):
        return f"User: {self.Name}"

with app.app_context():
    db.create_all()
    
if __name__ == "__main__":
    app.run()
