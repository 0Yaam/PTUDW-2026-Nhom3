import type { Metadata } from "next";
import { PasswordSecurity } from "@/components/password-security";

export const metadata: Metadata = { robots: { index: false, follow: false } };

export default function ChangePasswordPage() {
  return <PasswordSecurity mode="change" />;
}
