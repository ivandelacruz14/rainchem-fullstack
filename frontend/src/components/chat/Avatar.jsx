import AuthImage from "./AuthImage";

function initials(name) {
  return (name || "?").split(" ").filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join("") || "?";
}

/** A customer's picture (loaded with the admin's login) or their initials. */
export default function Avatar({ user, photoPath, size = 40, online }) {
  return (
    <span className="avatar" style={{ width: size, height: size, fontSize: size * 0.38 }}>
      {user?.hasPhoto && photoPath ? <AuthImage src={photoPath} alt="" className="avatar-img" /> : initials(user?.name)}
      {online !== undefined && <span className={`presence ${online ? "on" : ""}`} title={online ? "Online" : "Offline"} aria-label={online ? "Online" : "Offline"} />}
    </span>
  );
}
