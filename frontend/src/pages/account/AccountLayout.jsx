import { Outlet } from "react-router-dom";

// The account pages are opened from the account menu (top right), so this layout only holds the content.
export default function AccountLayout() {
  return (
    <div className="container account-page">
      <main className="account-main">
        <Outlet />
      </main>
    </div>
  );
}
