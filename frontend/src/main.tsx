import { ConfigProvider } from 'antd'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Provider } from 'react-redux'
import { BrowserRouter, Route, Routes } from 'react-router'
import { store } from './app/store'
import './index.css'
import Workspace from './features/investigation/Workspace'
import ListPage from './features/list/ListPage'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Provider store={store}>
      <ConfigProvider theme={{ token: { colorPrimary: '#4f46e5', borderRadius: 8, fontSize: 14 } }}>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<ListPage />} />
            <Route path="/investigations/:id" element={<Workspace />} />
          </Routes>
        </BrowserRouter>
      </ConfigProvider>
    </Provider>
  </StrictMode>,
)
