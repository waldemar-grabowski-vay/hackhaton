import { useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  type VehicleHarnessKey,
  HARNESS_IMAGES,
  HARNESS_LABELS,
  HARNESS_ORDER,
  CONNECTOR_HARNESS,
  vehicleConnectorLocations,
} from "@/connectorLocations";

const CONNECTOR_ZOOM = 4;
const DRAG_THRESHOLD = 4;

export interface VehicleFocusTarget {
  connectorId: string;
}

interface HarnessDiagramProps {
  focusTarget?: VehicleFocusTarget;
}

export function HarnessDiagram({ focusTarget }: HarnessDiagramProps) {
  const [activeHarness, setActiveHarness] = useState<VehicleHarnessKey>("board");
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const [zoom, setZoom] = useState(1);
  const [dragging, setDragging] = useState(false);

  const zoomRef = useRef(zoom);
  zoomRef.current = zoom;

  const pendingConnectorScroll = useRef(false);
  const dragOrigin = useRef({ x: 0, y: 0, scrollLeft: 0, scrollTop: 0 });
  const hasDragged = useRef(false);

  const focusLocation = focusTarget
    ? vehicleConnectorLocations[activeHarness]?.[focusTarget.connectorId]
    : undefined;

  function zoomAroundPoint(fx: number, fy: number, factor: number) {
    const container = containerRef.current;
    const img = imgRef.current;
    if (!container || !img) return;
    const curW = img.offsetWidth;
    const curH = img.offsetHeight;
    setZoom((z) => {
      const next = factor > 1
        ? Math.min(+(z * factor).toFixed(2), 12)
        : Math.max(+(z * factor).toFixed(2), 0.3);
      const scale = next / z;
      requestAnimationFrame(() => {
        container.scrollTo({
          left: Math.max(0, fx * curW * scale - container.clientWidth  / 2),
          top:  Math.max(0, fy * curH * scale - container.clientHeight / 2),
        });
      });
      return next;
    });
  }

  function zoomIn() {
    const container = containerRef.current;
    const img = imgRef.current;
    if (!container || !img) return;
    zoomAroundPoint(
      (container.scrollLeft + container.clientWidth  / 2) / img.offsetWidth,
      (container.scrollTop  + container.clientHeight / 2) / img.offsetHeight,
      1.5,
    );
  }
  function zoomOut() {
    const container = containerRef.current;
    const img = imgRef.current;
    if (!container || !img) return;
    zoomAroundPoint(
      (container.scrollLeft + container.clientWidth  / 2) / img.offsetWidth,
      (container.scrollTop  + container.clientHeight / 2) / img.offsetHeight,
      1 / 1.5,
    );
  }
  const zoomFit = () => {
    setZoom(1);
    containerRef.current?.scrollTo({ top: 0, left: 0, behavior: "smooth" });
  };

  function handleMouseDown(e: React.MouseEvent<HTMLDivElement>) {
    if (e.button !== 0) return;
    const container = containerRef.current;
    if (!container) return;
    hasDragged.current = false;
    dragOrigin.current = {
      x: e.clientX, y: e.clientY,
      scrollLeft: container.scrollLeft, scrollTop: container.scrollTop,
    };
    setDragging(true);
    e.preventDefault();
  }
  function handleMouseMove(e: React.MouseEvent<HTMLDivElement>) {
    if (!dragging) return;
    const container = containerRef.current;
    if (!container) return;
    const dx = e.clientX - dragOrigin.current.x;
    const dy = e.clientY - dragOrigin.current.y;
    if (Math.abs(dx) > DRAG_THRESHOLD || Math.abs(dy) > DRAG_THRESHOLD) hasDragged.current = true;
    container.scrollLeft = dragOrigin.current.scrollLeft - dx;
    container.scrollTop  = dragOrigin.current.scrollTop  - dy;
  }
  function handleMouseUp() { setDragging(false); }

  function handleImgClick(e: React.MouseEvent<HTMLImageElement>) {
    if (hasDragged.current) return;
    const img = imgRef.current;
    if (!img) return;
    const rect = img.getBoundingClientRect();
    zoomAroundPoint((e.clientX - rect.left) / rect.width, (e.clientY - rect.top) / rect.height, 2);
  }
  function handleImgContextMenu(e: React.MouseEvent<HTMLImageElement>) {
    e.preventDefault();
    if (hasDragged.current) return;
    const img = imgRef.current;
    if (!img) return;
    const rect = img.getBoundingClientRect();
    zoomAroundPoint((e.clientX - rect.left) / rect.width, (e.clientY - rect.top) / rect.height, 0.5);
  }

  // When focusTarget changes: switch to the correct harness tab then zoom in.
  useEffect(() => {
    if (!focusTarget) {
      setZoom(1);
      containerRef.current?.scrollTo({ top: 0, left: 0, behavior: "smooth" });
      return;
    }
    const targetHarness = CONNECTOR_HARNESS[focusTarget.connectorId];
    if (!targetHarness) return;

    if (targetHarness !== activeHarness) {
      setActiveHarness(targetHarness);
      pendingConnectorScroll.current = true;
      setZoom(CONNECTOR_ZOOM);
      return;
    }

    const loc = vehicleConnectorLocations[activeHarness]?.[focusTarget.connectorId];
    if (!loc) return;

    const container = containerRef.current;
    const img = imgRef.current;
    if (!container || !img) return;

    if (zoomRef.current === CONNECTOR_ZOOM) {
      container.scrollTo({
        left: Math.max(0, loc.fx * img.offsetWidth  - container.clientWidth  / 2),
        top:  Math.max(0, loc.fy * img.offsetHeight - container.clientHeight / 2),
        behavior: "smooth",
      });
    } else {
      pendingConnectorScroll.current = true;
      setZoom(CONNECTOR_ZOOM);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusTarget]);

  useLayoutEffect(() => {
    if (!pendingConnectorScroll.current || !focusTarget) return;
    pendingConnectorScroll.current = false;
    const container = containerRef.current;
    const img = imgRef.current;
    if (!container || !img) return;
    const loc = vehicleConnectorLocations[activeHarness]?.[focusTarget.connectorId];
    if (!loc) return;
    container.scrollTo({
      left: Math.max(0, loc.fx * img.offsetWidth  - container.clientWidth  / 2),
      top:  Math.max(0, loc.fy * img.offsetHeight - container.clientHeight / 2),
      behavior: "smooth",
    });
  }, [zoom, focusTarget, activeHarness]);

  function switchHarness(h: VehicleHarnessKey) {
    setActiveHarness(h);
    setZoom(1);
    containerRef.current?.scrollTo({ top: 0, left: 0 });
  }

  return (
    <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column" }}>
      <style>{`
        @keyframes hd-pulse {
          0%   { transform: translate(-50%, -50%) scale(1);   opacity: 0.9; }
          100% { transform: translate(-50%, -50%) scale(2.8); opacity: 0; }
        }
      `}</style>

      {/* Harness tabs */}
      <div style={{ flexShrink: 0, display: "flex", gap: 2, padding: "4px 8px", borderBottom: "1px solid hsl(var(--border) / 0.4)", background: "hsl(var(--muted) / 0.15)", overflowX: "auto" }}>
        {HARNESS_ORDER.map((h) => (
          <button
            key={h}
            type="button"
            onClick={() => switchHarness(h)}
            style={{
              flexShrink: 0,
              padding: "2px 10px",
              height: 26,
              borderRadius: 4,
              border: activeHarness === h
                ? "1px solid hsl(var(--primary) / 0.6)"
                : "1px solid hsl(var(--border) / 0.5)",
              background: activeHarness === h
                ? "hsl(var(--primary) / 0.12)"
                : "transparent",
              color: activeHarness === h
                ? "hsl(var(--primary))"
                : "hsl(var(--muted-foreground))",
              fontSize: 11,
              fontWeight: activeHarness === h ? 600 : 400,
              cursor: "pointer",
            }}
          >
            {HARNESS_LABELS[h]}
          </button>
        ))}
      </div>

      <div
        ref={containerRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        style={{
          flex: 1, minHeight: 0, overflow: "auto", background: "#f5f5f4",
          cursor: dragging ? "grabbing" : "grab",
          userSelect: "none", position: "relative",
        }}
      >
        <div style={{ position: "relative", width: `${Math.round(zoom * 100)}%` }}>
          <img
            key={activeHarness}
            ref={imgRef}
            src={HARNESS_IMAGES[activeHarness]}
            alt={`${HARNESS_LABELS[activeHarness]} harness diagram`}
            draggable={false}
            onClick={handleImgClick}
            onContextMenu={handleImgContextMenu}
            style={{
              display: "block", height: "auto", width: "100%", maxWidth: "none",
              cursor: dragging ? "grabbing" : "zoom-in",
            }}
          />

          {focusLocation && (
            <div style={{ position: "absolute", left: `${focusLocation.fx * 100}%`, top: `${focusLocation.fy * 100}%`, pointerEvents: "none" }}>
              <div style={{ position: "absolute", width: 40, height: 40, borderRadius: "50%", border: "2.5px solid #ef4444", animation: "hd-pulse 1.6s ease-out infinite" }} />
              <div style={{ position: "absolute", width: 32, height: 32, borderRadius: "50%", border: "3px solid #ef4444", background: "rgba(239,68,68,0.18)", transform: "translate(-50%, -50%)", boxShadow: "0 0 0 2px rgba(239,68,68,0.35)" }} />
              <div style={{ position: "absolute", width: 9, height: 9, borderRadius: "50%", background: "#ef4444", transform: "translate(-50%, -50%)" }} />
            </div>
          )}
        </div>
      </div>

      {/* Zoom bar */}
      <div style={{ flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", gap: 6, padding: "4px 10px", borderTop: "1px solid hsl(var(--border) / 0.4)", background: "hsl(var(--muted) / 0.15)" }}>
        <button type="button" onClick={zoomOut}
          style={{ width: 24, height: 24, borderRadius: 4, border: "1px solid hsl(var(--border) / 0.5)", background: "transparent", cursor: "pointer", fontSize: 16, lineHeight: 1 }}>−</button>
        <span style={{ fontSize: 11, minWidth: 44, textAlign: "center", color: "hsl(var(--muted-foreground))" }}>
          {Math.round(zoom * 100)}%
        </span>
        <button type="button" onClick={zoomIn}
          style={{ width: 24, height: 24, borderRadius: 4, border: "1px solid hsl(var(--border) / 0.5)", background: "transparent", cursor: "pointer", fontSize: 16, lineHeight: 1 }}>+</button>
        <button type="button" onClick={zoomFit}
          style={{ padding: "0 8px", height: 24, borderRadius: 4, border: "1px solid hsl(var(--border) / 0.5)", background: "transparent", cursor: "pointer", fontSize: 11, color: "hsl(var(--muted-foreground))" }}>
          Fit
        </button>
      </div>
    </div>
  );
}
