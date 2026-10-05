import type { Metadata } from "next";
import { ProfileForm } from "@/components/profile-form";

export const metadata: Metadata = { robots: { index: false, follow: false } };

export default function ProfilePage() {
  return <ProfileForm />;
}
