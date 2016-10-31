function fishing(socket)
{
  console.info('fishing');

  var hall = null;
  var room = null;

  function setup_hall()
  {
    console.info('setup hall: %o', hall);
    $content = $('#content');
    $content.empty();
    header = '<div class="page-header"><h1>Hall</h1></div>';
    rooms = '';
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
    create = '<div class="input-group">';
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
    header = '<div class="page-header"><h1>';
    header += 'Room #' + room['id'];
    header += '<button class="btn btn-lg btn-danger pull-right" id="leave-room-btn"><span class="glyphicon glyphicon-off"></span></button>';
    header += '</h1></div>';
    users = '<ul class="list-group">';
    for (var i = 0; i < room['users'].length; i++) {
      users += '<li class="list-group-item">' + room['users'][i] + '</li>';
    }
    users += '</ul>';
    start_disabled = '';
    if (room && room['users'] && room['users'].length < 2) {
      start_disabled = ' disabled';
    }
    start = '<button class="btn btn-primary" id="start-btn"' + start_disabled + '>start</button>';
    $content.append(header);
    $content.append(users);
    $content.append(start);
    $('#leave-room-btn').click(function() {
      socket.emit('leave room', room);
    });
  };

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
    if (!room) setup_hall();
  });

  socket.on('room', function(json) {
    console.info('room: %o', json);
    room = json;
    setup_room();
  });

  socket.on('leave room', function(json) {
    console.info('leave room: %o', json);
    if (json['id'] == room['id']) {
      room = null;
      setup_hall();
    }
  });

  socket.on('logout', function() {
    console.info('logout');
    window.location.href='/';
  });
};
