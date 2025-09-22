"use client";
import { useState } from "react";


const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL!;


export default function Compose() {
  const [prompt, setPrompt] = useState("");
  const [status, setStatus] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("");
    setLoading(true);
    setResult(null);
    // TODO: Call backend API for NLP processing
    // Example placeholder
    setTimeout(() => {
      setResult({
        imageUrl: "https://placehold.co/600x400?text=Composed+Image",
        caption: "Open house Sat and Sun 1-4 at 500 Some Street",
        facts: [
          "Spacious living room with natural light",
          "Recently renovated kitchen with modern appliances"
        ],
        cta: "Contact us to schedule a tour!"
      });
      setLoading(false);
    }, 1200);
  };

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <h1 className="text-3xl font-bold mb-4">Compose Listing Content</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <textarea
          className="w-full min-h-[120px] rounded border px-3 py-2 text-base focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Describe what you want to create. E.g. 'use colin1 in listing address 500 some street/living room add colin1 to be standing in the room and furnish the empty room with modern contemporary furniture and add captions ...'"
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          required
        />
        <button
          type="submit"
          className="inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-white font-semibold hover:bg-blue-700 disabled:opacity-60"
          disabled={loading || !prompt.trim()}
        >
          {loading ? "Generating..." : "Generate"}
        </button>
      </form>
      {status && <p className="mt-2 text-sm text-gray-700">{status}</p>}
      {result && (
        <div className="mt-8 border rounded-lg p-4 bg-gray-50">
          <img src={result.imageUrl} alt="Composed" className="w-full max-w-md rounded shadow mb-4" />
          <div className="mb-2 text-lg font-semibold">Caption:</div>
          <div className="mb-4 text-gray-800">{result.caption}</div>
          <div className="mb-2 text-lg font-semibold">Engaging Facts:</div>
          <ul className="list-disc ml-6 mb-4 text-gray-800">
            {result.facts.map((fact: string, i: number) => <li key={i}>{fact}</li>)}
          </ul>
          <div className="mb-2 text-lg font-semibold">Call to Action:</div>
          <div className="text-blue-700 font-bold">{result.cta}</div>
        </div>
      )}
    </div>
  );
}
