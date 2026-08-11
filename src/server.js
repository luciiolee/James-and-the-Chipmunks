import { Server } from "socket.io";

// Start server on port 3001, allowing connections from anywhere
const io = new Server(3001, {
  cors: { origin: "*" }
});

console.log("🎸 Spectator Server running on port 3001...");

io.on("connection", (socket) => {
  console.log("New computer connected:", socket.id);

  // When the Host sends a game update, broadcast it to all spectators
  socket.on("host_update", (data) => {
    socket.broadcast.emit("spectator_sync", data);
  });

  socket.on("disconnect", () => {
    console.log("Computer disconnected:", socket.id);
  });
});