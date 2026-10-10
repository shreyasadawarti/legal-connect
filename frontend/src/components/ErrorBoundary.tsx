import { Component, type ErrorInfo, type ReactNode } from 'react'
import { AlertTriangle, RefreshCcw } from 'lucide-react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  handleReset = (): void => {
    this.setState({ hasError: false })
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-surface-50 px-4 dark:bg-surface-900">
          <AlertTriangle className="h-12 w-12 text-red-500" />
          <h1 className="mt-4 text-xl font-bold text-surface-900 dark:text-surface-50">
            Something went wrong
          </h1>
          <p className="mt-2 max-w-md text-center text-sm text-surface-600 dark:text-surface-300">
            An unexpected error occurred. Please try reloading the page.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <button
              onClick={() => window.location.reload()}
              className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
            >
              <RefreshCcw className="h-4 w-4" />
              Reload page
            </button>
            <button
              onClick={this.handleReset}
              className="inline-flex items-center gap-2 rounded-lg border border-surface-300 px-4 py-2 text-sm font-medium text-surface-600 hover:bg-surface-100 dark:border-surface-700 dark:text-surface-300 dark:hover:bg-surface-800"
            >
              Try again
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
