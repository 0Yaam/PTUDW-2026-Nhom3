import { apiRequest } from "@/lib/api/client";

export type ContactInput = {
  fullName: string;
  email: string;
  message: string;
};

export type ContactReceipt = {
  id: string;
  status: "accepted";
};

export function submitContact(input: ContactInput): Promise<ContactReceipt> {
  return apiRequest<ContactReceipt>("/api/v1/contact", {
    method: "POST",
    body: JSON.stringify(input),
  });
}
