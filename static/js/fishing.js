function fishing(socket)
{
  var hall = null;
  var room = null;

  function setup_hall()
  {
    $content = $('#content');
    $content.empty();
    header = '<div class="page-header"><h1>Hall</h1></div>';
    rooms = '<div class="panel panel-primary">';
    rooms += '<div class="panel-heading">';
    rooms += '<h3 class="panel-title">Room List</h3>';
    rooms += '</div>';
    rooms += '<div class="panel-body">';
    rooms += '<div class="list-group">';
    for (var room in hall) {
      rooms += '<a class="list-group-item room" room-id="' + room + '">';
      rooms += '<h4 class="list-group-item-heading">Room #' + room + '</h4>';
      for (var i = 0; i < hall[room].length; i++) {
        rooms += '<p class="list-group-item-text">' + hall[room][i] + '</p>';
      }
      rooms += '</a>';
    }
    rooms += '</div>';
    rooms += '</div>';
    rooms += '</div>';
    create = '<div class="input-group">';
    create += '<input type="text" class="form-control" id="create-room-input" placeholder="Create New Room">';
    create += '<span class="input-group-btn"><button class="btn btn-primary" id="create-room-btn"><span class="glyphicon glyphicon-plus"></span></button>';
    create += '</div>';
    $content.append(header);
    $content.append(rooms);
    $content.append(create);
    $('.room').click(function() {
      socket.emit('enter room', {'room': $(this).attr('room-id')});
    });
    $('#create-room-btn').click(function() {
      socket.emit('create room', {'room': $('#create-room-input').val()});
    });
  };

  socket.on('connect', function() {
    console.info('connect');
  });

  socket.on('disconnect', function() {
    console.info('disconnect');
  });

  socket.on('hall', function(json) {
    console.info('hall: %o', json);
    hall = json;
    setup_hall();
  });

  socket.on('enter room', function(json) {
    console.info('enter room: %o', json);
    $content = $('#content');
  });
};
