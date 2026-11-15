export default function UserAvatar({ user, size = 36 }) {
  const label = user?.name || user?.email || "";
  const sizeStyle = { width: size, height: size };

  if (user?.avatarPhoto) {
    return <img className="user-avatar" src={user.avatarPhoto} alt={label} style={sizeStyle} />;
  }
  const initial = label.trim().charAt(0).toUpperCase() || "?";
  return (
    <span className="user-avatar user-avatar-initial" style={{ ...sizeStyle, fontSize: Math.round(size * 0.46) }} aria-label={label}>
      {initial}
    </span>
  );
}