import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Activity from './pages/Activity'
import Agents from './pages/Agents'
import DecisionCenter from './pages/DecisionCenter'
import Evaluation from './pages/Evaluation'
import Landing from './pages/Landing'
import Overview from './pages/Overview'
import ProductDetail from './pages/ProductDetail'
import Products from './pages/Products'
import Research from './pages/Research'
import Settings from './pages/Settings'
import SignalDetail from './pages/SignalDetail'
import Signals from './pages/Signals'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/overview" element={<Overview />} />
        <Route path="/products" element={<Products />} />
        <Route path="/products/:productId" element={<ProductDetail />} />
        <Route path="/signals" element={<Signals />} />
        <Route path="/signals/:signalId" element={<SignalDetail />} />
        <Route path="/research" element={<Research />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/decisions" element={<DecisionCenter />} />
        <Route path="/evaluation" element={<Evaluation />} />
        <Route path="/activity" element={<Activity />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
