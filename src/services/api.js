export async function analyzeIdea(idea) {
  const res = await fetch(
    "http://localhost:8000/validate",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ idea }),
    }
  );

  if (!res.ok) {
    throw new Error("Failed to analyze idea");
  }

  return await res.json();
}
