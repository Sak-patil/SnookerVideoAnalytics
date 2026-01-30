const ballValues = {
    "red-ball": 1, "yellow-ball": 2, "green-ball": 3, "brown-ball": 4,
    "blue-ball": 5, "pink-ball": 6, "black-ball": 7, "white-ball": 0
};

const processPotLogic = (potEvent, state) => {
    const ball = potEvent.label;
    const value = ballValues[ball];

    // --- RULE 1: FOUL (White Ball) ---
    if (ball === 'white-ball') {
        return handleFoul(state, 4, "White ball potted (In-off)");
    }

    // --- RULE 2: SEQUENCE VALIDATION ---
    if (state.isWaitingForColor) {
        if (ball === 'red-ball') {
            return handleFoul(state, 4, "Foul: Potted Red when Color was required");
        } else {
            // Legal Color Pot
            state.isWaitingForColor = false; // Next one must be Red
        }
    } else {
        if (ball !== 'red-ball') {
            return handleFoul(state, value < 4 ? 4 : value, "Foul: Potted Color when Red was required");
        } else {
            // Legal Red Pot
            state.isWaitingForColor = true; // Next one must be Color
        }
    }

    // --- IF LEGAL: UPDATE SCORE ---
    if (state.currentTurn === 1) state.player1Score += value;
    else state.player2Score += value;
    
    state.currentBreak += value;
    return state;
};

const handleFoul = (state, penalty, reason) => {
    console.log(`🚩 ${reason}`);
    // Add penalty to the OPPONENT
    if (state.currentTurn === 1) state.player2Score += penalty;
    else state.player1Score += penalty;

    // Reset break and switch turn
    state.currentBreak = 0;
    state.currentTurn = state.currentTurn === 1 ? 2 : 1;
    state.isWaitingForColor = false;
    return state;
};

module.exports = { processPotLogic };
