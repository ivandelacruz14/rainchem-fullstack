import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { AdminAuthProvider } from "./context/AdminAuthContext";
import { CartProvider } from "./context/CartContext";
import { ToastProvider } from "./context/ToastContext";
import { UIProvider } from "./context/UIContext";

import Layout from "./components/Layout";
import { ProtectedRoute, AdminProtectedRoute, AdminPermissionRoute } from "./components/ProtectedRoute";

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
import AdminServices from "./admin/pages/Services";
import DistributorOrders from "./admin/pages/DistributorOrders";
import { useAdminAuth } from "./context/AdminAuthContext";
import PaymentSettings from "./admin/pages/PaymentSettings";

function Guard({ permission, headOnly, children }) {
  return <AdminPermissionRoute permission={permission} headOnly={headOnly}>{children}</AdminPermissionRoute>;
}

function AdminHome() {
  const { admin } = useAdminAuth();
  if (admin.isHead) return <Overview />;
  const first = [
    ["manage_products", "products"], ["view_orders", "orders"],
    ["view_sales", "analytics"], ["manage_services", "services"],
  ].find(([permission]) => admin.permissions.includes(permission));
  return first
    ? <Navigate to={`/admin/${first[1]}`} replace />
    : <div className="alert alert-info">Your account has no permissions yet. Ask a Head Admin to grant access.</div>;
}

function AdminOrdersPage() {
  const { admin } = useAdminAuth();
  return admin.isHead ? <Orders /> : <DistributorOrders />;
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
                      <Route path="track" element={<AccountTrack />} />
                      <Route path="address" element={<AccountAddress />} />
                      <Route path="profile" element={<AccountProfile />} />
                      <Route path="settings" element={<AccountSettings />} />
                      <Route path="help" element={<AccountHelp />} />
                    </Route>
                  </Route>

                  <Route path="/admin/login" element={<AdminLogin />} />
                  <Route path="/admin" element={<AdminProtectedRoute><AdminLayout /></AdminProtectedRoute>}>
                    <Route index element={<AdminHome />} />
                    <Route path="products" element={<Guard permission="manage_products"><Products /></Guard>} />
                    <Route path="services" element={<Guard permission="manage_services"><AdminServices /></Guard>} />
                    <Route path="orders" element={<Guard permission="view_orders"><AdminOrdersPage /></Guard>} />
                    <Route path="users" element={<Guard headOnly><Users /></Guard>} />
                    <Route path="knowledge" element={<Guard headOnly><Knowledge /></Guard>} />
                    <Route path="monitor" element={<Guard headOnly><ChatMonitor /></Guard>} />
                    <Route path="accounts" element={<Guard headOnly><AdminAccounts /></Guard>} />
                    <Route path="analytics" element={<Guard permission="view_sales"><Analytics /></Guard>} />
                    <Route path="payments" element={<Guard headOnly><PaymentSettings /></Guard>} />
                    <Route path="*" element={<Navigate to="/admin" replace />} />
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