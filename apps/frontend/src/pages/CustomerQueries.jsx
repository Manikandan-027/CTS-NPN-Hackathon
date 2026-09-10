import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { MessageSquareText } from 'lucide-react'
import { apiClient, apiError } from '../api/client'
import Panel from '../components/shared/Panel'
import LoadingState from '../components/shared/LoadingState'
import ErrorState from '../components/shared/ErrorState'
import EmptyState from '../components/shared/EmptyState'
import { formatDateTime } from '../utils/format'

export default function CustomerQueries() {
  const [queries,setQueries]=useState([])
  const [loading,setLoading]=useState(true)
  const [error,setError]=useState(null)
  const fetchQueries=async()=>{try{const r=await apiClient.get('/api/support/customer-queries',{params:{limit:100}});setQueries(r.data?.queries||[]);setError(null)}catch(e){setError(apiError(e))}finally{setLoading(false)}}
  useEffect(()=>{fetchQueries();const id=setInterval(fetchQueries,5000);return()=>clearInterval(id)},[])
  const list = Array.isArray(queries) ? queries : []

  return (
    <Panel title={`Customer queries (${list.length})`}>
      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState error={error} onRetry={fetchQueries} />
      ) : list.length === 0 ? (
        <EmptyState
          icon={MessageSquareText}
          title="No customer queries yet"
          description="Queries submitted from the demo payment app will appear here."
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-ink-muted text-xs">
                <th className="px-3 py-2 font-mono font-medium">Query</th>
                <th className="px-3 py-2 font-mono font-medium">Customer</th>
                <th className="px-3 py-2 font-mono font-medium">Service</th>
                <th className="px-3 py-2 font-mono font-medium">Incident</th>
                <th className="px-3 py-2 font-mono font-medium">Status</th>
                <th className="px-3 py-2 font-mono font-medium">Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {list.map((q, i) => (
                <tr key={q.id || i} className="border-t border-border-subtle hover:bg-white/[0.03] transition-colors">
                  <td className="px-3 py-2.5 text-ink-primary max-w-[320px]">{q.query}</td>
                  <td className="px-3 py-2.5 text-ink-secondary">{q.customer_email || '—'}</td>
                  <td className="px-3 py-2.5 text-ink-secondary">{q.service || '—'}</td>
                  <td className="px-3 py-2.5 font-mono">
                    {q.incident_id ? (
                      <Link to={`/incidents/${q.incident_id}`} className="text-accent-cyan hover:underline">
                        {q.incident_id}
                      </Link>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td className="px-3 py-2.5 text-ink-muted text-xs">{q.status || '—'}</td>
                  <td className="px-3 py-2.5 text-ink-muted text-xs whitespace-nowrap">
                    {formatDateTime(q.timestamp || q.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  )
}
