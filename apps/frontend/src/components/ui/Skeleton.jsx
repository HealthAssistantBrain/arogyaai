export default function Skeleton({ height = 20, width = "100%", className = "" }) {
    return (
        <div
            className={`skeleton-loader ${className}`}
            style={{
                height,
                width,
                borderRadius: "8px",
                background: "linear-gradient(90deg, rgba(150, 150, 150, 0.1) 25%, rgba(150, 150, 150, 0.2) 50%, rgba(150, 150, 150, 0.1) 75%)",
                backgroundSize: "200% 100%",
                animation: "shimmer 1.5s infinite linear",
            }}
        />
    );
}

