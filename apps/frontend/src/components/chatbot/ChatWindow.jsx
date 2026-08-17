import { useEffect, useRef, useState } from 'react'
import { BrainCircuit } from 'lucide-react'
import ChatMessage from './ChatMessage'
import ChatInput from './ChatInput'
import { apiClient, apiError } from '../../api/client'

let msgCounter = 0
const nextId = () => `m${++msgCounter}-${Date.now()}`

export default function ChatWindow({ loadIncidentId, onIncidentLoaded, prefill }) {
  const [messages, setMessages] = useState([])
  const [conversationId, setConversationId] = useState(null)
  const [loadingIncident, setLoadingIncident] = useState(false)
  const scrollRef = useRef(null)
  const [sending,setSending]=useState(false)

  // Reopen a past incident selected from the conversation sidebar.
  // Reconstructs the thread from real backend data only — the original
  // incident text and its actual RCA — it does not fabricate a chat log.
  useEffect(() => {
    if (!loadIncidentId) return
    let cancelled = false
    setLoadingIncident(true)
    apiClient.get(`/api/support/incidents/${encodeURIComponent(loadIncidentId)}`).then((r) => { const incident=r.data
        if (cancelled) return
        setConversationId(incident.incident_id)
        setMessages([
          {
            id: nextId(),
            role: 'user',
            text: incident.error_message || incident.customer_query || incident.incident || incident.incident_id,
          },
          {
            id: nextId(),
            role: 'assistant',
            type: 'rca_result',
            text: '',
            incident,
          },
        ])
      })
      .catch((err) => {
        if (cancelled) return
        setMessages([{ id: nextId(), role: 'assistant', type: 'error', error: apiError(err) }])
      })
      .finally(() => {
        if (!cancelled) setLoadingIncident(false)
        onIncidentLoaded?.()
      })
    return () => {
      cancelled = true
    }
  }, [loadIncidentId])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  function sendMessage(text) {
    const userMsg = { id: nextId(), role: 'user', text }
    const loadingId = nextId()
    setMessages((prev) => [...prev, userMsg, { id: loadingId, role: 'assistant', type: 'loading' }])

    setSending(true)
    apiClient.post('/api/chat', { message: text, conversation_id: conversationId }).then(r => {
      const data=r.data; const newConversationId=data.conversation_id || data.incident?.incident_id || conversationId
      setConversationId(newConversationId)
      setMessages(prev=>prev.map(m=>m.id===loadingId?{id:loadingId,role:'assistant',type:data.incident?'rca_result':'text',text:data.reply||data.message||'',incident:data.incident||null}:m))
    }).catch(err=>{setMessages(prev=>prev.map(m=>m.id===loadingId?{id:loadingId,role:'assistant',type:'error',error:apiError(err),retryText:text}:m))}).finally(()=>setSending(false))
  }

  function retryMessage(text) {
    setMessages((prev) => prev.filter((m) => m.type !== 'error' || m.retryText !== text))
    sendMessage(text)
  }

  function handleValidated(messageIncidentId) {
    if (!messageIncidentId) return
    apiClient.get(`/api/support/incidents/${encodeURIComponent(messageIncidentId)}`).then((r) => { const fresh=r.data
        setMessages((prev) =>
          prev.map((m) =>
            m.type === 'rca_result' && m.incident?.incident_id === messageIncidentId
              ? { ...m, incident: fresh }
              : m
          )
        )
      })
      .catch(() => {})
  }

  const isEmpty = messages.length === 0 && !loadingIncident

  return (
    <div className="flex-1 min-w-0 flex flex-col h-full">
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 md:px-6 py-5 space-y-5">
        {isEmpty && (
          <div className="h-full flex flex-col items-center justify-center text-center gap-3 py-16">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-accent-cyan to-accent-blue flex items-center justify-center shadow-glow">
              <BrainCircuit size={22} className="text-bg-base" />
            </div>
            <div>
              <div className="text-sm font-medium text-ink-primary">
                Describe an incident to begin investigating
              </div>
              <div className="text-xs text-ink-muted mt-1 max-w-sm">
                The chatbot sends what you type to the real RCA pipeline — incident history,
                repository analysis, and the LLM run against your actual backend.
              </div>
            </div>
          </div>
        )}

        {loadingIncident && (
          <div className="flex items-center justify-center py-10 text-sm text-ink-muted">
            Loading conversation…
          </div>
        )}

        {messages.map((m) => (
          <ChatMessage
            key={m.id}
            message={m}
            onValidated={() => handleValidated(m.incident?.incident_id)}
            onRetry={m.type === 'error' && m.retryText ? () => retryMessage(m.retryText) : undefined}
          />
        ))}
      </div>

      <ChatInput onSend={sendMessage} sending={sending} prefill={prefill} />
    </div>
  )
}
