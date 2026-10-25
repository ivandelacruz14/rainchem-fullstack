import { useEffect, useState } from "react";
import client from "../api/client";

export default function useProductReviews(productId) {
  const [state, setState] = useState({ loading: true, error: false, data: null });

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true, error: false, data: null });
    client.get(`/api/products/${productId}/reviews`)
      .then((res) => { if (!cancelled) setState({ loading: false, error: false, data: res.data }); })
      .catch(() => { if (!cancelled) setState({ loading: false, error: true, data: null }); });
    return () => { cancelled = true; };
  }, [productId]);

  return state;
}
