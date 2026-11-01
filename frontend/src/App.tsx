import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Overview from './pages/Overview'
import Products from './pages/Products'
import ProductDetail from './pages/ProductDetail'
import Competitors from './pages/Competitors'
import MarketRadar from './pages/MarketRadar'
import Opportunities from './pages/Opportunities'
import PricingLab from './pages/PricingLab'
import ActionCenter from './pages/ActionCenter'
import Automations from './pages/Automations'
import Reports from './pages/Reports'
import Connections from './pages/Connections'
import Settings from './pages/Settings'
import Diagnostics from './pages/Diagnostics'
import Activity from './pages/Activity'
import Evaluation from './pages/Evaluation'
import Landing from './pages/Landing'
import Research from './pages/Research'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Landing / Default */}
        <Route path="/" element={<Landing />} />

        {/* WORKSPACE */}
        <Route path="/overview" element={<Overview />} />
        <Route path="/research" element={<Research />} />
        <Route path="/products" element={<Products />} />
        <Route path="/products/:productId" element={<ProductDetail />} />
        <Route path="/competitors" element={<Competitors />} />
        <Route path="/market-radar" element={<MarketRadar />} />
        <Route path="/opportunities" element={<Opportunities />} />
        <Route path="/pricing-lab" element={<PricingLab />} />

        {/* OPERATIONS */}
        <Route path="/actions" element={<ActionCenter />} />
        <Route path="/automations" element={<Automations />} />
        <Route path="/reports" element={<Reports />} />

        {/* SETUP & DIAGNOSTICS */}
        <Route path="/connections" element={<Connections />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/diagnostics" element={<Diagnostics />} />
        <Route path="/activity" element={<Activity />} />
        <Route path="/evaluation" element={<Evaluation />} />

        {/* BACKWARDS COMPATIBILITY REDIRECTS */}
        <Route path="/decisions" element={<Navigate to="/actions" replace />} />
        <Route path="/signals" element={<Navigate to="/overview" replace />} />
        <Route path="/signals/:signalId" element={<Navigate to="/overview" replace />} />
                <Route path="/agents" element={<Navigate to="/diagnostics" replace />} />
        <Route path="/products/:productId/intelligence" element={<Navigate to="/products/:productId" replace />} />

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
