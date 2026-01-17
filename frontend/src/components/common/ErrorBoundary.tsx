import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
    children?: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    error?: Error;
}

/**
 * ErrorBoundary - Catch-all for component crashes.
 * Displays a fallback UI instead of crashing the entire app.
 */
class ErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false
    };

    public static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('Uncaught error:', error, errorInfo);
    }

    public render() {
        if (this.state.hasError) {
            if (this.props.fallback) return this.props.fallback;

            return (
                <div className="flex items-center justify-center h-full p-6 text-center">
                    <div className="max-w-md p-8 bg-red-50 dark:bg-red-900/10 rounded-2xl border border-red-200 dark:border-red-800 shadow-xl">
                        <h2 className="text-xl font-bold text-red-700 dark:text-red-400 mb-4">
                            Visualizer Crashed
                        </h2>
                        <p className="text-sm text-red-600 dark:text-red-300 mb-6">
                            We encountered an error while rendering this part of the diagram.
                            This usually happens with highly complex or circular schema data.
                        </p>
                        <button
                            onClick={() => this.setState({ hasError: false })}
                            className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors font-semibold"
                        >
                            Try Again
                        </button>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
