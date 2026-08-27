// Minimal SSE-over-fetch reader. EventSource can't send a POST body, so
// /api/analyze is consumed by reading the streaming response body directly
// and splitting on the standard "event: ...\ndata: ...\n\n" frame format.

export interface SseFrame {
  event: string;
  data: unknown;
}

export async function* readSse(response: Response): AsyncGenerator<SseFrame> {
  if (!response.body) return;
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const raw = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);

      let event = "message";
      let dataLine = "";
      for (const line of raw.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7).trim();
        else if (line.startsWith("data: ")) dataLine += line.slice(6);
      }
      if (dataLine) {
        try {
          yield { event, data: JSON.parse(dataLine) };
        } catch {
          // ignore malformed frame
        }
      }
      boundary = buffer.indexOf("\n\n");
    }
  }
}
