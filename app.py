from enum import unique
import re
import json
import requests
import string
import uuid
import os
import jwt

from flask import render_template, url_for, request, redirect, session
from flask_login import login_user, logout_user, login_required
from datetime import datetime
from wtforms import ValidationError

from captions import get_vtt_file
from oauth import google
from to_text import convert_to_text
from summary import get_summary
from question_generator import generate_trivia
from cli import create_db
from config import Config
from models import app, db, Subtitles, Questions, Users, Answers, login_manager
from send_mail import send_mail


app.config.from_object(Config)
app.cli.add_command(create_db)
app.register_blueprint(google.blueprint, url_prefix="/login")
db.init_app(app)
login_manager.init_app(app)

# enabling insecure login for OAuth login
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

API_KEY = app.config['API_KEY']
WEAVY_ID = app.config['WEAVY_ID']
WEAVY_SECRET = app.config['WEAVY_SECRET']


@app.route('/', methods=["GET", "POST"])
def home():
    token = None
    space_name = None
    unique_id = None
    if session.get("user_id"):
        user = Users.query.filter_by(id=session['user_id']).first()
        if user.email is not None:
            email = user.email
        else:
            email = user.google_email
        payload = {
            "sub": "123",
            "name": user.user_name,
            "ext": 1629896376,
            "iss": WEAVY_ID,
            "email": email
        }
        secret = WEAVY_SECRET
        token = jwt.encode(payload=payload, key=secret)
        space_name = user.user_name
        unique_id = user.unique_id
    if request.method == "POST":
        query = request.form["query"]
        return redirect(url_for('search', q=query))
    return render_template('home.html',
                           token=token,
                           space_name=space_name,
                           unique_id=unique_id)


@app.route('/<unique_id>/profile')
@login_required
def profile(unique_id):
    user = Users.query.filter_by(unique_id=unique_id).first()
    if user.email is not None:
        email = user.email
    else:
        email = user.google_email
    payload = {
        "sub": "123",
        "name": user.user_name,
        "ext": 1629896376,
        "iss": WEAVY_ID,
        "email": email
    }
    secret = WEAVY_SECRET
    token = jwt.encode(payload=payload, key=secret)
    space_name = user.user_name

    answers = Answers.query.filter_by(unique_id=unique_id).all()
    total = 0
    correct = 0
    videos_count = 0
    for answer in answers:
        questions = json.loads(answer.answers)
        total += len(questions)
        correct += int(answer.correct)
        videos_count += 1
    return render_template('profile.html',
                           token=token,
                           space_name=space_name,
                           unique_id=unique_id,
                           user=user,
                           total=total,
                           correct=correct,
                           videos_count=videos_count)


@app.route('/search', methods=["GET", "POST"])
def search():
    q = request.args.get('q')
    token = None
    space_name = None
    unique_id = None
    if session.get("user_id"):
        user = Users.query.filter_by(id=session['user_id']).first()
        if user.email is not None:
            email = user.email
        else:
            email = user.google_email
        payload = {
            "sub": "123",
            "name": user.user_name,
            "ext": 1661086214,
            "iss": WEAVY_ID,
            "email": email
        }
        secret = WEAVY_SECRET
        token = jwt.encode(payload=payload, key=secret)
        space_name = user.user_name
        unique_id = user.unique_id
    videos = []
    base_url = "https://youtube.googleapis.com/youtube/v3/search?"
    if request.method == "POST":
        try:
            query = request.form['query']
        except:
            query = None
        try:
            next_page = request.form["next_page"]
        except:
            next_page = "None"
        try:
            prev_page = request.form["prev_page"]
        except:
            prev_page = "None"
        if query is not None:
            return redirect(url_for('search', q=query))
        if next_page == "None":
            page = prev_page
        else:
            page = next_page
        base_url = f"https://youtube.googleapis.com/youtube/v3/search?pageToken={page}&"
    if q is not None:
        response = requests.get(
            f"{base_url}part=snippet&q={q}&key={API_KEY}&maxResults=9&type=video&videoCaption=closedCaption&videoEmbeddable=true&regionCode=US"
        ).json()
        next_page = response['nextPageToken']
        try:
            prev_page = response['prevPageToken']
        except:
            prev_page = "None"

        for item in response["items"]:
            channel_id = item['snippet']['channelId']
            channel_response = requests.get(
                f'https://youtube.googleapis.com/youtube/v3/channels?part=snippet&id={channel_id}&key={API_KEY}'
            ).json()
            date_time = item['snippet']['publishedAt'].split("T")
            date_obj = datetime.strptime(date_time[0], '%Y-%M-%d')
            date = date_obj.strftime('%d %b %Y')
            videos.append({
                'videoId': item['id']['videoId'],
                'channelName': item['snippet']['channelTitle'],
                'description': item['snippet']['description'],
                'title': item['snippet']['title'],
                'publishedAt': date,
                'thumbNail': item['snippet']['thumbnails']['high']['url'],
                'channelLogo': channel_response['items'][0]['snippet']['thumbnails']['default']['url']
            })
    else:
        next_page = "None"
        prev_page = "None"
    return render_template('videos.html',
                           videos=videos,
                           token=token,
                           space_name=space_name,
                           unique_id=unique_id,
                           next_page=next_page,
                           prev_page=prev_page)


@app.route('/<unique_id>/result/<video_id>')
@login_required
def results(unique_id, video_id):
    user = Users.query.filter_by(unique_id=unique_id).first()
    if user.email is not None:
        email = user.email
    else:
        email = user.google_email
    payload = {
        "sub": "123",
        "name": user.user_name,
        "ext": 1629896376,
        "iss": WEAVY_ID,
        "email": email
    }
    secret = WEAVY_SECRET
    token = jwt.encode(payload=payload, key=secret)
    space_name = user.user_name
    answers = Answers.query.filter_by(unique_id=unique_id,
                                      video_id=video_id).first()
    all_answers = json.loads(answers.answers)
    total = len(all_answers)
    return render_template('result.html',
                           answers=answers,
                           total=total,
                           all_answers=all_answers,
                           token=token,
                           space_name=space_name,
                           unique_id=unique_id)


@app.route('/questions/<video_id>', methods=["GET", "POST"])
@login_required
def show_questions(video_id):
    user = Users.query.filter_by(id=session['user_id']).first()
    if user.email is not None:
        email = user.email
    else:
        email = user.google_email
    payload = {
        "sub": "123",
        "name": user.user_name,
        "ext": 1629896376,
        "iss": WEAVY_ID,
        "email": email
    }
    secret = WEAVY_SECRET
    token = jwt.encode(payload=payload, key=secret)
    space_name = user.user_name
    unique_id = user.unique_id
    all_questions = Questions.query.filter_by(
        video_id=video_id).first().questions
    questions = json.loads(all_questions)
    if request.method == "POST":
        user = Users.query.filter_by(id=session['user_id']).first()
        # answers_ = [{'question': ['correct', 'answer']}]
        answers_ = []
        correct = 0
        for i in range(len(questions)):
            name = 'question' + str(i + 1)
            index = questions[i]['correctIndex']
            answers_.append({
                questions[i]['question']:
                [questions[i]['answers'][index], request.form[name]]
            })
            if questions[i]['answers'][index].lower() == request.form[name]:
                correct += 1
        already_present = Answers.query.filter_by(video_id=video_id, unique_id=unique_id).first()
        if already_present is None:
            answers = Answers(unique_id=user.unique_id,
                            video_id=video_id,
                            answers=json.dumps(answers_),
                            correct=correct)
            db.session.add(answers)
        else:
            already_present.answers = json.dumps(answers_)
            already_present.correct = correct
            db.session.add(already_present)
        db.session.commit()
        return redirect(
            url_for('results', video_id=video_id, unique_id=user.unique_id))

    return render_template('show_questions.html',
                           questions=questions,
                           token=token,
                           space_name=space_name,
                           unique_id=unique_id)


@app.route('/generate_questions/<video_id>')
@login_required
def generate_questions(video_id):
    check_question = Questions.query.filter_by(video_id=video_id).first()
    if check_question is None:
        get_vtt_file(video_id)
        convert_to_text(video_id)
        subtitles = Subtitles.query.filter_by(video_id=video_id).first()
        text = subtitles.data_text
        summary = get_summary(text)

        rx = r"\.(?=\S)"
        summary = re.sub(rx, ". ", summary)
        re.sub(".", ". ", summary)

        json_data = json.loads(subtitles.data_json)
        questions = generate_trivia(summary)
        prevJumpToTime = 0
        for question in questions:
            correct_index = question['correctIndex']
            correct_answer = question['answers'][correct_index]
            for json_sentence in json_data:
                json_sentence_time = get_sec(json_sentence['time'])
                if json_sentence_time >= prevJumpToTime and json_sentence[
                        'line'].find(correct_answer) >= 0:
                    question['jumpToTime'] = json_sentence_time
                    prevJumpToTime = json_sentence_time
                    break
        json_questions = json.dumps(questions)
        question_obj = Questions(video_id=video_id, questions=json_questions)
        db.session.add(question_obj)
        db.session.commit()
    else:
        json_questions = check_question.questions
    return {"success": True}


@app.route('/video/<video_id>', methods=["GET", "POST"])
def show_video(video_id):
    token = None
    space_name = None
    unique_id = None
    if session.get("user_id"):
        user = Users.query.filter_by(id=session['user_id']).first()
        if user.email is not None:
            email = user.email
        else:
            email = user.google_email
        payload = {
            "sub": "123",
            "name": user.user_name,
            "ext": 1629896376,
            "iss": WEAVY_ID,
            "email": email
        }
        secret = WEAVY_SECRET
        token = jwt.encode(payload=payload, key=secret)
        space_name = user.user_name
        unique_id = user.unique_id
    video_response = requests.get(
        f'https://youtube.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={API_KEY}'
    ).json()
    title = video_response['items'][0]['snippet']['title']
    channel_name = video_response['items'][0]['snippet']['channelTitle']
    return render_template('show_video.html',
                           video_id=video_id,
                           title=title,
                           channel_name=channel_name,
                           token=token,
                           space_name=space_name,
                           unique_id=unique_id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    token = None
    space_name = None
    if session.get("user_id"):
        return redirect(url_for('home'))
    flag = False
    if request.method == "POST":
        user = Users.query.filter_by(email=request.form['username']).first()
        if user is None:
            user = Users.query.filter_by(
                user_name=request.form['username']).first()
        if user is not None:
            if user.check_password(request.form['password']):
                user = Users.query.filter_by(email=user.email).first()
                session['user_id'] = user.id
                login_user(user)
                return redirect(url_for("home"))
            else:
                flag = True
        else:
            flag = True
    return render_template('login.html',
                           flag=flag,
                           token=token,
                           space_name=space_name)


@app.route('/signup', methods=["GET", "POST"])
def signup():
    token = None
    space_name = None
    if session.get("user_id"):
        return redirect(url_for('home'))
    email_flag = False
    username_flag = False
    password_flag = False

    if request.method == "POST":
        user_name = request.form['username']
        email = request.form['email']
        password = request.form['password']

        password_flag = check_password(password)
        try:
            email_flag = check_mail(email)
        except ValidationError:
            email_flag = True

        try:
            username_flag = check_username(user_name)
        except ValidationError:
            username_flag = True

        if not username_flag and not email_flag and not password_flag and password_flag != "short":
            unique_id = uuid.uuid4().hex[:8]
            user = Users(unique_id, None, None, user_name, email, password)
            db.session.add(user)
            db.session.commit()
            session['user_id'] = user.id
            login_user(user)

            return redirect(url_for('home'))

    return render_template('signup.html',
                           email_flag=email_flag,
                           username_flag=username_flag,
                           password_flag=password_flag,
                           token=token,
                           space_name=space_name)


@app.route("/logout")
@login_required
def logout():
    session.pop('user_id', None)
    logout_user()
    return redirect(url_for("home"))


@app.route('/contact', methods=["GET", "POST"])
def contact_us():
    token = None
    space_name = None
    unique_id=None
    if session.get("user_id"):
        user = Users.query.filter_by(id=session['user_id']).first()
        if user.email is not None:
            email = user.email
        else:
            email = user.google_email
        payload = {
            "sub": "123",
            "name": user.user_name,
            "ext": 1629896376,
            "iss": WEAVY_ID,
            "email": email
        }
        secret = WEAVY_SECRET
        token = jwt.encode(payload=payload, key=secret)
        space_name = user.user_name
        unique_id = user.unique_id
    if request.method == "POST":
        name = request.form['txtName']
        email = request.form['txtEmail']
        phone = request.form['txtPhone']
        msg = request.form['txtMsg']
        send_mail(name, email, phone, msg)
    return render_template('contact_us.html',
                           token=token,
                           space_name=space_name,
                           unique_id=unique_id)


@app.route('/about')
def about_us():
    token = None
    space_name = None
    unique_id = None
    if session.get("user_id"):
        user = Users.query.filter_by(id=session['user_id']).first()
        if user.email is not None:
            email = user.email
        else:
            email = user.google_email
        payload = {
            "sub": "123",
            "name": user.user_name,
            "ext": 1629896376,
            "iss": WEAVY_ID,
            "email": email
        }
        secret = WEAVY_SECRET
        token = jwt.encode(payload=payload, key=secret)
        space_name = user.user_name
        unique_id = user.unique_id
    return render_template('about_us.html',
                           token=token,
                           space_name=space_name,
                           unique_id=unique_id)


# FUNCTIONS
def get_sec(time_str):
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)


def check_mail(data):
    if Users.query.filter_by(email=data).first():
        raise ValidationError('Your email is already registered.')
    else:
        return False


def check_username(data):
    if Users.query.filter_by(user_name=data).first():
        raise ValidationError('This username is already registered.')
    else:
        return False


def check_password(data):
    special_char = string.punctuation
    if len(data) < 6:
        return "short"
    elif not re.search("[a-zA-Z]", data):
        return True
    elif not re.search("[0-9]", data):
        return True
    for char in data:
        if char in special_char:
            break
    else:
        return True
    return False


if __name__ == '__main__':
    app.run(debug=True)
