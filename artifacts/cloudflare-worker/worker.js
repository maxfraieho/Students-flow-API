export default {
  async fetch(request, env, ctx) {
    const corsHeaders = {
      "Access-Control-Allow-Origin": env.FRONTEND_URL,
      "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
      "Access-Control-Max-Age": "86400",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 200, headers: corsHeaders });
    }

    const authHeader = request.headers.get("Authorization");
    if (!authHeader || !authHeader.startsWith("Bearer ")) {
      return new Response(
        JSON.stringify({ error: "Unauthorized", detail: "Missing or malformed Authorization header" }),
        {
          status: 401,
          headers: { "Content-Type": "application/json", ...corsHeaders },
        }
      );
    }

    const providedToken = authHeader.split(" ")[1];
    if (!providedToken || providedToken !== env.OPERATOR_TOKEN) {
      return new Response(
        JSON.stringify({ error: "Unauthorized", detail: "Invalid token" }),
        {
          status: 401,
          headers: { "Content-Type": "application/json", ...corsHeaders },
        }
      );
    }

    const incomingUrl = new URL(request.url);
    const tunnelBase = new URL(env.TUNNEL_URL);

    incomingUrl.protocol = tunnelBase.protocol;
    incomingUrl.hostname = tunnelBase.hostname;
    incomingUrl.port = tunnelBase.port || "";

    const forwardHeaders = new Headers(request.headers);
    forwardHeaders.delete("Authorization");
    forwardHeaders.set("X-Forwarded-Host", new URL(request.url).hostname);

    const proxyRequest = new Request(incomingUrl.toString(), {
      method: request.method,
      headers: forwardHeaders,
      body: request.body,
      redirect: "follow",
    });

    try {
      const response = await fetch(proxyRequest);

      const newResponse = new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
      });

      Object.entries(corsHeaders).forEach(([key, value]) => {
        newResponse.headers.set(key, value);
      });

      return newResponse;
    } catch (err) {
      return new Response(
        JSON.stringify({
          error: "Bad Gateway",
          detail: "Could not reach the backend. The Raspberry Pi may be offline or the tunnel is down.",
          message: err.message,
        }),
        {
          status: 502,
          headers: { "Content-Type": "application/json", ...corsHeaders },
        }
      );
    }
  },
};
