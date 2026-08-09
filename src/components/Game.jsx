import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { io } from 'socket.io-client'

const chartFiles = import.meta.glob('../charts/*.json', { eager: true })
const CHARTS = Object.values(chartFiles).map(file => file.default)

const FALL_TIME = 1800; 
const HIT_WINDOW = 350;     
const PERFECT_WINDOW = 100; 

const freqToNote = {
  261.63: "C4", 277.18: "C#4", 293.66: "D4", 311.13: "D#4", 329.63: "E4",
  349.23: "F4", 369.99: "F#4", 392.00: "G4", 415.30: "G#4", 440.00: "A4",
  466.16: "A#4", 493.88: "B4", 523.25: "C5", 554.37: "C#5", 587.33: "D5"
}

export default function Game() {
  const [role, setRole] = useState('select_role') 

  const [appState, setAppState] = useState('menu')
  const [currentSong, setCurrentSong] = useState(null)
  const [score, setScore] = useState(0)
  const [combo, setCombo] = useState(0)
  
  const [feedback, setFeedback] = useState({ text: '', color: '', id: 0 })
  const [currentNote, setCurrentNote] = useState('') 
  
  // 🔥 NEW: Half Time State
  const [isHalfTime, setIsHalfTime] = useState(false)
  
  const [activeNotes, setActiveNotes] = useState({
    green: false, red: false, yellow: false, blue: false,
  })
  
  const [connectionStatus, setConnectionStatus] = useState("NOT CONNECTED")
  
  const engineRef = useRef({ startTime: 0, timeElapsed: 0, notes: [], animationId: null })
  const [renderTrigger, setRenderTrigger] = useState(0)
  const portRef = useRef(null)
  const readerRef = useRef(null)
  const socketRef = useRef(null)
  const lastEmitRef = useRef(0)

  const syncStateRef = useRef({ 
    score: 0, 
    combo: 0, 
    activeNotes: { green: false, red: false, yellow: false, blue: false },
    feedback: { text: '', color: '', id: 0 },
    currentNote: '' 
  })

  // ==========================================
  // 1. SETUP WEBSOCKET CONNECTION
  // ==========================================
  useEffect(() => {
    const ip = window.location.hostname
    socketRef.current = io(`http://${ip}:5173`)

    socketRef.current.on("spectator_sync", (hostData) => {
      setAppState(hostData.appState)
      setScore(hostData.score)
      setCombo(hostData.combo)
      setActiveNotes(hostData.activeNotes)
      if (hostData.feedback) setFeedback(hostData.feedback) 
      if (hostData.currentNote !== undefined) setCurrentNote(hostData.currentNote)
      if (hostData.isHalfTime !== undefined) setIsHalfTime(hostData.isHalfTime) // Sync Half Time to spectator!
      
      engineRef.current.timeElapsed = hostData.timeElapsed
      engineRef.current.notes = hostData.notes
      
      setRenderTrigger(hostData.timeElapsed)
    })

    return () => socketRef.current.disconnect()
  }, [])

  // ==========================================
  // 2. HOST GAME LOOP
  // ==========================================
  const startGame = (song) => {
    setCurrentSong(song)
    setScore(0)
    setCombo(0)
    setFeedback({ text: '', color: '', id: 0 })
    setCurrentNote('')
    syncStateRef.current.score = 0
    syncStateRef.current.combo = 0
    syncStateRef.current.feedback = { text: '', color: '', id: 0 }
    syncStateRef.current.currentNote = ''
    
    // 🔥 Apply Half Time Multiplier to the timeline!
    const mult = isHalfTime ? 1.75 : 1.0;
    engineRef.current.notes = song.notes.map(n => ({ ...n, time: n.time * mult, hit: false, missed: false }))
    
    engineRef.current.startTime = performance.now()
    setAppState('playing')

    const loop = (timestamp) => {
      engineRef.current.timeElapsed = timestamp - engineRef.current.startTime
      setRenderTrigger(timestamp) 
      
      engineRef.current.notes.forEach(note => {
        // Generous Hit Windows scale with Half Time
        if (!note.hit && !note.missed && engineRef.current.timeElapsed > note.time + (HIT_WINDOW * mult)) {
          note.missed = true
          setCombo(0)
          syncStateRef.current.combo = 0 
          
          const fb = { text: 'MISS!', color: '#ff0000', id: performance.now() }
          setFeedback(fb)
          syncStateRef.current.feedback = fb
        }
      })

// 🔥 NETWORK THROTTLE & PAYLOAD OPTIMIZATION
      if (timestamp - lastEmitRef.current > 33) {
        
        // Calculate the current fall time so we know what is on screen
        const mult = isHalfTime ? 2.0 : 1.0; // Use whatever multiplier you set earlier!
        const currentFallTime = FALL_TIME * mult;
        
        // ✂️ THE FIX: Filter out all the thousands of notes that aren't on screen yet
        const visibleNotes = engineRef.current.notes.filter(n => {
          const timeUntilHit = n.time - engineRef.current.timeElapsed;
          // Only send notes that are about to appear, or just passed the hit bar
          return timeUntilHit > -1000 && timeUntilHit < currentFallTime + 1000;
        });

        socketRef.current.emit("host_update", {
          appState: 'playing',
          score: syncStateRef.current.score,
          combo: syncStateRef.current.combo,
          activeNotes: syncStateRef.current.activeNotes,
          feedback: syncStateRef.current.feedback, 
          currentNote: syncStateRef.current.currentNote, 
          isHalfTime: isHalfTime,
          timeElapsed: engineRef.current.timeElapsed,
          notes: visibleNotes // 👈 Blast ~10 notes instead of 2,000!
        })
        lastEmitRef.current = timestamp
      }

      const lastNoteTime = Math.max(...engineRef.current.notes.map(n => n.time))
      if (engineRef.current.timeElapsed > lastNoteTime + 2000) {
        setAppState('results')
        socketRef.current.emit("host_update", { 
          appState: 'results', score: syncStateRef.current.score, combo: syncStateRef.current.combo, 
          activeNotes: syncStateRef.current.activeNotes, feedback: syncStateRef.current.feedback, 
          currentNote: '', isHalfTime: isHalfTime, timeElapsed: 0, notes: [] 
        })
        return; 
      }
      engineRef.current.animationId = requestAnimationFrame(loop)
    }
    engineRef.current.animationId = requestAnimationFrame(loop)
  }

  useEffect(() => {
    return () => cancelAnimationFrame(engineRef.current.animationId)
  }, [])

  // ==========================================
  // 3. HIT DETECTION & INPUTS
  // ==========================================
  const processHit = (lane) => {
    if (role !== 'host') return 

    setActiveNotes(prev => {
      const newState = { ...prev, [lane]: true }
      syncStateRef.current.activeNotes = newState
      return newState
    })
    
    setTimeout(() => {
      setActiveNotes(prev => {
        const newState = { ...prev, [lane]: false }
        syncStateRef.current.activeNotes = newState
        return newState
      })
    }, 150)

    if (appState !== 'playing') return

    const mult = isHalfTime ? 1.75 : 1.0;
    const { timeElapsed, notes } = engineRef.current
    const targetNote = notes.find(n => n.lane === lane && !n.hit && !n.missed && Math.abs(n.time - timeElapsed) <= (HIT_WINDOW * mult))

    if (targetNote) {
      targetNote.hit = true
      
      const timeDiff = Math.abs(targetNote.time - timeElapsed)
      let points = 0
      let fbText = ''
      let fbColor = ''

      if (timeDiff <= (PERFECT_WINDOW * mult)) {
        points = 100
        fbText = 'PERFECT!'
        fbColor = '#00ffff'
      } else {
        points = 50
        fbText = 'OK!'
        fbColor = '#ffcc00'
      }

      setScore(prev => {
        const newScore = prev + points + (combo * 10)
        syncStateRef.current.score = newScore
        return newScore
      })
      setCombo(prev => {
        const newCombo = prev + 1
        syncStateRef.current.combo = newCombo
        return newCombo
      })
      
      const fb = { text: fbText, color: fbColor, id: performance.now() }
      setFeedback(fb)
      syncStateRef.current.feedback = fb
      
    } else {
      setCombo(0)
      syncStateRef.current.combo = 0
      
      const fb = { text: 'MISS!', color: '#ff0000', id: performance.now() }
      setFeedback(fb)
      syncStateRef.current.feedback = fb
    }
  }

  const processHitRef = useRef(processHit)
  useEffect(() => { processHitRef.current = processHit })

  // Keyboard
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.repeat || role !== 'host') return
      const key = e.key.toLowerCase()
      if (key === 'a') processHitRef.current('green')
      if (key === 's') processHitRef.current('red')
      if (key === 'd') processHitRef.current('yellow')
      if (key === 'f') processHitRef.current('blue')
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [role])

  // Web Serial
  const connectToPico = async () => {
    try {
      let port;
      const approvedPorts = await navigator.serial.getPorts()
      if (approvedPorts.length > 0) port = approvedPorts[0]
      else port = await navigator.serial.requestPort()

      await port.open({ baudRate: 115200 })
      portRef.current = port
      setConnectionStatus("CONNECTED 🎸")

      const textDecoder = new TextDecoderStream()
      port.readable.pipeTo(textDecoder.writable)
      const reader = textDecoder.readable.getReader()
      readerRef.current = reader

      let buffer = ""
      while (true) {
        const { value, done } = await reader.read()
        if (done) break 
        if (value) {
          buffer += value
          const lines = buffer.split('\n')
          buffer = lines.pop()

          for (const line of lines) {
            const cleanLine = line.trim()
            if (!cleanLine) continue
            try {
              const data = JSON.parse(cleanLine)
              if (data.type === "button_hit") {
                if (data.button === "lane1") processHitRef.current('green')
                if (data.button === "lane2") processHitRef.current('red')
                if (data.button === "lane3") processHitRef.current('yellow')
                if (data.button === "lane4") processHitRef.current('blue')
              }
              if (data.type === "log" && data.frequency) {
                const noteName = freqToNote[data.frequency] || "Unknown"
                setCurrentNote(noteName)
                syncStateRef.current.currentNote = noteName
              }
            } catch (err) {}
          }
        }
      }
    } catch (error) {
      setConnectionStatus("CONNECTION FAILED")
    }
  }

  // ==========================================
  // RENDER UI
  // ==========================================
  if (role === 'select_role') {
    return (
      <div style={{ minHeight: '100vh', background: '#050505', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
        <h1 style={{ color: '#d83a24', fontSize: '48px', marginBottom: '40px' }}>WHO ARE YOU?</h1>
        <div style={{ display: 'flex', gap: '30px' }}>
          <button onClick={() => setRole('host')} style={{ padding: '20px 40px', fontSize: '24px', background: 'linear-gradient(#ffdd00, #ff6800)', border: 'none', borderRadius: '50px', cursor: 'pointer', fontWeight: 'bold' }}>
            🎸 I AM PLAYING
          </button>
          <button onClick={() => setRole('spectator')} style={{ padding: '20px 40px', fontSize: '24px', background: '#333', color: 'white', border: '2px solid #555', borderRadius: '50px', cursor: 'pointer', fontWeight: 'bold' }}>
            👀 SPECTATE LIVE
          </button>
        </div>
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', background: '#050505', padding: '30px', display: 'flex', flexDirection: 'column', alignItems: 'center', userSelect: 'none' }}>
      
      <style>
        {`
          @keyframes feedbackPop {
            0% { transform: scale(0.5); opacity: 1; }
            40% { transform: scale(1.1); opacity: 1; }
            100% { transform: scale(1); opacity: 0; }
          }
        `}
      </style>

      <div style={{ width: '100%', maxWidth: '800px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <Link to="/" style={{ color: '#ffcc00', textDecoration: 'none', fontWeight: 'bold' }}>← EXIT SHOW</Link>
        
        {role === 'host' ? (
          <div style={{ textAlign: 'right' }}>
            <button onClick={connectToPico} style={{ padding: '8px 12px', background: '#ffcc00', fontWeight: 'bold', border: 'none', borderRadius: '5px', cursor: 'pointer', marginBottom: '5px' }}>
              🔌 CONNECT USB
            </button>
            <div style={{ color: connectionStatus.includes("CONNECTED") ? '#00ff55' : '#ff0000', fontSize: '12px', fontWeight: 'bold' }}>{connectionStatus}</div>
          </div>
        ) : (
          <div style={{ color: '#00ff55', fontWeight: 'bold', letterSpacing: '2px' }}>🔴 LIVE BROADCAST</div>
        )}
      </div>

      {appState === 'menu' && (
        <div style={{ textAlign: 'center', marginTop: '50px' }}>
          <h1 style={{ color: '#d83a24', fontSize: '48px' }}>
            {role === 'host' ? 'SETLIST' : 'WAITING FOR HOST TO START...'}
          </h1>
          
          {/* 🔥 NEW: Half Time Toggle Button */}
          {role === 'host' && (
            <div style={{ marginBottom: '30px' }}>
              <button onClick={() => setIsHalfTime(!isHalfTime)} style={{ padding: '15px 30px', fontSize: '20px', background: isHalfTime ? '#00ffff' : '#333', color: isHalfTime ? '#000' : '#fff', border: isHalfTime ? 'none' : '2px solid #555', borderRadius: '50px', cursor: 'pointer', fontWeight: 'bold', transition: '0.2s' }}>
                {isHalfTime ? '🐢 HALF TIME MOD: ON' : '🐢 HALF TIME MOD: OFF'}
              </button>
            </div>
          )}
          
          {role === 'host' && CHARTS.map(song => (
            <button key={song.id} onClick={() => startGame(song)} style={{ padding: '20px 40px', fontSize: '24px', background: 'linear-gradient(#ffdd00, #ff6800)', border: 'none', borderRadius: '50px', cursor: 'pointer', fontWeight: 'bold', margin: '10px' }}>
              PLAY: {song.title}
            </button>
          ))}
        </div>
      )}

      {appState === 'playing' && (
        <>
          <div style={{ display: 'flex', width: '100%', maxWidth: '500px', justifyContent: 'space-between', marginBottom: '10px' }}>
            <h2 style={{ color: 'white', margin: 0 }}>SCORE: {score}</h2>
            <h2 style={{ color: combo > 5 ? '#ffcc00' : 'white', margin: 0 }}>COMBO: {combo}</h2>
          </div>

          <div style={{
            width: '100%', maxWidth: '500px', height: '65vh',
            background: 'linear-gradient(to bottom, #111, #222)',
            borderLeft: '4px solid #444', borderRight: '4px solid #444',
            position: 'relative', overflow: 'visible' 
          }}>
            
            <div style={{
              position: 'absolute', left: '-160px', top: '15%', width: '130px', color: '#fff', textAlign: 'center',
              background: '#111', padding: '15px 5px', borderRadius: '10px', border: '2px solid #444',
              opacity: currentNote ? 1 : 0.2, transition: 'opacity 0.2s', zIndex: 10
            }}>
              <div style={{ fontSize: '12px', color: '#888', marginBottom: '5px' }}>CURRENT NOTE</div>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#00ff55' }}>
                {currentNote || '---'}
              </div>
            </div>

            {feedback.text && (
              <div key={feedback.id} style={{
                position: 'absolute', right: '-200px', bottom: '15%', width: '180px', color: feedback.color,
                fontSize: '42px', fontWeight: 'bold', fontStyle: 'italic', textShadow: `0 0 15px ${feedback.color}`,
                animation: 'feedbackPop 0.6s ease-out forwards', zIndex: 10
              }}>
                {feedback.text}
              </div>
            )}

            {engineRef.current.notes.map((note, idx) => {
              // 🔥 Render Math: Custom fast fall speed during Half Time!
              // If Half Time is ON, drop in 800ms. If OFF, use the normal 2000ms.
              const currentFallTime = isHalfTime ? 550 : FALL_TIME;
              const timeUntilHit = note.time - engineRef.current.timeElapsed
              const progress = 1 - (timeUntilHit / currentFallTime)

              if (progress < -0.1 || progress > 1.2 || note.hit) return null

              const laneColors = { green: '#00ff55', red: '#ff0000', yellow: '#ffe600', blue: '#008cff' }
              const lanePositions = { green: '12%', red: '37%', yellow: '62%', blue: '87%' }

              return (
                <div key={idx} style={{
                  position: 'absolute', top: `${progress * 85}%`, left: lanePositions[note.lane],
                  width: '50px', height: '20px', background: laneColors[note.lane],
                  borderRadius: '10px', boxShadow: `0 0 15px ${laneColors[note.lane]}`,
                  transform: 'translateX(-50%)', opacity: note.missed ? 0.3 : 1
                }} />
              )
            })}
            
            <div className="fret-board" style={{ position: 'absolute', bottom: '20px', width: '100%', margin: 0, gap: '20px', display: 'flex', justifyContent: 'center' }}>
              <div className={`fret green ${activeNotes.green ? 'visualizer-green' : ''}`} style={{ transform: activeNotes.green ? 'scale(0.95)' : 'scale(1)', width: '70px', height: '70px', borderWidth: '5px' }}></div>
              <div className={`fret red ${activeNotes.red ? 'visualizer-red' : ''}`} style={{ transform: activeNotes.red ? 'scale(0.95)' : 'scale(1)', width: '70px', height: '70px', borderWidth: '5px' }}></div>
              <div className={`fret yellow ${activeNotes.yellow ? 'visualizer-yellow' : ''}`} style={{ transform: activeNotes.yellow ? 'scale(0.95)' : 'scale(1)', width: '70px', height: '70px', borderWidth: '5px' }}></div>
              <div className={`fret blue ${activeNotes.blue ? 'visualizer-blue' : ''}`} style={{ transform: activeNotes.blue ? 'scale(0.95)' : 'scale(1)', width: '70px', height: '70px', borderWidth: '5px' }}></div>
            </div>
          </div>
        </>
      )}

      {appState === 'results' && (
        <div style={{ textAlign: 'center', marginTop: '50px' }}>
          <h1 style={{ color: '#ffcc00', fontSize: '64px', margin: 0 }}>SHOW OVER</h1>
          <h2 style={{ color: 'white', fontSize: '32px' }}>FINAL SCORE: {score}</h2>
          
          {role === 'host' && (
            <button onClick={() => {
              setAppState('menu');
              socketRef.current.emit("host_update", { appState: 'menu', score: 0, combo: 0, activeNotes: {}, feedback: {text: '', color: '', id: 0}, currentNote: '', isHalfTime: isHalfTime, timeElapsed: 0, notes: [] })
            }} style={{ marginTop: '30px', padding: '15px 30px', background: '#333', color: 'white', border: 'none', borderRadius: '10px', cursor: 'pointer', fontSize: '18px' }}>
              BACK TO SETLIST
            </button>
          )}
        </div>
      )}
    </div>
  )
}