"use client";
import { useState } from "react";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8080";

async function getUploadUrl(orgId: number, mimeType: string) {
  const res = await fetch(
    `${apiBase}/assets/upload-url?org_id=${orgId}&content_type=${encodeURIComponent(mimeType || "image/jpeg")}`
  );
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`upload-url failed: ${res.status} ${res.statusText} ${text}`);
  }
  return (await res.json()) as { url: string; gcs_uri: string };
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
    try {
      const mime = file.type || "image/jpeg";
      const { url, gcs_uri } = await getUploadUrl(orgId, mime);
      setStatus("Uploading to GCS…");
      const putRes = await fetch(url, {
        method: "PUT",
        headers: { "Content-Type": mime },
        body: file,
      });
      if (!putRes.ok) {
        const text = await putRes.text().catch(() => "");
        throw new Error(`PUT failed: ${putRes.status} ${putRes.statusText} ${text}`);
      }
      setGcsUri(gcs_uri);
      const vRes = await fetch(
        `${apiBase}/assets/view-url?gcs_uri=${encodeURIComponent(gcs_uri)}`
      );
      if (!vRes.ok) {
        const text = await vRes.text().catch(() => "");
        throw new Error(`view-url failed: ${vRes.status} ${vRes.statusText} ${text}`);
      }
      const v = await vRes.json();
      setViewUrl(v.url);
      setStatus("Uploaded!");
    } catch (err: any) {
      setStatus(err?.message || String(err));
    }
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
