import { Link } from 'react-router-dom'

export default function Performance() {
  return (
    <section id="performance">
      <h2 className="section-title">⚡ LIVE PERFORMANCE VISUALIZER ⚡</h2>

      {/* Wrapping the visualizer box in a Link to the game page */}
      <Link to="/game" style={{ textDecoration: 'none' }}>
        <div id="visualizer" style={{ cursor: 'pointer' }}>
          <div id="stage-light"></div>
          <div id="particles"></div>
          <h2 style={{ color: '#ffcc00', marginTop: '120px' }}>
            CLICK TO ENTER RHYTHM GAME 🎸
          </h2>
        </div>
      </Link>
    </section>
  )
}