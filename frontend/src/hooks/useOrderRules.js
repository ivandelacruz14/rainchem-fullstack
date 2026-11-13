import { useEffect, useState } from "react";
import client from "../api/client";

// The box and bulk limits from the server. Fetched once and shared by every screen.
const FALLBACK = { personalMaxBoxes: 10, basicMaxBoxes: 20, verifiedMaxBoxes: 200, reviewBoxes: 100 };
let cached = null;

export default function useOrderRules() {
  const [rules, setRules] = useState(cached || FALLBACK);

  useEffect(() => {
    if (cached) return;
    client.get("/api/orders/rules")
      .then((res) => { cached = res.data; setRules(res.data); })
      .catch(() => {});
  }, []);

  return rules;
}
