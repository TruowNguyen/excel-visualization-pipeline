export async function onRequest({ request, env }) {
  if (!env.BACKEND_URL) {
    return new Response('Chưa cấu hình BACKEND_URL', { status: 503 });
  }

  let target;
  try {
    const backendUrl = String(env.BACKEND_URL).trim().replace(/^(["'`])(.*)\1$/s, '$2').trim();
    target = new URL(backendUrl);
    if (target.protocol !== 'https:' || target.username || target.password) {
      throw new Error('Invalid backend URL');
    }
  } catch {
    return new Response('BACKEND_URL phải là URL HTTPS hợp lệ', { status: 503 });
  }

  const incoming = new URL(request.url);
  target.pathname = incoming.pathname;
  target.search = incoming.search;

  try {
    const upstream = new Request(target.toString(), request);
    upstream.headers.delete('host');
    const response = await fetch(upstream, { redirect: 'manual' });
    const headers = new Headers(response.headers);
    headers.set('Cache-Control', 'no-store');

    const location = headers.get('location');
    if (location) {
      const redirect = new URL(location, target);
      if (redirect.origin === target.origin) {
        headers.set('location', `${incoming.origin}${redirect.pathname}${redirect.search}${redirect.hash}`);
      }
    }

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers,
    });
  } catch {
    return new Response('Không kết nối được backend demo', { status: 502 });
  }
}
