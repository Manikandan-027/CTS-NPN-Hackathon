import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import ConversationList from '../components/chatbot/ConversationList'
import ChatWindow from '../components/chatbot/ChatWindow'

export default function Chatbot() {
  const location = useLocation()
  const [sessionKey, setSessionKey] = useState(0)
  const [loadIncidentId, setLoadIncidentId] = useState(null)
  const [activeIncidentId, setActiveIncidentId] = useState(null)

  // Supports being deep-linked from elsewhere in the app (e.g. an
  // "Investigate with RCA Chatbot" action) via
  // navigate('/chatbot', { state: { prefillMessage: '...' } }).
  const prefill = location.state?.prefillMessage

  function handleNewInvestigation() {
    setLoadIncidentId(null)
    setActiveIncidentId(null)
    setSessionKey((k) => k + 1)
  }

  function handleSelectConversation(incidentId) {
    setActiveIncidentId(incidentId)
    setLoadIncidentId(incidentId)
    setSessionKey((k) => k + 1)
  }

  return (
    <div className="glass-panel rounded-2xl shadow-glass overflow-hidden flex h-[calc(100vh-160px)] min-h-[560px]">
      <ConversationList
        activeIncidentId={activeIncidentId}
        onSelect={handleSelectConversation}
        onNewInvestigation={handleNewInvestigation}
      />
      <ChatWindow
        key={sessionKey}
        loadIncidentId={loadIncidentId}
        onIncidentLoaded={() => setLoadIncidentId(null)}
        prefill={sessionKey === 0 ? prefill : undefined}
      />
    </div>
  )
}
