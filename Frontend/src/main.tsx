import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import App from './App.tsx'
import Gallery from './Gallery.tsx'
import ComponentList from './ComponentList.tsx'
import PseudoDiagram from './PseudoDiagram.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/gallery" element={<Gallery />} />
        <Route path="/component-list/:requestId" element={<ComponentList />} />
        <Route path="/pseudo-diagram/:requestId" element={<PseudoDiagram />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
)
