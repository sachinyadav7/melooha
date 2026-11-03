/** Reads complete server-sent events from a text buffer. Returns the events and the unfinished rest. */
export function parseSSE(buffer) {
  const events = [];
  let rest = buffer.replace(/\r\n/g, "\n");
  let end;
  while ((end = rest.indexOf("\n\n")) !== -1) {
    const block = rest.slice(0, end);
    rest = rest.slice(end + 2);
    let name = null;
    let data = null;
    for (const line of block.split("\n")) {
      if (line.startsWith("event: ")) name = line.slice(7);
      else if (line.startsWith("data: ")) {
        try {
          data = JSON.parse(line.slice(6));
        } catch {
          data = null;
        }
      }
    }
    if (name) events.push({ name, data });
  }
  return { events, rest };
}
