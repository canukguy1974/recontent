"use client";
import { useState } from "react";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL!;

export default function Compose() {
  const [orgId, setOrgId] = useState(1);
  const [userId, setUserId] = useState(1);
  const [agentUri, setAgentUri] = useState("");
  const [roomUri, setRoomUri] = useState("");
  const [brief, setBrief] = useState("Agent in living room, natural light.");

  const [status, setStatus] = useState("");

  const compose = async () => {
    setStatus("Queuing job…");
    const res = await fetch(`${apiBase}/jobs/composite`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ org_id: orgId, user_id: userId, agent_gcs: agentUri, room_gcs: roomUri, brief }),
    });
    if (!res.ok) {
      setStatus("Failed to queue");
      return;
    }
    setStatus("Queued! Check worker logs or outputs below (if mocked).");
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold">Compose (Agent in Scene)</h1>
      <div className="mt-3 grid max-w-2xl gap-2">
        <label className="block text-sm"> 
          Org ID
          <input className="ml-2 w-24 rounded border px-2 py-1" type="number" value={orgId} onChange={(e) => setOrgId(parseInt(e.target.value, 10) || 1)} />
        </label>
        <label className="block text-sm">
          User ID
          <input className="ml-2 w-24 rounded border px-2 py-1" type="number" value={userId} onChange={(e) => setUserId(parseInt(e.target.value, 10) || 1)} />
        </label>
        <label className="block text-sm">
          Agent GCS URI
          <input className="mt-1 w-full rounded border px-2 py-1" value={agentUri} onChange={(e) => setAgentUri(e.target.value)} placeholder="gs://recontent-raw/org_1/agent.jpg" />
        </label>
        <label className="block text-sm">
          Room GCS URI
          <input className="mt-1 w-full rounded border px-2 py-1" value={roomUri} onChange={(e) => setRoomUri(e.target.value)} placeholder="gs://recontent-raw/org_1/room.jpg" />
        </label>
        <label className="block text-sm">
          Brief
          <input className="mt-1 w-full rounded border px-2 py-1" value={brief} onChange={(e) => setBrief(e.target.value)} />
        </label>
        <button className="mt-3 inline-flex items-center rounded-md bg-black px-3 py-1.5 text-sm text-white" onClick={compose}>Run Composite</button>
      </div>
      <p className="mt-2 text-sm text-gray-700">{status}</p>
      <p className="mt-6 text-sm">Need to upload images first? <a className="underline text-blue-700" href="/upload">Upload</a></p>
    </div>
  );
}
