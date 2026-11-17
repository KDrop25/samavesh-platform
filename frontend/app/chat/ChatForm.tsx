"use client";

import { useActionState } from "react";
import { askAssistant, type ChatState } from "./actions";

const initial: ChatState = { question: "" };

export default function ChatForm() {
  const [state, action, pending] = useActionState(askAssistant, initial);
  return (
    <div className="space-y-4">
      <form action={action} className="flex flex-col gap-2">
        <label htmlFor="message" className="font-medium">Ask the Samavesh assistant</label>
        <textarea id="message" name="message" rows={3} maxLength={2000} required className="rounded border p-2" />
        <button type="submit" disabled={pending} className="self-start rounded bg-black px-4 py-2 text-white disabled:opacity-50">
          {pending ? "Thinking..." : "Ask"}
        </button>
      </form>
      {state.error && <p role="alert" className="text-red-700">{state.error}</p>}
      {state.reply && (
        <div className="rounded border p-3">
          <p className="text-sm text-neutral-600">You: {state.question}</p>
          <p className="mt-2 whitespace-pre-wrap">{state.reply}</p>
        </div>
      )}
    </div>
  );
}
