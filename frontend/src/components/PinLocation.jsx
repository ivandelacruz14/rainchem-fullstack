import { useState } from "react";

const mapLink = (lat, lng) => `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;

/** Lets the customer drop a pin where the item should be delivered, using the phone's location.
 *  The rider opens this pin in Maps, which is far more exact than a written address. */
export default function PinLocation({ lat, lng, onChange }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pinned = lat !== "" && lat !== null && lat !== undefined && lng !== "" && lng !== null && lng !== undefined;

  function pin() {
    if (!navigator.geolocation) {
      setError("This browser cannot share its location. Describe the place in the delivery instructions instead.");
      return;
    }
    setBusy(true);
    setError("");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setBusy(false);
        onChange(Number(pos.coords.latitude.toFixed(6)), Number(pos.coords.longitude.toFixed(6)));
      },
      (err) => {
        setBusy(false);
        setError(err.code === 1
          ? "Location is blocked. Allow location for this site in your browser settings, then try again."
          : "We could not get your location. Try again with a better signal.");
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 },
    );
  }

  return (
    <div className="pin-location">
      <strong>Delivery pin</strong>
      {pinned ? (
        <p className="pin-ok">
          Pinned. <a href={mapLink(lat, lng)} target="_blank" rel="noreferrer">Check it on the map</a>
        </p>
      ) : (
        <p className="field-hint">Stand at the delivery address and pin your location, so the rider can find it.</p>
      )}
      {error && <p className="field-error" role="alert">{error}</p>}
      <div className="pin-actions">
        <button type="button" className="btn btn-outline btn-sm" disabled={busy} onClick={pin}>
          {busy ? "Getting your location..." : pinned ? "Pin again" : "Pin my current location"}
        </button>
        {pinned && <button type="button" className="btn btn-outline btn-sm" onClick={() => onChange("", "")}>Remove pin</button>}
      </div>
    </div>
  );
}
