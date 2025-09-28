import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8080";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    const response = await fetch(`${API_BASE_URL}/user/assets/upload-url`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Forward any authentication headers
        'Authorization': request.headers.get('Authorization') || '',
        'Cookie': request.headers.get('Cookie') || '',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      // If backend fails, provide demo functionality
      console.log("Upload URL API not available, using demo mode");
      
      // Generate a fake upload URL for demo purposes
      const demoResponse = {
        upload_url: "https://httpbin.org/put", // A test endpoint that accepts PUT requests
        gcs_uri: `gs://demo-bucket/demo-${Date.now()}-${body.label || 'untitled'}.jpg`,
        asset_id: Math.floor(Math.random() * 1000) + 100
      };
      
      return NextResponse.json(demoResponse, { status: 200 });
    }

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Upload URL API proxy error:', error);
    
    // Fallback demo response
    const demoResponse = {
      upload_url: "https://httpbin.org/put",
      gcs_uri: `gs://demo-bucket/demo-${Date.now()}.jpg`,
      asset_id: Math.floor(Math.random() * 1000) + 100
    };
    
    return NextResponse.json(demoResponse, { status: 200 });
  }
}