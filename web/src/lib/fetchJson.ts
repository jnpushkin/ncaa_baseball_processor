export async function fetchJsonWithRetry<T>(
  url: string,
  {
    attempts = 4,
    retryDelayMs = 750,
    timeoutMs = 9000,
  }: { attempts?: number; retryDelayMs?: number; timeoutMs?: number } = {}
): Promise<T> {
  let lastError: unknown;

  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, { signal: controller.signal });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return (await response.json()) as T;
    } catch (error) {
      lastError = error;
      if (attempt === attempts) break;
      await new Promise((resolve) => setTimeout(resolve, retryDelayMs * attempt));
    } finally {
      clearTimeout(timeoutId);
    }
  }

  throw lastError instanceof Error ? lastError : new Error("Failed to load JSON");
}
