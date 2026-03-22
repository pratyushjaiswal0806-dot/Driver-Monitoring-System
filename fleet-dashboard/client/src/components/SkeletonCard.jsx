export default function SkeletonCard({ className = '' }) {
    return (
        <div className={`skeleton-card p-5 ${className}`}>
            <div className="space-y-4">
                <div className="h-[14px] w-28 rounded-full bg-white/6" />
                <div className="h-[32px] w-40 rounded-[10px] bg-white/6" />
                <div className="h-[10px] w-48 rounded-full bg-white/6" />
            </div>
            <div className="skeleton-shimmer" />
        </div>
    );
}
