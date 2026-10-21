import { createBrief, toggleInterest, togglePace, toggleTransport, type Brief, type Interest, type Pace, type Transport } from "./editor";

export type Profile = { display_name: string; initials: string; currency: string; interests: Interest[]; pace: Pace | null; transport: Transport[]; notes: string };

/** Only the explicit new-brief initializer calls this; confirmed requests stay independent. */
export function briefFromProfile(profile: Profile): Brief {
  let brief = { ...createBrief(), currency: profile.currency, preferences: profile.notes };
  for (const interest of profile.interests) brief = toggleInterest(brief, interest);
  if (profile.pace) brief = togglePace(brief, profile.pace);
  for (const transport of profile.transport) brief = toggleTransport(brief, transport);
  return brief;
}
