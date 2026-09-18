import { Outlet } from "react-router-dom";
import Header from "./Header";
import Footer from "./Footer";
import CartDrawer from "./CartDrawer";
import ChatWidget from "./ChatWidget";
import AuthModal from "./AuthModal";

export default function Layout() {
  return (
    <>
      <Header />
      <Outlet />
      <Footer />
      <CartDrawer />
      <ChatWidget />
      <AuthModal />
    </>
  );
}
