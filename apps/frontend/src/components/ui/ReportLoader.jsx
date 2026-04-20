import React, { useEffect, useRef } from "react";

const ReportLoader = () => {
    const svgRef = useRef(null);

    useEffect(() => {
        const svg = svgRef.current;
        if (!svg) return;

        const group = svg.querySelector('#group');
        const path = svg.querySelector('#path');

        const config = {
            name: "Rose Curve",
            tag: "r = a cos(kθ)",
            rotate: true,
            particleCount: 78,
            trailSpan: 0.32,
            durationMs: 5400,
            rotationDurationMs: 28000,
            pulseDurationMs: 4600,
            strokeWidth: 4.5,
            roseA: 9.2,
            roseABoost: 0.6,
            roseBreathBase: 0.72,
            roseBreathBoost: 0.28,
            roseK: 5,
            roseScale: 3.25,
            point(progress, detailScale, config) {
                const t = progress * Math.PI * 2;
                const a = config.roseA + detailScale * config.roseABoost;
                const k = Math.round(config.roseK);
                const r = a * (config.roseBreathBase + detailScale * config.roseBreathBoost) * Math.cos(k * t);
                return {
                    x: 50 + Math.cos(t) * r * config.roseScale,
                    y: 50 + Math.sin(t) * r * config.roseScale,
                };
            }
        };

        path.setAttribute('stroke-width', String(config.strokeWidth));

        const SVG_NS = 'http://www.w3.org/2000/svg';

        // Clean up existing particles to prevent duplicate additions
        const existingParticles = group.querySelectorAll('circle');
        existingParticles.forEach(c => c.remove());

        const particles = Array.from({ length: config.particleCount }, () => {
            const circle = document.createElementNS(SVG_NS, 'circle');
            circle.setAttribute('fill', 'currentColor');
            group.appendChild(circle);
            return circle;
        });

        function normalizeProgress(progress) {
            return ((progress % 1) + 1) % 1;
        }

        function getDetailScale(time) {
            const pulseProgress = (time % config.pulseDurationMs) / config.pulseDurationMs;
            const pulseAngle = pulseProgress * Math.PI * 2;
            return 0.52 + ((Math.sin(pulseAngle + 0.55) + 1) / 2) * 0.48;
        }

        function getRotation(time) {
            if (!config.rotate) return 0;
            return -((time % config.rotationDurationMs) / config.rotationDurationMs) * 360;
        }

        function buildPath(detailScale, steps = 480) {
            return Array.from({ length: steps + 1 }, (_, index) => {
                const point = config.point(index / steps, detailScale, config);
                return `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`;
            }).join(' ');
        }

        function getParticle(index, progress, detailScale) {
            const tailOffset = index / (config.particleCount - 1);
            const point = config.point(normalizeProgress(progress - tailOffset * config.trailSpan), detailScale, config);
            const fade = Math.pow(1 - tailOffset, 0.56);
            return {
                x: point.x,
                y: point.y,
                radius: 0.9 + fade * 2.7,
                opacity: 0.04 + fade * 0.96,
            };
        }

        let animationFrameId;
        const startedAt = performance.now();

        function render(now) {
            const time = now - startedAt;
            const progress = (time % config.durationMs) / config.durationMs;
            const detailScale = getDetailScale(time);

            group.setAttribute('transform', `rotate(${getRotation(time)} 50 50)`);
            path.setAttribute('d', buildPath(detailScale));

            particles.forEach((node, index) => {
                const particle = getParticle(index, progress, detailScale);
                node.setAttribute('cx', particle.x.toFixed(2));
                node.setAttribute('cy', particle.y.toFixed(2));
                node.setAttribute('r', particle.radius.toFixed(2));
                node.setAttribute('opacity', particle.opacity.toFixed(3));
            });

            animationFrameId = requestAnimationFrame(render);
        }

        animationFrameId = requestAnimationFrame(render);

        return () => {
            cancelAnimationFrame(animationFrameId);
            particles.forEach(c => c.remove());
        };
    }, []);

    return (
        <div className="report-loader" style={{ width: '220px', height: '220px', margin: 'auto', color: '#6C5CE7' }}>
            <svg ref={svgRef} viewBox="0 0 100 100" fill="none" aria-hidden="true" style={{ width: '100%', height: '100%', overflow: 'visible' }}>
                <g id="group">
                    <path id="path" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" opacity="0.1"></path>
                </g>
            </svg>
        </div>
    );
};

export default React.memo(ReportLoader);
