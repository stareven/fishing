#!/usr/bin/env python3

import functools
import flask
import flask_login
import flask_socketio
import logging
import logging.config

logging.config.dictConfig({
    "version": 1,
    "formatters": {
        "default": {"format": "%(asctime)s %(levelname)s - %(message)s"},
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
users = {}
rooms = {}


class User(flask_login.UserMixin):
    def __init__(self, id_):
        super(User, self).__init__()
        self.id_ = id_
        self.room_id = None

    def get_id(self):
        return self.id_

    def in_room(self):
        return self.room_id is not None

    def enter_room(self, room_id):
        if self.id_ in rooms[room_id]:
            logging.warning('already in the room')
            return True
        if self.in_room():
            self.leave_room()
        logging.info('<%s> enter room #%s', self.id_, room_id)
        self.room_id = room_id
        rooms[room_id].append(self.id_)
        return True

    def leave_room(self):
        if not self.in_room():
            logging.warning('not in room')
            return True
        logging.info('<%s> leave room #%s', self.id_, self.room_id)
        rooms[self.room_id].remove(self.id_)
        if len(rooms[self.room_id]) == 0:
            logging.info('empty room #%s, remove', self.room_id)
            del rooms[self.room_id]
        self.room_id = None
        return True


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
    logging.info('<%s> login' % user.id_)
    users[id_] = user
    flask_login.login_user(user)
    return flask.redirect(flask.url_for('index'))


@app.route('/logout')
def logout():
    user = flask_login.current_user
    if user.is_anonymous:
        return flask.redirect(flask.url_for('login'))
    logging.info('<%s> logout' % user.id_)
    if user.in_room():
        user.leave_room()
    users.pop(user.id_, None)
    flask_login.logout_user()
    return flask.redirect(flask.url_for('login'))


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
    if not user.in_room():
        flask_socketio.emit('hall', rooms)


@socketio.on('disconnect')
@authenticated_only
def disconnect():
    user = flask_login.current_user
    logging.info('<%s> disconnect', user.id_)


@socketio.on('enter room')
@authenticated_only
def enter_room(message):
    user = flask_login.current_user
    logging.info('<%s> enter room: %s', user.id_, message)
    room_id = message['room']
    if not room_id or room_id not in rooms:
        logging.warning('invalid room id: %s', room_id)
        return
    user.enter_room(room_id)
    flask_socketio.emit('enter room', {'room': room_id})
    flask_socketio.emit('hall', rooms, broadcast=True)


@socketio.on('leave room')
@authenticated_only
def leave_room(message):
    user = flask_login.current_user
    logging.info('<%s> leave room: %s', user.id_, message)
    user.leave_room()
    flask_socketio.emit('hall', rooms, broadcast=True)


@socketio.on('create room')
@authenticated_only
def create_room(message):
    user = flask_login.current_user
    logging.info('<%s> create room: %s', user.id_, message)
    room_id = message['room']
    if not room_id:
        logging.warning('invalid room id: %s', room_id)
        return
    if room_id in rooms:
        logging.warning('already exist: %s', room_id)
        return
    rooms[room_id] = []
    user.enter_room(room_id)
    flask_socketio.emit('hall', rooms, broadcast=True)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', debug=True)
