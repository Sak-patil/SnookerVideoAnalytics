import React, { useState, useEffect } from 'react';

const App = () => {
    // Stage Management: 'welcome', 'calibration', 'live'
    const [appStage, setAppStage] = useState('welcome');
    const [scoreData, setScoreData] = useState(null);
    const [ballPositions, setBallPositions] = useState([]);

    // 1. Polling for Live Data (Only active during 'live' stage)
    useEffect(() => {
        let interval;
        if (appStage === 'live') {
            interval = setInterval(async () => {
                try {
                    const sRes = await fetch('http://localhost:5000/api/analytics/scorecard');
                    const bRes = await fetch('http://localhost:5000/api/analytics/table-live');
                    setScoreData(await sRes.json());
                    const balls = await bRes.json();
                    setBallPositions(balls.balls || []);
                } catch (err) {
                    console.error("Sync Error:", err);
                }
            }, 1000);
        }
        return () => clearInterval(interval);
    }, [appStage]);

    // 2. Control Functions
    const handleUpload = () => {
        // Logic to trigger Python AI start would go here
        setAppStage('calibration');
    };

    const sendSignal = async (cmd) => {
        await fetch('http://localhost:5000/api/send-command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: cmd })
        });
        if (cmd === 'y') setAppStage('live');
        else setAppStage('welcome'); // Reset if 'n'
    };

    return (
        <div style={{ backgroundColor: '#121212', color: 'white', minHeight: '100vh', padding: '40px', fontFamily: 'Arial' }}>
            
            {/* --- STAGE 1: WELCOME & UPLOAD --- */}
            {appStage === 'welcome' && (
                <div style={{ textAlign: 'center', marginTop: '100px' }}>
                    <h1>Welcome to Snooker Video Analytics</h1>
                    <p>Upload your match video to begin AI tracking.</p>
                    <input type="file" style={{ margin: '20px 0' }} />
                    <br />
                    <button onClick={handleUpload} style={btnStyle}>Analyze Video</button>
                </div>
            )}

            {/* --- STAGE 2: CALIBRATION (Y/N) --- */}
            {appStage === 'calibration' && (
                <div style={{ textAlign: 'center' }}>
                    <h2>Calibration Phase</h2>
                    <p>Please check the OpenCV window on your computer.</p>
                    <p>Are the table corners and balls detected correctly?</p>
                    <div style={{ display: 'flex', justifyContent: 'center', gap: '20px', marginTop: '30px' }}>
                        <button onClick={() => sendSignal('y')} style={{ ...btnStyle, backgroundColor: '#2e7d32' }}>Yes (Y) - Start Match</button>
                        <button onClick={() => sendSignal('n')} style={{ ...btnStyle, backgroundColor: '#c62828' }}>No (N) - Reset</button>
                    </div>
                </div>
            )}

            {/* --- STAGE 3: LIVE DASHBOARD --- */}
            {appStage === 'live' && (
                <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
                        <div style={cardStyle}>
                            <h3>Player 1</h3>
                            <h1 style={{ fontSize: '4rem' }}>{scoreData?.player1Score || 0}</h1>
                        </div>
                        <div style={{ textAlign: 'center' }}>
                            <h2>Turn: Player {scoreData?.currentTurn}</h2>
                            <p>Current Break: {scoreData?.currentBreak || 0}</p>
                        </div>
                        <div style={cardStyle}>
                            <h3>Player 2</h3>
                            <h1 style={{ fontSize: '4rem' }}>{scoreData?.player2Score || 0}</h1>
                        </div>
                    </div>

                    {/* 2D Mini-Map */}
                    <div style={tableStyle}>
                        {ballPositions.map((ball, i) => (
                            <div key={i} style={{
                                position: 'absolute',
                                left: `${(ball.x / 400) * 100}%`,
                                top: `${(ball.y / 800) * 100}%`,
                                width: '12px', height: '12px', borderRadius: '50%',
                                backgroundColor: ball.label.split('-')[0],
                                border: '1px solid black', transform: 'translate(-50%, -50%)'
                            }} />
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

// --- STYLING OBJECTS ---
const btnStyle = { padding: '12px 24px', fontSize: '18px', cursor: 'pointer', borderRadius: '5px', border: 'none', backgroundColor: '#1976d2', color: 'white' };
const cardStyle = { backgroundColor: '#1e1e1e', padding: '20px', borderRadius: '10px', width: '200px', textAlign: 'center' };
const tableStyle = { position: 'relative', width: '300px', height: '600px', backgroundColor: '#2e7d32', margin: '0 auto', borderRadius: '10px', border: '8px solid #5d4037' };

export default App;
