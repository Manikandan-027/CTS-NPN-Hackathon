import { Component } from 'react'
import { AlertOctagon, RotateCcw } from 'lucide-react'

// Prevents any single page-level failure from crashing the whole React tree.
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    console.error('RCA Console crashed:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-bg-base px-4">
          <div className="glass-panel rounded-2xl p-8 max-w-md text-center space-y-3">
            <AlertOctagon size={28} className="text-state-danger mx-auto" />
            <h2 className="font-display text-lg font-semibold text-ink-primary">
              Something went wrong
            </h2>
            <p className="text-sm text-ink-muted">
              This page hit an unexpected error. Try reloading — your data on the backend is unaffected.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="inline-flex items-center gap-2 rounded-lg bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30 px-4 py-2 text-sm font-semibold hover:bg-accent-cyan/25 transition-colors"
            >
              <RotateCcw size={14} /> Reload
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
