#!/usr/bin/env python3

import flask
import flask_login
import flask_socketio
import logging

from fishing import socketio


users = {} # id -> User()
rooms = {} # id -> Room()


class Hall:
    def __init__(self, id_):
        self.id_ = id_
        self.users = {}

    def __str__(self):
        return '<Hall %s: users: %s>' % (self.id_, ','.join(user.id_ for user in self.users.values()))

    def join(self, user):
        logging.info('%s join hall', user)
        if user.id_ in self.users:
            logging.warning('%s already in hall', user)
        flask_socketio.join_room(self.id_)
        self.users[user.id_] = user
        self.broadcast()
        return True

    def leave(self, user):
        logging.info('%s leave hall', user)
        if user.id_ not in self.users:
            logging.warning('%s not in hall', user)
        else:
            del self.users[user.id_]
        flask_socketio.leave_room(self.id_)
        self.broadcast()
        return True

    def broadcast(self):
        flask_socketio.emit('hall', [r.json() for r in rooms.values()], room=self.id_)


hall = Hall('<hall>')


class User(flask_login.UserMixin):
    def __init__(self, id_):
        super(User, self).__init__()
        self.id_ = id_
        self.connected = False
        self.room = hall

    def __str__(self):
        return '<User: %s@%s>' % (self.id_, self.room.id_)

    def get_id(self):
        return self.id_

    def connect(self):
        self.connected = True
        self.room.join(self)

    def disconnect(self):
        self.connected = False

    def in_room(self):
        return self.room is not hall

    def login(self):
        logging.info('%s login', self)
        flask_login.login_user(self)
        users[self.id_] = self
        return True

    def logout(self):
        logging.info('%s logout', self)
        if self.in_room(): self.leave_room(self.room)
        hall.leave(self)
        flask_login.logout_user()
        del users[self.id_]
        flask_socketio.emit('logout')
        return True

    def join_room(self, room):
        logging.info('%s join %s', self, room)
        if self.in_room() and self.room is room:
            logging.warning('already in room')
            return True
        if not room.join(self): return False
        self.room.leave(self)
        self.room = room
        return True

    def leave_room(self, room):
        logging.info('%s leave %s', self, room)
        if not hall.join(self): return False
        room.leave(self)
        self.room = hall
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
        return '<Room: %s, users: %s>' % (self.id_, ','.join(user.id_ for user in self.users.values()))

    def join(self, user):
        logging.info('%s join room', user)
        if user.id_ in self.users:
            logging.warning('already in the room')
        if user.id_ not in self.users and len(self.users) >= 2:
            logging.warning('room occuppied')
            return False
        flask_socketio.join_room(self.id_)
        self.users[user.id_] = user
        self.broadcast()
        return True

    def leave(self, user):
        logging.info('%s leave room', user)
        if user.id_ not in self.users:
            logging.warning('not in room')
        else:
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