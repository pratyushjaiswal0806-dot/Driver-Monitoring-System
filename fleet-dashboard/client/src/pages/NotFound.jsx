import { Link } from 'react-router-dom';

export default function NotFound() {
    return (
        <div className="flex min-h-[70vh] items-center justify-center px-4">
            <div className="dashboard-card w-full max-w-[400px] p-10 text-center md:p-[48px_40px]">
                <div className="font-display text-[5rem] font-extrabold leading-none text-transparent bg-[linear-gradient(135deg,#3b82f6,#8b5cf6)] bg-clip-text">404</div>
                <h2 className="mt-4 font-display text-[1.5rem] font-semibold text-white">Page not found</h2>
                <p className="mx-auto mt-4 max-w-lg text-[0.875rem] leading-6 text-white/40">
                    The route you requested does not exist or has been moved. Return to the fleet overview to continue monitoring.
                </p>
                <div className="mt-8 flex justify-center">
                    <Link to="/" className="inline-flex items-center justify-center rounded-xl bg-[linear-gradient(135deg,#3b82f6,#2563eb)] px-7 py-3 text-[0.875rem] font-semibold text-white shadow-[0_4px_16px_rgba(59,130,246,0.3)] transition hover:-translate-y-0.5 hover:brightness-110">
                        Back to Fleet
                    </Link>
                </div>
            </div>
        </div>
    );
}
