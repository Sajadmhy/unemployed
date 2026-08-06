"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api, type Profile } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

const EMPTY: Profile = {
  name: "",
  email: "",
  phone: "",
  location: "",
  links: {},
  summary: "",
  education: "",
  college: "",
};

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile>(EMPTY);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .getProfile()
      .then((p) => setProfile({ ...EMPTY, ...p }))
      .catch(() => {});
  }, []);

  function set(patch: Partial<Profile>) {
    setProfile((p) => ({ ...p, ...patch }));
  }

  function setLink(key: string, value: string) {
    setProfile((p) => ({ ...p, links: { ...p.links, [key]: value } }));
  }

  async function save() {
    setSaving(true);
    try {
      await api.updateProfile(profile);
      toast.success("Profile saved");
    } catch (e) {
      toast.error(String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-semibold">Profile</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          This is the header of every generated resume. It is never
          AI-generated — only what you type here appears.
        </p>
      </div>

      <div className="rounded-lg border p-5 space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label>Full name</Label>
            <Input
              value={profile.name}
              onChange={(e) => set({ name: e.target.value })}
              placeholder="Ananya Sharma"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Email</Label>
            <Input
              value={profile.email}
              onChange={(e) => set({ email: e.target.value })}
              placeholder="you@example.com"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Phone</Label>
            <Input
              value={profile.phone}
              onChange={(e) => set({ phone: e.target.value })}
              placeholder="+91 ..."
            />
          </div>
          <div className="space-y-1.5">
            <Label>Location</Label>
            <Input
              value={profile.location}
              onChange={(e) => set({ location: e.target.value })}
              placeholder="Bengaluru, India"
            />
          </div>
          <div className="space-y-1.5">
            <Label>GitHub</Label>
            <Input
              value={profile.links?.github ?? ""}
              onChange={(e) => setLink("github", e.target.value)}
              placeholder="github.com/you"
            />
          </div>
          <div className="space-y-1.5">
            <Label>LinkedIn</Label>
            <Input
              value={profile.links?.linkedin ?? ""}
              onChange={(e) => setLink("linkedin", e.target.value)}
              placeholder="linkedin.com/in/you"
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <Label>Education</Label>
          <Textarea
            value={profile.education}
            onChange={(e) => set({ education: e.target.value })}
            rows={2}
            placeholder="B.Tech Computer Science, VIT Vellore, 2022-2026 | CGPA 8.6"
          />
        </div>

        <div className="space-y-1.5">
          <Label>College name only</Label>
          <Input
            value={profile.college}
            onChange={(e) => set({ college: e.target.value })}
            placeholder="VIT Vellore"
          />
          <p className="text-xs text-muted-foreground">
            Used to find alumni at each company — alumni replies convert far
            better than cold outreach.
          </p>
        </div>

        <Button onClick={save} disabled={saving}>
          {saving ? "Saving…" : "Save profile"}
        </Button>
      </div>
    </div>
  );
}
