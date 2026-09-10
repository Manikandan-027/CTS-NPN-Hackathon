import { Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import ErrorBoundary from './components/shared/ErrorBoundary'
import Dashboard from './pages/Dashboard'
import Chatbot from './pages/Chatbot'
import Incidents from './pages/Incidents'
import IncidentDetail from './pages/IncidentDetail'
import Validation from './pages/Validation'
import CustomerQueries from './pages/CustomerQueries'
import Activity from './pages/Activity'
import KnowledgeBase from './pages/KnowledgeBase'
import KnowledgeBaseEntry from './pages/KnowledgeBaseEntry'
import AddKnowledge from './pages/AddKnowledge'
import Settings from './pages/Settings'

export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/chatbot" element={<Chatbot />} />
          <Route path="/incidents" element={<Incidents />} />
          <Route path="/incidents/:incidentId" element={<IncidentDetail />} />
          <Route path="/validation" element={<Validation />} />
          <Route path="/customer-queries" element={<CustomerQueries />} />
          <Route path="/activity" element={<Activity />} />
          <Route path="/knowledge-base" element={<KnowledgeBase />} />
          <Route path="/knowledge-base/add" element={<AddKnowledge />} />
          <Route path="/knowledge-base/:kbId" element={<KnowledgeBaseEntry />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Dashboard />} />
        </Route>
      </Routes>
    </ErrorBoundary>
  )
}
