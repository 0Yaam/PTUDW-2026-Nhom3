import type { Metadata } from "next";
import { PasswordSecurity } from "@/components/password-security";

export const metadata: Metadata = { robots: { index: false, follow: false } };

export default function ForgotPasswordPage() {
  return <PasswordSecurity mode="forgot" />;
}
