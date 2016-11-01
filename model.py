#!/usr/bin/env python3

import flask
import flask_login
import flask_socketio
import logging
import random

from fishing import socketio


users = {} # id -> User()
rooms = {} # id -> Room()
games = {} # id -> Game()
players = {} # id -> Player()


# unique room ID
def URID(o):
    return '%s:%s' % (o.__class__.__name__, o.id_)


class User(flask_login.UserMixin):
    def __init__(self, id_):
        super(User, self).__init__()
        self.id_ = id_
        self.connected = False
        self.room = Hall()

    def __str__(self):
        return '<User: %s@%s>' % (self.id_, self.room.id_)

    def get_id(self):
        return self.id_

    def uniq_room_id(self):
        return 'user:%s' % self.id_

    def in_room(self):
        return self.room is not Hall()

    def connect(self):
        self.connected = True
        flask_socketio.join_room(URID(self))
        self.room.join(self)

    def disconnect(self):
        self.connected = False
        flask_socketio.leave_room(URID(self))

    def login(self):
        logging.info('%s login', self)
        flask_login.login_user(self)
        users[self.id_] = self
        return True

    def logout(self):
        logging.info('%s logout', self)
        if self.in_room(): self.leave_room(self.room)
        Hall().leave(self)
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
        if not Hall().join(self): return False
        room.leave(self)
        self.room = Hall()
        flask_socketio.emit('leave room', {'id': room.id_})
        return True


class Room:
    def __init__(self, id_):
        self.id_ = id_
        self.users = {}
        self.game = None

    def __str__(self):
        return '<Room: %s, users: %s>' % (self.id_, ','.join(user.id_ for user in self.users.values()))

    def json(self):
        json = {}
        json['id'] = self.id_
        json['users'] = [user.id_ for user in self.users.values()]
        return json

    def join(self, user):
        logging.info('%s join room', user)
        if user.id_ in self.users:
            logging.warning('already in the room')
        if user.id_ not in self.users and len(self.users) >= 2:
            logging.warning('room occuppied')
            return False
        flask_socketio.join_room(URID(self))
        self.users[user.id_] = user
        self.broadcast()
        return True

    def leave(self, user):
        logging.info('%s leave room', user)
        if user.id_ not in self.users:
            logging.warning('not in room')
        else:
            del self.users[user.id_]
        flask_socketio.leave_room(URID(self))
        self.broadcast()
        if not self.users:
            logging.info('empty room %s, remove', self)
            del rooms[self.id_]
        return True

    def broadcast(self):
        flask_socketio.emit('room', self.json(), room=URID(self))
        if self.game:
            self.game.broadcast()

    def start_game(self):
        if self.game is not None:
            logging.warning('game already started')
            return False
        if len(self.users) != 2:
            logging.warning('players not ready')
            return False
        self.game = Game(self)
        self.game.start()


class Singleton:
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            orig = super(Singleton, cls)
            cls._instance = orig.__new__(cls, *args, **kwargs)
        return cls._instance


class Hall(Singleton):
    def __init__(self):
        self.id_ = '<hall>'
        self.users = {}

    def __str__(self):
        return '<Hall %s: users: %s>' % (self.id_, ','.join(user.id_ for user in self.users.values()))

    def join(self, user):
        logging.info('%s join hall', user)
        if user.id_ in self.users:
            logging.warning('%s already in hall', user)
        flask_socketio.join_room(URID(self))
        self.users[user.id_] = user
        self.broadcast()
        return True

    def leave(self, user):
        logging.info('%s leave hall', user)
        if user.id_ not in self.users:
            logging.warning('%s not in hall', user)
        else:
            del self.users[user.id_]
        flask_socketio.leave_room(URID(self))
        self.broadcast()
        return True

    def broadcast(self):
        flask_socketio.emit('hall', [r.json() for r in rooms.values()], room=URID(self))


class Card:
    symbols = ['♠', '♥', '♣', '♦']
    orders = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    total = 52
    J = 10

    @staticmethod
    def id2str(id_):
        assert 0 <= id_ < Card.total
        symbol, order = id_ // len(Card.orders), id_ % len(Card.orders)
        return Card.symbols[symbol] + Card.orders[order]

    @staticmethod
    def str2id(s):
        symbol, order = s[0], s[1:]
        assert symbol in Card.symbols and order in Card.orders
        return Card.symbols.index(symbol) * len(Card.orders) + Card.orders.index(order)

    @staticmethod
    def play(table, card):
        assert 0 <= card < Card.total
        if card % len(Card.orders) == Card.J:
            return [], table + [card]
        for i, c in enumerate(table):
            if c % len(Card.orders) == card % len(Card.orders):
                return table[:i], table[i:] + [card]
        return table + [card], []


class Player:
    def __init__(self, user, game):
        self.user = user
        self.game = game
        self.cards = []

    def __str__(self):
        return str(self.user)

    def gain_cards(self, cards):
        self.cards.extend(cards)


class Game:
    def __init__(self, room):
        self.room = room
        self.current_player = None
        self.waiting_player = None
        self.table = []
        games[self.room.id_] = self

    def __str__(self):
        return '<Game@%s, current=%s, waiting=%s, table=%s>' % (
            self.room,
            self.current_player,
            self.waiting_player,
            ','.join(Card.id2str(id_) for id_ in self.table))

    def start(self):
        logging.info('%s start', self)
        games[self.room.id_] = self
        self.table = []
        users = list(self.room.users.values())
        random.shuffle(users)
        current_user, waiting_user = users
        self.current_player = Player(current_user, self)
        self.waiting_player = Player(waiting_user, self)
        rand_cards = list(range(Card.total))
        random.shuffle(rand_cards)
        logging.info('rand cards: %s', rand_cards)
        # self.current_player.gain_cards(rand_cards[:Card.total // 2])
        self.table = rand_cards[:3]
        self.current_player.gain_cards(rand_cards[3:Card.total // 2])
        self.waiting_player.gain_cards(rand_cards[Card.total // 2:])
        players[self.current_player.user.id_] = self.current_player
        players[self.waiting_player.user.id_] = self.waiting_player
        self.broadcast()

    def play(self, player, card_str):
        logging.info('%s play %s', player, card_str)
        if player is not self.current_player:
            logging.warning('not my turn')
            return False
        card = Card.str2id(card_str)
        if card not in player.cards[:3]:
            logging.warning('can not play')
            return False
        player.cards.remove(card)
        table, gain = Card.play(self.table, card)
        self.table = table
        self.current_player.gain_cards(gain)
        self.current_player, self.waiting_player = self.waiting_player, self.current_player
        self.broadcast()

    def broadcast(self):
        message = {}
        message['id'] = self.room.id_
        message['table'] = list(map(Card.id2str, self.table))
        current = {
            'id': self.current_player.user.id_,
            'remains': len(self.current_player.cards),
            'front': list(map(Card.id2str, self.current_player.cards[:3])),
        }
        message['current'] = current
        waiting = {
            'id': self.waiting_player.user.id_,
            'remains': len(self.waiting_player.cards),
            'front': list(map(Card.id2str, self.waiting_player.cards[:3])),
        }
        message['waiting'] = waiting
        flask_socketio.emit('game', message, room=URID(self.room))
