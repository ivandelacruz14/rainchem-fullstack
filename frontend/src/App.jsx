import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { AdminAuthProvider, useAdminAuth } from "./context/AdminAuthContext";
import { CartProvider } from "./context/CartContext";
import { ToastProvider } from "./context/ToastContext";
import { UIProvider } from "./context/UIContext";

import Layout from "./components/Layout";
import { ProtectedRoute, AdminProtectedRoute, PermissionRoute } from "./components/ProtectedRoute";

import Home from "./pages/Home";
import Shop from "./pages/Shop";
import FAQs from "./pages/FAQs";
import Services from "./pages/Services";
import ResetPassword from "./pages/ResetPassword";
import Checkout from "./pages/Checkout";
import OrderSuccess from "./pages/OrderSuccess";
import PaymentPage from "./pages/PaymentPage";
import PaymentResult from "./pages/PaymentResult";
import PaymentDemo from "./pages/PaymentDemo";
import Receipt from "./pages/Receipt";

import AccountLayout from "./pages/account/AccountLayout";
import AccountOverview from "./pages/account/AccountOverview";
import AccountOrders from "./pages/account/AccountOrders";
import AccountTrack from "./pages/account/AccountTrack";
import AccountAddress from "./pages/account/AccountAddress";
import AccountProfile from "./pages/account/AccountProfile";
import AccountSettings from "./pages/account/AccountSettings";
import AccountHelp from "./pages/account/AccountHelp";
import AccountServices from "./pages/account/AccountServices";

import AdminLogin from "./admin/AdminLogin";
import AdminLayout from "./admin/AdminLayout";
import Overview from "./admin/pages/Overview";
import Products from "./admin/pages/Products";
import Orders from "./admin/pages/Orders";
import Users from "./admin/pages/Users";
import Knowledge from "./admin/pages/Knowledge";
import ChatMonitor from "./admin/pages/ChatMonitor";
import AdminAccounts from "./admin/pages/AdminAccounts";
import Analytics from "./admin/pages/Analytics";
import PaymentSettings from "./admin/pages/PaymentSettings";
import AdminServices from "./admin/pages/AdminServices";
import AdminSales from "./admin/pages/AdminSales";
import ScopedOrders from "./admin/pages/ScopedOrders";

function OrdersRoute() {
  const { admin } = useAdminAuth();
  if (admin?.isHead) return <Orders />;
  return (
    <PermissionRoute permission="orders">
      <ScopedOrders />
    </PermissionRoute>
  );
}

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
                    <Route path="/shop" element={<Shop />} />
                    <Route path="/faqs" element={<FAQs />} />
                    <Route path="/services" element={<Services />} />
                    <Route path="/reset-password" element={<ResetPassword />} />
                    <Route path="/checkout" element={<ProtectedRoute><Checkout /></ProtectedRoute>} />
                    <Route path="/payment/:orderId" element={<ProtectedRoute><PaymentPage /></ProtectedRoute>} />
                    <Route path="/payment/result" element={<ProtectedRoute><PaymentResult /></ProtectedRoute>} />
                    <Route path="/payment/demo/:orderId" element={<ProtectedRoute><PaymentDemo /></ProtectedRoute>} />
                    <Route path="/order-success" element={<ProtectedRoute><OrderSuccess /></ProtectedRoute>} />
                    <Route path="/receipt/:orderId" element={<ProtectedRoute><Receipt /></ProtectedRoute>} />

                    <Route path="/account" element={<ProtectedRoute><AccountLayout /></ProtectedRoute>}>
                      <Route index element={<AccountOverview />} />
                      <Route path="orders" element={<AccountOrders />} />
                      <Route path="services" element={<AccountServices />} />
                      <Route path="track" element={<AccountTrack />} />
                      <Route path="address" element={<AccountAddress />} />
                      <Route path="profile" element={<AccountProfile />} />
                      <Route path="settings" element={<AccountSettings />} />
                      <Route path="help" element={<AccountHelp />} />
                    </Route>
                  </Route>

                  <Route path="/admin/login" element={<AdminLogin />} />
                  <Route path="/admin" element={<AdminProtectedRoute><AdminLayout /></AdminProtectedRoute>}>
                    <Route index element={<Overview />} />
                    <Route path="products" element={<PermissionRoute permission="products"><Products /></PermissionRoute>} />
                    <Route path="orders" element={<OrdersRoute />} />
                    <Route path="users" element={<PermissionRoute headOnly><Users /></PermissionRoute>} />
                    <Route path="knowledge" element={<PermissionRoute headOnly><Knowledge /></PermissionRoute>} />
                    <Route path="monitor" element={<PermissionRoute headOnly><ChatMonitor /></PermissionRoute>} />
                    <Route path="accounts" element={<PermissionRoute headOnly><AdminAccounts /></PermissionRoute>} />
                    <Route path="analytics" element={<PermissionRoute permission="analytics"><Analytics /></PermissionRoute>} />
                    <Route path="services" element={<PermissionRoute permission="services"><AdminServices /></PermissionRoute>} />
                    <Route path="sales" element={<PermissionRoute permission="products"><AdminSales /></PermissionRoute>} />
                    <Route path="payments" element={<PermissionRoute headOnly><PaymentSettings /></PermissionRoute>} />
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