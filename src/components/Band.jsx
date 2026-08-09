export default function Band() {
  return (
    <section id="band">
      <h2 className="section-title">🎤 MEET THE BAND</h2>
      <div className="band-photo-box">
        <img src="/IMG_2872.jpeg" alt="James and the Chipmunks" className="band-picture" />
      </div>

      <div className="band-grid">
        <div className="member">
          <div className="member-icon">🎸</div>
          <h3>Thaomi</h3>
          <h4>THEODORE</h4>
          <p className="member-role">GUITAR & CODING</p>
          <p>Works on the guitar controls and programming that connects our instrument to the live visual effects.</p>
        </div>
        <div className="member">
          <div className="member-icon">🐿️</div>
          <h3>Rose</h3>
          <h4>SIMON</h4>
          <p className="member-role">CAD DESIGN</p>
          <p>Works on the CAD design and physical appearance of our custom Guitar Hero inspired controller.</p>
        </div>
        <div className="member">
          <div className="member-icon">⚙️</div>
          <h3>Mustafa</h3>
          <h4>JAMES</h4>
          <p className="member-role">CAD DESIGN</p>
          <p>Helps design the guitar body and mechanical components used in the final instrument.</p>
        </div>
        <div className="member">
          <div className="member-icon">⚡</div>
          <h3>Mariana</h3>
          <h4>ALVIN</h4>
          <p className="member-role">ELECTRONICS & CODING</p>
          <p>Works on the circuits, electronic components, button inputs, and programming used by the guitar controller.</p>
        </div>
      </div>
    </section>
  )
}