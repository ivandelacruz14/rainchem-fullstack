import { Navigate } from "react-router-dom";
import { useAdminAuth } from "../context/AdminAuthContext";

/** Only accounts with the Rider role can open the delivery screen. Everyone else is sent back to the overview. */
export default function RiderRoute({ children }) {
  const { admin } = useAdminAuth();
  if (admin && admin.role !== "Rider") return <Navigate to="/admin" replace />;
  return children;
}
