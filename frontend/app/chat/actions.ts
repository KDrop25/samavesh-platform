"use server";

import { api } from "@/lib/api";

export type ChatState = { question: string; reply?: string; error?: string };

/** Forwards one question to the backend assistant (Qwen via Ollama). Auth comes from the session cookie. */
export async function askAssistant(_: ChatState, form: FormData): Promise<ChatState> {
  const question = String(form.get("message") ?? "").trim();
  if (!question) return { question, error: "Type a question first." };
  const result = await api<{ reply: string }>("/chat", { method: "POST", body: { message: question } });
  if (!result.ok) return { question, error: "The assistant is unavailable right now." };
  return { question, reply: result.data.reply };
}
