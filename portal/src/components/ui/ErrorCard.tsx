// Error card with retry action (§10.3)
interface ErrorCardProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export default function ErrorCard({ title = 'Something went wrong', message, onRetry }: ErrorCardProps) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
      <p className="text-red-800 font-medium">{title}</p>
      {message && <p className="text-red-600 text-sm mt-1">{message}</p>}
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 px-4 py-2 text-sm font-medium text-red-700 bg-white border border-red-300 rounded-md hover:bg-red-50"
        >
          Try again
        </button>
      )}
    </div>
  );
}
