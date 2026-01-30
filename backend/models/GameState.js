
const mongoose = require('mongoose');

const GameStateSchema = new mongoose.Schema({
    player1Score: { type: Number, default: 0 },
    player2Score: { type: Number, default: 0 },
    currentTurn: { type: Number, default: 1 }, // 1 or 2
    isWaitingForColor: { type: Boolean, default: false },
    currentBreak: { type: Number, default: 0 },
    lastUpdated: { type: Date, default: Date.now }
});

module.exports = mongoose.model('GameState', GameStateSchema, 'game_state');
