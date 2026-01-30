
const mongoose = require('mongoose');

const MatchSchema = new mongoose.Schema({
    match_score: { type: Number, default: 0 },
    balls: [
        {
            label: String,
            x: Number,
            y: Number
        }
    ],
    createdAt: { type: Date, default: Date.now }
});

// The third argument 'live_ball_data' tells Mongoose exactly which collection to use
module.exports = mongoose.model('Match', MatchSchema, 'live_ball_data');
