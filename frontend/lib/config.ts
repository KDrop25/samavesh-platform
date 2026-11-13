/** Where the Next.js server reaches the FastAPI backend. */
export const API_URL = process.env.API_URL ?? "http://localhost:8210";

/** Where the browser reaches it. Only used for file upload forms and download redirects. */
export const API_PUBLIC_URL = process.env.API_PUBLIC_URL ?? API_URL;
