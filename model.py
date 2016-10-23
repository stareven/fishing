#!/usr/bin/env python3

import flask
import flask_login
import flask_socketio
import logging

from fishing import socketio


users = {} # id -> User()
rooms = {} # id -> Room()


class User(flask_login.UserMixin):
    def __init__(self, id_):
        super(User, self).__init__()
        self.id_ = id_
        self.room = None

    def __str__(self):
        return '<User: %s@%s>' % (self.id_, self.room or '<hall>')

    def get_id(self):
        return self.id_

    def in_room(self):
        return self.room is not None

    def login(self):
        logging.info('%s login', self)
        users[self.id_] = self
        flask_login.login_user(self)
        return True

    def logout(self):
        logging.info('%s logout', self)
        if self.in_room(): self.leave_room(self.room)
        users.pop(self.id_, None)
        flask_login.logout_user()
        return True

    def join_room(self, room):
        logging.info('%s join %s', self, room)
        if self.in_room(): self.leave_room(self.room)
        if not room.join(self): return False
        self.room = room
        return True

    def leave_room(self, room):
        logging.info('%s leave %s', self, room)
        if not room.leave(self): return False
        self.room = None
        flask_socketio.emit('leave room', {'id': room.id_})
        if not room.users:
            logging.info('empty room %s, remove', room)
            del rooms[room.id_]
        return True


class Room:
    def __init__(self, id_):
        self.id_ = id_
        self.users = {}

    def __str__(self):
        return '<Room: %s, users: %s>' % (self.id_, ','.join(str(user) for user in self.users))

    def join(self, user):
        if user.id_ in self.users:
            logging.warning('already in the room')
            return False
        if len(self.users) >= 2:
            logging.warning('room occuppied')
            return False
        self.users[user.id_] = user
        flask_socketio.join_room(self.id_)
        self.broadcast()
        return True

    def leave(self, user):
        if user.id_ not in self.users:
            logging.warning('not in room')
            return False
        del self.users[user.id_]
        flask_socketio.leave_room(self.id_)
        self.broadcast()
        return True

    def json(self):
        json = {}
        json['id'] = self.id_
        json['users'] = [user.id_ for user in self.users.values()]
        return json

    def broadcast(self):
        flask_socketio.emit('room', self.json(), room=self.id_)