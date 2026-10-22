export interface Env {
  BACKEND: Fetcher;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // Forward path and search query to internal backend service over Cloudflare VPC
    const targetUrl = new URL(url.pathname + url.search, "http://127.0.0.1:8000");

    const response = await env.BACKEND.fetch(targetUrl.toString(), {
      method: request.method,
      headers: request.headers,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
    });

    const headers = new Headers(response.headers);

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: headers,
    });
  },
};
