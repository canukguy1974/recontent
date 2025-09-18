"use client";
import { useState } from "react";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL!;

async function getUploadUrl(orgId: number) {
  const res = await fetch(`${apiBase}/assets/upload-url?org_id=${orgId}&content_type=${encodeURIComponent("image/jpeg")}`);
  return (await res.json()) as Promise<{ url: string; gcs_uri: string }>;
}

export default function Upload() {
  const [orgId, setOrgId] = useState<number>(1);
  const [file, setFile] = useState<File | null>(null);
  const [gcsUri, setGcsUri] = useState<string | null>(null);
  const [viewUrl, setViewUrl] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("");

  const upload = async () => {
    if (!file) return;
    setStatus("Requesting signed URL…");
    const { url, gcs_uri } = await getUploadUrl(orgId);
    setStatus("Uploading to GCS…");
    await fetch(url, {
      method: "PUT",
      headers: { "content-type": file.type || "image/jpeg" },
      body: file,
    });
    setGcsUri(gcs_uri);
    const v = await fetch(`${apiBase}/assets/view-url?gcs_uri=${encodeURIComponent(gcs_uri)}`).then((r) => r.json());
    setViewUrl(v.url);
    setStatus("Uploaded!");
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold">Upload an image</h1>
      <label className="mt-3 block text-sm">
        Org ID:
        <input
          value={orgId}
          onChange={(e) => setOrgId(parseInt(e.target.value || "1", 10))}
          type="number"
          className="ml-2 w-24 rounded border px-2 py-1"
        />
      </label>
      <div className="mt-3">
        <input className="block" type="file" accept="image/*" onChange={(e) => setFile(e.target.files?.[0] || null)} />
      </div>
      <button
        onClick={upload}
        disabled={!file}
        className="mt-3 inline-flex items-center rounded-md bg-black px-3 py-1.5 text-sm text-white disabled:opacity-50"
      >
        Upload
      </button>
      <p className="mt-2 text-sm text-gray-700">{status}</p>
      {viewUrl && <img src={viewUrl} alt="preview" className="mt-3 max-w-sm" />}
      {gcsUri && <p className="mt-2 text-sm">GCS URI: {gcsUri}</p>}
    </div>
  );
}
