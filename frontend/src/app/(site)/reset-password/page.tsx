import type { Metadata } from "next";
import { PasswordSecurity } from "@/components/password-security";

export const metadata: Metadata = { robots: { index: false, follow: false } };

export default async function ResetPasswordPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const { token = "" } = await searchParams;
  return <PasswordSecurity mode="reset" token={token} />;
}
