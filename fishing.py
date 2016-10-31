#!/usr/bin/env python3

import functools
import flask
import flask_login
import flask_socketio
import logging
import logging.config

from model import *

logging.config.dictConfig({
    "version": 1,
    "formatters": {
        "default": {"format": "[%(asctime)s] %(levelname)s [%(filename)s:%(lineno)d] - %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "DEBUG",
            "stream": "ext://sys.stdout"
        },
    },
    "root": {"level": "DEBUG", "handlers": ["console"]},
})


app = flask.Flask(__name__)
app.secret_key = 'secret'
login_manager = flask_login.LoginManager(app)
socketio = flask_socketio.SocketIO(app, logger=True)


@login_manager.user_loader
def user_loader(id_):
    if id_ not in users: return
    return users.get(id_)


@app.route('/')
@flask_login.login_required
def index():
    return flask.render_template('fishing.html', title='fishing')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if flask.request.method == 'GET':
        return flask.render_template('login.html', title='login')

    id_ = flask.request.form['id']
    if id_ in users:
        user = users[id_]
    else:
        user = User(id_)
    logging.info('%s login' % user)
    user.login()
    return flask.redirect(flask.url_for('index'))


@login_manager.unauthorized_handler
def unauthorized_handler():
    return flask.redirect(flask.url_for('login'))


def authenticated_only(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        user = flask_login.current_user
        if not user.is_authenticated:
            flask_socketio.disconnect()
        else:
            return f(*args, **kwargs)
    return wrapped


@socketio.on('connect')
@authenticated_only
def connect():
    user = flask_login.current_user
    logging.info('%s connect', user)
    flask_socketio.emit('hall', [room.json() for room in rooms.values()])
    user.connect()


@socketio.on('disconnect')
@authenticated_only
def disconnect():
    user = flask_login.current_user
    logging.info('%s disconnect', user)
    user.disconnect()


@socketio.on('logout')
@authenticated_only
def logout():
    user = flask_login.current_user
    logging.info('%s logout' % user)
    user.logout()


@socketio.on('join room')
@authenticated_only
def join_room(message):
    user = flask_login.current_user
    logging.info('%s join room: %s', user, message)
    room_id = message['id']
    if not room_id or room_id not in rooms:
        logging.warning('invalid room id: %s', room_id)
        return
    room = rooms[room_id]
    user.join_room(room)
    hall.broadcast()


@socketio.on('leave room')
@authenticated_only
def leave_room(message):
    user = flask_login.current_user
    logging.info('%s leave room: %s', user, message)
    room_id = message['id']
    if not room_id or room_id not in rooms:
        logging.warning('invalid room id: %s', room_id)
        return
    room = rooms[room_id]
    user.leave_room(room)
    hall.broadcast()


@socketio.on('create room')
@authenticated_only
def create_room(message):
    user = flask_login.current_user
    logging.info('%s create room: %s', user, message)
    room_id = message['id']
    if not room_id:
        logging.warning('invalid room id: %s', room_id)
        return
    if room_id in rooms:
        logging.warning('already exist: %s', room_id)
        return
    room = Room(room_id)
    rooms[room_id] = room
    user.join_room(room)
    hall.broadcast()


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', debug=True)
