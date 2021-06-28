from flask import redirect, render_template, request
from flask_socketio import emit, close_room, join_room, leave_room, rooms

import uuid
import time

from app import app, db, socketio
from app.models import Room

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
