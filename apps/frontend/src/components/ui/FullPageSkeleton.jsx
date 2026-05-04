/**
 * FullPageSkeleton — lightweight background shimmer used on the /auth/callback
 * loading state. Keeps the screen from appearing blank while the OAuth handshake
 * completes. No props required.
 */
export default function FullPageSkeleton() {
    return (
        <div className="full-page-skeleton">
            <div className="skeleton-header" />
            <div className="skeleton-card" />
            <div className="skeleton-card" />
            <div className="skeleton-card skeleton-card--short" />

            <style>{`
        .full-page-skeleton {
          position: fixed;
          inset: 0;
          padding: 48px 40px;
          z-index: 0;
          pointer-events: none;
        }

        @keyframes shimmer {
          0%   { background-position: -600px 0; }
          100% { background-position:  600px 0; }
        }

        .skeleton-header,
        .skeleton-card {
          border-radius: 14px;
          background: linear-gradient(
            90deg,
            rgba(200, 200, 220, 0.18) 25%,
            rgba(200, 200, 220, 0.32) 50%,
            rgba(200, 200, 220, 0.18) 75%
          );
          background-size: 1200px 100%;
          animation: shimmer 1.6s infinite linear;
        }

        .skeleton-header {
          height: 52px;
          margin-bottom: 24px;
          max-width: 320px;
        }

        .skeleton-card {
          height: 124px;
          margin-bottom: 20px;
          max-width: 640px;
        }

        .skeleton-card--short {
          height: 72px;
          max-width: 480px;
        }

        /* Darker skeleton for dark-mode pages */
        .dark .skeleton-header,
        .dark .skeleton-card {
          background: linear-gradient(
            90deg,
            rgba(255, 255, 255, 0.05) 25%,
            rgba(255, 255, 255, 0.10) 50%,
            rgba(255, 255, 255, 0.05) 75%
          );
          background-size: 1200px 100%;
        }
      `}</style>
        </div>
    );
}

