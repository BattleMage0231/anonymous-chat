from flask import *
from flask_socketio import *
from flask_sqlalchemy import *

import time
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(120), unique=True, nullable=False)
    size = db.Column(db.Integer, nullable=False)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/create/')
def create():
    key = str(uuid.uuid4())
    while Room.query.filter_by(key=key).all():
        key = str(uuid.uuid4())
    room = Room(key=key, size=0)
    db.session.add(room)
    db.session.commit()
    return redirect(f'/room/{key}')

@app.route('/join/', methods=['GET', 'POST'])
def join():
    if request.method == 'POST':
        code = request.form['code'].strip()
        if Room.query.filter_by(key=code).all():
            return redirect(f'/room/{code}/')
        else:
            return redirect('/')
    else:
        return render_template('join.html')

@app.route('/room/<key>/')
def room(key):
    if Room.query.filter_by(key=key):
        return render_template('room.html', room=key)
    else:
        return 'Room not found'

@socketio.on('joined')
def joined(data):
    key = data['room']
    res = Room.query.filter_by(key=key).all()
    if len(res) == 0:
        emit('purge', {'room': key})
        return
    room = res[0]
    room.size += 1
    db.session.commit()
    join_room(key)
    emit('welcome', {'timestamp': int(time.time() * 1000)}, to=key)

@socketio.on('disconnect')
def left():
    for key in rooms():
        res = Room.query.filter_by(key=key).all()
        if res:
            room = res[0]
            print(room)
            room.size -= 1
            if room.size == 0:
                db.session.delete(room)
                close_room(key)
            else:
                leave_room(key)
                emit('goodbye', {'timestamp': int(time.time() * 1000)}, to=key)
            db.session.commit()
    print(Room.query.all())

@socketio.on('send')
def send(data):
    room = data['room']
    msg = data['msg']
    timestamp = data['timestamp']
    emit('message', {'content': msg, 'timestamp': timestamp}, room=room)

db.create_all()
socketio.run(app, debug=True)
