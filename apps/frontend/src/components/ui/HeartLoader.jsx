import { useEffect, useRef } from "react";

export default function HeartLoader({ size = 100, color = "#6143f4" }) {
    const svgRef = useRef(null);

    useEffect(() => {
        const svg = svgRef.current;
        if (!svg) return;

        let frameId;
        let start = performance.now();

        const animate = (time) => {
            const elapsed = time - start;
            const scale = 1 + 0.15 * Math.sin(elapsed * 0.005);
            svg.style.transform = `scale(${scale})`;
            frameId = requestAnimationFrame(animate);
        };

        frameId = requestAnimationFrame(animate);

        return () => cancelAnimationFrame(frameId);
    }, []);

    return (
        <div className="flex justify-center items-center loader-container">
            <svg
                ref={svgRef}
                viewBox="0 0 100 100"
                width={size}
                height={size}
                fill={color}
                className="transition-transform origin-center"
            >
                <path d="M50 88.54C50 88.54 13.96 61.32 13.96 34.02C13.96 17.5 26.54 12.27 34.42 12.27C44.3 12.27 50 19.98 50 19.98C50 19.98 55.7 12.27 65.58 12.27C73.46 12.27 86.04 17.5 86.04 34.02C86.04 61.32 50 88.54 50 88.54Z" />
            </svg>
        </div>
    );
}
