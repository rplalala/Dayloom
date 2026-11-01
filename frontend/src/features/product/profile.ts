import { createBrief, toggleInterest, togglePace, toggleTransport, type Brief, type Interest, type Pace, type Transport } from "./editor";

export type Profile = { display_name: string; initials: string; currency: string; interests: Interest[]; pace: Pace | null; transport: Transport[]; notes: string; can_delete_account?: boolean };

/** Initialize structured defaults only; legacy notes never become hidden Plan preferences. */
export function briefFromProfile(profile: Profile): Brief {
  let brief = { ...createBrief(), currency: profile.currency };
  for (const interest of profile.interests) brief = toggleInterest(brief, interest);
  if (profile.pace) brief = togglePace(brief, profile.pace);
  for (const transport of profile.transport) brief = toggleTransport(brief, transport);
  return brief;
}
