import { useEffect, useRef, useState } from "react";

/**
 * Camera scanning for the QR code or barcode on the printed receipt. Works where the browser supports
 * the BarcodeDetector API (Chrome on Android). Elsewhere, a barcode scanner or typing the code still works.
 */
export default function ScanConfirm({ onDetected, onClose }) {
  const videoRef = useRef(null);
  const [message, setMessage] = useState("Point the camera at the QR code or barcode.");

  useEffect(() => {
    if (!("BarcodeDetector" in window) || !navigator.mediaDevices?.getUserMedia) {
      setMessage("Camera scanning is not supported in this browser. Use a barcode scanner or type the code.");
      return undefined;
    }
    let stream = null;
    let timer = null;
    let stopped = false;
    const detector = new window.BarcodeDetector({ formats: ["qr_code", "code_128"] });
    navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } })
      .then((s) => {
        if (stopped) { s.getTracks().forEach((t) => t.stop()); return; }
        stream = s;
        videoRef.current.srcObject = s;
        videoRef.current.play().catch(() => {});
        timer = setInterval(async () => {
          try {
            const codes = await detector.detect(videoRef.current);
            if (codes.length && codes[0].rawValue) { stopped = true; onDetected(codes[0].rawValue); }
          } catch { /* keep trying */ }
        }, 300);
      })
      .catch(() => setMessage("The camera could not be opened. Allow camera access, or type the code."));
    return () => {
      stopped = true;
      if (timer) clearInterval(timer);
      if (stream) stream.getTracks().forEach((t) => t.stop());
    };
  }, [onDetected]);

  return (
    <div className="scan-box">
      <video ref={videoRef} className="scan-video" muted playsInline aria-label="Camera preview" />
      <p className="field-hint">{message}</p>
      <button type="button" className="btn btn-outline btn-sm" onClick={onClose}>Stop camera</button>
    </div>
  );
}
