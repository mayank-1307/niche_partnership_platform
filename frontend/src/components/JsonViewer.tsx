import { Copy, Download } from "lucide-react";
import toast from "react-hot-toast";

import { formatCurrencyDisplay, isCurrencyKey, isTextFieldKey } from "../lib/format";

function sanitizeFilenamePart(value: string): string {
  return value
    .trim()
    .replace(/[<>:"/\\|?*]+/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-");
}

function formatDownloadTimestamp(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, "0");

  return [
    date.getFullYear(),
    pad(date.getMonth() + 1),
    pad(date.getDate()),
    pad(date.getHours()),
    pad(date.getMinutes()),
    pad(date.getSeconds())
  ].join("-");
}

function getDownloadFilename(companyName: string): string {
  const name = sanitizeFilenamePart(companyName) || "company";
  return `${name}-${formatDownloadTimestamp(new Date())}.json`;
}

export function JsonViewer({
  data,
  downloadUrl,
  companyName = ""
}: {
  data: Record<string, unknown> | null;
  downloadUrl: string | null;
  companyName?: string;
}) {
  const hasJsonData = Boolean(data && Object.keys(data).length > 0);
  const content = data ? JSON.stringify(data, null, 2) : "{}";

  const copy = async () => {
    if (!hasJsonData) return;

    await navigator.clipboard.writeText(content);
    toast.success("JSON copied");
  };

  const download = async () => {
    if (!downloadUrl || !hasJsonData) return;

    try {
      const response = await fetch(downloadUrl);
      if (!response.ok) throw new Error("Download failed");

      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = getDownloadFilename(companyName);
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(objectUrl);
    } catch {
      toast.error("Unable to download JSON");
    }
  };

  const renderValue = (value: unknown, depth = 0, keyName = ""): JSX.Element => {
    if (Array.isArray(value)) {
      return (
        <div className="space-y-2">
          {value.length === 0 && <span className="text-slate-500">[]</span>}
          {value.map((item, index) => (
            <div key={`${depth}-${index}`} className="rounded-lg border border-white/10 bg-black/25 p-2">
              {renderValue(item, depth + 1, keyName)}
            </div>
          ))}
        </div>
      );
    }

    if (value && typeof value === "object") {
      const entries = Object.entries(value as Record<string, unknown>);
      return (
        <div className="space-y-2">
          {entries.length === 0 && <span className="text-slate-500">{"{}"}</span>}
          {entries.map(([key, val]) => (
            <div key={`${depth}-${key}`} className="rounded-lg border border-white/10 bg-black/25 p-3">
              <div className="mb-1 text-[11px] uppercase tracking-wide text-cyan/90">{key}</div>
              {renderValue(val, depth + 1, key)}
            </div>
          ))}
        </div>
      );
    }

    if (typeof value === "string") {
      if (isTextFieldKey(keyName)) {
        return <div className="break-words whitespace-pre-wrap text-slate-100">{value || <span className="text-slate-500">""</span>}</div>;
      }

      const formattedCurrency = formatCurrencyDisplay(value, keyName);
      if (formattedCurrency) {
        return <div className="break-words text-mint">{formattedCurrency}</div>;
      }

      return <div className="break-words text-slate-100">{value || <span className="text-slate-500">""</span>}</div>;
    }

    if (typeof value === "number") {
      if (isCurrencyKey(keyName)) {
        return <div className="text-mint">{formatCurrencyDisplay(value, keyName)}</div>;
      }

      return <div className="text-mint">{value}</div>;
    }

    if (typeof value === "boolean") {
      return <div className={value ? "text-mint" : "text-amber-300"}>{String(value)}</div>;
    }

    return <div className="text-slate-500">null</div>;
  };

  return (
    <div className="glass flex h-full min-h-0 flex-col overflow-hidden rounded-2xl">
      <div className="flex items-center justify-between px-5 pb-3 pt-5">
        <h3 className="text-sm text-cyan">Structured JSON</h3>
        <div className="flex gap-2">
          {data && (
            <button
              onClick={copy}
              disabled={!hasJsonData}
              className="rounded-lg border border-white/10 px-3 py-2 text-xs hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-transparent"
            >
              <Copy className="mr-1 inline h-3 w-3" /> Copy
            </button>
          )}
          {downloadUrl && hasJsonData ? (
            <button type="button" onClick={download} className="rounded-lg bg-mint/20 px-3 py-2 text-xs text-mint hover:bg-mint/30">
              <Download className="mr-1 inline h-3 w-3" /> Download
            </button>
          ) : (
            data && (
              <button
                type="button"
                disabled
                className="rounded-lg bg-mint/20 px-3 py-2 text-xs text-mint opacity-50 disabled:cursor-not-allowed"
              >
                <Download className="mr-1 inline h-3 w-3" /> Download
              </button>
            )
          )}
        </div>
      </div>
      <div className="min-h-0 flex-1 border-t border-white/10 bg-black/40 p-4 text-xs">
        <div className="max-h-[420px] overflow-auto">
          {renderValue(data ?? {})}
        </div>
      </div>
    </div>
  );
}
