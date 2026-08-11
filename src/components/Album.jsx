export default function Album() {
  return (
    <section id="album">
      <h2 className="section-title">💿 NEWEST ALBUM</h2>
      <div className="album-header">
        <p>JAMES AND THE CHIPMUNKS PRESENT</p>
        <h3>CHIPMUNK HERO</h3>
        <p>Our Battle of the Builds live set.</p>
      </div>

      <div className="song-card">
        <div className="track-number">TRACK 01</div>
        <h2>Bad Apple!!</h2>
        <h3>Alstroemeria Records</h3>
        <p>Featured performance song</p>

        <div className="video-container">
          <iframe
            src="https://www.youtube.com/embed/FtutLA63Cp8"
            title="Bad Apple!! - Alstroemeria Records"
            frameBorder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          ></iframe>
        </div>
      </div>
      <p className="set-note">🎸 LIVE SET • JAMES AND THE CHIPMUNKS</p>
    </section>
  )
}