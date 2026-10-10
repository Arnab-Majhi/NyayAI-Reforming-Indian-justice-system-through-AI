export type Theme = "light" | "dark" | "system";
export const STORAGE_KEY = "nyayaai-theme";
export const SYSTEM_QUERY = "(prefers-color-scheme: dark)";
export const validTheme = (value: string | null): Theme => value === "light" || value === "dark" ? value : "system";

// Fixed application code, never interpolated user input. Runs before first paint.
export const themeInitializationScript = `(()=>{let t="system";try{const s=localStorage.getItem("${STORAGE_KEY}");if(s==="light"||s==="dark")t=s}catch{}document.documentElement.dataset.theme=t==="system"?(matchMedia("${SYSTEM_QUERY}").matches?"dark":"light"):t})()`;