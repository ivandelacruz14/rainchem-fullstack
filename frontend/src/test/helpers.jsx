import { MemoryRouter } from "react-router-dom";
import { ToastProvider } from "../context/ToastContext";
import { ThemeProvider } from "../context/ThemeContext";
import { AuthProvider } from "../context/AuthContext";
import { CartProvider } from "../context/CartContext";
import { UIProvider } from "../context/UIContext";

export function Providers({ children, route = "/" }) {
  return (
    <MemoryRouter initialEntries={[route]}>
      <ToastProvider>
        <ThemeProvider>
          <AuthProvider>
            <UIProvider>
              <CartProvider>{children}</CartProvider>
            </UIProvider>
          </AuthProvider>
        </ThemeProvider>
      </ToastProvider>
    </MemoryRouter>
  );
}
