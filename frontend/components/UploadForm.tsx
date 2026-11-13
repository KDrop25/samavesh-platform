import { API_PUBLIC_URL } from "@/lib/config";

/**
 * File upload as a plain multipart form posted straight to the API. It works without
 * JavaScript, and the file (up to 10 MB) never passes through the Next.js host. The API
 * validates it and redirects back to the page with ?uploaded=1 or ?upload_error=code.
 * `token` is a short-lived upload token the page requested for this user and record.
 */
export function UploadForm({ token, label, hint, submit }: { token: string; label: string; hint: string; submit: string }) {
  return (
    <form
      action={`${API_PUBLIC_URL}/files?token=${token}`}
      method="post"
      encType="multipart/form-data"
      className="mt-6 flex max-w-md flex-col gap-4"
    >
      <div>
        <label htmlFor="file" className="mb-1 block font-semibold">
          {label}
        </label>
        <p id="file-hint" className="mb-1 text-muted">
          {hint}
        </p>
        <input
          id="file"
          name="file"
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
          required
          aria-describedby="file-hint"
          className="input"
        />
      </div>
      <div>
        <button type="submit" className="btn">
          {submit}
        </button>
      </div>
    </form>
  );
}
