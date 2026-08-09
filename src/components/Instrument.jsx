export default function Instrument() {
  return (
    <section id="instrument">
      <h2 className="section-title">🎸 OUR INSTRUMENT</h2>
      <div className="instrument-main">
        <h3>CUSTOM USB GUITAR HERO CONTROLLER</h3>
        <p>
          Our instrument is a custom Guitar Hero-inspired controller built using CAD, circuits, coding, physical buttons, and a Raspberry Pi Pico.
        </p>
        <p>
          When the player presses one of the colored fret buttons, the Pico detects the input and sends information through a USB data cable to our performance website.
        </p>
        <p>
          The website reacts instantly by creating a different visual effect for every unique fret.
        </p>
      </div>

      <div className="info-grid">
        <div className="info-card">
          <div className="card-icon">🔊</div>
          <h3>SOUND PROFILE</h3>
          <p>The instrument is designed around an energetic, fast-paced rock sound inspired by Guitar Hero and arcade rhythm games.</p>
        </div>
        <div className="info-card">
          <div className="card-icon">⚡</div>
          <h3>EFFECTS</h3>
          <p>Every fret button produces its own visual effect.</p>
          <p>Green creates a pulse, red creates distortion, yellow creates a shockwave, and blue creates a spinning stage effect.</p>
        </div>
        <div className="info-card">
          <div className="card-icon">🛠️</div>
          <h3>DESIGN</h3>
          <p>The guitar body was designed using CAD with inspiration from classic Guitar Hero controllers.</p>
        </div>
        <div className="info-card">
          <div className="card-icon">🔥</div>
          <h3>AESTHETIC</h3>
          <p>Our overall visual style combines Guitar Hero, 2000s arcade games, dark concert stages, bright neon colors, and rock music.</p>
        </div>
      </div>
    </section>
  )
}