import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { Server } from 'socket.io'

// Custom plugin to run Socket.IO on the exact same server as Vite
const socketPlugin = {
  name: 'socket-io-plugin',
  configureServer(server) {
    const io = new Server(server.httpServer, {
      cors: { origin: '*' }
    });

    console.log("🎸 WebSocket Server attached to Vite!");

    io.on('connection', (socket) => {
      console.log('✅ Computer connected via WebSocket:', socket.id);

      socket.on('host_update', (data) => {
        socket.broadcast.emit('spectator_sync', data);
      });

      socket.on('disconnect', () => {
        console.log('❌ Computer disconnected:', socket.id);
      });
    });
  }
}

export default defineConfig({
  plugins: [react(), socketPlugin],
})