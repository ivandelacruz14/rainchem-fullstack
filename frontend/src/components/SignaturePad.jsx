import { useEffect, useRef } from "react";

/** Draw a signature with a mouse, finger, or stylus. Reports a PNG data URL, or null when cleared. */
export default function SignaturePad({ onChange, height = 170 }) {
  const canvasRef = useRef(null);
  const drawing = useRef(false);
  const inked = useRef(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ratio = window.devicePixelRatio || 1;
    canvas.width = canvas.clientWidth * ratio;
    canvas.height = height * ratio;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.lineWidth = 2.2;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.strokeStyle = "#111111";
  }, [height]);

  function point(e) {
    const r = canvasRef.current.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }

  function start(e) {
    e.preventDefault();
    canvasRef.current.setPointerCapture(e.pointerId);
    drawing.current = true;
    const p = point(e);
    const ctx = canvasRef.current.getContext("2d");
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
  }

  function move(e) {
    if (!drawing.current) return;
    const p = point(e);
    const ctx = canvasRef.current.getContext("2d");
    ctx.lineTo(p.x, p.y);
    ctx.stroke();
    inked.current = true;
  }

  function end() {
    if (!drawing.current) return;
    drawing.current = false;
    onChange(inked.current ? canvasRef.current.toDataURL("image/png") : null);
  }

  function clear() {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.restore();
    inked.current = false;
    onChange(null);
  }

  return (
    <div className="sig-pad">
      <canvas ref={canvasRef} className="sig-canvas" style={{ height }}
        onPointerDown={start} onPointerMove={move} onPointerUp={end} onPointerLeave={end} onPointerCancel={end} />
      <div className="sig-foot">
        <span className="field-hint">Ask the customer to sign inside the box.</span>
        <button type="button" className="btn btn-outline btn-sm" onClick={clear}>Clear</button>
      </div>
    </div>
  );
}
