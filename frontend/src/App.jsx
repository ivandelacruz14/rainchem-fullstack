import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { AdminAuthProvider } from "./context/AdminAuthContext";
import { CartProvider } from "./context/CartContext";
import { ToastProvider } from "./context/ToastContext";
import { UIProvider } from "./context/UIContext";

import Layout from "./components/Layout";
import { ProtectedRoute, AdminProtectedRoute } from "./components/ProtectedRoute";

import Home from "./pages/Home";
import Checkout from "./pages/Checkout";
import OrderSuccess from "./pages/OrderSuccess";
import Receipt from "./pages/Receipt";
import ResetPassword from "./pages/ResetPassword";

import AccountLayout from "./pages/account/AccountLayout";
import AccountOverview from "./pages/account/AccountOverview";
import AccountOrders from "./pages/account/AccountOrders";
import AccountTrack from "./pages/account/AccountTrack";
import AccountAddress from "./pages/account/AccountAddress";
import AccountProfile from "./pages/account/AccountProfile";

import AdminLogin from "./admin/AdminLogin";
import AdminLayout from "./admin/AdminLayout";
import Overview from "./admin/pages/Overview";
import Products from "./admin/pages/Products";
import Orders from "./admin/pages/Orders";
import Users from "./admin/pages/Users";
import Knowledge from "./admin/pages/Knowledge";
import AiTester from "./admin/pages/AiTester";
import ChatMonitor from "./admin/pages/ChatMonitor";
import AdminAccounts from "./admin/pages/AdminAccounts";

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <AdminAuthProvider>
            <CartProvider>
              <UIProvider>
                <Routes>
                  <Route element={<Layout />}>
                    <Route path="/" element={<Home />} />
                    <Route path="/reset-password" element={<ResetPassword />} />
                    <Route path="/checkout" element={<ProtectedRoute><Checkout /></ProtectedRoute>} />
                    <Route path="/order-success" element={<ProtectedRoute><OrderSuccess /></ProtectedRoute>} />
                    <Route path="/receipt/:orderId" element={<ProtectedRoute><Receipt /></ProtectedRoute>} />

                    <Route path="/account" element={<ProtectedRoute><AccountLayout /></ProtectedRoute>}>
                      <Route index element={<AccountOverview />} />
                      <Route path="orders" element={<AccountOrders />} />
                      <Route path="track" element={<AccountTrack />} />
                      <Route path="address" element={<AccountAddress />} />
                      <Route path="profile" element={<AccountProfile />} />
                    </Route>
                  </Route>

                  <Route path="/admin/login" element={<AdminLogin />} />
                  <Route path="/admin" element={<AdminProtectedRoute><AdminLayout /></AdminProtectedRoute>}>
                    <Route index element={<Overview />} />
                    <Route path="products" element={<Products />} />
                    <Route path="orders" element={<Orders />} />
                    <Route path="users" element={<Users />} />
                    <Route path="knowledge" element={<Knowledge />} />
                    <Route path="tester" element={<AiTester />} />
                    <Route path="monitor" element={<ChatMonitor />} />
                    <Route path="accounts" element={<AdminAccounts />} />
                  </Route>
                </Routes>
              </UIProvider>
            </CartProvider>
          </AdminAuthProvider>
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  );
}
