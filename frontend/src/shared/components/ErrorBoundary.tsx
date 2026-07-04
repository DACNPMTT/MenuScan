import { Component, type ReactNode } from 'react'

interface ErrorBoundaryProps {
  children: ReactNode
  /** Render-prop fallback. `reset` clears the caught error so the boundary
   * re-renders its children; callers usually pair it with a reload/navigate
   * because re-rendering unchanged inputs typically re-throws. */
  fallback: (error: Error, reset: () => void) => ReactNode
}

interface ErrorBoundaryState {
  error: Error | null
}

/** React error boundary. Catches render/lifecycle errors in the subtree so a
 * single broken screen never blanks the whole app. The stack trace is logged
 * to the console only — never surfaced in the UI. */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, info: { componentStack?: string | null }): void {
    // Devtools is the right place for the stack; the UI never shows it.
    console.error('[ErrorBoundary]', error, info.componentStack ?? '')
  }

  reset = (): void => {
    this.setState({ error: null })
  }

  render(): ReactNode {
    if (this.state.error) {
      return this.props.fallback(this.state.error, this.reset)
    }
    return this.props.children
  }
}
