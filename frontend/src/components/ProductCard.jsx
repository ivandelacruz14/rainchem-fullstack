import ProductVisual from "./ProductVisual";
import { peso } from "../utils/format";
import { useAuth } from "../context/AuthContext";
import { useCart } from "../context/CartContext";
import { useToast } from "../context/ToastContext";
import { useUI } from "../context/UIContext";

export default function ProductCard({ product, onOpen }) {
  const { user } = useAuth();
  const { addItem } = useCart();
  const showToast = useToast();
  const { requireLogin } = useUI();

  function handleAddToCart(e) {
    e.stopPropagation();
    if (!user) {
      requireLogin("login", "Please log in to add items to your cart");
      return;
    }
    addItem(product, 1);
    showToast("Added to cart", "success");
  }

  return (
    <div className="product-card">
      <div className="product-thumb" onClick={() => onOpen(product)}>
        {product.stock === 0 ? (
          <span className="stock-tag out">Out of Stock</span>
        ) : product.stock < 20 ? (
          <span className="stock-tag">Low Stock</span>
        ) : null}
        <ProductVisual product={product} widthPercent={56} />
      </div>
      <div className="product-info">
        <span className="product-cat">{product.category}</span>
        <span className="product-name" onClick={() => onOpen(product)}>{product.name}</span>
        <span className="product-rating">{"\u2605"} {product.rating} ({product.reviews})</span>
        <span className={`stock-count ${product.stock < 20 ? "low" : ""}`}>
          {product.stock > 0 ? `${product.stock} units available` : "Out of stock"}
        </span>
        <div className="product-bottom">
          <span className="product-price">{peso(product.price)}</span>
          {user ? (
            <button className="icon-add" title="Add to cart" onClick={handleAddToCart}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="9" cy="21" r="1" /><circle cx="19" cy="21" r="1" />
                <path d="M1 1h4l2.6 13.4a2 2 0 0 0 2 1.6h9.8a2 2 0 0 0 2-1.6L23 6H6" />
              </svg>
            </button>
          ) : (
            <button className="icon-add" title="Log in to buy" onClick={(e) => { e.stopPropagation(); requireLogin("login", "Please log in to buy this item"); }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="11" width="18" height="10" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
