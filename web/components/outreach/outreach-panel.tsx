"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { api, CONTACT_STATUSES, type Contact, type ContactStatus } from "@/lib/api";
import { Working } from "@/components/working";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/**
 * Referrals convert far better than cold applications, so this sits next to the
 * resume rather than behind it.
 *
 * Nothing here scrapes LinkedIn — each row is a targeted search *you* open, plus
 * a draft grounded in your real accomplishments. The tool writes the query and
 * the opening line; you do the looking and the connecting.
 */
export function OutreachPanel({ jobId }: { jobId: number }) {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [busy, setBusy] = useState(false);
  const [openId, setOpenId] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      setContacts(await api.listContacts(jobId));
    } catch {
      /* backend not reachable */
    }
  }, [jobId]);

  useEffect(() => {
    load();
  }, [load]);

  async function generate() {
    setBusy(true);
    try {
      setContacts(await api.generateOutreach(jobId));
      toast.success("Outreach list ready");
    } catch (e) {
      toast.error(String(e));
    } finally {
      setBusy(false);
    }
  }

  function patch(id: number, changes: Partial<Contact>) {
    setContacts((prev) => prev.map((c) => (c.id === id ? { ...c, ...changes } : c)));
  }

  async function save(contact: Contact) {
    try {
      await api.updateContact(contact.id, {
        name: contact.name,
        profile_url: contact.profile_url,
        status: contact.status,
        notes: contact.notes,
        draft: contact.draft,
      });
      toast.success("Saved");
    } catch (e) {
      toast.error(String(e));
    }
  }

  return (
    <div className="rounded-lg border p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="font-medium">Who to reach out to</h2>
        <Button size="sm" variant="outline" onClick={generate} disabled={busy}>
          {busy ? "Preparing…" : contacts.length ? "Regenerate" : "Find people"}
        </Button>
      </div>

      {busy && <Working label="Drafting a message for each kind of contact" />}

      {contacts.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Builds a targeted search for each kind of person worth contacting —
          alumni, people in this role, engineering leaders, recruiters, founders —
          plus a short message grounded in your actual work.
        </p>
      )}

      <div className="space-y-2">
        {contacts.map((c) => (
          <div key={c.id} className="rounded-md border p-3 space-y-2">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium flex-1 truncate">{c.label}</span>
              <a
                href={c.search_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm underline underline-offset-4 whitespace-nowrap"
              >
                Search →
              </a>
              <Select
                value={c.status}
                onValueChange={(v) => {
                  const next = { ...c, status: v as ContactStatus };
                  patch(c.id, { status: v as ContactStatus });
                  save(next);
                }}
              >
                <SelectTrigger className="w-32" size="sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CONTACT_STATUSES.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <button
                onClick={() => setOpenId(openId === c.id ? null : c.id)}
                className="text-sm underline underline-offset-4 whitespace-nowrap"
              >
                {openId === c.id ? "Hide" : "Draft"}
              </button>
            </div>

            {openId === c.id && (
              <div className="space-y-2 pt-1">
                <Textarea
                  value={c.draft}
                  onChange={(e) => patch(c.id, { draft: e.target.value })}
                  rows={4}
                  placeholder="No draft yet — click Find people, or write your own."
                />
                <div className="grid grid-cols-2 gap-2">
                  <Input
                    value={c.name}
                    onChange={(e) => patch(c.id, { name: e.target.value })}
                    placeholder="Who did you find?"
                  />
                  <Input
                    value={c.profile_url}
                    onChange={(e) => patch(c.id, { profile_url: e.target.value })}
                    placeholder="Their profile URL"
                  />
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => navigator.clipboard.writeText(c.draft)}
                  >
                    Copy message
                  </Button>
                  <Button size="sm" onClick={() => save(c)}>
                    Save
                  </Button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
