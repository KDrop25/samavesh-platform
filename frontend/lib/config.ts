/** Where the FastAPI backend lives. Server-side only; the browser never calls it for pages. */
export const API_URL = process.env.API_URL ?? "http://localhost:8210";
