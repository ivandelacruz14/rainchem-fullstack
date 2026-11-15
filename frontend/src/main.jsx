import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/site.css'
import './styles/admin.css'
import App from './App.jsx'
import { ThemeProvider } from './context/ThemeContext.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </StrictMode>,
)