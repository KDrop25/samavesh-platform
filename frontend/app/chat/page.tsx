import { requireUser } from "@/lib/session";
import ChatForm from "./ChatForm";

export default async function ChatPage() {
  await requireUser();
  return (
    <main className="mx-auto max-w-2xl p-4">
      <h1 className="mb-4 text-2xl font-semibold">Assistant</h1>
      <ChatForm />
    </main>
  );
}
