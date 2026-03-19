export default {
  async fetch(request, env, ctx) {
    const corsHeaders = {
      "Access-Control-Allow-Origin": env.FRONTEND_URL || "*",
      "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
      "Access-Control-Max-Age": "86400",
    };

    // ── Preflight ──────────────────────────────────────────────────────────
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    // ── Auth ───────────────────────────────────────────────────────────────
    const authHeader = request.headers.get("Authorization");
    if (!authHeader || !authHeader.startsWith("Bearer ")) {
      return json401("Missing or malformed Authorization header", corsHeaders);
    }
    if (authHeader.split(" ")[1] !== env.OPERATOR_TOKEN) {
      return json401("Invalid token", corsHeaders);
    }

    // ── Build upstream URL ─────────────────────────────────────────────────
    const incomingUrl = new URL(request.url);
    const tunnelBase  = new URL(env.TUNNEL_URL);

    incomingUrl.protocol = tunnelBase.protocol;
    incomingUrl.hostname = tunnelBase.hostname;
    incomingUrl.port     = tunnelBase.port || "";

    // ── Forward headers (strip auth, add forwarding info) ─────────────────
    const forwardHeaders = new Headers(request.headers);
    forwardHeaders.delete("Authorization");
    forwardHeaders.set("X-Forwarded-Host", new URL(request.url).hostname);
    forwardHeaders.set("X-Forwarded-Proto", "https");

    // ── Proxy request ──────────────────────────────────────────────────────
    const hasBody = request.body !== null &&
                    !["GET", "HEAD"].includes(request.method);

    const proxyInit = {
      method:   request.method,
      headers:  forwardHeaders,
      redirect: "follow",
    };
    if (hasBody) {
      proxyInit.body   = request.body;
      proxyInit.duplex = "half";   // required for streaming request bodies
    }

    let upstream;
    try {
      upstream = await fetch(new Request(incomingUrl.toString(), proxyInit));
    } catch (err) {
      return new Response(
        JSON.stringify({
          error:  "Bad Gateway",
          detail: "Could not reach the backend. The Raspberry Pi may be offline or the tunnel is down.",
        }),
        { status: 502, headers: { "Content-Type": "application/json", ...corsHeaders } }
      );
    }

    // ── Build response — preserve ALL upstream headers, then add CORS ──────
    const responseHeaders = new Headers(upstream.headers);
    for (const [k, v] of Object.entries(corsHeaders)) {
      responseHeaders.set(k, v);
    }

    // SSE streams: ensure no buffering hint is preserved
    const isSSE = (upstream.headers.get("Content-Type") || "").includes("text/event-stream");
    if (isSSE) {
      responseHeaders.set("X-Accel-Buffering", "no");
      responseHeaders.set("Cache-Control", "no-cache");
    }

    return new Response(upstream.body, {
      status:     upstream.status,
      statusText: upstream.statusText,
      headers:    responseHeaders,
    });
  },
};

// ── Helpers ────────────────────────────────────────────────────────────────
function json401(detail, corsHeaders) {
  return new Response(
    JSON.stringify({ error: "Unauthorized", detail }),
    { status: 401, headers: { "Content-Type": "application/json", ...corsHeaders } }
  );
}
