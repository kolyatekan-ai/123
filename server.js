const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const { v4: uuidv4 } = require('uuid');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

app.use(express.static('public'));

const rooms = new Map();

wss.on('connection', (ws) => {
  ws.id = uuidv4();
  ws.room = null;

  ws.on('message', (data) => {
    let msg;
    try {
      msg = JSON.parse(data);
    } catch (e) {
      return;
    }

    switch (msg.type) {
      case 'create-room': {
        const roomId = uuidv4().substring(0, 8);
        rooms.set(roomId, new Set([ws.id]));
        ws.room = roomId;
        ws.send(JSON.stringify({ type: 'room-created', roomId }));
        break;
      }

      case 'join-room': {
        const { roomId } = msg;
        if (rooms.has(roomId)) {
          rooms.get(roomId).add(ws.id);
          ws.room = roomId;
          ws.send(JSON.stringify({ type: 'room-joined', roomId }));
          broadcast(wss, ws, roomId, { type: 'user-joined', userId: ws.id });
        } else {
          ws.send(JSON.stringify({ type: 'error', message: 'Комната не найдена' }));
        }
        break;
      }

      case 'offer':
      case 'answer':
      case 'ice-candidate': {
        broadcast(wss, ws, ws.room, msg, true);
        break;
      }

      case 'leave-room': {
        leaveRoom(ws);
        break;
      }
    }
  });

  ws.on('close', () => {
    leaveRoom(ws);
  });
});

function broadcast(wss, sender, roomId, data, excludeSender = false) {
  if (!roomId || !rooms.has(roomId)) return;
  wss.clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN && client.room === roomId) {
      if (excludeSender && client.id === sender.id) return;
      client.send(JSON.stringify(data));
    }
  });
}

function leaveRoom(ws) {
  if (ws.room && rooms.has(ws.room)) {
    rooms.get(ws.room).delete(ws.id);
    broadcast(wss, ws, ws.room, { type: 'user-left', userId: ws.id });
    if (rooms.get(ws.room).size === 0) {
      rooms.delete(ws.room);
    }
    ws.room = null;
  }
}

const PORT = process.env.PORT || 3000;
server.listen(PORT, '0.0.0.0', () => {
  console.log(`Сервер запущен на порту ${PORT}`);
});
