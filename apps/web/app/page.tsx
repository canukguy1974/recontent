"use client";
import { useState } from "react";

const plans = [
  { id: "basic", name: "Basic", price: 99, posts: 2, priceEnv: "STRIPE_PRICE_BASIC" },
  { id: "pro", name: "Pro", price: 199, posts: 3, priceEnv: "STRIPE_PRICE_PRO" },
  { id: "premium", name: "Premium", price: 299, posts: 5, priceEnv: "STRIPE_PRICE_PREMIUM" },
];

export default function Page() {
  const [loading, setLoading] = useState<string | null>(null);

  const checkout = async (planId: string) => {
    try {
      setLoading(planId);
      const res = await fetch("/api/checkout", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ planId }),
      });
      const { url, error } = (await res.json()) as { url?: string; error?: string };
      setLoading(null);
      if (error || !url) {
        alert(error || "Checkout failed");
        return;
      }
      window.location.href = url;
    } catch (e: any) {
      setLoading(null);
      alert(e?.message || "Checkout error");
    }
  };

  return (
    <div>
      <h1 className="text-3xl font-bold">recontent</h1>
      <p className="mt-2 text-gray-700">Generate agent-in-scene composites, virtual staging, and social-ready posts.</p>

      <h2 className="mt-8 text-2xl font-semibold">Pricing</h2>
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {plans.map((p) => (
          <div key={p.id} className="rounded-lg border border-gray-200 p-4">
            <h3 className="text-xl font-semibold">{p.name}</h3>
            <p className="mt-1 text-gray-700">${p.price}/mo — {p.posts} posts/week</p>
            <button
              onClick={() => checkout(p.id)}
              disabled={loading === p.id}
              className="mt-3 inline-flex items-center rounded-md bg-black px-3 py-1.5 text-sm text-white disabled:opacity-50"
            >
              {loading === p.id ? "Redirecting…" : "Subscribe"}
            </button>
          </div>
        ))}
      </div>

      <div className="mt-6 text-sm text-blue-700">
        <a className="underline" href="/upload">Upload</a>
        <span className="mx-1">·</span>
        <a className="underline" href="/compose">Compose</a>
      </div>
    </div>
  );
}
