import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import Hero from './components/Hero'
import Instrument from './components/Instrument'
import Band from './components/Band'
import Album from './components/Album'
import Performance from './components/Performance'
import Footer from './components/Footer'
import Game from './components/Game'
import './App.css'

function Home() {
  return (
    <>
      <Hero />
      <Instrument />
      <Band />
      <Album />
      <Performance />
      <Footer />
    </>
  )
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/game" element={<Game />} />
      </Routes>
    </Router>
  )
}

export default App