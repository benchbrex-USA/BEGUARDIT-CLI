// Skeleton loading placeholder (§10.3)
interface SkeletonProps {
  className?: string;
}

export default function Skeleton({ className = '' }: SkeletonProps) {
  return <div className={`animate-pulse bg-slate-200 rounded ${className}`} />;
}
