import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { LanguageProvider } from './i18n'
import { ChatProvider } from './chatContext'
import './styles/index.css'
import './styles/rtl.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <LanguageProvider>
        <ChatProvider>
          <App />
        </ChatProvider>
      </LanguageProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
