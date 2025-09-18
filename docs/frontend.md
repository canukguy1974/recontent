Part 1 — Add/modify FastAPI (API) for CORS and signed GET URLs Make these two changes in services/api.

Enable CORS (allow your web origins) Edit services/api/main.py to include CORSMiddleware:
from fastapi import FastAPI from fastapi.middleware.cors import CORSMiddleware from services.api.routers import health, uploads, jobs, stripe_webhooks from packages.common.logging import get_logger import os

app = FastAPI(title="recontent API") log = get_logger("api")

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.addmiddleware( CORSMiddleware, allow_origins=[o.strip() for o in allowed_origins], allow_credentials=True, allow_methods=[""], allowheaders=[""], )

app.include_router(health.router, tags=["system"]) app.include_router(uploads.router, prefix="/assets", tags=["assets"]) app.include_router(jobs.router, prefix="/jobs", tags=["jobs"]) app.include_router(stripe_webhooks.router, tags=["billing"])

Set ALLOWED_ORIGINS env var on Cloud Run to include your web URL(s), e.g. http://localhost:3000,https://recontent-web-xyz.a.run.app.

Add a signed GET URL endpoint so the UI can preview images from GCS Append this to services/api/routers/uploads.py:
@router.get("/view-url") def viewurl(gcs_uri: str): assert gcs_uri.startswith("gs://") , bucket_name, *path = gcs_uri.replace("gs://","").split("/") client = storage.Client() blob = client.bucket(bucket_name).blob("/".join(path)) url = blob.generate_signed_url(version="v4", expiration=600, method="GET") return {"url": url}

Part 2 — Create the Next.js app under apps/web In your repo, create these files.

apps/web/package.json { "name": "recontent-web", "private": true, "scripts": { "dev": "next dev -p 3000", "build": "next build", "start": "next start -p 3000", "lint": "next lint" }, "dependencies": { "next": "14.2.12", "react": "18.3.1", "react-dom": "18.3.1", "stripe": "16.8.0", "zod": "3.23.8" }, "devDependencies": { "@types/node": "20.12.12", "@types/react": "18.2.66", "typescript": "5.5.4", "eslint": "8.57.0", "eslint-config-next": "14.2.12" } }

apps/web/next.config.mjs /* @type {import('next').NextConfig} / const nextConfig = { reactStrictMode: true, experimental: { serverActions: { bodySizeLimit: '6mb' } } }; export default nextConfig;

apps/web/tsconfig.json { "compilerOptions": { "target": "ES2022", "lib": ["dom", "dom.iterable", "es2022"], "allowJs": false, "skipLibCheck": true, "strict": true, "forceConsistentCasingInFileNames": true, "noEmit": true, "esModuleInterop": true, "module": "esnext", "moduleResolution": "bundler", "resolveJsonModule": true, "isolatedModules": true, "jsx": "preserve", "incremental": true }, "include": ["next-env.d.ts", "/*.ts", "/*.tsx"] }

apps/web/.env.local.example NEXTPUBLIC_API_BASE_URL=http://localhost:8080 STRIPE_SECRET_KEY=sk_live_or_test NEXTPUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_or_test STRIPE_PRICE_SETUP=price_SETUPFEE_ID STRIPE_PRICE_BASIC=price_BASIC_ID STRIPE_PRICE_PRO=price_PRO_ID STRIPE_PRICE_PREMIUM=price_PREMIUM_ID CHECKOUT_SUCCESS_URL=http://localhost:3000/success CHECKOUT_CANCEL_URL=http://localhost:3000/cancel

apps/web/app/layout.tsx export const metadata = { title: "recontent", description: "AI content for real estate" }; export default function RootLayout({ children }: { children: React.ReactNode }) { return ( <body style={{ fontFamily: "system-ui", margin: 0 }}>{children} ); }

apps/web/app/page.tsx (Landing + pricing + Checkout buttons) "use client"; import { useState } from "react";

const plans = [ { id: "basic", name: "Basic", price: 99, posts: 2, priceEnv: "STRIPE_PRICE_BASIC" }, { id: "pro", name: "Pro", price: 199, posts: 3, priceEnv: "STRIPE_PRICE_PRO" }, { id: "premium", name: "Premium", price: 299, posts: 5, priceEnv: "STRIPE_PRICE_PREMIUM" }, ];

export default function Page() { const [loading, setLoading] = useState<string | null>(null);

const checkout = async (planId: string) => { setLoading(planId); const res = await fetch("/api/checkout", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ planId }), }); const { url, error } = await res.json(); setLoading(null); if (error) { alert(error); return; } window.location.href = url; };

return ( <div style={{ padding: 24, maxWidth: 960, margin: "0 auto" }}> 

recontent
 
Generate agent-in-scene composites, virtual staging, and social-ready posts.

 
Pricing
 <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}> {plans.map(p => ( <div key={p.id} style={{ border: "1px solid #ddd", borderRadius: 8, padding: 16 }}> 
{p.name}
 
${p.price}/mo — {p.posts} posts/week

 <button onClick={() => checkout(p.id)} disabled={loading=p.id}> {loading=p.id ? "Redirecting…" : "Subscribe"}   ))}  <div style={{ marginTop: 24 }}> Upload · Compose   ); }
apps/web/app/success/page.tsx export default function Success() { return ( <div style={{ padding: 24 }}> 

Thank you!
 
Your subscription is being finalized. You’ll receive access shortly.

 Back to home  ); }
apps/web/app/cancel/page.tsx export default function Cancel() { return ( <div style={{ padding: 24 }}> 

Checkout canceled
 Try again  ); }
apps/web/app/upload/page.tsx "use client"; import { useState } from "react";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL!;

async function getUploadUrl(orgId: number) { const res = await fetch(${apiBase}/assets/upload-url?org_id=${orgId}); return res.json() as Promise<{ url: string; gcs_uri: string }>; }

export default function Upload() { const [orgId, setOrgId] = useState<number>(1); const [file, setFile] = useState<File | null>(null); const [gcsUri, setGcsUri] = useState<string | null>(null); const [viewUrl, setViewUrl] = useState<string | null>(null); const [status, setStatus] = useState<string>("");

const upload = async () => { if (!file) return; setStatus("Requesting signed URL…"); const { url, gcs_uri } = await getUploadUrl(orgId); setStatus("Uploading to GCS…"); await fetch(url, { method: "PUT", headers: { "content-type": file.type || "image/jpeg" }, body: file }); setGcsUri(gcs_uri); const v = await fetch(${apiBase}/assets/view-url?gcs_uri=${encodeURIComponent(gcs_uri)}).then(r=>r.json()); setViewUrl(v.url); setStatus("Uploaded!"); };

return ( <div style={{ padding: 24 }}> <h1>Upload an image</h1> <label>Org ID: <input value={orgId} onChange={e=>setOrgId(parseInt(e.target.value||"1",10))} type="number"/></label> <div style={{ marginTop: 12 }}> <input type="file" accept="image/*" onChange={e=>setFile(e.target.files?.[0] || null)} /> </div> <button onClick={upload} disabled={!file} style={{ marginTop: 12 }}>Upload</button> <p>{status}</p> {viewUrl && <img src={viewUrl} alt="preview" style={{ maxWidth: 360, display: "block" }} />} {gcsUri && <p>GCS URI: {gcsUri}</p>} </div> ); }

apps/web/app/compose/page.tsx "use client"; import { useState } from "react";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL!;

export default function Compose() { const [orgId, setOrgId] = useState(1); const [userId, setUserId] = useState(1); const [agentUri, setAgentUri] = useState(""); const [roomUri, setRoomUri] = useState(""); const [brief, setBrief] = useState("Agent in living room, natural light.");

const [outputs, setOutputs] = useState<string[]>([]); const [status, setStatus] = useState("");

const compose = async () => { setStatus("Queuing job…"); const res = await fetch(${apiBase}/jobs/composite, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ org_id: orgId, user_id: userId, agent_gcs: agentUri, room_gcs: roomUri, brief }), }); if (!res.ok) { setStatus("Failed to queue"); return; } setStatus("Queued! Check worker logs or outputs below (if mocked)."); };

return ( <div style={{ padding: 24 }}> 

Compose (Agent in Scene)
 <div style={{ display: "grid", gap: 8, maxWidth: 720 }}> Org ID <input type="number" value={orgId} onChange={e=>setOrgId(parseInt(e.target.value,10))}/> User ID <input type="number" value={userId} onChange={e=>setUserId(parseInt(e.target.value,10))}/> Agent GCS URI <input value={agentUri} onChange={e=>setAgentUri(e.target.value)} placeholder="gs://recontent-raw/org_1/agent.jpg"/> Room GCS URI <input value={roomUri} onChange={e=>setRoomUri(e.target.value)} placeholder="gs://recontent-raw/org_1/room.jpg"/> Brief <input value={brief} onChange={e=>setBrief(e.target.value)} />  <button style={{ marginTop: 12 }} onClick={compose}>Run Composite 
{status}

 {outputs?.length > 0 && ( 
{outputs.map((u,i)=>
{u}
)}
 )} <p style={{ marginTop: 24 }}>Need to upload images first?
  ); }
apps/web/app/api/checkout/route.ts (Stripe Checkout Session) import { NextRequest, NextResponse } from "next/server"; import Stripe from "stripe";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY as string, { apiVersion: "2024-06-20" });

const prices: Record<string, string> = { basic: process.env.STRIPE_PRICE_BASIC as string, pro: process.env.STRIPE_PRICE_PRO as string, premium: process.env.STRIPE_PRICE_PREMIUM as string };

export async function POST(req: NextRequest) { try { const { planId } = await req.json(); if (!prices[planId]) return NextResponse.json({ error: "Unknown plan"}, { status: 400 });

text

const successUrl = process.env.CHECKOUT_SUCCESS_URL!;
const cancelUrl = process.env.CHECKOUT_CANCEL_URL!;
const setupPrice = process.env.STRIPE_PRICE_SETUP!;

// Create a subscription checkout with a one-time setup fee line item
const session = await stripe.checkout.sessions.create({
  mode: "subscription",
  line_items: [
    { price: setupPrice, quantity: 1 },              // one-time setup fee
    { price: prices[planId], quantity: 1 }           // recurring subscription
  ],
  success_url: successUrl,
  cancel_url: cancelUrl,
  allow_promotion_codes: true,
  // You can add client_reference_id or metadata for plan mapping
  metadata: { planId }
});

return NextResponse.json({ url: session.url });
} catch (e: any) { console.error(e); return NextResponse.json({ error: e.message || "Stripe error" }, { status: 500 }); } }

Part 3 — Dockerfile and Cloud Build for web apps/web/Dockerfile

Build
FROM node:20-alpine AS builder WORKDIR /app COPY package.json package-lock.json pnpm-lock.yaml yarn.lock* ./ RUN if [ -f yarn.lock ]; then yarn --frozen-lockfile;
elif [ -f pnpm-lock.yaml ]; then corepack enable && pnpm i --frozen-lockfile;
else npm ci; fi COPY . . RUN npm run build

Run
FROM node:20-alpine WORKDIR /app ENV NODE_ENV=production COPY --from=builder /app ./ EXPOSE 3000 CMD ["npm","start"]

infra/cloudbuild/build-web.yaml steps:

name: gcr.io/cloud-builders/docker args: ["build","-t","gcr.io/_TAG","."] dir: "apps/web"
name: gcr.io/cloud-builders/docker args: ["push","gcr.io/_TAG"]
name: gcr.io/google.com/cloudsdktool/cloud-sdk args: [ "gcloud","run","deploy","recontent-web", "--image","gcr.io/_TAG", "--region","us-central1","--allow-unauthenticated", "--service-account","recontent-api-sa@(stripe_secret)", "NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=(price_setup)", "STRIPE_PRICE_BASIC=(price_pro)", "STRIPE_PRICE_PREMIUM=$(price_premium)", "CHECKOUT_SUCCESS_URL=https://REPLACE_WEB_URL/success", "CHECKOUT_CANCEL_URL=https://REPLACE_WEB_URL/cancel" ] availableSecrets: secretManager:
versionName: projects/$PROJECT_ID/secrets/stripe-secret/versions/latest env: "stripe_secret"
versionName: projects/$PROJECT_ID/secrets/stripe-pk/versions/latest env: "stripe_pk" substitutions: _TAG: "v1"
Part 4 — Stripe: what you need to set up In Stripe Dashboard:

Create Products/Prices:
Setup Fee (one-time) → copy price id to STRIPE_PRICE_SETUP
Basic (recurring monthly) → STRIPE_PRICE_BASIC
Pro (recurring monthly) → STRIPE_PRICE_PRO
Premium (recurring monthly) → STRIPE_PRICE_PREMIUM
Get API keys:
STRIPE_SECRET_KEY (secret)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY (publishable)
Webhook (recommended): point to your API’s Stripe webhook endpoint
URL: https://YOUR_API_URL/webhooks/stripe
Events: checkout.session.completed, customer.subscription.updated, invoice.payment_failed
Copy signing secret into STRIPE_WEBHOOK_SECRET on the API service
In your API, complete the webhook handling to:
On checkout.session.completed: create org, map planId (from session.metadata.planId) to weekly_limit 2/3/5, set status=active, and invite the user by email if desired
On customer.subscription.updated: update plan/weekly_limit if changed
On invoice.payment_failed: set org status=suspended
Part 5 — Local dev instructions (UI + API + Worker)

API (FastAPI)
Add ALLOWED_ORIGINS=http://localhost:3000 to the API service env
make run-api
Worker
make run-worker
Web
cd apps/web
cp .env.local.example .env.local
Fill:
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080
STRIPE_SECRET_KEY + NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
STRIPEPRICE* IDs
CHECKOUT_SUCCESS_URL=http://localhost:3000/success
CHECKOUT_CANCEL_URL=http://localhost:3000/cancel
npm install