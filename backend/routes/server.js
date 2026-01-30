const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
require('dotenv').config();

// 1. IMPORT MODELS AND LOGIC (Updated paths for your folder structure)
const Match = require('./models/Match');              // From models folder
const GameState = require('./models/GameState');      // From models folder
const { processPotLogic } = require('./controllers/matchController'); // From controllers folder

const app = express();

// 2. MIDDLEWARE
app.use(cors());
app.use(express.json());

// 3. ROUTE INTEGRATION
// This connects your separate routes file to the main server
app.use('/api/analytics', require('./routes/analytics'));

// 4. MONGODB CONNECTION
const MONGO_URI = "mongodb+srv://sakshipatil062007_db_user:Mongo_sakshi@cluster0.vepqdnh.mongodb.net/SnookerAnalytics?appName=Cluster0";

mongoose.connect(MONGO_URI)
    .then(() => {
        console.log("✅ Connected to MongoDB Atlas");
        console.log("📡 Referee logic is now watching 'live_ball_data'...");

        // --- THE LIVE REFEREE WATCHER (Change Stream) ---
        const matchChangeStream = Match.watch(); //

        matchChangeStream.on('change', async (change) => {
            // Watch for new frames inserted by Python
            if (change.operationType === 'insert') {
                const newFrame = change.fullDocument;

                // Fetch latest referee score state
                let state = await GameState.findOne().sort({ lastUpdated: -1 });
                if (!state) {
                    state = new GameState(); 
                    await state.save();
                }

                // Logic: Check if Python AI detected a score increase
                const totalBackendScore = state.player1Score + state.player2Score;

                if (newFrame.match_score > totalBackendScore) {
                    console.log("Ball Pot Detected. Running Referee Logic...");

                    // Take the last detected ball to determine points/rules
                    const lastBall = newFrame.balls[newFrame.balls.length - 1]; 
                    
                    // Process rules (Fouls, turn switches, etc.)
                    const updatedState = processPotLogic(lastBall, state);
                    
                    // Save calculated results to GameState
                    updatedState.lastUpdated = new Date();
                    const finalizedState = new GameState(updatedState);
                    await finalizedState.save();

                    console.log(`✅ Score Updated: P1: ${updatedState.player1Score} | P2: ${updatedState.player2Score}`);
                }
            }
        });
    })
    .catch((err) => console.error("❌ MongoDB Connection Error:", err));

// 5. DIRECT API ROUTES (For legacy support or specific actions)

// Reset the Game (Start fresh)
app.post('/api/reset-game', async (req, res) => {
    try {
        await GameState.deleteMany({});
        const newState = new GameState();
        await newState.save();
        res.json({ message: "Game Reset Successfully", state: newState });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// 6. START SERVER
const PORT = 5000;
app.listen(PORT, () => {
    console.log(`🚀 Server is running on http://localhost:${PORT}`);
    console.log(`📡 Scorecard: http://localhost:5000/api/analytics/scorecard`);
    console.log(`📡 Mini-map: http://localhost:5000/api/analytics/table-live`);
});
