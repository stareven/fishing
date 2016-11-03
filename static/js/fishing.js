function fishing(me, socket)
{
  console.info('fishing');

  var hall = null;
  var room = null;
  var game = null;

  function setup_hall()
  {
    console.info('setup hall: %o', hall);
    $content = $('#content');
    $content.empty();
    var header = '<div class="page-header"><h1>Hall</h1></div>';
    var rooms = '';
    if (!hall || hall.length == 0) {
      rooms += '<p>no rooms</p>';
    }
    rooms += '<div class="list-group">';
    for (var room in hall) {
      rooms += '<a class="list-group-item room" room-id="' + hall[room]['id'] + '">';
      rooms += '<h4 class="list-group-item-heading">Room #' + hall[room]['id'] + '</h4>';
      for (var i = 0; i < hall[room]['users'].length; i++) {
        rooms += '<p class="list-group-item-text">' + hall[room]['users'][i] + '</p>';
      }
      rooms += '</a>';
    }
    var create = '<div class="input-group">';
    create += '<input type="text" class="form-control" id="create-room-input" placeholder="Create New Room">';
    create += '<span class="input-group-btn"><button class="btn btn-primary" id="create-room-btn"><span class="glyphicon glyphicon-plus"></span></button>';
    create += '</div>';
    $content.append(header);
    $content.append(rooms);
    $content.append(create);

    $('.room').click(function() {
      socket.emit('join room', {'id': $(this).attr('room-id')});
    });
    $('#create-room-btn').click(function() {
      socket.emit('create room', {'id': $('#create-room-input').val()});
    });
  };

  function setup_room()
  {
    console.info('setup room: %o', room);
    $content = $('#content');
    $content.empty();
    var header = '<div class="page-header"><h1>';
    header += 'Room #' + room['id'];
    header += '<button class="btn btn-lg btn-danger pull-right" id="leave-room-btn"><span class="glyphicon glyphicon-off"></span></button>';
    header += '</h1></div>';
    var users = '<ul class="list-group">';
    for (var i = 0; i < room['users'].length; i++) {
      users += '<li class="list-group-item">' + room['users'][i] + '</li>';
    }
    users += '</ul>';
    var start = '<button class="btn btn-primary" id="start-btn">start</button>';
    $content.append(header);
    $content.append(users);
    $content.append(start);

    if (room && room['users'] && room['users'].length < 2) {
      $('#start-btn').attr('disabled', 'disabled');
    }
    $('#leave-room-btn').click(function() {
      socket.emit('leave room', room);
    });
    $('#start-btn').click(function() {
      socket.emit('start game', room)
    });
  };

  function setup_game()
  {
    console.info('setup game: %o', game);
    $content = $('#content');
    $content.empty();
    var header = '<div class="page-header"><h1>';
    header += 'Game #' + game['id'];
    header += '<button class="btn btn-lg btn-danger pull-right" id="leave-room-btn"><span class="glyphicon glyphicon-off"></span></button>';
    header += '</h1></div>';
    $content.append(header);

    if (game['current']['front'].length == 0 || game['waiting']['front'].length == 0) {
      var result = '';
      if (game['current']['id'] == me && game['current']['front'].length == 0 ||
          game['waiting']['id'] == me && game['waiting']['front'].length == 0)
        result = '<div class="alert alert-danger" role="alert">You Lose...</div>'
      else
        result = '<div class="alert alert-success" role="alert">You Win!!!</div>'
      var start = '<button class="btn btn-primary" id="start-btn">start</button>';
      $content.append(result);
      $content.append(start);
      $('#start-btn').click(function() {
        socket.emit('start game', room)
      });
    } else {
      var table = '<div class="well">';
      table += '<h4>table> ';
      if (!game['table'] || game['table'].length == 0) {
        table += 'empty...';
      } else {
        for (var i = 0; i < game['table'].length; i++) {
          table += game['table'][i] + ' => ';
        }
      }
      table += '</h4>';
      table += '<p>[' + game['current']['id'] + '] remains ' + game['current']['remains'] + ' card(s)';
      table += '<p>[' + game['waiting']['id'] + '] remains ' + game['waiting']['remains'] + ' card(s)';
      table += '</div>';
      var myturn = game['current']['id'] == me;
      var cards = [];
      if (myturn)
        cards = game['current']['front'];
      else
        cards = game['waiting']['front'];
      var hands = '<div class="btn-group btn-group-lg pull-right">';
      for (var i = 0; i < cards.length; i++) {
        hands += '<button type="button" class="btn btn-primary play-btn">' + cards[i] + '</button>';
      }
      hands += '</div>'
      $content.append(table);
      $content.append(hands);
      if (!myturn) {
        $('.play-btn').attr('disabled', 'disabled');
      }
      $('.play-btn').click(function() {
        var message = {
          'id': game['id'],
          'card': $(this).html(),
        };
        socket.emit('play card', message);
      });
    }
    $('#leave-room-btn').click(function() {
      socket.emit('leave room', room);
    });
  }

  function setup_ui()
  {
    console.info('setup ui');
    if (game) {
      setup_game();
      return;
    }
    if (room) {
      setup_room();
      return;
    }
    setup_hall();
  }

  $('#logout').click(function() {
    socket.emit('logout');
  });

  socket.on('connect', function() {
    console.info('connect');
  });

  socket.on('disconnect', function() {
    console.info('disconnect');
  });

  socket.on('hall', function(json) {
    console.info('hall: %o', json);
    hall = json;
    setup_ui();
  });

  socket.on('room', function(json) {
    console.info('room: %o', json);
    room = json;
    setup_ui();
  });

  socket.on('leave room', function(json) {
    console.info('leave room: %o', json);
    if (json['id'] != room['id']) return;
    room = null;
    setup_ui();
  });

  socket.on('game', function(json) {
    console.info('game: %o', json);
    if (json['id'] != room['id']) return;
    game = json;
    setup_ui();
  });

  socket.on('game over', function(json) {
    console.info('game over: %o', json);
    if (json['id'] != game['id']) return;
    game = null;
    setup_ui();
  });

  socket.on('logout', function() {
    console.info('logout');
    window.location.href='/';
  });
};
